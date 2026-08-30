# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Tests for profile-bound release validation and deterministic evidence."""

from __future__ import annotations

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
    / "actions/validate-release-bundle/scripts/validate_release_bundle.py"
)
SPEC = importlib.util.spec_from_file_location("validate_release_bundle", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
release_bundle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_bundle)

SOURCE_REVISION = "a" * 40


def write_checksums(directory: Path) -> None:
    """Write Relay's complete sorted SHA256SUMS convention for a test bundle."""

    records = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            relative = path.relative_to(directory).as_posix()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            records.append(f"{digest}  {relative}")
    (directory / "SHA256SUMS").write_text("\n".join(records) + "\n", encoding="utf-8")


def profile_bundle(directory: Path, profile: str) -> None:
    """Build the minimal evidence bundle accepted by one checked-in profile."""

    shared = {
        "provenance.json": "{}\n",
        "sbom.spdx.json": "{}\n",
        "signature.json": "{}\n",
    }
    for relative, content in shared.items():
        (directory / relative).write_text(content, encoding="utf-8")
    profile_files = {
        "binary": {"tool.zip": "binary payload\n"},
        "container-image": {"image-digest.json": "{}\n"},
        "github-action": {
            "action-catalog.json": "{}\n",
            "workflow-catalog.json": "{}\n",
            "relay.tar.gz": "action payload\n",
        },
        "npm-specification": {"package.json": "{}\n", "package.tgz": "package payload\n"},
        "pdfa-document": {"paper.pdf": "%PDF-1.7\n", "pdfa-validation.json": "{}\n"},
        "static-site": {"index.html": "<!doctype html>\n", "site.json": "{}\n"},
    }
    for relative, content in profile_files[profile].items():
        (directory / relative).write_text(content, encoding="utf-8")
    write_checksums(directory)


class ReleaseProfileTests(unittest.TestCase):
    """Require every profile to preserve a strict, portable evidence boundary."""

    def validate(self, directory: Path, profile: str) -> dict:
        """Validate one temporary bundle with the canonical profile catalog."""

        return release_bundle.validate_release_bundle(
            bundle_directory=directory,
            profiles_path=REPOSITORY_ROOT / "release-profiles.json",
            profile_id=profile,
            release_version="v1.4.0",
            source_revision=SOURCE_REVISION,
        )

    def test_every_required_repository_class_has_a_valid_minimal_bundle(self) -> None:
        profiles = (
            "binary",
            "container-image",
            "github-action",
            "npm-specification",
            "pdfa-document",
            "static-site",
        )
        for profile in profiles:
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                profile_bundle(directory, profile)
                evidence = self.validate(directory, profile)
                self.assertEqual(evidence["schema"], "egohygiene.relay-release-evidence/v1")
                self.assertEqual(evidence["profile"]["id"], profile)
                self.assertEqual(evidence["release_version"], "v1.4.0")
                self.assertEqual(evidence["source_revision"], SOURCE_REVISION)
                self.assertTrue(evidence["rollback"]["instructions"])

    def test_evidence_is_byte_stable_and_binds_the_complete_checksum_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            profile_bundle(directory, "npm-specification")
            first = self.validate(directory, "npm-specification")
            second = self.validate(directory, "npm-specification")
        self.assertEqual(first, second)
        self.assertEqual(first["bundle"]["verified_checksum_count"], 5)
        self.assertEqual(first["bundle"]["file_count"], 6)

    def test_checksum_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            profile_bundle(directory, "binary")
            (directory / "tool.zip").write_text("tampered\n", encoding="utf-8")
            with self.assertRaisesRegex(release_bundle.ValidationError, "checksum mismatch"):
                self.validate(directory, "binary")

    def test_missing_profile_specific_evidence_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            profile_bundle(directory, "container-image")
            (directory / "image-digest.json").unlink()
            write_checksums(directory)
            with self.assertRaisesRegex(release_bundle.ValidationError, "requires image-digest.json"):
                self.validate(directory, "container-image")

    def test_symlinked_release_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            profile_bundle(directory, "static-site")
            (directory / "linked-index.html").symlink_to(directory / "index.html")
            write_checksums(directory)
            with self.assertRaisesRegex(release_bundle.ValidationError, "must not contain symlinks"):
                self.validate(directory, "static-site")

    def test_cli_writes_canonical_evidence_and_github_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            profile_bundle(directory, "pdfa-document")
            evidence_output = directory / "release-evidence.json"
            github_output = directory / "github-output.txt"
            result = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "--bundle-directory",
                    str(directory),
                    "--evidence-output",
                    str(evidence_output),
                    "--github-output",
                    str(github_output),
                    "--profile",
                    "pdfa-document",
                    "--profiles-path",
                    str(REPOSITORY_ROOT / "release-profiles.json"),
                    "--release-version",
                    "v1.4.0",
                    "--source-revision",
                    SOURCE_REVISION,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Validated release bundle profile=pdfa-document", result.stdout)
            self.assertIn("pdfa-document", evidence_output.read_text(encoding="utf-8"))
            self.assertRegex(
                github_output.read_text(encoding="utf-8"),
                r"release-evidence-sha256=[0-9a-f]{64}",
            )


if __name__ == "__main__":
    unittest.main()
