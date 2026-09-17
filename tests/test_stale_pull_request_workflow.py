# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Security and caller-contract tests for stale lifecycle orchestration."""

from __future__ import annotations

from pathlib import Path
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPOSITORY_ROOT / ".github/workflows/stale-pull-requests.yml"
EXAMPLE = REPOSITORY_ROOT / "examples/workflows/stale-pull-requests.md"
ACTION = REPOSITORY_ROOT / "actions/stale-pull-requests/action.yml"


class StalePullRequestWorkflowTests(unittest.TestCase):
    """Keep advisory evidence separate from authorized provider mutation."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.example = EXAMPLE.read_text(encoding="utf-8")
        cls.action = ACTION.read_text(encoding="utf-8")

    def test_workflow_is_advisory_and_pull_request_only_by_default(self) -> None:
        self.assertIn("  workflow_call:", self.workflow)
        self.assertRegex(
            self.workflow,
            r"(?s)      advisory:.*?        default: true",
        )
        self.assertRegex(
            self.workflow,
            r"(?s)      process-issues:.*?        default: false",
        )
        self.assertRegex(
            self.workflow,
            r"(?s)      close-enabled:.*?        default: false",
        )
        self.assertIn('default: ""\n      exempt-labels:', self.workflow)

    def test_read_only_plan_precedes_conditional_write_job(self) -> None:
        pr_plan_start = self.workflow.index("  plan_pull_requests:")
        issue_plan_start = self.workflow.index("  plan_pull_requests_and_issues:")
        pr_apply_start = self.workflow.index("  apply_pull_requests:")
        issue_apply_start = self.workflow.index("  apply_pull_requests_and_issues:")
        self.assertLess(pr_plan_start, issue_plan_start)
        self.assertLess(issue_plan_start, pr_apply_start)
        self.assertLess(pr_apply_start, issue_apply_start)

        pr_plan = self.workflow[pr_plan_start:issue_plan_start]
        issue_plan = self.workflow[issue_plan_start:pr_apply_start]
        pr_apply = self.workflow[pr_apply_start:issue_apply_start]
        issue_apply = self.workflow[issue_apply_start:]

        self.assertIn('if: "${{ inputs.process-issues == false }}"', pr_plan)
        self.assertIn("      pull-requests: read", pr_plan)
        self.assertNotIn("      issues:", pr_plan)
        self.assertNotIn("pull-requests: write", pr_plan)

        self.assertIn('if: "${{ inputs.process-issues == true }}"', issue_plan)
        self.assertIn("      issues: read", issue_plan)
        self.assertIn("      pull-requests: read", issue_plan)
        self.assertNotIn("pull-requests: write", issue_plan)

        self.assertIn(
            'if: "${{ inputs.advisory == false && inputs.process-issues == false }}"',
            pr_apply,
        )
        self.assertIn("needs: plan_pull_requests", pr_apply)
        self.assertIn("      pull-requests: write", pr_apply)
        self.assertNotIn("      issues:", pr_apply)

        self.assertIn(
            'if: "${{ inputs.advisory == false && inputs.process-issues == true }}"',
            issue_apply,
        )
        self.assertIn("needs: plan_pull_requests_and_issues", issue_apply)
        self.assertIn("      issues: write", issue_apply)
        self.assertIn("      pull-requests: write", issue_apply)

        self.assertEqual(
            self.workflow.count("Authorize default-branch enforcement"), 2
        )
        self.assertEqual(
            self.workflow.count(
                '[[ "${REQUESTED_REF}" == "refs/heads/${DEFAULT_BRANCH}" ]]'
            ),
            2,
        )

    def test_apply_consumes_the_exact_checksum_bound_plan(self) -> None:
        self.assertEqual(
            self.workflow.count(
                "printf 'artifact-name=relay-stale-plan-%s\\n' \"${PLAN_SHA256}\""
            ),
            2,
        )
        for plan_job in ("plan_pull_requests", "plan_pull_requests_and_issues"):
            self.assertIn(
                f'name: "${{{{ needs.{plan_job}.outputs.artifact-name }}}}"',
                self.workflow,
            )
            self.assertIn(
                f'expected-plan-sha256: "${{{{ needs.{plan_job}.outputs.plan-sha256 }}}}"',
                self.workflow,
            )
        for name in (
            "inactivity-days",
            "warning-days",
            "stale-label",
            "closed-label",
            "exempt-labels",
            "exempt-users",
            "exempt-review-teams",
            "exempt-drafts",
            "exempt-bots",
            "process-issues",
            "close-enabled",
            "maximum-items",
            "warning-message",
            "close-message",
        ):
            self.assertEqual(
                self.workflow.count(f'{name}: "${{{{ inputs.{name} }}}}"'),
                4,
                name,
            )
        self.assertEqual(
            self.workflow.count("Revalidate live state and apply authorized changes"),
            2,
        )

    def test_outputs_select_the_only_active_plan_job(self) -> None:
        for name in (
            "artifact-name",
            "plan-sha256",
            "candidate-count",
            "warning-count",
            "closure-count",
            "reset-count",
            "exemption-count",
        ):
            self.assertIn(
                f"jobs.plan_pull_requests.outputs.{name} || "
                f"jobs.plan_pull_requests_and_issues.outputs.{name}",
                self.workflow,
            )

    def test_workflow_uses_exact_relay_revision_without_consumer_code(self) -> None:
        self.assertEqual(
            self.workflow.count("uses: $/actions/stale-pull-requests"), 4
        )
        self.assertNotIn("actions/checkout@", self.workflow)
        self.assertNotIn("uses: ./actions/stale-pull-requests", self.workflow)
        self.assertNotIn("actions/stale@", self.workflow)
        self.assertNotIn("pull_request_target", self.workflow)
        self.assertNotIn("delete-branch", self.workflow)
        self.assertIn("cancel-in-progress: false", self.workflow)

    def test_evaluation_time_is_plan_only_and_apply_rejects_it(self) -> None:
        self.assertIn(
            'if [[ -n "${INPUT_EVALUATION_TIME}" ]]; then', self.action
        )
        self.assertIn(
            "evaluation-time is plan-only and must be empty during apply",
            self.action,
        )

    def test_consumer_example_owns_schedule_and_permission_transition(self) -> None:
        self.assertIn('cron: "17 4 * * *"', self.example)
        self.assertIn("@<full-relay-commit-sha>", self.example)
        self.assertIn("      pull-requests: read", self.example)
        self.assertIn("      pull-requests: write", self.example)
        self.assertNotIn("      issues: read", self.example)
        self.assertNotIn("      issues: write", self.example)
        self.assertIn("add `issues: read` to advisory jobs", self.example)
        self.assertIn("      advisory: true", self.example)
        self.assertIn("      advisory: false", self.example)
        self.assertIn("      close-enabled: false", self.example)


if __name__ == "__main__":
    unittest.main()
