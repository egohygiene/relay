# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Integration tests for guarded report snapshot publication."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ACTION_ROOT = REPOSITORY_ROOT / "actions/publish-report-snapshot"
SCRIPT = ACTION_ROOT / "scripts/publish_report_snapshot.sh"


def git(repository: Path, *arguments: str) -> str:
    """Run Git and return normalized standard output."""

    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


class PublishReportSnapshotTests(unittest.TestCase):
    """Keep the only write-capable intelligence action tightly bounded."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        temporary_root = Path(self.temporary_directory.name)
        self.remote = temporary_root / "remote.git"
        self.repository = temporary_root / "repository"
        self.output = temporary_root / "github-output.txt"

        subprocess.run(
            ["git", "init", "--bare", "--initial-branch", "main", str(self.remote)],
            check=True,
            capture_output=True,
            text=True,
        )
        git(temporary_root, "init", "--initial-branch", "main", str(self.repository))
        git(self.repository, "config", "user.name", "Fixture")
        git(self.repository, "config", "user.email", "fixture@example.test")
        git(self.repository, "remote", "add", "origin", str(self.remote))
        summary = self.repository / ".reports/osv/summary.json"
        summary.parent.mkdir(parents=True)
        summary.write_text('{"version": 1}\n', encoding="utf-8")
        git(self.repository, "add", ".reports/osv/summary.json")
        git(self.repository, "commit", "--message", "initialize fixture")
        git(self.repository, "push", "--set-upstream", "origin", "main")

    def run_action(
        self,
        *,
        event: str = "push",
        ref_name: str = "main",
        paths: str = ".reports/osv/summary.json",
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Run the action script with a deterministic GitHub-like environment."""

        environment = os.environ.copy()
        environment.update(
            {
                "GITHUB_EVENT_NAME": event,
                "GITHUB_REF_NAME": ref_name,
                "GITHUB_REF_TYPE": "branch",
                "GITHUB_OUTPUT": str(self.output),
                "GITHUB_WORKSPACE": str(self.repository),
                "INPUT_AUTHOR_EMAIL": "bot@example.test",
                "INPUT_AUTHOR_NAME": "Report Bot",
                "INPUT_COMMIT_MESSAGE": "chore(reports): refresh fixture [skip ci]",
                "INPUT_DEFAULT_BRANCH": "main",
                "INPUT_PATHS": paths,
            }
        )
        return subprocess.run(
            ["bash", str(SCRIPT)],
            check=check,
            capture_output=True,
            text=True,
            env=environment,
        )

    def test_publishes_only_changed_report_paths(self) -> None:
        summary = self.repository / ".reports/osv/summary.json"
        summary.write_text('{"version": 2}\n', encoding="utf-8")

        self.run_action()

        output = self.output.read_text(encoding="utf-8")
        self.assertIn("changed=true", output)
        published_commit = git(self.remote, "rev-parse", "refs/heads/main")
        self.assertIn(f"commit-sha={published_commit}", output)
        self.assertEqual(
            git(self.remote, "show", "main:.reports/osv/summary.json"),
            '{"version": 2}',
        )

    def test_no_change_is_a_successful_noop(self) -> None:
        self.run_action()

        self.assertEqual(
            self.output.read_text(encoding="utf-8"),
            "changed=false\ncommit-sha=\n",
        )

    def test_rejects_pull_requests_and_non_default_branches(self) -> None:
        pull_request = self.run_action(event="pull_request", check=False)
        self.assertEqual(pull_request.returncode, 2)
        self.assertIn("forbidden", pull_request.stderr)

        workflow_run = self.run_action(event="workflow_run", check=False)
        self.assertEqual(workflow_run.returncode, 2)
        self.assertIn("forbidden", workflow_run.stderr)

        wrong_branch = self.run_action(ref_name="feature", check=False)
        self.assertEqual(wrong_branch.returncode, 2)
        self.assertIn("requires default branch", wrong_branch.stderr)

    def test_rejects_non_report_and_history_paths(self) -> None:
        readme = self.repository / "README.md"
        readme.write_text("# fixture\n", encoding="utf-8")
        non_report = self.run_action(paths="README.md", check=False)
        self.assertEqual(non_report.returncode, 2)
        self.assertIn("under .reports", non_report.stderr)

        history = self.repository / ".reports/osv/history/2026-08-19.json"
        history.parent.mkdir(parents=True)
        history.write_text("{}\n", encoding="utf-8")
        historical = self.run_action(paths=".reports/osv/history", check=False)
        self.assertEqual(historical.returncode, 2)
        self.assertIn("history", historical.stderr)

    def test_rejects_symlinked_report_paths(self) -> None:
        outside = self.repository.parent / "outside.json"
        outside.write_text('{"version": 2}\n', encoding="utf-8")
        linked = self.repository / ".reports/osv/linked.json"
        linked.symlink_to(outside)

        result = self.run_action(paths=".reports/osv/linked.json", check=False)

        self.assertEqual(result.returncode, 2)
        self.assertIn("symbolic links", result.stderr)

    def test_action_manifest_calls_the_guarded_script(self) -> None:
        action = (ACTION_ROOT / "action.yml").read_text(encoding="utf-8")

        self.assertIn("scripts/publish_report_snapshot.sh", action)
        self.assertIn("changed:", action)
        self.assertIn("commit-sha:", action)


if __name__ == "__main__":
    unittest.main()
