# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Keep repository-journal orchestration permission-separated and inspectable."""

from __future__ import annotations

from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = REPOSITORY_ROOT / ".github/workflows"


class RepositoryJournalWorkflowTests(unittest.TestCase):
    """Exercise static authority, rendering, dogfood, and CI boundaries."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.core = (WORKFLOW_ROOT / "repository-journal.yml").read_text(
            encoding="utf-8"
        )
        cls.copilot = (
            WORKFLOW_ROOT / "repository-journal-copilot.yml"
        ).read_text(encoding="utf-8")
        cls.dogfood = (
            WORKFLOW_ROOT / "repository-journal-dogfood.yml"
        ).read_text(encoding="utf-8")
        cls.action = (
            REPOSITORY_ROOT / "actions/repository-journal/action.yml"
        ).read_text(encoding="utf-8")
        cls.runner = (
            REPOSITORY_ROOT / "actions/repository-journal/journal.py"
        ).read_text(encoding="utf-8")

    def test_default_workflow_is_no_billing_and_read_only(self) -> None:
        top_level = self.core.split("\njobs:\n", maxsplit=1)[0]
        self.assertIn("permissions:\n  contents: read", top_level)
        self.assertNotIn("copilot-requests", self.core)
        for permission in (
            "actions: read",
            "contents: read",
            "issues: read",
            "pull-requests: read",
            "security-events: read",
        ):
            self.assertIn(permission, self.core)
        self.assertNotIn("actions/checkout@", self.core)
        self.assertNotIn("pull_request_target", self.core)
        self.assertIn("uses: $/actions/repository-journal", self.core)

    def test_copilot_authority_is_isolated_and_preflight_bound(self) -> None:
        self.assertIn("copilot-requests: write", self.copilot)
        self.assertNotIn("copilot-requests: write", self.core)
        self.assertNotIn("copilot-requests: write", self.dogfood)
        self.assertIn("mode: copilot", self.copilot)
        self.assertIn("organization-policy-state", self.copilot)
        self.assertIn("billing-acknowledged", self.copilot)
        self.assertIn("actions/setup-node@395ad3262231945c25e8478fd5baf05154b1d79f", self.copilot)
        self.assertNotIn("actions/checkout@", self.copilot)
        self.assertIn("--available-tools", self.runner)
        self.assertIn("--disable-builtin-mcps", self.runner)
        self.assertIn("env --ignore-environment", self.action)
        self.assertIn("trap preserve_failure ERR", self.action)
        self.assertIn("--reason execution-failed", self.action)

    def test_both_workflows_preserve_journal_and_failure_evidence(self) -> None:
        for workflow in (self.core, self.copilot):
            with self.subTest(workflow=workflow.splitlines()[5]):
                self.assertIn("continue-on-error: true", workflow)
                self.assertIn("repository-journal-summary.md", workflow)
                self.assertIn("repository-journal.md", workflow)
                self.assertIn('cat "${journal}" >> "${GITHUB_STEP_SUMMARY}"', workflow)
                self.assertIn(
                    "actions/upload-artifact@"
                    "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
                    workflow,
                )
                self.assertIn("Fail after preserving rejected evidence", workflow)

    def test_relay_dogfood_schedules_deterministic_adapter(self) -> None:
        self.assertIn("  schedule:", self.dogfood)
        self.assertIn("  workflow_dispatch:", self.dogfood)
        self.assertIn("mode: deterministic", self.dogfood)
        self.assertIn("uses: ./.github/workflows/repository-journal.yml", self.dogfood)
        self.assertNotIn("repository-journal-copilot.yml", self.dogfood)
        self.assertNotIn("actions/checkout@", self.dogfood)

    def test_validation_workflow_exercises_manual_artifact_seam(self) -> None:
        validation = (WORKFLOW_ROOT / "validate.yml").read_text(encoding="utf-8")

        self.assertIn("repository-journal-manual-smoke:", validation)
        self.assertIn("evidence-artifact-name: relay-repository-journal-evidence", validation)
        self.assertIn("candidate-artifact-name: relay-repository-journal-candidate", validation)
        self.assertIn('[[ "${STATUS}" == "complete" ]]', validation)
        self.assertIn('[[ "${RESULT_SHA256}" =~ ^[0-9a-f]{64}$ ]]', validation)


if __name__ == "__main__":
    unittest.main()
