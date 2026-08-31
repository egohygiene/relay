# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Static contracts for Relay's reusable profile-bound release workflow."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY_ROOT / "scripts/validate_actions.py"
SPEC = importlib.util.spec_from_file_location("validate_actions", VALIDATOR_PATH)
assert SPEC is not None
assert SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class ReleaseArtifactWorkflowTests(unittest.TestCase):
    """Keep release evidence separate from consumer-controlled adapters."""

    @property
    def workflow(self) -> str:
        return (REPOSITORY_ROOT / ".github/workflows/release-artifact.yml").read_text(
            encoding="utf-8"
        )

    def test_uses_profile_validator_from_the_exact_called_relay_revision(self) -> None:
        self.assertIn("uses: $/actions/validate-release-bundle", self.workflow)
        self.assertNotIn("uses: ./actions/validate-release-bundle", self.workflow)
        self.assertIn("release-profiles.json", (REPOSITORY_ROOT / "RELEASE_PROFILES.md").read_text(encoding="utf-8"))

    def test_requires_default_branch_and_immutable_commit_identity(self) -> None:
        self.assertIn("release publication requires the caller repository default branch", self.workflow)
        self.assertIn("expected-source-revision must equal the caller workflow SHA", self.workflow)
        self.assertIn("release must represent the current caller default-branch head", self.workflow)
        self.assertIn("immutable release tag already targets another commit", self.workflow)
        self.assertNotIn("pull_request_target:", self.workflow)

    def test_publishes_exactly_the_reviewed_release_evidence_assets(self) -> None:
        self.assertIn("release-evidence.json", self.workflow)
        self.assertIn("release-asset.sha256", self.workflow)
        self.assertIn("gh release create", self.workflow)
        self.assertIn("gh release upload", self.workflow)
        self.assertIn("existing immutable release evidence differs from this request", self.workflow)
        self.assertIn("existing release contains unexpected immutable assets", self.workflow)
        self.assertIn("sha256sum --check --strict", self.workflow)
        self.assertNotIn("--clobber", self.workflow)
        self.assertIn("rollback-reference", self.workflow)

    def test_catalog_validator_accepts_the_release_profile_surface(self) -> None:
        self.assertEqual(validator.validate_catalog(REPOSITORY_ROOT), [])


if __name__ == "__main__":
    unittest.main()
