# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Focused tests for the Repository Intelligence Compare route."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ACTION_ROOT = REPOSITORY_ROOT / "actions/repository-intelligence"
ACTION_MANIFEST = ACTION_ROOT / "action.yml"
FIXTURE = REPOSITORY_ROOT / "tests/fixtures/repository-intelligence-site/snapshot.json"
SOURCE_COMMIT = "1" * 40
BEFORE_COMMIT = "0" * 40


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


compare = load_module(
    "repository_intelligence_compare",
    ACTION_ROOT / "scripts/render_repository_intelligence_compare.py",
)


def summary() -> dict[str, object]:
    return {
        "generated_at": "2026-08-25T14:00:00Z",
        "repository": {"name": "example/repository", "source_commit": SOURCE_COMMIT},
        "states": {"execution": {"failure": 0, "success": 1, "unknown": 0}},
    }


def search_record(
    identifier: str,
    key: str,
    title: str,
    kind: str,
    state: str,
    url: str,
) -> dict[str, str]:
    return {
        "id": identifier,
        "key": key,
        "title": title,
        "kind": kind,
        "repository": "example/repository",
        "state": state,
        "assertion": "authoritative",
        "confidence": "authoritative",
        "freshness": "current",
        "visibility": "public",
        "canonical_url": url,
        "search_text": f"{title} {key} {kind} {state} example/repository".lower(),
    }


def digest(character: str) -> str:
    return "sha256:" + character * 64


def view_records(*, changed: set[str] | None = None) -> list[dict[str, object]]:
    changed = changed or set()
    records = []
    for index, name in enumerate(compare.COMPARE_VIEW_NAMES):
        before = digest(format(index % 16, "x"))
        after = digest(format((index + 1) % 16, "x")) if name in changed else before
        records.append(
            {
                "view": name,
                "changed": name in changed,
                "before_digest": before,
                "after_digest": after,
            }
        )
    return records


def comparison_fixture(snapshot: dict[str, object]) -> dict[str, object]:
    return {
        "schema": compare.COMPARE_SCHEMA,
        "contract_version": compare.COMPARE_CONTRACT_VERSION,
        "repository": "example/repository",
        "before": {
            "snapshot_id": f"example/repository@{BEFORE_COMMIT}",
            "represented_commit": BEFORE_COMMIT,
            "observed_at": "2026-08-20T12:00:00Z",
        },
        "after": {
            "snapshot_id": snapshot["snapshot_id"],
            "represented_commit": SOURCE_COMMIT,
            "observed_at": snapshot["observed_at"],
        },
        "entities": {
            "added": ["ri:example/repository:pull-request:45"],
            "removed": ["ri:example/repository:issue:12"],
            "changed": [
                {
                    "id": "ri:example/repository:issue:44",
                    "fields": ["state.value", "title"],
                }
            ],
        },
        "relationships": {
            "added": ["relationship:quest-tracks-pr45"],
            "removed": ["relationship:old-dependency"],
            "changed": [
                {"id": "relationship:quest-depends-foundation", "fields": ["freshness"]}
            ],
        },
        "events": {
            "added": ["event:pr-merged"],
            "removed": ["event:old-check"],
            "changed": [{"id": "event:issue-opened", "fields": ["recorded_at"]}],
        },
        "views": view_records(changed={"roadmap", "work"}),
    }


class RepositoryIntelligenceCompareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base_snapshot = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def snapshot(self) -> dict[str, object]:
        snapshot = copy.deepcopy(self.base_snapshot)
        snapshot["views"]["search"] = {
            "records": [
                search_record(
                    "ri:example/repository:issue:44",
                    "44",
                    "Publish the visual roadmap",
                    "issue",
                    "closed",
                    "https://github.com/example/repository/issues/44",
                ),
                search_record(
                    "ri:example/repository:pull-request:45",
                    "45",
                    "Implement deterministic projection",
                    "pull_request",
                    "merged",
                    "https://github.com/example/repository/pull/45",
                ),
            ]
        }
        return snapshot

    def populated(self) -> tuple[dict[str, object], dict[str, object]]:
        snapshot = self.snapshot()
        return snapshot, comparison_fixture(snapshot)

    def test_populated_comparison_preserves_structural_categories(self) -> None:
        snapshot, comparison = self.populated()
        rendered = compare.comparison_body(
            comparison,
            snapshot=snapshot,
            repository="example/repository",
            source_commit=SOURCE_COMMIT,
        )
        self.assertIn("What structurally changed?", rendered)
        self.assertIn(BEFORE_COMMIT[:12], rendered)
        self.assertIn(SOURCE_COMMIT[:12], rendered)
        self.assertIn("Added entities", rendered)
        self.assertIn("Removed entities", rendered)
        self.assertIn("Changed field paths", rendered)
        self.assertIn("state.value", rendered)
        self.assertIn("relationship:old-dependency", rendered)
        self.assertIn("event:pr-merged", rendered)
        self.assertIn("Roadmap", rendered)
        self.assertIn("Changed", rendered)
        self.assertIn("Unchanged", rendered)
        self.assertIn('href="https://github.com/example/repository/pull/45"', rendered)
        self.assertIn('href="https://github.com/example/repository/issues/44"', rendered)
        self.assertNotIn("https://github.com/example/repository/issues/12", rendered)
        self.assertIn("does not claim which commit, person, decision, or event caused", rendered)

    def test_missing_comparison_is_explicitly_unavailable(self) -> None:
        rendered = compare.comparison_body(
            None,
            snapshot=self.snapshot(),
            repository="example/repository",
            source_commit=SOURCE_COMMIT,
        )
        self.assertIn("Comparison evidence unavailable", rendered)
        self.assertIn("will not reconstruct historical evidence", rendered)
        self.assertIn('data-state="partial"', rendered)

    def test_valid_zero_change_comparison_is_distinct_from_unavailable(self) -> None:
        snapshot, comparison = self.populated()
        for collection in ("entities", "relationships", "events"):
            comparison[collection] = {"added": [], "removed": [], "changed": []}
        comparison["views"] = view_records()
        rendered = compare.comparison_body(
            comparison,
            snapshot=snapshot,
            repository="example/repository",
            source_commit=SOURCE_COMMIT,
        )
        self.assertIn("No normalized structural differences", rendered)
        self.assertNotIn("Comparison evidence unavailable", rendered)

    def test_comparison_requires_matching_repository(self) -> None:
        snapshot, comparison = self.populated()
        comparison["repository"] = "example/other"
        with self.assertRaisesRegex(compare.CompareViewError, "repository must match"):
            compare.validate_comparison(
                comparison,
                repository="example/repository",
                source_commit=SOURCE_COMMIT,
                snapshot=snapshot,
            )

    def test_comparison_requires_matching_after_commit(self) -> None:
        snapshot, comparison = self.populated()
        comparison["after"]["represented_commit"] = "2" * 40
        with self.assertRaisesRegex(compare.CompareViewError, "after.represented_commit"):
            compare.validate_comparison(
                comparison,
                repository="example/repository",
                source_commit=SOURCE_COMMIT,
                snapshot=snapshot,
            )

    def test_comparison_requires_matching_after_snapshot(self) -> None:
        snapshot, comparison = self.populated()
        comparison["after"]["snapshot_id"] = "example/repository@different"
        with self.assertRaisesRegex(compare.CompareViewError, "after.snapshot_id"):
            compare.validate_comparison(
                comparison,
                repository="example/repository",
                source_commit=SOURCE_COMMIT,
                snapshot=snapshot,
            )

    def test_comparison_requires_current_after_snapshot(self) -> None:
        _, comparison = self.populated()
        with self.assertRaisesRegex(compare.CompareViewError, "requires the matching Observatory after snapshot"):
            compare.validate_comparison(
                comparison,
                repository="example/repository",
                source_commit=SOURCE_COMMIT,
                snapshot=None,
            )

    def test_delta_categories_must_be_disjoint(self) -> None:
        snapshot, comparison = self.populated()
        comparison["entities"]["removed"] = ["ri:example/repository:pull-request:45"]
        with self.assertRaisesRegex(compare.CompareViewError, "categories must be disjoint"):
            compare.validate_comparison(
                comparison,
                repository="example/repository",
                source_commit=SOURCE_COMMIT,
                snapshot=snapshot,
            )

    def test_changed_field_paths_must_be_nonempty_and_unique(self) -> None:
        snapshot, comparison = self.populated()
        comparison["entities"]["changed"][0]["fields"] = []
        with self.assertRaisesRegex(compare.CompareViewError, "non-empty array"):
            compare.validate_comparison(
                comparison,
                repository="example/repository",
                source_commit=SOURCE_COMMIT,
                snapshot=snapshot,
            )

    def test_view_changed_flag_must_match_digest_difference(self) -> None:
        snapshot, comparison = self.populated()
        comparison["views"][0]["changed"] = not comparison["views"][0]["changed"]
        with self.assertRaisesRegex(compare.CompareViewError, "contradicts"):
            compare.validate_comparison(
                comparison,
                repository="example/repository",
                source_commit=SOURCE_COMMIT,
                snapshot=snapshot,
            )

    def test_view_order_and_digest_shape_fail_closed(self) -> None:
        snapshot, comparison = self.populated()
        comparison["views"][0], comparison["views"][1] = comparison["views"][1], comparison["views"][0]
        with self.assertRaisesRegex(compare.CompareViewError, "canonical view order"):
            compare.validate_comparison(
                comparison,
                repository="example/repository",
                source_commit=SOURCE_COMMIT,
                snapshot=snapshot,
            )
        comparison = comparison_fixture(snapshot)
        comparison["views"][0]["before_digest"] = "sha256:not-a-digest"
        with self.assertRaisesRegex(compare.CompareViewError, "SHA-256"):
            compare.validate_comparison(
                comparison,
                repository="example/repository",
                source_commit=SOURCE_COMMIT,
                snapshot=snapshot,
            )

    def test_entity_delta_is_bound_to_after_search_snapshot(self) -> None:
        snapshot, comparison = self.populated()
        snapshot["views"]["search"]["records"] = snapshot["views"]["search"]["records"][:1]
        with self.assertRaisesRegex(compare.CompareViewError, "missing from the matching after snapshot"):
            compare.validate_comparison(
                comparison,
                repository="example/repository",
                source_commit=SOURCE_COMMIT,
                snapshot=snapshot,
            )
        snapshot, comparison = self.populated()
        snapshot["views"]["search"]["records"].append(
            search_record(
                "ri:example/repository:issue:12",
                "12",
                "Historical issue",
                "issue",
                "closed",
                "https://github.com/example/repository/issues/12",
            )
        )
        with self.assertRaisesRegex(compare.CompareViewError, "removed entities are still present"):
            compare.validate_comparison(
                comparison,
                repository="example/repository",
                source_commit=SOURCE_COMMIT,
                snapshot=snapshot,
            )

    def test_shell_is_static_first_and_preserves_compare_route(self) -> None:
        snapshot, comparison = self.populated()
        rendered = compare.render_page(
            comparison=comparison,
            snapshot=snapshot,
            summary=summary(),
            repository="example/repository",
            source_commit=SOURCE_COMMIT,
        )
        self.assertIn('data-ri-route="compare"', rendered)
        self.assertIn('aria-current="page">Compare</a>', rendered)
        self.assertIn('<main id="main-content" tabindex="-1">', rendered)
        self.assertLess(rendered.index("What structurally changed?"), rendered.index('src="../site.js" defer'))

    def test_rendering_is_deterministic(self) -> None:
        snapshot, comparison = self.populated()
        first = compare.render_page(
            comparison=comparison,
            snapshot=snapshot,
            summary=summary(),
            repository="example/repository",
            source_commit=SOURCE_COMMIT,
        )
        second = compare.render_page(
            comparison=copy.deepcopy(comparison),
            snapshot=copy.deepcopy(snapshot),
            summary=summary(),
            repository="example/repository",
            source_commit=SOURCE_COMMIT,
        )
        self.assertEqual(first, second)

    def test_action_exposes_explicit_comparison_input_and_renderer(self) -> None:
        manifest = ACTION_MANIFEST.read_text(encoding="utf-8")
        self.assertIn("observatory-comparison:", manifest)
        self.assertIn('INPUT_OBSERVATORY_COMPARISON: "${{ inputs.observatory-comparison }}"', manifest)
        self.assertIn("render_repository_intelligence_compare.py", manifest)
        self.assertIn('--comparison "${GITHUB_WORKSPACE}/${INPUT_OBSERVATORY_COMPARISON}"', manifest)


if __name__ == "__main__":
    unittest.main()
