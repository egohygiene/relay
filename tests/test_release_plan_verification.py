# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Tests for read-only semantic-release planning and prepared verification."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    REPOSITORY_ROOT
    / "actions/verify-release-plan/scripts/verify_release_plan.py"
)
SPEC = importlib.util.spec_from_file_location("verify_release_plan", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
release_plan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_plan)


def command(directory: Path, *arguments: str) -> str:
    """Run one fixture command and return stdout."""

    result = subprocess.run(
        list(arguments),
        cwd=directory,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def write_checksums(directory: Path) -> None:
    """Write Relay's exact complete checksum inventory."""

    records = []
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            records.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    (directory / "SHA256SUMS").write_text("\n".join(records) + "\n", encoding="utf-8")


def github_action_bundle(directory: Path) -> None:
    """Build a minimal valid github-action profile bundle."""

    files = {
        "action-catalog.json": "{}\n",
        "workflow-catalog.json": "{}\n",
        "provenance.json": "{}\n",
        "sbom.spdx.json": "{}\n",
        "signature.json": "{}\n",
        "relay.tar.gz": "reviewed bytes\n",
    }
    directory.mkdir()
    for name, content in files.items():
        (directory / name).write_text(content, encoding="utf-8")
    write_checksums(directory)


class ReleasePlanVerificationTests(unittest.TestCase):
    """Require release intent, authority, Git identity, and profile agreement."""

    def fixture(self, *, promoted: bool) -> tuple[tempfile.TemporaryDirectory[str], Path, Path, str]:
        """Create one current-main repository and its bare origin."""

        temporary = tempfile.TemporaryDirectory()
        base = Path(temporary.name)
        remote = base / "origin.git"
        repository = base / "consumer"
        remote.mkdir()
        repository.mkdir()
        command(remote, "git", "init", "--bare")
        command(repository, "git", "init", "--initial-branch", "main")
        command(repository, "git", "config", "user.name", "Relay Tests")
        command(repository, "git", "config", "user.email", "relay@example.invalid")
        command(repository, "git", "remote", "add", "origin", str(remote))
        (repository / ".egohygiene").mkdir()
        declaration = {
            "$schema": release_plan.DECLARATION_SCHEMA_URL,
            "schema_version": release_plan.DECLARATION_SCHEMA,
            "repository": {
                "id": "egohygiene/example",
                "lifecycle": "active",
                "release_profile": "contract",
            },
            "release": {
                "state": "released",
                "tag_prefix": "v",
                "immutable_tags": True,
                "major_alias": "optional",
            },
            "changelog": {
                "path": "CHANGELOG.md",
                "format": "keep-a-changelog/1.1",
                "unreleased_heading": "Unreleased",
            },
            "components": [
                {
                    "id": "example",
                    "kind": "catalog",
                    "version_authority": {
                        "kind": "catalog-record",
                        "path": "release.json",
                        "selector": "version",
                    },
                }
            ],
            "delivery": {
                "channels": [
                    {
                        "kind": "github-release",
                        "state": "configured",
                        "relay_profile": "github-action",
                    }
                ]
            },
            "evidence": {
                "source": "required",
                "change": "required",
                "provenance": "required",
                "sbom": "required",
                "signature": "unavailable",
                "rollback": {
                    "strategy": "revert-and-successor-tag",
                    "instructions": "Keep immutable evidence and publish a corrected successor.",
                },
            },
            "automation": {
                "taskfile_path": "Taskfile.yml",
                "tasks": {
                    "plan": "release:plan",
                    "prepare": "release:prepare",
                    "verify": "release:verify",
                    "publish": "release:publish",
                },
                "github": {
                    "manual_dispatch_required": True,
                    "workflow_path": ".github/workflows/release.yml",
                    "state": "configured",
                },
            },
        }
        (repository / ".egohygiene/release.json").write_text(
            json.dumps(declaration, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (repository / ".github/workflows").mkdir(parents=True)
        (repository / ".github/workflows/release.yml").write_text(
            "---\nname: Release\non:\n  workflow_dispatch:\npermissions:\n  contents: read\njobs: {}\n",
            encoding="utf-8",
        )
        (repository / "Taskfile.yml").write_text(
            "---\nversion: \"3\"\ntasks:\n"
            "  release:plan: {}\n"
            "  release:prepare: {}\n"
            "  release:verify: {}\n"
            "  release:publish: {}\n",
            encoding="utf-8",
        )
        (repository / "release.json").write_text('{"version":"v2.0.0"}\n', encoding="utf-8")
        if promoted:
            changelog = "# Changelog\n\n## [Unreleased]\n\n## [2.0.0] - 2026-09-01\n\n### Added\n\n- Reviewed release.\n"
        else:
            changelog = "# Changelog\n\n## [Unreleased]\n\n### Added\n\n- Reviewed release.\n"
        (repository / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
        command(repository, "git", "add", ".")
        command(repository, "git", "commit", "--message", "test: release fixture")
        command(repository, "git", "push", "--set-upstream", "origin", "main")
        source = command(repository, "git", "rev-parse", "HEAD")
        return temporary, repository, remote, source

    def arguments(
        self,
        repository: Path,
        source: str,
        mode: str,
        bundle: Path | None = None,
    ) -> argparse.Namespace:
        """Return one verifier invocation."""

        return argparse.Namespace(
            repository=repository,
            repository_id="egohygiene/example",
            declaration=".egohygiene/release.json",
            component_id="example",
            release_version="v2.0.0",
            profile="github-action",
            source_revision=source,
            default_branch="main",
            mode=mode,
            bundle_directory=bundle,
            profiles_path=REPOSITORY_ROOT / "release-profiles.json",
            relay_root=REPOSITORY_ROOT,
        )

    def test_plan_accepts_human_authored_unreleased_candidate(self) -> None:
        temporary, repository, _, source = self.fixture(promoted=False)
        self.addCleanup(temporary.cleanup)

        evidence = release_plan.verify(self.arguments(repository, source, "plan"))

        self.assertEqual(evidence["status"], "verified")
        self.assertFalse(evidence["changelog"]["promoted"])
        self.assertEqual(evidence["tag_state"], "available")
        self.assertIsNone(evidence["bundle"])

    def test_verify_binds_promoted_changelog_and_complete_profile_bundle(self) -> None:
        temporary, repository, _, source = self.fixture(promoted=True)
        self.addCleanup(temporary.cleanup)
        bundle = Path(temporary.name) / "bundle"
        github_action_bundle(bundle)

        evidence = release_plan.verify(self.arguments(repository, source, "verify", bundle))

        self.assertTrue(evidence["changelog"]["promoted"])
        self.assertEqual(evidence["component"]["authoritative_version"], "v2.0.0")
        self.assertEqual(evidence["bundle"]["profile"]["id"], "github-action")

    def test_version_authority_drift_fails_closed(self) -> None:
        temporary, repository, _, source = self.fixture(promoted=False)
        self.addCleanup(temporary.cleanup)
        (repository / "release.json").write_text('{"version":"v2.0.1"}\n', encoding="utf-8")

        with self.assertRaisesRegex(release_plan.VerificationError, "version authority"):
            release_plan.verify(self.arguments(repository, source, "plan"))

    def test_verify_rejects_dirty_and_non_default_branch_sources(self) -> None:
        temporary, repository, _, source = self.fixture(promoted=True)
        self.addCleanup(temporary.cleanup)
        bundle = Path(temporary.name) / "bundle"
        github_action_bundle(bundle)
        (repository / "untracked.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaisesRegex(release_plan.VerificationError, "clean working tree"):
            release_plan.verify(self.arguments(repository, source, "verify", bundle))
        (repository / "untracked.txt").unlink()
        (repository / "local-only.txt").write_text("ahead\n", encoding="utf-8")
        command(repository, "git", "add", "local-only.txt")
        command(repository, "git", "commit", "--message", "test: local release source")
        source = command(repository, "git", "rev-parse", "HEAD")
        with self.assertRaisesRegex(release_plan.VerificationError, "current default-branch head"):
            release_plan.verify(self.arguments(repository, source, "verify", bundle))

    def test_verify_requires_promoted_changelog_and_complete_profile_evidence(self) -> None:
        temporary, repository, _, source = self.fixture(promoted=False)
        self.addCleanup(temporary.cleanup)
        bundle = Path(temporary.name) / "bundle"
        github_action_bundle(bundle)
        with self.assertRaisesRegex(release_plan.VerificationError, r"dated \[2.0.0\]"):
            release_plan.verify(self.arguments(repository, source, "verify", bundle))
        (repository / "CHANGELOG.md").write_text(
            "# Changelog\n\n## [Unreleased]\n\n## [2.0.0] - 2026-09-01\n\n- Ready.\n",
            encoding="utf-8",
        )
        command(repository, "git", "add", "CHANGELOG.md")
        command(repository, "git", "commit", "--message", "test: promote changelog")
        command(repository, "git", "push", "origin", "main")
        source = command(repository, "git", "rev-parse", "HEAD")
        (bundle / "signature.json").unlink()
        write_checksums(bundle)
        with self.assertRaisesRegex(release_plan.VerificationError, "profile evidence failed"):
            release_plan.verify(self.arguments(repository, source, "verify", bundle))

    def test_conflicting_immutable_tag_fails_closed(self) -> None:
        temporary, repository, _, _ = self.fixture(promoted=True)
        self.addCleanup(temporary.cleanup)
        command(repository, "git", "tag", "v2.0.0")
        command(repository, "git", "push", "origin", "refs/tags/v2.0.0")
        (repository / "CHANGELOG.md").write_text(
            (repository / "CHANGELOG.md").read_text(encoding="utf-8") + "\n",
            encoding="utf-8",
        )
        command(repository, "git", "add", "CHANGELOG.md")
        command(repository, "git", "commit", "--message", "test: move release source")
        command(repository, "git", "push", "origin", "main")
        source = command(repository, "git", "rev-parse", "HEAD")
        bundle = Path(temporary.name) / "bundle"
        github_action_bundle(bundle)

        with self.assertRaisesRegex(release_plan.VerificationError, "already targets another"):
            release_plan.verify(self.arguments(repository, source, "verify", bundle))

    def test_cli_retains_bounded_failure_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "failure.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "--repository-id",
                    "egohygiene/example",
                    "--release-version",
                    "not-semver",
                    "--profile",
                    "github-action",
                    "--source-revision",
                    "a" * 40,
                    "--mode",
                    "plan",
                    "--profiles-path",
                    str(REPOSITORY_ROOT / "release-profiles.json"),
                    "--evidence-output",
                    str(evidence),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            document = json.loads(evidence.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 2)
        self.assertEqual(document["status"], "failed")
        self.assertIn("vMAJOR.MINOR.PATCH", document["errors"][0])


if __name__ == "__main__":
    unittest.main()
