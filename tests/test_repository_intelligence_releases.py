# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Focused tests for the Repository Intelligence Releases route."""

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


releases = load_module(
    "repository_intelligence_releases",
    ACTION_ROOT / "scripts/render_repository_intelligence_releases.py",
)


def summary() -> dict[str, object]:
    return {
        "generated_at": "2026-08-25T14:00:00Z",
        "repository": {"name": "example/repository", "source_commit": SOURCE_COMMIT},
        "states": {"execution": {"failure": 0, "success": 1, "unknown": 0}},
    }


def ref(
    identifier: str,
    key: str,
    title: str,
    kind: str,
    state: str,
    url: str,
    *,
    freshness: str = "current",
    assertion: str = "authoritative",
) -> dict[str, str]:
    return {
        "id": identifier,
        "key": key,
        "title": title,
        "kind": kind,
        "state": state,
        "canonical_url": url,
        "repository": "example/repository",
        "assertion": assertion,
        "confidence": assertion,
        "freshness": freshness,
        "visibility": "public",
    }


def release_record(
    version: str,
    published_at: str,
    *,
    freshness: str = "current",
    include_suffix: str = "45",
    deployment_suffix: str = "101",
) -> dict[str, object]:
    return {
        "entity": ref(
            f"ri:example/repository:release:{version}",
            version,
            f"Example {version}",
            "release",
            "published",
            f"https://github.com/example/repository/releases/tag/{version}",
            freshness=freshness,
        ),
        "published_at": published_at,
        "includes": [
            ref(
                f"ri:example/repository:pull-request:{include_suffix}",
                include_suffix,
                f"Ship release work {include_suffix}",
                "pull_request",
                "merged",
                f"https://github.com/example/repository/pull/{include_suffix}",
            ),
            ref(
                f"ri:example/repository:commit:{include_suffix * 2}",
                include_suffix * 2,
                f"Release commit {include_suffix}",
                "commit",
                "recorded",
                f"https://github.com/example/repository/commit/{include_suffix * 2}",
                freshness="not_applicable",
            ),
        ],
        "deployments": [
            ref(
                f"ri:example/repository:deployment:{deployment_suffix}",
                deployment_suffix,
                f"Production deployment {deployment_suffix}",
                "deployment",
                "success",
                f"https://github.com/example/repository/deployments/{deployment_suffix}",
            )
        ],
        "boundary_event_ids": [f"event:release-published:{version}"],
    }


class RepositoryIntelligenceReleasesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.snapshot = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def populated(self) -> dict[str, object]:
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["views"]["releases"] = {
            "releases": [
                release_record("v1.1.0", "2026-08-20T09:00:00Z", include_suffix="44", deployment_suffix="100"),
                release_record("v1.2.0", "2026-08-25T09:00:00Z"),
            ]
        }
        return snapshot

    def test_populated_view_separates_release_includes_and_deployments(self) -> None:
        rendered = releases.releases_body(self.populated())
        self.assertIn("What has actually shipped?", rendered)
        self.assertIn("Latest projected release", rendered)
        self.assertIn("Example v1.2.0", rendered)
        self.assertIn("Included evidence", rendered)
        self.assertIn("Deployment evidence", rendered)
        self.assertIn("Boundary evidence", rendered)
        self.assertIn('href="https://github.com/example/repository/releases/tag/v1.2.0"', rendered)
        self.assertIn('href="https://github.com/example/repository/pull/45"', rendered)
        self.assertIn('href="https://github.com/example/repository/deployments/101"', rendered)
        self.assertIn("event:release-published:v1.2.0", rendered)

    def test_latest_highlight_does_not_reorder_normalized_records(self) -> None:
        rendered = releases.releases_body(self.populated())
        self.assertLess(rendered.index("Example v1.1.0"), rendered.index("Example v1.2.0"))
        self.assertIn("Latest projected release:</strong> Example v1.2.0", rendered)
        self.assertIn("normalized record order is preserved", rendered)

    def test_release_and_deployment_state_are_not_conflated(self) -> None:
        snapshot = self.populated()
        release = snapshot["views"]["releases"]["releases"][1]
        release["deployments"][0]["state"] = "failure"
        rendered = releases.releases_body(snapshot)
        self.assertIn("Published", rendered)
        self.assertIn("Failure", rendered)
        self.assertIn("Release publication is not treated as deployment success", rendered)

    def test_stale_and_unknown_evidence_remain_visible(self) -> None:
        snapshot = self.populated()
        release = snapshot["views"]["releases"]["releases"][1]
        release["entity"]["freshness"] = "stale"
        release["deployments"][0]["freshness"] = "unknown"
        rendered = releases.releases_body(snapshot)
        self.assertIn("Stale", rendered)
        self.assertIn("Unknown", rendered)

    def test_shell_is_static_first_and_filterable(self) -> None:
        rendered = releases.render_page(
            snapshot=self.populated(),
            summary=summary(),
            repository="example/repository",
            source_commit=SOURCE_COMMIT,
        )
        self.assertIn('data-ri-route="releases"', rendered)
        self.assertIn('aria-current="page">Releases</a>', rendered)
        self.assertIn('data-kind="release"', rendered)
        self.assertIn('<main id="main-content" tabindex="-1">', rendered)
        self.assertLess(rendered.index("Projected release boundaries"), rendered.index('src="../site.js" defer'))

    def test_empty_releases_are_not_presented_as_unavailable(self) -> None:
        snapshot = self.populated()
        snapshot["views"]["releases"] = {"releases": []}
        rendered = releases.releases_body(snapshot)
        self.assertIn("No releases projected", rendered)
        self.assertIn('data-state="not_applicable"', rendered)

    def test_missing_releases_view_remains_explicitly_partial(self) -> None:
        snapshot = self.populated()
        del snapshot["views"]["releases"]
        rendered = releases.releases_body(snapshot)
        self.assertIn("Releases view not projected", rendered)
        self.assertIn("will not reconstruct release membership", rendered)
        self.assertIn('data-state="partial"', rendered)

    def test_missing_snapshot_remains_explicitly_unavailable(self) -> None:
        rendered = releases.releases_body(None)
        self.assertIn("Release evidence unavailable", rendered)
        self.assertIn('data-state="partial"', rendered)

    def test_malformed_deployment_kind_fails_closed(self) -> None:
        snapshot = self.populated()
        snapshot["views"]["releases"]["releases"][0]["deployments"][0]["kind"] = "release"
        with self.assertRaisesRegex(releases.ReleasesViewError, "must describe deployment"):
            releases.releases_body(snapshot)

    def test_invalid_publication_timestamp_fails_closed(self) -> None:
        snapshot = self.populated()
        snapshot["views"]["releases"]["releases"][0]["published_at"] = "sometime"
        with self.assertRaisesRegex(releases.ReleasesViewError, "RFC 3339 timestamp"):
            releases.releases_body(snapshot)

    def test_duplicate_boundary_event_ids_fail_closed(self) -> None:
        snapshot = self.populated()
        record = snapshot["views"]["releases"]["releases"][0]
        record["boundary_event_ids"] = ["event:release", "event:release"]
        with self.assertRaisesRegex(releases.ReleasesViewError, "boundary_event_ids must be unique"):
            releases.releases_body(snapshot)

    def test_duplicate_release_ids_fail_closed(self) -> None:
        snapshot = self.populated()
        duplicate = copy.deepcopy(snapshot["views"]["releases"]["releases"][0])
        duplicate["published_at"] = "2026-08-21T09:00:00Z"
        snapshot["views"]["releases"]["releases"].append(duplicate)
        with self.assertRaisesRegex(releases.ReleasesViewError, "release IDs must be unique"):
            releases.releases_body(snapshot)

    def test_rendering_is_deterministic(self) -> None:
        first = releases.render_page(
            snapshot=self.populated(),
            summary=summary(),
            repository="example/repository",
            source_commit=SOURCE_COMMIT,
        )
        second = releases.render_page(
            snapshot=self.populated(),
            summary=summary(),
            repository="example/repository",
            source_commit=SOURCE_COMMIT,
        )
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
