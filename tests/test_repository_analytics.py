# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPOSITORY_ROOT = Path(__file__).parents[1]
ACTION_ROOT = REPOSITORY_ROOT / "actions/repository-intelligence"
MODULE_PATH = ACTION_ROOT / "scripts/generate_repository_analytics.py"
SPEC = importlib.util.spec_from_file_location("repository_analytics", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
repository_analytics = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repository_analytics)


def git(repository_root: Path, *arguments: str, date: str | None = None) -> str:
    environment = os.environ.copy()
    if date is not None:
        environment["GIT_AUTHOR_DATE"] = date
        environment["GIT_COMMITTER_DATE"] = date
    return subprocess.run(
        ["git", "-C", str(repository_root), *arguments],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    ).stdout.strip()


def create_repository(repository_root: Path) -> None:
    git(repository_root, "init", "--initial-branch", "main")
    git(repository_root, "config", "user.name", "Private Example")
    git(repository_root, "config", "user.email", "private@example.test")
    (repository_root / "src").mkdir()
    (repository_root / ".reports").mkdir()
    (repository_root / "src" / "app.py").write_text(
        """print("hello")
""",
        encoding="utf-8",
    )
    (repository_root / ".reports" / "generated.json").write_text(
        json.dumps({"generated": True}) + "\n",
        encoding="utf-8",
    )
    git(repository_root, "add", "src/app.py", ".reports/generated.json")
    git(
        repository_root,
        "commit",
        "--message",
        "Initial source and generated report",
        date="2025-08-15T12:00:00+00:00",
    )
    (repository_root / "README.md").write_text("# Example\n", encoding="utf-8")
    (repository_root / "src" / "app.py").write_text(
        """print("hello")
print("world")
""",
        encoding="utf-8",
    )
    (repository_root / ".reports" / "generated.json").write_text(
        json.dumps({"generated": True, "large": True}) + "\n",
        encoding="utf-8",
    )
    git(repository_root, "add", "README.md", "src/app.py", ".reports/generated.json")
    git(
        repository_root,
        "commit",
        "--message",
        "Update source and generated report",
        date="2026-08-14T12:00:00+00:00",
    )


class RepositoryAnalyticsTests(unittest.TestCase):
    def test_normalizes_git_rename_display_paths(self) -> None:
        self.assertEqual(
            repository_analytics.normalize_git_path("src/{old => new}/module.py"),
            "src/new/module.py",
        )
        self.assertEqual(
            repository_analytics.normalize_git_path("old.txt => new.txt"),
            "new.txt",
        )

    def test_relative_window_is_anchored_to_source_commit(self) -> None:
        anchor = datetime(2024, 2, 29, 12, tzinfo=UTC)

        self.assertEqual(
            repository_analytics.resolve_since("1 year ago", anchor),
            datetime(2023, 2, 28, 12, tzinfo=UTC),
        )

    def test_summary_is_deterministic_filtered_and_public_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository_root = Path(temporary_directory)
            create_repository(repository_root)
            excluded_paths = repository_analytics.DEFAULT_EXCLUDED_PATHS

            first = repository_analytics.generate_summary(
                repo_root=repository_root,
                ref="HEAD",
                since_value="1 year ago",
                excluded_paths=excluded_paths,
            )
            second = repository_analytics.generate_summary(
                repo_root=repository_root,
                ref="HEAD",
                since_value="1 year ago",
                excluded_paths=excluded_paths,
            )

            self.assertEqual(first, second)
            self.assertEqual(first["schema"], "egohygiene.repository-analytics/v1")
            self.assertEqual(first["scope"]["resolved_since"], "2025-08-14T12:00:00Z")
            self.assertEqual(first["repository"]["tracked_files"], 2)
            self.assertEqual(first["activity"]["commits"], 2)
            self.assertEqual(first["activity"]["contributors"], 1)
            self.assertEqual(first["activity"]["first_commit_at"], "2025-08-15T12:00:00Z")
            self.assertEqual(first["activity"]["last_commit_at"], "2026-08-14T12:00:00Z")
            self.assertEqual(first["changes"]["files_changed"], 2)
            self.assertGreater(first["filters"]["excluded_change_records"], 0)
            serialized = json.dumps(first)
            self.assertNotIn("Private Example", serialized)
            self.assertNotIn("private@example.test", serialized)
            self.assertNotIn("generated.json", serialized)

    def test_repo_activity_reports_oldest_and_newest_matching_commits(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository_root = Path(temporary_directory)
            create_repository(repository_root)

            subprocess.run(
                [
                    "bash",
                    str(ACTION_ROOT / "scripts/repo-activity"),
                    "--repo",
                    str(repository_root),
                    "--output",
                    ".cache/activity",
                    "--since",
                    "2 years ago",
                    "--ref",
                    "HEAD",
                    "--color",
                    "never",
                    "--quiet",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            summary = (repository_root / ".cache/activity/summary.md").read_text(encoding="utf-8")

            self.assertIn("First matching commit: `2025-08-15T12:00:00Z`", summary)
            self.assertIn("Last matching commit: `2026-08-14T12:00:00Z`", summary)


if __name__ == "__main__":
    unittest.main()
