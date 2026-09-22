# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Focused tests for the Repository Intelligence Health route."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ACTION_ROOT = REPOSITORY_ROOT / "actions/repository-intelligence"
FIXTURE = REPOSITORY_ROOT / "tests/fixtures/repository-intelligence-health/snapshot.json"
SOURCE_COMMIT = "1" * 40


def load_module(name: str, path: Path):
    """Load one repository script without changing Python's import path."""

    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


health = load_module(
    "repository_intelligence_health",
    ACTION_ROOT / "scripts/render_repository_intelligence_health.py",
)


def summary() -> dict[str, object]:
    """Return the minimum shared-shell summary required by the renderer."""

    return {
        "generated_at": "2026-08-25T14:00:00Z",
        "repository": {"name": "example/repository", "source_commit": SOURCE_COMMIT},
        "states": {"execution": {"failure": 0, "success": 1, "unknown": 0}},
    }


class RepositoryIntelligenceHealthTests(unittest.TestCase):
    """Prove Health remains normalized, explicit, static-first, and score-free."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.snapshot = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def populated(self) -> dict[str, object]:
        return copy.deepcopy(self.snapshot)

    def test_populated_view_renders_check_posture_and_canonical_sources(self) -> None:
        rendered = health.health_body(self.populated())
        self.assertIn("What does the current evidence say?", rendered)
        self.assertIn(">3</strong><span>normalized checks", rendered)
        self.assertIn("Repository validation", rendered)
        self.assertIn("Contract validation", rendered)
        self.assertIn("Publication verification", rendered)
        self.assertIn('href="https://github.com/example/repository/actions/runs/101"', rendered)
        self.assertIn("Assertion distribution", rendered)
        self.assertIn("Freshness distribution", rendered)
        self.assertIn("Stale evidence IDs (1)", rendered)
        self.assertIn("Unknown evidence IDs (1)", rendered)
        self.assertIn("ri:example/repository:check:contracts-102", rendered)
        self.assertIn("ri:example/repository:check:publication-103", rendered)

    def test_null_score_contract_is_explained_without_manufacturing_a_grade(self) -> None:
        rendered = health.health_body(self.populated())
        self.assertIn("No roll-up score", rendered)
        self.assertIn("preserves evidence states instead of manufacturing a roll-up score", rendered)
        self.assertIn("score: null", rendered)
        self.assertNotIn("93%", rendered)
        self.assertNotIn("A+", rendered)
        self.assertIn("not complete Hygiene conformance", rendered)

    def test_full_parent_state_vocabulary_is_preserved_without_rollup(self) -> None:
        snapshot = self.populated()
        states = (
            "conformant",
            "non_conformant",
            "partial",
            "drifted",
            "stale",
            "unknown",
            "blocked",
            "not_applicable",
        )
        template = snapshot["views"]["health"]["checks"][0]
        checks = []
        for index, state in enumerate(states):
            check = copy.deepcopy(template)
            check["id"] = f"ri:example/repository:check:state-{index}"
            check["key"] = f"state-{index}"
            check["title"] = f"{health.site.state_label(state)} evidence"
            check["state"] = state
            checks.append(check)
        snapshot["views"]["health"]["checks"] = checks
        snapshot["views"]["health"]["check_states"] = {
            state: 1 for state in states
        }
        rendered = health.health_body(snapshot)
        for state in states:
            with self.subTest(state=state):
                self.assertIn(health.site.state_label(state), rendered)
        self.assertIn("No roll-up score", rendered)

    def test_shell_is_static_first_and_exposes_accessible_filter_hooks(self) -> None:
        rendered = health.render_page(
            snapshot=self.populated(),
            summary=summary(),
            repository="example/repository",
            source_commit=SOURCE_COMMIT,
        )
        self.assertIn('data-ri-route="health"', rendered)
        self.assertIn('href="../health/" aria-current="page">Health</a>', rendered)
        self.assertIn('<main id="main-content" tabindex="-1">', rendered)
        self.assertIn('data-filter-extra="check-state"', rendered)
        self.assertIn('data-filter-extra="freshness"', rendered)
        self.assertIn('data-filter-check-state="failure"', rendered)
        self.assertIn('data-filter-freshness="stale"', rendered)
        self.assertIn('aria-label="Normalized Repository Intelligence health checks"', rendered)
        self.assertIn('aria-live="polite"', rendered)
        self.assertLess(rendered.index("Repository validation"), rendered.index('src="../site.js" defer'))

    def test_empty_check_projection_is_not_presented_as_passing_or_unavailable(self) -> None:
        snapshot = self.populated()
        snapshot["views"]["health"]["checks"] = []
        snapshot["views"]["health"]["check_states"] = {}
        rendered = health.health_body(snapshot)
        self.assertIn("No check records projected", rendered)
        self.assertIn("Absence of check evidence is not a passing state", rendered)
        self.assertIn('data-state="not_applicable"', rendered)
        self.assertIn("Stale evidence IDs (1)", rendered)
        self.assertNotIn("Health evidence unavailable", rendered)

    def test_missing_health_view_remains_explicitly_partial(self) -> None:
        snapshot = self.populated()
        del snapshot["views"]["health"]
        rendered = health.health_body(snapshot)
        self.assertIn("Health view not projected", rendered)
        self.assertIn("will not rebuild health semantics", rendered)
        self.assertIn('data-state="partial"', rendered)

    def test_missing_snapshot_remains_explicitly_unavailable(self) -> None:
        rendered = health.health_body(None)
        self.assertIn("Health evidence unavailable", rendered)
        self.assertIn("Missing evidence is never treated as passing", rendered)
        self.assertIn('data-state="partial"', rendered)

    def test_stale_and_unknown_identifier_order_is_preserved(self) -> None:
        snapshot = self.populated()
        snapshot["views"]["health"]["freshness"]["stale"] = 2
        snapshot["views"]["health"]["stale_ids"] = ["stale:first", "stale:second"]
        snapshot["views"]["health"]["freshness"]["unknown"] = 2
        snapshot["views"]["health"]["unknown_ids"] = ["unknown:first", "unknown:second"]
        rendered = health.health_body(snapshot)
        self.assertLess(rendered.index("stale:first"), rendered.index("stale:second"))
        self.assertLess(rendered.index("unknown:first"), rendered.index("unknown:second"))

    def test_duplicate_check_ids_fail_closed(self) -> None:
        snapshot = self.populated()
        snapshot["views"]["health"]["checks"].append(
            copy.deepcopy(snapshot["views"]["health"]["checks"][0])
        )
        snapshot["views"]["health"]["check_states"]["success"] = 2
        with self.assertRaisesRegex(health.HealthViewError, "check IDs must be unique"):
            health.health_body(snapshot)

    def test_contradictory_check_state_counts_fail_closed(self) -> None:
        snapshot = self.populated()
        snapshot["views"]["health"]["check_states"]["success"] = 2
        with self.assertRaisesRegex(health.HealthViewError, "exactly describe projected checks"):
            health.health_body(snapshot)

    def test_stale_unknown_overlap_fails_closed(self) -> None:
        snapshot = self.populated()
        snapshot["views"]["health"]["unknown_ids"] = [
            "ri:example/repository:check:contracts-102"
        ]
        with self.assertRaisesRegex(health.HealthViewError, "must be disjoint"):
            health.health_body(snapshot)

    def test_freshness_distribution_must_match_exception_ids(self) -> None:
        snapshot = self.populated()
        snapshot["views"]["health"]["freshness"]["stale"] = 2
        with self.assertRaisesRegex(health.HealthViewError, "freshness.stale must match stale_ids"):
            health.health_body(snapshot)

    def test_non_null_score_fails_closed(self) -> None:
        snapshot = self.populated()
        snapshot["views"]["health"]["score"] = 0.93
        with self.assertRaisesRegex(health.HealthViewError, "score must be null"):
            health.health_body(snapshot)

    def test_invalid_distribution_fails_closed(self) -> None:
        snapshot = self.populated()
        snapshot["views"]["health"]["assertions"]["authoritative"] = -1
        with self.assertRaisesRegex(health.HealthViewError, "non-negative integer"):
            health.health_body(snapshot)

    def test_unsafe_canonical_check_url_fails_closed(self) -> None:
        snapshot = self.populated()
        snapshot["views"]["health"]["checks"][0]["canonical_url"] = "javascript:alert(1)"
        with self.assertRaisesRegex(health.HealthViewError, "credential-free HTTPS URL"):
            health.health_body(snapshot)

    def test_hostile_display_text_and_ids_are_escaped(self) -> None:
        snapshot = self.populated()
        snapshot["views"]["health"]["checks"][0]["title"] = "<script>alert(1)</script>"
        snapshot["views"]["health"]["freshness"]["stale"] = 1
        snapshot["views"]["health"]["stale_ids"] = ["<stale>"]
        rendered = health.health_body(snapshot)
        self.assertNotIn("<script>alert(1)</script>", rendered)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", rendered)
        self.assertIn("&lt;stale&gt;", rendered)

    def test_rendering_is_deterministic(self) -> None:
        first = health.render_page(
            snapshot=self.populated(),
            summary=summary(),
            repository="example/repository",
            source_commit=SOURCE_COMMIT,
        )
        second = health.render_page(
            snapshot=self.populated(),
            summary=summary(),
            repository="example/repository",
            source_commit=SOURCE_COMMIT,
        )
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
