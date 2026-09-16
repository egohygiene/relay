# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Focused tests for the Repository Intelligence dependency-impact route."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ACTION_ROOT = REPOSITORY_ROOT / "actions/repository-intelligence"
FIXTURE = (
    REPOSITORY_ROOT
    / "tests/fixtures/repository-intelligence-dependencies/snapshot.json"
)
SOURCE_COMMIT = "1" * 40


def load_module(name: str, path: Path):
    """Load one repository script without changing Python's import path."""

    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dependencies = load_module(
    "repository_intelligence_dependencies",
    ACTION_ROOT / "scripts/render_repository_intelligence_dependencies.py",
)


def summary() -> dict[str, object]:
    """Return the minimum shell projection required by the focused renderer."""

    return {
        "generated_at": "2026-08-25T18:00:00Z",
        "repository": {
            "name": "example/repository",
            "source_commit": SOURCE_COMMIT,
        },
        "states": {
            "execution": {
                "failure": 0,
                "success": 1,
                "unknown": 0,
            }
        },
    }


class RepositoryIntelligenceDependenciesTests(unittest.TestCase):
    """Prove dependency evidence stays directional, explicit, and static-first."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.snapshot = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_populated_view_preserves_direction_and_evidence_states(self) -> None:
        rendered = dependencies.dependencies_body(
            copy.deepcopy(self.snapshot),
            repository="example/repository",
        )
        self.assertIn("What depends on what?", rendered)
        self.assertIn(">3</strong><span>directed relationships", rendered)
        self.assertIn(">2</strong><span>depends-on edges", rendered)
        self.assertIn(">1</strong><span>blocking edges", rendered)
        self.assertIn("Build the dependency view depends on Establish the graph contract", rendered)
        self.assertIn("Await normalized evidence blocks Build the dependency view", rendered)
        self.assertIn("Assertion: Authoritative", rendered)
        self.assertIn("Assertion: Inferred", rendered)
        self.assertIn("Freshness: Unknown", rendered)
        self.assertIn("Freshness: Stale", rendered)
        self.assertIn("source:roadmap", rendered)
        self.assertIn("source:hygiene", rendered)
        self.assertIn('data-filter-scope="cross-repository"', rendered)
        self.assertIn('data-filter-relationship="blocks"', rendered)
        self.assertNotIn("93%", rendered)
        self.assertNotIn("health score", rendered.lower())

    def test_cross_repository_root_is_visible_without_weakening_link_allowlist(self) -> None:
        rendered = dependencies.dependencies_body(
            copy.deepcopy(self.snapshot),
            repository="example/repository",
        )
        self.assertIn("egohygiene/hygiene", rendered)
        self.assertIn('data-source-repository="egohygiene/hygiene"', rendered)
        self.assertNotIn('href="https://github.com/egohygiene/hygiene"', rendered)
        self.assertIn(
            'href="https://github.com/egohygiene/hygiene/blob/2222222222222222222222222222222222222222/ROADMAP.md"',
            rendered,
        )

    def test_shell_keeps_static_relationships_and_accessible_filters(self) -> None:
        rendered = dependencies.render_page(
            snapshot=copy.deepcopy(self.snapshot),
            summary=summary(),
            repository="example/repository",
            source_commit=SOURCE_COMMIT,
        )
        self.assertIn('data-ri-route="dependencies"', rendered)
        self.assertIn('href="../dependencies/" aria-current="page">Dependencies</a>', rendered)
        self.assertIn('<main id="main-content" tabindex="-1">', rendered)
        self.assertIn("Build the dependency view depends on Establish the graph contract", rendered)
        self.assertIn('<select data-filter-extra="relationship">', rendered)
        self.assertIn('<span>Assertion</span><select data-filter-extra="assertion">', rendered)
        self.assertIn('aria-live="polite"', rendered)
        self.assertIn('src="../site.js" defer', rendered)
        self.assertLess(
            rendered.index("What depends on what?"),
            rendered.index('src="../site.js" defer'),
        )

    def test_empty_dependencies_query_is_not_presented_as_ecosystem_health(self) -> None:
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["views"]["dependencies"] = {
            "external_repositories": [],
            "relationships": [],
        }
        rendered = dependencies.dependencies_body(
            snapshot,
            repository="example/repository",
        )
        self.assertIn("No dependency relationships projected", rendered)
        self.assertIn("does not prove the wider ecosystem has no dependencies", rendered)
        self.assertIn('data-state="not_applicable"', rendered)

    def test_missing_dependencies_query_remains_explicitly_partial(self) -> None:
        snapshot = copy.deepcopy(self.snapshot)
        del snapshot["views"]["dependencies"]
        rendered = dependencies.dependencies_body(
            snapshot,
            repository="example/repository",
        )
        self.assertIn("Dependencies view not projected", rendered)
        self.assertIn("Relay will not infer dependency truth from other views", rendered)
        self.assertIn('data-state="partial"', rendered)

    def test_missing_snapshot_remains_explicitly_unavailable(self) -> None:
        rendered = dependencies.dependencies_body(
            None,
            repository="example/repository",
        )
        self.assertIn("Dependency evidence unavailable", rendered)
        self.assertIn("repository- and commit-matched Observatory read model", rendered)
        self.assertIn('data-state="partial"', rendered)

    def test_incompatible_relationship_fails_closed(self) -> None:
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["views"]["dependencies"]["relationships"][0]["type"] = "maybe-depends-on"
        with self.assertRaisesRegex(
            dependencies.DependencyViewError,
            "unsupported type maybe-depends-on",
        ):
            dependencies.dependencies_body(
                snapshot,
                repository="example/repository",
            )

    def test_rendering_is_deterministic(self) -> None:
        first = dependencies.render_page(
            snapshot=copy.deepcopy(self.snapshot),
            summary=summary(),
            repository="example/repository",
            source_commit=SOURCE_COMMIT,
        )
        second = dependencies.render_page(
            snapshot=copy.deepcopy(self.snapshot),
            summary=summary(),
            repository="example/repository",
            source_commit=SOURCE_COMMIT,
        )
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
