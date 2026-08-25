# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Tests for the routed Repository Intelligence shell and operational Now view."""

from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ACTION_ROOT = REPOSITORY_ROOT / "actions/repository-intelligence"
FIXTURE = REPOSITORY_ROOT / "tests/fixtures/repository-intelligence-site/snapshot.json"
AS_OF = datetime(2026, 8, 25, 14, tzinfo=UTC)
GENERATOR_COMMIT = "a" * 40


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dashboard_builder = load_module(
    "site_dashboard_builder",
    ACTION_ROOT / "scripts/generate_repository_intelligence_dashboard.py",
)
site_builder = load_module(
    "repository_intelligence_site_builder",
    ACTION_ROOT / "scripts/generate_repository_intelligence_site.py",
)
bundle_validator = load_module(
    "site_bundle_validator",
    ACTION_ROOT / "scripts/validate_repository_intelligence_bundle.py",
)


def git(repository: Path, *arguments: str, environment: dict[str, str] | None = None) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    ).stdout.strip()


def initialize_repository(repository: Path) -> str:
    git(repository, "init", "--quiet", "--initial-branch", "main")
    git(repository, "config", "user.name", "Site Fixture")
    git(repository, "config", "user.email", "fixture@example.test")
    (repository / "README.md").write_text("# Repository\n", encoding="utf-8")
    git(repository, "add", "README.md")
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_DATE": "2026-08-25T14:00:00Z",
            "GIT_COMMITTER_DATE": "2026-08-25T14:00:00Z",
        }
    )
    git(repository, "commit", "--quiet", "--message", "fixture", environment=environment)
    return git(repository, "rev-parse", "HEAD")


class RepositoryIntelligenceSiteTests(unittest.TestCase):
    """Prove the shell remains truthful, accessible, local-first, and deterministic."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.repository = Path(self.temporary_directory.name) / "repository"
        self.repository.mkdir()
        self.source_commit = initialize_repository(self.repository)
        self.snapshot = json.loads(FIXTURE.read_text(encoding="utf-8"))
        serialized = json.dumps(self.snapshot).replace("1" * 40, self.source_commit)
        self.snapshot = json.loads(serialized)

    def build(self, relative: str, *, include_snapshot: bool = True) -> Path:
        output = self.repository / relative
        output.mkdir(parents=True)
        dashboard = dashboard_builder.build_dashboard(
            repository_root=self.repository,
            reports_root=self.repository / ".reports",
            repository="example/repository",
            default_branch="main",
            source_commit=self.source_commit,
            as_of=AS_OF,
        )
        provenance = dashboard_builder.build_bundle_provenance(
            repository="example/repository",
            source_commit=self.source_commit,
            generated_at=AS_OF,
            timestamp_source="consumer-source-commit",
            generator_version="1.2.0",
            generator_repository="egohygiene/relay",
            generator_ref=GENERATOR_COMMIT,
            generator_commit=GENERATOR_COMMIT,
            generator_immutable=True,
            consumer_visibility="public",
        )
        dashboard_builder.write_dashboard_bundle(
            output,
            dashboard,
            ACTION_ROOT / "assets/dashboard.css",
            ACTION_ROOT / "assets/explorer.js",
            provenance,
            "dashboard",
        )
        snapshot_path = self.repository / ".cache/repository-intelligence/snapshot.json"
        if include_snapshot:
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path.write_text(
                json.dumps(self.snapshot, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        arguments = [
            "python3",
            str(ACTION_ROOT / "scripts/generate_repository_intelligence_site.py"),
            "--repository-root",
            str(self.repository),
            "--output-root",
            str(output),
            "--summary",
            str(output / "summary.json"),
            "--provenance",
            str(output / "provenance.json"),
            "--repository",
            "example/repository",
            "--source-commit",
            self.source_commit,
            "--stylesheet-source",
            str(ACTION_ROOT / "assets/site.css"),
            "--script-source",
            str(ACTION_ROOT / "assets/site.js"),
        ]
        if include_snapshot:
            arguments.extend(["--snapshot", str(snapshot_path)])
        subprocess.run(arguments, check=True, capture_output=True, text=True)
        bundle_validator.validate_bundle(
            repository_root=self.repository,
            output_root=output,
            repository="example/repository",
            repository_visibility="public",
            source_commit=self.source_commit,
            generator_version="1.2.0",
            generator_source_ref=GENERATOR_COMMIT,
            generator_source_commit=GENERATOR_COMMIT,
            generator_immutable=True,
        )
        return output

    def test_now_is_default_and_keeps_operational_states_distinct(self) -> None:
        output = self.build("dist/intelligence")
        root = (output / "index.html").read_text(encoding="utf-8")
        routed = (output / "now/index.html").read_text(encoding="utf-8")
        for rendered in (root, routed):
            self.assertIn("Where things stand", rendered)
            self.assertIn("Current quests", rendered)
            self.assertIn("Blockers", rendered)
            self.assertIn("Checks that regressed", rendered)
            self.assertIn("Decisions awaiting closure", rendered)
            self.assertIn("The next three grounded moves", rendered)
            self.assertIn("The shared shell is available", rendered)
            self.assertIn("Establish the evidence contract", rendered)
            self.assertIn("Open canonical work", rendered)
        self.assertNotIn("Incomplete work is blocked", root)
        self.assertTrue((output / "dashboard/index.html").is_file())
        dashboard = (output / "dashboard/index.html").read_text(encoding="utf-8")
        self.assertIn('aria-label="Repository Intelligence views"', dashboard)
        self.assertIn('href="../now/"', dashboard)

    def test_ready_queue_is_bounded_to_three_actions(self) -> None:
        snapshot = json.loads(json.dumps(self.snapshot))
        template_entity = snapshot["views"]["now"]["next_ready"][0]
        template_step = snapshot["views"]["roadmap"]["steps"][1]
        ready = []
        steps = [snapshot["views"]["roadmap"]["steps"][0]]
        for index in range(1, 5):
            candidate = json.loads(json.dumps(template_entity))
            candidate["id"] = f"ri:example/repository:roadmap-step:EX-NEXT-{index}"
            candidate["key"] = f"EX-NEXT-{index}"
            candidate["title"] = f"Ready action {index}"
            step = json.loads(json.dumps(template_step))
            step["entity"] = candidate
            ready.append(candidate)
            steps.append(step)
        snapshot["views"]["now"]["next_ready"] = ready
        snapshot["views"]["roadmap"]["steps"] = steps
        rendered = site_builder.render_next_actions(snapshot)
        self.assertEqual(rendered.count('<li class="ri-action"'), 3)
        self.assertIn("Ready action 3", rendered)
        self.assertNotIn("Ready action 4", rendered)

    def test_shell_reserves_every_route_with_consistent_navigation(self) -> None:
        output = self.build("dist/intelligence")
        expected_routes = {route for route, _ in site_builder.ROUTES}
        for route in expected_routes:
            rendered = (output / route / "index.html").read_text(encoding="utf-8")
            self.assertIn('class="ri-route-nav"', rendered)
            self.assertIn(f'data-ri-route="{route}"', rendered)
            self.assertIn('aria-current="page"', rendered)
            self.assertIn("../site.css", rendered)
            self.assertIn("../site.js", rendered)

    def test_url_filters_keyboard_focus_and_local_resume_are_explicit(self) -> None:
        output = self.build("dist/intelligence")
        rendered = (output / "now/index.html").read_text(encoding="utf-8")
        script = (output / "site.js").read_text(encoding="utf-8")
        styles = (output / "site.css").read_text(encoding="utf-8")
        self.assertIn("URLSearchParams", script)
        self.assertIn("history.replaceState", script)
        self.assertIn("localStorage", script)
        self.assertIn("ArrowDown", script)
        self.assertIn('event.key === "/"', script)
        self.assertIn("Resume data stays in this browser", rendered)
        self.assertIn('aria-live="polite"', rendered)
        self.assertIn('href="#main-content"', rendered)
        self.assertIn('@media (prefers-reduced-motion: reduce)', styles)
        self.assertIn("@media print", styles)
        self.assertIn("@media (max-width: 48rem)", styles)
        self.assertNotIn("localStorage", (output / "summary.json").read_text(encoding="utf-8"))
        self.assertNotIn("resume.v1", (output / "provenance.json").read_text(encoding="utf-8"))

    def test_missing_snapshot_is_honest_not_green(self) -> None:
        output = self.build("dist/intelligence", include_snapshot=False)
        rendered = (output / "now/index.html").read_text(encoding="utf-8")
        self.assertIn("Observatory snapshot unavailable", rendered)
        self.assertIn("cannot be asserted", rendered)
        self.assertIn('data-state="unknown"', rendered)

    def test_snapshot_identity_and_commit_are_required(self) -> None:
        wrong = json.loads(json.dumps(self.snapshot))
        wrong["represented_commit"] = "f" * 40
        with self.assertRaisesRegex(site_builder.SiteInputError, "represent"):
            site_builder.validate_snapshot(
                wrong,
                "example/repository",
                self.source_commit,
            )
        wrong = json.loads(json.dumps(self.snapshot))
        wrong["repository"]["key"] = "example/other"
        with self.assertRaisesRegex(site_builder.SiteInputError, "repository"):
            site_builder.validate_snapshot(
                wrong,
                "example/repository",
                self.source_commit,
            )

    def test_sibling_contract_lock_pins_observatory_and_holon(self) -> None:
        lock = json.loads(
            (
                ACTION_ROOT
                / "contracts/repository-intelligence-siblings.v1.lock.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            lock["observatory"]["contract"],
            site_builder.SNAPSHOT_SCHEMA,
        )
        self.assertRegex(lock["observatory"]["source_commit"], r"^[0-9a-f]{40}$")
        self.assertRegex(lock["holon"]["source_commit"], r"^[0-9a-f]{40}$")
        self.assertEqual(
            lock["holon"]["package"],
            "@egohygiene/repository-intelligence@0.1.0-alpha.1",
        )

    def test_snapshot_path_rejects_symlink_components(self) -> None:
        outside = Path(self.temporary_directory.name) / "outside.json"
        outside.write_text("{}\n", encoding="utf-8")
        link = self.repository / "snapshot.json"
        link.symlink_to(outside)
        with self.assertRaisesRegex(site_builder.SiteInputError, "symbolic-link"):
            site_builder.validate_repository_path(
                self.repository.resolve(),
                link.absolute(),
                "Observatory snapshot",
            )

    def test_public_bundle_rejects_identity_leakage_from_snapshot_text(self) -> None:
        self.snapshot["views"]["now"]["current_focus"][0]["title"] = (
            "Coordinate with private-person@example.test"
        )
        with self.assertRaisesRegex(bundle_validator.BundleValidationError, "email"):
            self.build("dist/intelligence")

    def test_routed_site_is_byte_stable(self) -> None:
        first = self.build("first/intelligence")
        second = self.build("second/intelligence")
        first_files = {
            path.relative_to(first): path.read_bytes()
            for path in first.rglob("*")
            if path.is_file()
        }
        second_files = {
            path.relative_to(second): path.read_bytes()
            for path in second.rglob("*")
            if path.is_file()
        }
        self.assertEqual(first_files, second_files)


if __name__ == "__main__":
    unittest.main()
