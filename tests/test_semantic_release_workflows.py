# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Static security contracts for semantic-release orchestration."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class SemanticReleaseWorkflowTests(unittest.TestCase):
    """Keep preparation read-only and publication explicit."""

    @property
    def preparation(self) -> str:
        return (REPOSITORY_ROOT / ".github/workflows/release-prepare.yml").read_text(
            encoding="utf-8"
        )

    @property
    def publication(self) -> str:
        return (REPOSITORY_ROOT / ".github/workflows/semantic-release.yml").read_text(
            encoding="utf-8"
        )

    def test_preparation_is_read_only_and_retains_failure_evidence(self) -> None:
        self.assertIn("uses: $/actions/verify-release-plan", self.preparation)
        self.assertIn('if: "${{ always() }}"', self.preparation)
        self.assertIn("release-plan-evidence.json", self.preparation)
        self.assertIn("actions: read", self.preparation)
        self.assertNotIn("contents: write", self.preparation)
        self.assertNotIn("pull_request_target:", self.preparation)
        self.assertNotIn("gh release", self.preparation)

    def test_publication_composes_exact_review_and_immutable_release(self) -> None:
        self.assertIn(
            "uses: $/.github/workflows/release-prepare.yml", self.publication
        )
        self.assertIn(
            "uses: $/.github/workflows/release-artifact.yml", self.publication
        )
        self.assertIn('mode: "verify"', self.publication)
        self.assertIn('release-name: "${{ inputs.release-name }}"', self.publication)
        self.assertIn("release-publication-outcome.json", self.publication)
        self.assertIn('if: "${{ always() }}"', self.publication)
        self.assertNotIn("pull_request_target:", self.publication)

    def test_relay_dogfood_is_manual_and_aether_declared(self) -> None:
        workflow = (REPOSITORY_ROOT / ".github/workflows/release.yml").read_text(
            encoding="utf-8"
        )
        declaration = json.loads(
            (REPOSITORY_ROOT / ".egohygiene/release.json").read_text(
                encoding="utf-8"
            )
        )
        changelog = (REPOSITORY_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        taskfile = (REPOSITORY_ROOT / "Taskfile.yml").read_text(encoding="utf-8")

        self.assertIn("  workflow_dispatch:", workflow)
        self.assertNotIn("  push:", workflow)
        self.assertIn("uses: $/.github/workflows/semantic-release.yml", workflow)
        self.assertIn('release-name: "relay"', workflow)
        self.assertEqual(
            declaration["schema_version"], "egohygiene.repository-release/v1"
        )
        self.assertIn("## [Unreleased]", changelog)
        for task in ("release:plan", "release:prepare", "release:verify", "release:publish"):
            self.assertIn(f"{task}:", taskfile)


if __name__ == "__main__":
    unittest.main()
