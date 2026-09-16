# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Focused tests for the Repository Intelligence Work route."""

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


work = load_module(
    "repository_intelligence_work",
    ACTION_ROOT / "scripts/render_repository_intelligence_work.py",
)


def summary() -> dict[str, object]:
    return {
        "generated_at": "2026-08-25T14:00:00Z",
        "repository": {"name": "example/repository", "source_commit": SOURCE_COMMIT},
        "states": {"execution": {"failure": 0, "success": 1, "unknown": 0}},
    }


def ref(identifier: str, key: str, title: str, kind: str, state: str, url: str) -> dict[str, str]:
    return {
        "id": identifier,
        "key": key,
        "title": title,
        "kind": kind,
        "state": state,
        "canonical_url": url,
        "repository": "example/repository",
        "assertion": "authoritative",
        "confidence": "authoritative",
        "freshness": "current",
        "visibility": "public",
    }


class RepositoryIntelligenceWorkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.snapshot = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def populated(self) -> dict[str, object]:
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["views"]["work"] = {
            "open_issues": [
                ref("ri:example/repository:issue:44", "44", "Publish the visual roadmap", "issue", "open", "https://github.com/example/repository/issues/44")
            ],
            "open_pull_requests": [
                ref("ri:example/repository:pull-request:45", "45", "Build the visual roadmap", "pull_request", "open", "https://github.com/example/repository/pull/45")
            ],
            "roadmap_queues": {
                "active": [ref("ri:example/repository:roadmap-step:EX-Q02", "EX-Q02", "Wire the operational shell", "roadmap_step", "active", "https://github.com/example/repository/blob/1111111111111111111111111111111111111111/ROADMAP.md#ex-q02")],
                "ready": [ref("ri:example/repository:roadmap-step:EX-Q04", "EX-Q04", "Publish the visual roadmap", "roadmap_step", "ready", "https://github.com/example/repository/blob/1111111111111111111111111111111111111111/ROADMAP.md#ex-q04")],
                "waiting": [ref("ri:example/repository:roadmap-step:EX-Q05", "EX-Q05", "Wait for deployment proof", "roadmap_step", "planned", "https://github.com/example/repository/blob/1111111111111111111111111111111111111111/ROADMAP.md#ex-q05")],
                "blocked": [ref("ri:example/repository:roadmap-step:EX-Q06", "EX-Q06", "Blocked publication follow-up", "roadmap_step", "blocked", "https://github.com/example/repository/blob/1111111111111111111111111111111111111111/ROADMAP.md#ex-q06")],
                "unknown": [ref("ri:example/repository:roadmap-step:EX-Q07", "EX-Q07", "Unknown provider migration", "roadmap_step", "planned", "https://github.com/example/repository/blob/1111111111111111111111111111111111111111/ROADMAP.md#ex-q07")],
            },
        }
        return snapshot

    def test_populated_view_separates_execution_and_readiness(self) -> None:
        rendered = work.work_body(self.populated())
        self.assertIn("What work needs attention?", rendered)
        self.assertIn("Active roadmap work", rendered)
        self.assertIn("Blocked, waiting, and unknown", rendered)
        self.assertIn("Ready roadmap work", rendered)
        self.assertIn("Open GitHub work", rendered)
        self.assertIn('href="https://github.com/example/repository/issues/44"', rendered)
        self.assertIn('href="https://github.com/example/repository/pull/45"', rendered)
        self.assertIn('data-filter-readiness="blocked"', rendered)
        self.assertIn('data-filter-readiness="unknown"', rendered)

    def test_roadmap_records_deep_link_to_generated_and_canonical_views(self) -> None:
        rendered = work.work_body(self.populated())
        anchor = work.site.stable_fragment("quest", "ri:example/repository:roadmap-step:EX-Q04")
        self.assertIn(f'href="../roadmap/#{anchor}"', rendered)
        self.assertIn("Open canonical roadmap step", rendered)

    def test_shell_is_static_first_and_filterable(self) -> None:
        rendered = work.render_page(
            snapshot=self.populated(),
            summary=summary(),
            repository="example/repository",
            source_commit=SOURCE_COMMIT,
        )
        self.assertIn('data-ri-route="work"', rendered)
        self.assertIn('aria-current="page">Work</a>', rendered)
        self.assertIn('<select data-filter-extra="readiness">', rendered)
        self.assertIn('<main id="main-content" tabindex="-1">', rendered)
        self.assertLess(rendered.index("Active roadmap work"), rendered.index('src="../site.js" defer'))

    def test_empty_work_is_not_presented_as_unavailable(self) -> None:
        snapshot = self.populated()
        snapshot["views"]["work"] = {
            "open_issues": [],
            "open_pull_requests": [],
            "roadmap_queues": {name: [] for name in work.READINESS_QUEUES},
        }
        rendered = work.work_body(snapshot)
        self.assertIn("No work records projected", rendered)
        self.assertIn('data-state="not_applicable"', rendered)

    def test_missing_work_view_remains_explicitly_partial(self) -> None:
        snapshot = self.populated()
        del snapshot["views"]["work"]
        rendered = work.work_body(snapshot)
        self.assertIn("Work view not projected", rendered)
        self.assertIn("will not reconstruct work state", rendered)
        self.assertIn('data-state="partial"', rendered)

    def test_missing_snapshot_remains_explicitly_unavailable(self) -> None:
        rendered = work.work_body(None)
        self.assertIn("Work evidence unavailable", rendered)
        self.assertIn('data-state="partial"', rendered)

    def test_malformed_queue_fails_closed(self) -> None:
        snapshot = self.populated()
        snapshot["views"]["work"]["roadmap_queues"]["ready"][0]["kind"] = "issue"
        with self.assertRaisesRegex(work.WorkViewError, "must describe roadmap_step"):
            work.work_body(snapshot)

    def test_rendering_is_deterministic(self) -> None:
        first = work.render_page(snapshot=self.populated(), summary=summary(), repository="example/repository", source_commit=SOURCE_COMMIT)
        second = work.render_page(snapshot=self.populated(), summary=summary(), repository="example/repository", source_commit=SOURCE_COMMIT)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
