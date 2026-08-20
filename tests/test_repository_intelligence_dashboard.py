# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Tests for the deterministic static repository intelligence dashboard."""

from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ACTION_ROOT = REPOSITORY_ROOT / "actions/repository-intelligence"
FIXTURE_ROOT = REPOSITORY_ROOT / "tests/fixtures/repository-intelligence-dashboard"
MODULE_PATH = ACTION_ROOT / "scripts/generate_repository_intelligence_dashboard.py"
SPEC = importlib.util.spec_from_file_location(
    "generate_repository_intelligence_dashboard", MODULE_PATH
)
assert SPEC is not None
assert SPEC.loader is not None
dashboard_builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dashboard_builder)

PREPARE_MODULE_PATH = ACTION_ROOT / "scripts/prepare_output_directory.py"
PREPARE_SPEC = importlib.util.spec_from_file_location(
    "prepare_output_directory", PREPARE_MODULE_PATH
)
assert PREPARE_SPEC is not None
assert PREPARE_SPEC.loader is not None
output_preparer = importlib.util.module_from_spec(PREPARE_SPEC)
PREPARE_SPEC.loader.exec_module(output_preparer)

AS_OF = datetime(2026, 8, 14, 12, tzinfo=UTC)
REPOSITORY = "example/repository"


def git(repository: Path, *arguments: str, environment: dict[str, str] | None = None) -> str:
    """Run one deterministic Git command in a fixture repository."""

    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    return result.stdout.strip()


def initialize_repository(root: Path) -> str:
    """Create a minimal full-history repository for vitality collection."""

    git(root, "init", "--quiet")
    git(root, "config", "--local", "user.name", "Dashboard Fixture")
    git(root, "config", "--local", "user.email", "fixture@example.test")
    workflow = root / ".github/workflows/example.yml"
    action = root / ".github/actions/example/action.yml"
    test_module = root / "tests/test_example.py"
    for path, content in (
        (workflow, "name: Example\n"),
        (action, "name: Example\nruns:\n  using: composite\n  steps: []\n"),
        (test_module, '"""Fixture test module."""\n'),
        (root / "README.md", "# Fixture repository\n"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    git(root, "add", "--all")
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_DATE": "2026-08-14T10:00:00Z",
            "GIT_COMMITTER_DATE": "2026-08-14T10:00:00Z",
        }
    )
    git(root, "commit", "--quiet", "--message", "fixture: initialize", environment=environment)
    return git(root, "rev-parse", "HEAD")


class RepositoryIntelligenceDashboardTests(unittest.TestCase):
    """Keep aggregation, public projection, and rendering truthful."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.repository_root = Path(self.temporary_directory.name) / "repository"
        self.repository_root.mkdir()
        self.source_commit = initialize_repository(self.repository_root)

    def build(
        self,
        reports_root: Path,
        analytics_summary: Path | None = None,
        repository_tree: Path | None = None,
    ) -> dict[str, object]:
        """Build one dashboard against the fixture checkout."""

        return dashboard_builder.build_dashboard(
            repository_root=self.repository_root,
            reports_root=reports_root,
            repository=REPOSITORY,
            default_branch="main",
            source_commit=self.source_commit,
            as_of=AS_OF,
            analytics_summary=analytics_summary,
            repository_tree=repository_tree,
        )

    def copy_reports(self) -> Path:
        """Copy the complete producer fixture set into the temporary checkout."""

        reports_root = self.repository_root / ".reports"
        shutil.copytree(FIXTURE_ROOT, reports_root)
        for summary_path in sorted(reports_root.glob("*/summary.json")):
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["commit"] = self.source_commit
            summary["links"] = {
                key: value.replace("1" * 40, self.source_commit)
                for key, value in summary["links"].items()
            }
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
        return reports_root

    def write_analytics_summary(self) -> Path:
        """Write one public-safe analytics contract for chart rendering."""

        path = self.repository_root / ".cache/intelligence/analytics/summary.json"
        path.parent.mkdir(parents=True)
        payload = {
            "schema": "egohygiene.repository-analytics/v1",
            "schema_version": 1,
            "source": {
                "revision": self.source_commit,
                "ref": "HEAD",
                "committed_at": "2026-08-14T10:00:00Z",
            },
            "scope": {
                "since": "1 year ago",
                "resolved_since": "2025-08-14T10:00:00Z",
            },
            "privacy": {
                "public_safe": True,
                "contributor_identities_included": False,
                "commit_messages_included": False,
            },
            "repository": {
                "tracked_files": 100,
                "areas": [
                    {"name": "src", "file_count": 48},
                    {"name": ".github", "file_count": 22},
                    {"name": "tests", "file_count": 18},
                    {"name": "docs", "file_count": 8},
                    {"name": "(root)", "file_count": 4},
                ],
                "extensions": [],
            },
            "activity": {
                "commits": 18,
                "merges": 4,
                "contributors": 3,
                "first_commit_at": "2026-07-27T10:00:00Z",
                "last_commit_at": "2026-08-14T10:00:00Z",
                "weekly": [
                    {"week": "2026-07-27", "commits": 4, "merges": 1},
                    {"week": "2026-08-03", "commits": 6, "merges": 1},
                    {"week": "2026-08-10", "commits": 8, "merges": 2},
                ],
            },
            "changes": {
                "files_changed": 64,
                "insertions": 2400,
                "deletions": 600,
                "net_lines": 1800,
                "areas": [
                    {
                        "name": "src",
                        "commit_touches": 40,
                        "insertions": 1200,
                        "deletions": 300,
                        "binary_changes": 0,
                    },
                    {
                        "name": ".github",
                        "commit_touches": 24,
                        "insertions": 700,
                        "deletions": 200,
                        "binary_changes": 0,
                    },
                    {
                        "name": "tests",
                        "commit_touches": 18,
                        "insertions": 500,
                        "deletions": 100,
                        "binary_changes": 0,
                    },
                ],
                "hotspots": [],
            },
            "filters": {
                "excluded_paths": [".reports"],
                "excluded_tracked_files": 12,
                "excluded_change_records": 42,
            },
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def write_repository_tree(self) -> Path:
        """Write one commit-scoped public repository-tree contract."""

        path = self.repository_root / ".cache/intelligence/tree/repo.json"
        path.parent.mkdir(parents=True)
        payload = {
            "schema": "egohygiene.repository-tree/v1",
            "schema_version": 1,
            "source": {
                "revision": self.source_commit,
                "ref": "HEAD",
                "committed_at": "2026-08-14T10:00:00Z",
            },
            "tree": {
                "name": "repository",
                "path": ".",
                "type": "directory",
                "children": [
                    {
                        "name": "tests",
                        "path": "tests",
                        "type": "directory",
                        "children": [
                            {
                                "name": "test_example.py",
                                "path": "tests/test_example.py",
                                "type": "file",
                            }
                        ],
                        "descendants": {
                            "directories": 0,
                            "files": 1,
                            "symlinks": 0,
                            "submodules": 0,
                        },
                    },
                    {
                        "name": "README.md",
                        "path": "README.md",
                        "type": "file",
                    },
                ],
                "descendants": {
                    "directories": 1,
                    "files": 2,
                    "symlinks": 0,
                    "submodules": 0,
                },
            },
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_complete_reports_preserve_independent_states(self) -> None:
        dashboard = self.build(self.copy_reports())

        self.assertEqual(dashboard["states"]["execution"]["success"], 2)
        self.assertEqual(dashboard["states"]["execution"]["failure"], 1)
        self.assertEqual(dashboard["states"]["findings"]["attention"], 2)
        self.assertEqual(dashboard["states"]["findings"]["clear"], 1)
        self.assertEqual(dashboard["states"]["freshness"]["fresh"], 2)
        self.assertEqual(dashboard["states"]["freshness"]["stale"], 1)
        self.assertEqual(dashboard["producers"]["scorecard"]["metrics"]["aggregate_score"], 4.1)

    def test_missing_reports_are_unavailable_and_unknown(self) -> None:
        dashboard = self.build(self.repository_root / ".reports")
        rendered = dashboard_builder.render_html(dashboard)

        self.assertEqual(dashboard["states"]["availability"]["unavailable"], 3)
        self.assertEqual(dashboard["states"]["execution"]["unknown"], 3)
        self.assertEqual(dashboard["states"]["findings"]["unknown"], 3)
        self.assertEqual(dashboard["states"]["freshness"]["unknown"], 3)
        self.assertIn("may be unconfigured, not applicable", rendered)
        self.assertIn("unknown", dashboard_builder.render_findings_chart(dashboard["producers"]))

    def test_public_analytics_renders_accessible_statistical_snapshots(self) -> None:
        dashboard = self.build(
            self.copy_reports(),
            self.write_analytics_summary(),
        )
        rendered = dashboard_builder.render_html(dashboard)

        self.assertEqual(dashboard["analytics"]["availability"], "available")
        self.assertIn("Weekly repository commits and merges", rendered)
        self.assertIn("Repository file composition", rendered)
        self.assertIn("Repository change hotspots", rendered)
        self.assertIn("Scanner findings by producer", rendered)
        self.assertIn("<progress", rendered)
        self.assertGreaterEqual(rendered.count("<table>"), 5)
        self.assertIn('<script src="./explorer.js" defer></script>', rendered)

    def test_repository_tree_renders_searchable_source_pinned_anatomy(self) -> None:
        dashboard = self.build(
            self.copy_reports(),
            self.write_analytics_summary(),
            self.write_repository_tree(),
        )
        rendered = dashboard_builder.render_html(dashboard)

        self.assertEqual(dashboard["anatomy"]["availability"], "available")
        self.assertEqual(dashboard["anatomy"]["summary"]["node_count"], 4)
        self.assertIn("Explore the source tree", rendered)
        self.assertIn("data-repository-explorer", rendered)
        self.assertIn("data-tree-search", rendered)
        self.assertIn("<details", rendered)
        self.assertIn(
            f"https://github.com/example/repository/blob/{self.source_commit}/README.md",
            rendered,
        )
        self.assertIn("Showing all 3 entries.", rendered)

    def test_repository_tree_for_another_commit_is_invalid_not_rendered(self) -> None:
        tree_path = self.write_repository_tree()
        payload = json.loads(tree_path.read_text(encoding="utf-8"))
        payload["source"]["revision"] = "b" * 40
        tree_path.write_text(json.dumps(payload), encoding="utf-8")

        dashboard = self.build(self.copy_reports(), repository_tree=tree_path)
        rendered = dashboard_builder.render_html(dashboard)

        self.assertEqual(dashboard["anatomy"]["availability"], "invalid")
        self.assertIn("Repository anatomy unavailable", rendered)
        self.assertNotIn("data-repository-explorer", rendered)

    def test_repository_tree_names_are_escaped_and_source_paths_are_encoded(self) -> None:
        tree_path = self.write_repository_tree()
        payload = json.loads(tree_path.read_text(encoding="utf-8"))
        leaf = payload["tree"]["children"][1]
        leaf["name"] = "<script>.md"
        leaf["path"] = "<script>.md"
        tree_path.write_text(json.dumps(payload), encoding="utf-8")

        dashboard = self.build(self.copy_reports(), repository_tree=tree_path)
        rendered = dashboard_builder.render_html(dashboard)

        self.assertEqual(dashboard["anatomy"]["availability"], "available")
        self.assertIn("&lt;script&gt;.md", rendered)
        self.assertIn("%3Cscript%3E.md", rendered)
        self.assertNotIn("<script>.md", rendered)

    def test_analytics_for_another_commit_is_invalid_not_rendered(self) -> None:
        analytics_path = self.write_analytics_summary()
        payload = json.loads(analytics_path.read_text(encoding="utf-8"))
        payload["source"]["revision"] = "a" * 40
        analytics_path.write_text(json.dumps(payload), encoding="utf-8")

        dashboard = self.build(self.copy_reports(), analytics_path)
        rendered = dashboard_builder.render_html(dashboard)

        self.assertEqual(dashboard["analytics"]["availability"], "invalid")
        self.assertIn("Statistical snapshots unavailable", rendered)
        self.assertNotIn("Weekly repository commits and merges", rendered)

    def test_malformed_report_is_invalid_instead_of_green(self) -> None:
        reports_root = self.repository_root / ".reports"
        malformed = reports_root / "scorecard/summary.json"
        malformed.parent.mkdir(parents=True)
        malformed.write_text("{not-json}\n", encoding="utf-8")

        dashboard = self.build(reports_root)

        scorecard = dashboard["producers"]["scorecard"]
        self.assertEqual(scorecard["availability"], "invalid")
        self.assertEqual(scorecard["execution"]["state"], "failure")
        self.assertEqual(scorecard["findings"]["state"], "unknown")

    def test_symlinked_report_is_invalid_and_not_read(self) -> None:
        reports_root = self.repository_root / ".reports"
        producer_root = reports_root / "osv"
        producer_root.mkdir(parents=True)
        outside = Path(self.temporary_directory.name) / "private.json"
        outside.write_text(
            json.dumps({"private_metadata": "must not be read"}),
            encoding="utf-8",
        )
        (producer_root / "summary.json").symlink_to(outside)

        dashboard = self.build(reports_root)

        self.assertEqual(dashboard["producers"]["osv"]["availability"], "invalid")
        self.assertIn("symbolic links", dashboard["producers"]["osv"]["execution"]["message"])

    def test_stale_boundary_is_inclusive(self) -> None:
        reports_root = self.copy_reports()
        osv_path = reports_root / "osv/summary.json"
        osv = json.loads(osv_path.read_text(encoding="utf-8"))
        osv["generated_at"] = "2026-08-06T12:00:00Z"
        osv["freshness"]["expires_at"] = "2026-08-14T12:00:00Z"
        osv_path.write_text(json.dumps(osv), encoding="utf-8")

        dashboard = self.build(reports_root)

        self.assertEqual(dashboard["producers"]["osv"]["freshness"]["state"], "stale")

    def test_report_for_another_commit_is_invalid_and_not_rendered(self) -> None:
        reports_root = self.copy_reports()
        osv_path = reports_root / "osv/summary.json"
        osv = json.loads(osv_path.read_text(encoding="utf-8"))
        osv["commit"] = "b" * 40
        osv_path.write_text(json.dumps(osv), encoding="utf-8")

        dashboard = self.build(reports_root)
        projection = dashboard["producers"]["osv"]

        self.assertEqual(projection["availability"], "invalid")
        self.assertEqual(projection["execution"]["state"], "failure")
        self.assertEqual(projection["findings"]["state"], "unknown")
        self.assertEqual(projection["metrics"], {})
        self.assertIn("source commit", projection["execution"]["message"])

    def test_renderer_escapes_text_and_rejects_unsafe_links(self) -> None:
        reports_root = self.copy_reports()
        osv_path = reports_root / "osv/summary.json"
        osv = json.loads(osv_path.read_text(encoding="utf-8"))
        osv["execution"]["message"] = "<script>alert('no')</script>"
        osv["links"]["detail"] = "https://user:token@github.com/example/repository"
        osv["links"]["workflow"] = "https://github.com/example/repository?token=fake"
        osv["links"]["security"] = "./../../.cache/repository-intelligence/activity"
        osv["links"]["source"] = "https://[broken/repository"
        osv_path.write_text(json.dumps(osv), encoding="utf-8")

        dashboard = self.build(reports_root)
        rendered = dashboard_builder.render_html(dashboard)

        self.assertNotIn("<script>", rendered)
        self.assertNotIn("user:token", rendered)
        self.assertNotIn("?token=", rendered)
        self.assertNotIn(".cache/repository-intelligence", rendered)
        self.assertNotIn("[broken", rendered)
        self.assertNotIn("&lt;script&gt;", rendered)
        self.assertIn("evidence was normalized successfully", rendered)
        for unsafe in (
            "https://user:token@github.com/example/repository",
            "https://github.com/example/repository?token=fake",
            "./../../.cache/repository-intelligence/activity",
            "./summary.json?token=fake",
            "./summary.json#PRIVATE-ISSUE-BODY-SENTINEL-LEAK",
            "https://github.com/example/repository#token",
            "https://internal.example.invalid/private-report",
            "https://127.0.0.1/report",
            "https://github.com/%67%68%70%5fAAAAAAAAAAAAAAAAAAAA",
            "https://github.com/egohygiene/private-repository/actions/runs/123",
            "https://github.com:444/example/repository/actions/runs/123",
            "https://scorecard.dev/viewer/?uri=github.com/../repo",
            "https://scorecard.dev:444/viewer/?uri=github.com/example/repository",
            "https://[broken/repository",
        ):
            with self.subTest(unsafe=unsafe):
                self.assertEqual(dashboard_builder.safe_url(unsafe, REPOSITORY), "")

    def test_report_links_must_match_the_dashboard_source_commit(self) -> None:
        reports_root = self.copy_reports()
        osv_path = reports_root / "osv/summary.json"
        osv = json.loads(osv_path.read_text(encoding="utf-8"))
        osv["links"]["source"] = f"https://github.com/{REPOSITORY}/commit/{'b' * 40}"
        osv["links"]["detail"] = (
            f"https://github.com/{REPOSITORY}/tree/{'b' * 40}/.reports/osv"
        )
        osv_path.write_text(json.dumps(osv), encoding="utf-8")

        dashboard = self.build(reports_root)

        self.assertNotIn("source", dashboard["producers"]["osv"]["links"])
        self.assertNotIn("detail", dashboard["producers"]["osv"]["links"])

    def test_absolute_analytics_hotspot_is_invalid(self) -> None:
        analytics_path = self.write_analytics_summary()
        analytics = json.loads(analytics_path.read_text(encoding="utf-8"))
        analytics["changes"]["hotspots"] = [
            {
                "path": "/home/runner/work/private/source.py",
                "commit_touches": 1,
                "insertions": 1,
                "deletions": 0,
                "binary_changes": 0,
            }
        ]
        analytics_path.write_text(json.dumps(analytics), encoding="utf-8")

        dashboard = self.build(self.copy_reports(), analytics_path)

        self.assertEqual(dashboard["analytics"]["availability"], "invalid")
        self.assertIn("repository-relative", dashboard["analytics"]["message"])

    def test_bundle_is_deterministic_and_contains_no_contributor_identities(self) -> None:
        reports_root = self.copy_reports()
        analytics_summary = self.write_analytics_summary()
        repository_tree = self.write_repository_tree()
        first = self.build(reports_root, analytics_summary, repository_tree)
        second = self.build(reports_root, analytics_summary, repository_tree)
        output_root = self.repository_root / "site/intelligence"
        provenance = dashboard_builder.build_bundle_provenance(
            repository=REPOSITORY,
            source_commit=self.source_commit,
            generated_at=AS_OF,
            timestamp_source="consumer-source-commit",
            generator_version="1.1.0",
            generator_repository="egohygiene/relay",
            generator_ref="a" * 40,
            generator_commit="a" * 40,
            generator_immutable=True,
            consumer_visibility="public",
        )

        dashboard_builder.write_dashboard_bundle(
            output_root,
            first,
            ACTION_ROOT / "assets/dashboard.css",
            ACTION_ROOT / "assets/explorer.js",
            provenance,
        )
        first_files = {
            path.name: path.read_bytes() for path in sorted(output_root.iterdir())
        }
        dashboard_builder.write_dashboard_bundle(
            output_root,
            second,
            ACTION_ROOT / "assets/dashboard.css",
            ACTION_ROOT / "assets/explorer.js",
            provenance,
        )
        second_files = {
            path.name: path.read_bytes() for path in sorted(output_root.iterdir())
        }

        self.assertEqual(first_files, second_files)
        self.assertEqual(
            set(first_files),
            {"explorer.js", "index.html", "provenance.json", "styles.css", "summary.json"},
        )
        first_json = first_files["summary.json"].decode("utf-8")
        first_html = first_files["index.html"].decode("utf-8")
        self.assertNotIn("fixture@example.test", first_json)
        self.assertNotIn("fixture: initialize", first_json)
        self.assertNotIn("fixture: initialize", first_html)
        self.assertEqual(first["vitality"]["metrics"]["contributors_90_days"], 1)
        self.assertTrue((output_root / "styles.css").is_file())
        self.assertTrue((output_root / "explorer.js").is_file())
        self.assertIn(self.source_commit, first_files["provenance.json"].decode("utf-8"))

    def test_output_preparation_removes_stale_files_without_leaving_repository(self) -> None:
        output_root = self.repository_root / "dist/intelligence"
        output_root.mkdir(parents=True)
        (output_root / "stale.txt").write_text("stale\n", encoding="utf-8")
        root_index = self.repository_root / "dist/index.html"
        cname = self.repository_root / "dist/CNAME"
        root_index.write_text("root site\n", encoding="utf-8")
        cname.write_text("example.test\n", encoding="utf-8")

        prepared = output_preparer.prepare_output_directory(
            self.repository_root,
            "dist/intelligence",
        )

        self.assertEqual(prepared, output_root)
        self.assertEqual(list(prepared.iterdir()), [])
        self.assertEqual(root_index.read_text(encoding="utf-8"), "root site\n")
        self.assertEqual(cname.read_text(encoding="utf-8"), "example.test\n")

        outside = Path(self.temporary_directory.name) / "outside"
        outside.mkdir()
        symlink = self.repository_root / "linked-output"
        symlink.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symbolic-link components"):
            output_preparer.prepare_output_directory(
                self.repository_root,
                "linked-output/intelligence",
            )
        protected_target = self.repository_root / ".github/intelligence"
        protected_target.mkdir()
        victim = protected_target / "victim.txt"
        victim.write_text("preserve me\n", encoding="utf-8")
        internal_link = self.repository_root / "linked-protected"
        internal_link.symlink_to(self.repository_root / ".github", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symbolic-link components"):
            output_preparer.prepare_output_directory(
                self.repository_root,
                "linked-protected/intelligence",
            )
        self.assertEqual(victim.read_text(encoding="utf-8"), "preserve me\n")
        with self.assertRaisesRegex(ValueError, "canonical repository-relative"):
            output_preparer.prepare_output_directory(self.repository_root, "../intelligence")
        for noncanonical in ("dist//intelligence", "dist/intelligence/", "./dist"):
            with self.subTest(noncanonical=noncanonical), self.assertRaisesRegex(
                ValueError,
                "canonical repository-relative",
            ):
                output_preparer.prepare_output_directory(
                    self.repository_root,
                    noncanonical,
                )
        with self.assertRaisesRegex(ValueError, "protected repository area"):
            output_preparer.prepare_output_directory(self.repository_root, ".github/intelligence")

    def test_directory_layout_separates_public_private_and_report_paths(self) -> None:
        resolved = output_preparer.validate_directory_layout(
            self.repository_root,
            "dist/intelligence",
            ".cache/repository-intelligence",
            ".reports",
        )

        self.assertEqual(resolved["output-directory"], self.repository_root / "dist/intelligence")
        for output, work, reports in (
            ("dist/intelligence", "dist/intelligence/private", ".reports"),
            ("dist/intelligence", ".cache", "dist/intelligence/reports"),
        ):
            with self.assertRaisesRegex(ValueError, "must not overlap"):
                output_preparer.validate_directory_layout(
                    self.repository_root,
                    output,
                    work,
                    reports,
                )
        with self.assertRaisesRegex(ValueError, "site composition root"):
            output_preparer.validate_directory_layout(
                self.repository_root,
                "dist/intelligence",
                "dist/repository-intelligence",
                ".reports",
            )
        with self.assertRaisesRegex(ValueError, "nested inside reports-directory"):
            output_preparer.validate_directory_layout(
                self.repository_root,
                "dist/intelligence",
                ".reports/private",
                ".reports",
            )
        nested_reports = output_preparer.validate_directory_layout(
            self.repository_root,
            "dist/intelligence",
            ".cache/repository-intelligence",
            ".cache/repository-intelligence/reports",
        )
        self.assertEqual(
            nested_reports["reports-directory"],
            self.repository_root / ".cache/repository-intelligence/reports",
        )
        with self.assertRaisesRegex(ValueError, "subtree within a site composition root"):
            output_preparer.validate_directory_layout(
                self.repository_root,
                "intelligence",
                ".cache/repository-intelligence",
                ".reports",
            )
        with self.assertRaisesRegex(ValueError, "end with the intelligence subtree"):
            output_preparer.validate_directory_layout(
                self.repository_root,
                "dist/not-intelligence",
                ".cache/repository-intelligence",
                ".reports",
            )
        with self.assertRaisesRegex(ValueError, "protected repository area"):
            output_preparer.validate_directory_layout(
                self.repository_root,
                "dist/intelligence",
                ".git/intelligence",
                ".reports",
            )

    def test_directory_layout_rejects_managed_child_and_report_symlinks(self) -> None:
        work_root = self.repository_root / ".cache/repository-intelligence"
        work_root.mkdir(parents=True)
        public_root = self.repository_root / "dist"
        public_root.mkdir()
        (work_root / "activity").symlink_to(public_root, target_is_directory=True)

        with self.assertRaisesRegex(ValueError, "symbolic-link components"):
            output_preparer.validate_directory_layout(
                self.repository_root,
                "dist/intelligence",
                ".cache/repository-intelligence",
                ".reports",
            )

        (work_root / "activity").unlink()
        report_root = self.repository_root / ".reports/osv"
        report_root.mkdir(parents=True)
        outside = Path(self.temporary_directory.name) / "private-summary.json"
        outside.write_text("{}\n", encoding="utf-8")
        (report_root / "summary.json").symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "symbolic-link components"):
            output_preparer.validate_directory_layout(
                self.repository_root,
                "dist/intelligence",
                ".cache/repository-intelligence",
                ".reports",
            )

    def test_vitality_uses_the_represented_commit_not_untracked_files(self) -> None:
        untracked_workflow = self.repository_root / ".github/workflows/untracked.yml"
        untracked_action = self.repository_root / ".github/actions/untracked/action.yml"
        untracked_test = self.repository_root / "tests/untracked.spec.ts"
        for path in (untracked_workflow, untracked_action, untracked_test):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# not represented by the source commit\n", encoding="utf-8")

        dashboard = self.build(self.repository_root / ".reports")
        metrics = dashboard["vitality"]["metrics"]

        self.assertEqual(metrics["workflows"], 1)
        self.assertEqual(metrics["composite_actions"], 1)
        self.assertEqual(metrics["test_artifacts"], 1)

    def test_vitality_counts_cross_ecosystem_test_artifacts(self) -> None:
        for relative_path in (
            "tests/rust_integration.rs",
            "src/widget.test.ts",
            "spec/content/navigation.yml",
            "pkg/handler_test.go",
        ):
            path = self.repository_root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture\n", encoding="utf-8")
        git(self.repository_root, "add", "--all")
        git(self.repository_root, "commit", "--quiet", "--message", "add test fixtures")
        represented_commit = git(self.repository_root, "rev-parse", "HEAD")

        dashboard = dashboard_builder.build_dashboard(
            repository_root=self.repository_root,
            reports_root=self.repository_root / ".reports",
            repository=REPOSITORY,
            default_branch="main",
            source_commit=represented_commit,
            as_of=AS_OF,
        )

        self.assertEqual(dashboard["vitality"]["metrics"]["test_artifacts"], 5)

    def test_vitality_is_independent_of_dirty_mailmap_state(self) -> None:
        second_file = self.repository_root / "second.txt"
        second_file.write_text("second\n", encoding="utf-8")
        git(self.repository_root, "add", "second.txt")
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_AUTHOR_NAME": "Second Private Author",
                "GIT_AUTHOR_EMAIL": "second@example.test",
                "GIT_AUTHOR_DATE": "2026-08-14T11:00:00Z",
                "GIT_COMMITTER_DATE": "2026-08-14T11:00:00Z",
            }
        )
        git(
            self.repository_root,
            "commit",
            "--quiet",
            "--message",
            "second private message",
            environment=environment,
        )
        represented_commit = git(self.repository_root, "rev-parse", "HEAD")
        first = dashboard_builder.collect_vitality(
            self.repository_root,
            REPOSITORY,
            "main",
            represented_commit,
            AS_OF,
        )
        (self.repository_root / ".mailmap").write_text(
            "Combined <combined@example.test> <fixture@example.test>\n"
            "Combined <combined@example.test> <second@example.test>\n",
            encoding="utf-8",
        )
        git(
            self.repository_root,
            "config",
            "mailmap.file",
            str(self.repository_root / ".mailmap"),
        )
        second = dashboard_builder.collect_vitality(
            self.repository_root,
            REPOSITORY,
            "main",
            represented_commit,
            AS_OF,
        )

        self.assertEqual(first, second)
        self.assertEqual(second["metrics"]["contributors_90_days"], 2)

    def test_checked_in_schema_declares_public_contract(self) -> None:
        schema = json.loads(
            (ACTION_ROOT / "schemas/repository-intelligence-dashboard.schema.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            schema["properties"]["schema"]["const"], dashboard_builder.DASHBOARD_SCHEMA
        )
        self.assertIn("producers", schema["required"])
        self.assertIn("analytics", schema["required"])
        self.assertIn("anatomy", schema["required"])
        self.assertIn("vitality", schema["required"])

    def test_public_action_composes_dashboard_without_deploying(self) -> None:
        action = (ACTION_ROOT / "action.yml").read_text(encoding="utf-8")

        self.assertIn('default: "dist/intelligence"', action)
        self.assertIn("scripts/generate_repository_intelligence_dashboard.py", action)
        self.assertIn("assets/dashboard.css", action)
        self.assertIn("assets/explorer.js", action)
        self.assertNotIn("deploy-pages", action)
        self.assertNotIn("upload-pages-artifact", action)


if __name__ == "__main__":
    unittest.main()
