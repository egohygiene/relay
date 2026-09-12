# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Static contracts for Relay's reusable profile-bound release workflow."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import subprocess
import textwrap
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY_ROOT / "scripts/validate_actions.py"
SPEC = importlib.util.spec_from_file_location("validate_actions", VALIDATOR_PATH)
assert SPEC is not None
assert SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def workflow_step_script(workflow: str, step_name: str) -> str:
    _, separator, remainder = workflow.partition(f"      - name: {step_name}\n")
    if not separator:
        raise AssertionError(f"release workflow has no {step_name} step")
    step, _, _ = remainder.partition("\n      - name: ")
    _, separator, script = step.partition("        run: |\n")
    if not separator:
        raise AssertionError(f"release workflow step {step_name} has no run block")
    return textwrap.dedent(script)


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

    def test_authorization_accepts_v0_without_accepting_leading_zeroes(self) -> None:
        guard = next(
            line
            for line in self.workflow.splitlines()
            if '"${RELEASE_VERSION}" =~ ' in line
        )
        match = re.search(r"=~ (.+) \]\]; then$", guard)
        self.assertIsNotNone(match)
        pattern = re.compile(match.group(1))

        for version in ("v0.1.0", "v0.0.1", "v1.5.0", "v12.34.56"):
            with self.subTest(version=version):
                self.assertIsNotNone(pattern.fullmatch(version))

        for version in ("v00.1.0", "v01.0.0", "v0.01.0", "v0.1.00", "1.0.0"):
            with self.subTest(version=version):
                self.assertIsNone(pattern.fullmatch(version))

    def test_release_name_is_a_bounded_product_identity(self) -> None:
        guard = next(
            line
            for line in self.workflow.splitlines()
            if '"${RELEASE_NAME}" =~ ' in line
        )
        match = re.search(r"=~ (.+) \]\]; then$", guard)
        self.assertIsNotNone(match)
        pattern = re.compile(match.group(1))

        for release_name in ("optiflow", "relay", "ego-hygiene-cli"):
            with self.subTest(release_name=release_name):
                self.assertIsNotNone(pattern.fullmatch(release_name))

        for release_name in ("OptiFlow", "optiflow/cli", "-optiflow", "optiflow-"):
            with self.subTest(release_name=release_name):
                self.assertIsNone(pattern.fullmatch(release_name))

        self.assertGreaterEqual(
            self.workflow.count('release_name="${RELEASE_NAME:-${PROFILE}}"'),
            2,
        )
        self.assertIn(
            'archive_name="${release_name}-${RELEASE_VERSION}.tar.gz"',
            self.workflow,
        )
        self.assertIn(
            'release_title="${release_name} ${RELEASE_VERSION}"',
            self.workflow,
        )
        self.assertIn('--title "${release_title}"', self.workflow)
        self.assertIn(
            '--pattern "${release_name}-${RELEASE_VERSION}.tar.gz"',
            self.workflow,
        )
        self.assertIn(
            "immutable release tag already uses another product name",
            self.workflow,
        )
        self.assertIn(
            "existing immutable release uses another product name",
            self.workflow,
        )
        self.assertIn(
            'release_notes="Profile-bound release evidence for ${PROFILE}.',
            self.workflow,
        )

    def test_release_name_shell_paths_parse(self) -> None:
        for step_name in (
            "Require caller default-branch identity and bounded inputs",
            "Package exact reviewed release bytes",
            "Verify default-branch head and publish immutable evidence",
        ):
            with self.subTest(step=step_name):
                completed = subprocess.run(
                    ["bash", "--noprofile", "--norc", "-n"],
                    input=workflow_step_script(self.workflow, step_name),
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)

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
