# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Static contract tests for the reusable artifact-budget workflow."""

from __future__ import annotations

from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPOSITORY_ROOT / ".github/workflows/artifact-budget.yml"
ACTION_PATH = REPOSITORY_ROOT / "actions/artifact-budget/action.yml"


class ArtifactBudgetWorkflowTests(unittest.TestCase):
    """Keep the artifact handoff read-only, pinned, and consumer-owned."""

    def test_workflow_is_callable_and_statically_read_only(self) -> None:
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn("workflow_call:", workflow)
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("pull_request_target", workflow)
        self.assertNotIn("actions/checkout@", workflow)
        self.assertNotIn("npm install", workflow)
        self.assertNotIn("pnpm install", workflow)

    def test_workflow_downloads_only_caller_owned_artifacts(self) -> None:
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertEqual(workflow.count("actions/download-artifact@"), 2)
        self.assertIn('name: "${{ inputs.current-artifact-name }}"', workflow)
        self.assertIn('name: "${{ inputs.baseline-artifact-name }}"', workflow)
        self.assertIn("uses: $/actions/artifact-budget", workflow)
        self.assertNotIn("uses: ./actions/artifact-budget", workflow)

    def test_workflow_uploads_report_even_after_blocking_budget_failure(self) -> None:
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn(
            'if: "${{ always() && steps.evaluate.outputs.report-sha256 != \'\' }}"',
            workflow,
        )
        self.assertIn('path: ".relay/artifact-budget/report.json"', workflow)
        self.assertIn("include-hidden-files: true", workflow)
        self.assertIn("if-no-files-found: error", workflow)

    def test_action_exposes_advisory_and_blocking_budget_inputs(self) -> None:
        action = ACTION_PATH.read_text(encoding="utf-8")

        for input_name in (
            "adapter",
            "artifact-kind",
            "current-path",
            "baseline-path",
            "current-revision",
            "baseline-revision",
            "mode",
            "maximum-bytes",
            "maximum-increase-bytes",
            "maximum-increase-percent",
            "warning-threshold-percent",
            "maximum-files",
            "maximum-items",
            "scan-maximum-bytes",
        ):
            self.assertIn(f"  {input_name}:\n", action)
        self.assertIn("set -euo pipefail", action)
        self.assertIn("${GITHUB_ACTION_PATH}/scripts/artifact_budget.py", action)


if __name__ == "__main__":
    unittest.main()
