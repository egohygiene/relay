# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Focused tests for the Repository Intelligence Search route."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ACTION_ROOT = REPOSITORY_ROOT / "actions/repository-intelligence"
FIXTURE = REPOSITORY_ROOT / "tests/fixtures/repository-intelligence-site/snapshot.json"
SOURCE_COMMIT = "1" * 40


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


search = load_module(
    "repository_intelligence_search",
    ACTION_ROOT / "scripts/render_repository_intelligence_search.py",
)


def summary() -> dict[str, object]:
    return {
        "generated_at": "2026-08-25T14:00:00Z",
        "repository": {"name": "example/repository", "source_commit": SOURCE_COMMIT},
        "states": {"execution": {"failure": 0, "success": 1, "unknown": 0}},
    }


def record(
    identifier: str,
    key: str,
    title: str | None,
    kind: str,
    state: str,
    url: str,
    search_text: str,
    *,
    freshness: str = "current",
    assertion: str = "authoritative",
    repository: str = "example/repository",
) -> dict[str, str | None]:
    return {
        "id": identifier,
        "key": key,
        "title": title,
        "kind": kind,
        "repository": repository,
        "state": state,
        "assertion": assertion,
        "confidence": assertion,
        "freshness": freshness,
        "visibility": "public",
        "canonical_url": url,
        "search_text": search_text,
    }


class RepositoryIntelligenceSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.snapshot = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def populated(self) -> dict[str, object]:
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["views"]["search"] = {
            "records": [
                record(
                    "ri:example/repository:roadmap-step:EX-Q04",
                    "EX-Q04",
                    "Publish the visual roadmap",
                    "roadmap_step",
                    "ready",
                    "https://github.com/example/repository/blob/1111111111111111111111111111111111111111/ROADMAP.md#ex-q04",
                    "publish the visual roadmap ex-q04 roadmap_step ready example/repository",
                ),
                record(
                    "ri:example/repository:architecture-decision:ADR-009",
                    "ADR-009",
                    "Select the publication boundary",
                    "architecture_decision",
                    "accepted",
                    "https://github.com/example/repository/blob/1111111111111111111111111111111111111111/docs/decisions/ADR-009.md",
                    "select the publication boundary adr-009 architecture_decision accepted example/repository",
                    freshness="stale",
                ),
                record(
                    "ri:example/repository:pull-request:45",
                    "45",
                    "Build the visual roadmap",
                    "pull_request",
                    "open",
                    "https://github.com/example/repository/pull/45",
                    "build the visual roadmap 45 pull_request open example/repository",
                    freshness="unknown",
                    assertion="unknown",
                ),
                record(
                    "ri:example/repository:release:v1.2.0",
                    "v1.2.0",
                    "Repository Intelligence v1.2.0",
                    "release",
                    "published",
                    "https://github.com/example/repository/releases/tag/v1.2.0",
                    "repository intelligence v1.2.0 v1.2.0 release published example/repository",
                ),
            ]
        }
        return snapshot

    def test_populated_view_renders_normalized_entities_and_sources(self) -> None:
        rendered = search.search_body(self.populated())
        self.assertIn("Find a normalized repository object", rendered)
        self.assertIn("Searchable evidence", rendered)
        self.assertIn("4</strong><span>searchable records", rendered)
        self.assertIn("Publish the visual roadmap", rendered)
        self.assertIn("Select the publication boundary", rendered)
        self.assertIn("Repository Intelligence v1.2.0", rendered)
        self.assertIn('href="https://github.com/example/repository/pull/45"', rendered)
        self.assertIn("Stale", rendered)
        self.assertIn("Unknown", rendered)

    def test_renderer_uses_observatory_search_text_without_rebuilding_it(self) -> None:
        snapshot = self.populated()
        target = snapshot["views"]["search"]["records"][0]
        target["search_text"] = "observatory supplied token only"
        rendered = search.search_body(snapshot)
        self.assertIn('data-search="observatory supplied token only"', rendered)
        self.assertNotIn(
            'data-search="publish the visual roadmap ex-q04 roadmap_step ready example/repository"',
            rendered,
        )

    def test_projection_order_is_preserved_without_relevance_ranking(self) -> None:
        rendered = search.search_body(self.populated())
        results = rendered.index('aria-label="Normalized Repository Intelligence search records"')
        quest = rendered.index("Publish the visual roadmap", results)
        decision = rendered.index("Select the publication boundary", results)
        pull_request = rendered.index("Build the visual roadmap", results)
        release = rendered.index("Repository Intelligence v1.2.0", results)
        self.assertLess(quest, decision)
        self.assertLess(decision, pull_request)
        self.assertLess(pull_request, release)
        self.assertIn("does not rank by activity or inferred relevance", rendered)

    def test_shell_is_static_first_and_uses_shared_url_filters(self) -> None:
        rendered = search.render_page(
            snapshot=self.populated(),
            summary=summary(),
            repository="example/repository",
            source_commit=SOURCE_COMMIT,
        )
        self.assertIn('data-ri-route="search"', rendered)
        self.assertIn('aria-current="page">Search</a>', rendered)
        self.assertIn("data-filter-query", rendered)
        self.assertIn("data-filter-state", rendered)
        self.assertIn("data-filter-kind", rendered)
        self.assertIn('data-filter-extra="freshness"', rendered)
        self.assertIn('data-filter-freshness="stale"', rendered)
        self.assertIn('data-no-results hidden', rendered)
        self.assertLess(rendered.index("Searchable evidence"), rendered.index('src="../site.js" defer'))

    def test_empty_projection_is_not_presented_as_unavailable(self) -> None:
        snapshot = self.populated()
        snapshot["views"]["search"] = {"records": []}
        rendered = search.search_body(snapshot)
        self.assertIn("No searchable records projected", rendered)
        self.assertIn('data-state="not_applicable"', rendered)

    def test_missing_search_view_remains_explicitly_partial(self) -> None:
        snapshot = self.populated()
        del snapshot["views"]["search"]
        rendered = search.search_body(snapshot)
        self.assertIn("Search view not projected", rendered)
        self.assertIn("will not rebuild a search index", rendered)
        self.assertIn('data-state="partial"', rendered)

    def test_missing_snapshot_remains_explicitly_unavailable(self) -> None:
        rendered = search.search_body(None)
        self.assertIn("Search evidence unavailable", rendered)
        self.assertIn('data-state="partial"', rendered)

    def test_duplicate_record_ids_fail_closed(self) -> None:
        snapshot = self.populated()
        snapshot["views"]["search"]["records"].append(
            copy.deepcopy(snapshot["views"]["search"]["records"][0])
        )
        with self.assertRaisesRegex(search.SearchViewError, "record IDs must be unique"):
            search.search_body(snapshot)

    def test_missing_or_invalid_search_text_fails_closed(self) -> None:
        snapshot = self.populated()
        snapshot["views"]["search"]["records"][0]["search_text"] = ""
        with self.assertRaisesRegex(search.SearchViewError, "search_text must be a non-empty string"):
            search.search_body(snapshot)

    def test_unsafe_canonical_url_fails_closed(self) -> None:
        snapshot = self.populated()
        snapshot["views"]["search"]["records"][0]["canonical_url"] = "javascript:alert(1)"
        with self.assertRaisesRegex(search.SearchViewError, "credential-free HTTPS URL"):
            search.search_body(snapshot)

    def test_hostile_display_text_is_escaped(self) -> None:
        snapshot = self.populated()
        target = snapshot["views"]["search"]["records"][0]
        target["title"] = "<script>alert(1)</script>"
        target["search_text"] = 'unsafe " <token>'
        rendered = search.search_body(snapshot)
        self.assertNotIn("<script>alert(1)</script>", rendered)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", rendered)
        self.assertIn('data-search="unsafe &quot; &lt;token&gt;"', rendered)

    def test_rendering_is_deterministic(self) -> None:
        first = search.render_page(
            snapshot=self.populated(),
            summary=summary(),
            repository="example/repository",
            source_commit=SOURCE_COMMIT,
        )
        second = search.render_page(
            snapshot=self.populated(),
            summary=summary(),
            repository="example/repository",
            source_commit=SOURCE_COMMIT,
        )
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
