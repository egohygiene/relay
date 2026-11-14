"""Regression controls for canonical event ordering across native sources."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "actions/repository-intelligence/scripts/prepare_repository_sources_build.py"
spec = importlib.util.spec_from_file_location("source_composition_order", SCRIPT)
composition = importlib.util.module_from_spec(spec)
spec.loader.exec_module(composition)


def projection(events):
    # Controlled fragments isolate the composition contract. Native acceptance
    # is separately exercised with real owner schemas and normalization.
    return {"schema": "fixture", "contract_version": "fixture", "projection_id": "fixture",
            "repository": "egohygiene/fixture", "represented_commit": "1" * 40,
            "visibility": "public", "observed_at": "2026-11-14T00:00:00Z",
            "generator": {"name": "fixture"}, "sources": [], "entities": [],
            "relationships": [], "events": events}


class SourceCompositionEventTests(unittest.TestCase):
    def compose(self, inputs):
        normalized = []

        def normalize(runtime, value):
            normalized.append(value)
            return {"normalized": True}, {"hygiene": "valid", "coverage": "valid", "observatory": "normalized"}

        result, snapshot = composition.compose(inputs, normalize, None, {})
        self.assertEqual([result], normalized)
        self.assertEqual({"normalized": True}, snapshot)
        return result

    def test_empty_second_inventory_preserves_existing_event_chronology(self) -> None:
        events = [{"id": "event:z", "occurred_at": "2026-11-13T01:00:00Z"},
                  {"id": "event:a", "occurred_at": "2026-11-13T02:00:00Z"}]
        inputs = [projection(events), projection([])]
        original = copy.deepcopy(inputs)
        result = self.compose(inputs)
        self.assertEqual(["event:z", "event:a"], [event["id"] for event in result["events"]])
        self.assertEqual(original, inputs)

    def test_two_inventories_merge_by_time_with_identity_ties(self) -> None:
        early = {"id": "event:z", "occurred_at": "2026-11-13T01:00:00Z"}
        late_a = {"id": "event:a", "occurred_at": "2026-11-13T02:00:00Z"}
        late_b = {"id": "event:b", "occurred_at": "2026-11-13T02:00:00Z"}
        result = self.compose([projection([late_b]), projection([early, late_a])])
        self.assertEqual(["event:z", "event:a", "event:b"], [event["id"] for event in result["events"]])

    def test_conflicting_event_identity_still_fails_before_normalization(self) -> None:
        left = projection([{"id": "event:a", "occurred_at": "2026-11-13T01:00:00Z"}])
        right = projection([{"id": "event:a", "occurred_at": "2026-11-13T02:00:00Z"}])

        def forbidden_normalization(*args):
            self.fail("conflicting events reached normalization")

        with self.assertRaisesRegex(ValueError, "conflicting-record"):
            composition.compose([left, right], forbidden_normalization, None, {})


if __name__ == "__main__":
    unittest.main()
