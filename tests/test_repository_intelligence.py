# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ACTION_ROOT = Path(__file__).parents[1] / "actions/repository-intelligence"
MODULE_PATH = ACTION_ROOT / "scripts/generate_repository_intelligence.py"
FIXTURE_PATH = Path(__file__).parent / "fixtures/default-branch-cases.json"
SPEC = importlib.util.spec_from_file_location("repository_intelligence", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
repository_intelligence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repository_intelligence)


def git(repository_root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository_root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def resolve_default_branch_from_action(
    input_default_branch: str,
    event_default_branch: str,
    current_ref: str,
) -> str:
    action = (ACTION_ROOT / "action.yml").read_text(encoding="utf-8")
    resolution_line = next(
        line.strip()
        for line in action.splitlines()
        if line.strip().startswith("default_branch=")
    )
    script = f"""set -euo pipefail
{resolution_line}
printf "%s" "${{default_branch}}"
"""
    return subprocess.run(
        ["bash", "-c", script],
        check=True,
        capture_output=True,
        text=True,
        env={
            "EVENT_DEFAULT_BRANCH": event_default_branch,
            "GITHUB_REF_NAME": current_ref,
            "INPUT_DEFAULT_BRANCH": input_default_branch,
        },
    ).stdout


class RepositoryIntelligenceTests(unittest.TestCase):
    def test_action_surfaces_public_tree_and_analytics_contracts(self) -> None:
        action = (ACTION_ROOT / "action.yml").read_text(encoding="utf-8")

        self.assertIn("repository-tree:", action)
        self.assertIn("analytics-summary:", action)
        self.assertIn("generate_repository_analytics.py", action)

    def test_default_branch_compatibility_fixtures(self) -> None:
        fixtures = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

        self.assertEqual(
            fixtures["schema"],
            "egohygiene.relay-default-branch-fixtures/v1",
        )
        cases = fixtures["cases"]
        self.assertEqual(
            {case["id"] for case in cases},
            {
                "main-default",
                "master-default",
                "both-branches-master-default",
                "non-default-release-branch",
                "fork-pull-request",
            },
        )

        for case in cases:
            with self.subTest(case=case["id"]):
                resolved = resolve_default_branch_from_action(
                    input_default_branch=case["input_default_branch"],
                    event_default_branch=case["event_default_branch"],
                    current_ref=case["current_ref"],
                )
                self.assertEqual(resolved, case["expected_default_branch"])
                self.assertEqual(
                    case["current_ref"] == case["expected_default_branch"],
                    case["release_authorized"],
                )

    def test_default_branch_explicit_input_precedes_event_metadata(self) -> None:
        self.assertEqual(
            resolve_default_branch_from_action(
                input_default_branch="stable",
                event_default_branch="master",
                current_ref="master",
            ),
            "stable",
        )

    def test_default_branch_falls_back_to_main_without_metadata(self) -> None:
        self.assertEqual(
            resolve_default_branch_from_action(
                input_default_branch="",
                event_default_branch="",
                current_ref="feature/example",
            ),
            "main",
        )

    def test_normalizes_and_removes_empty_exclusions(self) -> None:
        self.assertEqual(
            repository_intelligence.normalize_excluded_paths(" .git, /dist/ ,, build "),
            [".git", "dist", "build"],
        )

    def test_build_tree_is_sorted_excluded_and_annotated(self) -> None:
        tree = repository_intelligence.build_tree(
            repository_name="example",
            entries=[
                ("zeta.txt", "100644"),
                ("alpha/value.txt", "100644"),
                ("alpha/link", "120000"),
                ("node_modules/ignored.js", "100644"),
            ],
            excluded_paths=["node_modules"],
            max_depth=5,
        )

        self.assertEqual(
            [child["name"] for child in tree["children"]],
            ["alpha", "zeta.txt"],
        )
        self.assertEqual(
            tree["descendants"],
            {"directories": 1, "files": 2, "symlinks": 1, "submodules": 0},
        )

    def test_git_tree_ignores_untracked_worktree_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository_root = Path(temporary_directory)
            git(repository_root, "init", "--initial-branch", "main")
            git(repository_root, "config", "user.name", "Example")
            git(repository_root, "config", "user.email", "example@example.test")
            (repository_root / "tracked.txt").write_text("tracked\n", encoding="utf-8")
            git(repository_root, "add", "tracked.txt")
            git(repository_root, "commit", "--message", "Initial")
            (repository_root / "untracked.txt").write_text("untracked\n", encoding="utf-8")

            revision = repository_intelligence.resolve_revision(repository_root, "HEAD")
            entries = repository_intelligence.list_git_entries(repository_root, revision)

            self.assertEqual(entries, [("tracked.txt", "100644")])

    def test_write_outputs_produces_versioned_commit_scoped_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_root = Path(temporary_directory)
            tree = repository_intelligence.build_tree(
                repository_name="example",
                entries=[],
                excluded_paths=[],
                max_depth=5,
            )
            revision = "a" * 40

            repository_intelligence.write_outputs(
                output_root=output_root,
                tree=tree,
                revision=revision,
                ref="HEAD",
                committed_at="2026-08-14T12:00:00+00:00",
            )

            payload = json.loads((output_root / "tree" / "repo.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["schema"], "egohygiene.repository-tree/v1")
            self.assertEqual(payload["source"]["revision"], revision)
            self.assertEqual(payload["tree"], tree)
            self.assertTrue((output_root / "visualization" / "repository.svg").is_file())


if __name__ == "__main__":
    unittest.main()
