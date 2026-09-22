# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Mutation tests for Repository Intelligence workflow stage gates."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import shutil
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY_ROOT / "scripts/validate_actions.py"
WORKFLOW_PATH = REPOSITORY_ROOT / ".github/workflows/repository-intelligence.yml"
STEP_PATTERN = re.compile(
    r"^      - (?P<body>.*?)(?=^      - |\Z)",
    re.MULTILINE | re.DOTALL,
)

SPEC = importlib.util.spec_from_file_location("validate_actions", VALIDATOR_PATH)
assert SPEC is not None
assert SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class RepositoryIntelligenceWorkflowGateTests(unittest.TestCase):
    """Reject orchestration mutations that bypass durable failure evidence."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    def validate_workflow(self, workflow: str) -> list[str]:
        """Validate one mutated workflow in a minimal isolated repository."""

        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "relay"
        workflow_path = root / ".github/workflows/repository-intelligence.yml"
        workflow_path.parent.mkdir(parents=True)
        workflow_path.write_text(workflow, encoding="utf-8")

        source_action = REPOSITORY_ROOT / "actions/repository-intelligence"
        target_action = root / "actions/repository-intelligence"
        target_action.mkdir(parents=True)
        shutil.copy2(source_action / "action.yml", target_action / "action.yml")
        shutil.copytree(
            source_action / "workflow-evidence",
            target_action / "workflow-evidence",
        )

        errors: list[str] = []
        validator.validate_repository_intelligence_workflow(root, errors)
        return errors

    def mutate_step(
        self,
        marker: str,
        original: str,
        replacement: str,
    ) -> str:
        """Replace text in exactly one workflow step selected by a stable marker."""

        matches = [
            match
            for match in STEP_PATTERN.finditer(self.workflow)
            if marker in match.group("body")
        ]
        self.assertEqual(len(matches), 1, marker)
        match = matches[0]
        body = match.group("body")
        self.assertEqual(body.count(original), 1, marker)
        mutated = body.replace(original, replacement, 1)
        return (
            self.workflow[: match.start("body")]
            + mutated
            + self.workflow[match.end("body") :]
        )

    def swap_steps(self, first_marker: str, second_marker: str) -> str:
        """Swap two complete steps while preserving their unmodified bodies."""

        matches = list(STEP_PATTERN.finditer(self.workflow))
        blocks = [match.group(0) for match in matches]
        first = [index for index, block in enumerate(blocks) if first_marker in block]
        second = [index for index, block in enumerate(blocks) if second_marker in block]
        self.assertEqual(len(first), 1, first_marker)
        self.assertEqual(len(second), 1, second_marker)
        blocks[first[0]], blocks[second[0]] = blocks[second[0]], blocks[first[0]]
        return (
            self.workflow[: matches[0].start()]
            + "".join(blocks)
            + self.workflow[matches[-1].end() :]
        )

    def test_canonical_workflow_passes_gate_validation(self) -> None:
        self.assertEqual(self.validate_workflow(self.workflow), [])

    def test_every_critical_stage_order_is_enforced(self) -> None:
        order_error = (
            "repository-intelligence workflow steps must preserve the exact "
            "harden, preflight, checkout, generation, provenance, site upload, "
            "finalize, preserve, summary, and final reassertion order"
        )
        adjacent_stages = (
            ("        id: checkout\n", "        id: generation\n"),
            ("        id: generation\n", "        id: provenance\n"),
            ("        id: provenance\n", "        id: site\n"),
            ("        id: site\n", "        id: finalize\n"),
            ("        id: finalize\n", "        id: preserve\n"),
            (
                "        id: preserve\n",
                "name: Reassert Repository Intelligence result after evidence preservation",
            ),
        )

        for first, second in adjacent_stages:
            with self.subTest(first=first.strip(), second=second.strip()):
                errors = self.validate_workflow(self.swap_steps(first, second))
                self.assertIn(order_error, errors)

    def test_stage_dependency_gates_are_exact(self) -> None:
        cases = (
            (
                "preflight",
                "        id: preflight\n",
                '        if: "${{ steps.harden.outcome == \'success\' }}"',
                '        if: "${{ always() }}"',
            ),
            (
                "checkout",
                "        id: checkout\n",
                """        if: >-
          ${{ steps.harden.outcome == 'success' &&
          steps.preflight.outcome == 'success' }}""",
                '        if: "${{ steps.harden.outcome == \'success\' }}"',
            ),
            (
                "generation",
                "        id: generation\n",
                """        if: >-
          ${{ steps.harden.outcome == 'success' &&
          steps.preflight.outcome == 'success' &&
          steps.checkout.outcome == 'success' }}""",
                """        if: >-
          ${{ steps.harden.outcome == 'success' &&
          steps.preflight.outcome == 'success' }}""",
            ),
            (
                "provenance",
                "        id: provenance\n",
                '        if: "${{ steps.generation.outcome == \'success\' }}"',
                '        if: "${{ always() }}"',
            ),
            (
                "site",
                "        id: site\n",
                '        if: "${{ steps.provenance.outcome == \'success\' }}"',
                '        if: "${{ steps.generation.outcome == \'success\' }}"',
            ),
            (
                "finalize",
                "        id: finalize\n",
                '        if: "${{ always() }}"',
                '        if: "${{ success() }}"',
            ),
            (
                "preserve",
                "        id: preserve\n",
                (
                    '        if: "${{ always() && '
                    "steps.finalize.outcome == 'success' }}\""
                ),
                '        if: "${{ steps.finalize.outcome == \'success\' }}"',
            ),
        )

        for identifier, marker, original, replacement in cases:
            with self.subTest(stage=identifier):
                mutated = self.mutate_step(marker, original, replacement)
                self.assertIn(
                    "repository-intelligence workflow has an unsafe execution "
                    f"gate for {identifier}",
                    self.validate_workflow(mutated),
                )

    def test_each_outcome_stage_must_continue_to_finalization(self) -> None:
        for identifier in (
            "harden",
            "preflight",
            "checkout",
            "generation",
            "provenance",
            "site",
            "finalize",
            "preserve",
        ):
            with self.subTest(stage=identifier):
                mutated = self.mutate_step(
                    f"        id: {identifier}\n",
                    "        continue-on-error: true\n",
                    "",
                )
                self.assertIn(
                    "repository-intelligence workflow must capture the outcome and "
                    f"continue to durable finalization after {identifier}",
                    self.validate_workflow(mutated),
                )

    def test_final_reassertion_requires_always_and_cannot_continue(self) -> None:
        marker = (
            "name: Reassert Repository Intelligence result after evidence preservation"
        )
        condition_mutation = self.mutate_step(
            marker,
            '        if: "${{ always() }}"',
            '        if: "${{ success() }}"',
        )
        continue_mutation = self.mutate_step(
            marker,
            '        if: "${{ always() }}"\n',
            '        if: "${{ always() }}"\n        continue-on-error: true\n',
        )
        expected = (
            "repository-intelligence final result gate must run with always() and "
            "fail closed on finalize, preserve, and workflow outcomes"
        )

        self.assertIn(expected, self.validate_workflow(condition_mutation))
        self.assertIn(expected, self.validate_workflow(continue_mutation))

    def test_final_reassertion_comparisons_fail_closed(self) -> None:
        marker = (
            "name: Reassert Repository Intelligence result after evidence preservation"
        )
        for variable in (
            "FINALIZE_OUTCOME",
            "PRESERVE_OUTCOME",
            "WORKFLOW_OUTCOME",
        ):
            with self.subTest(variable=variable):
                mutated = self.mutate_step(
                    marker,
                    f'if [[ "${{{variable}}}" != "success" ]]; then',
                    f'if [[ "${{{variable}}}" == "success" ]]; then',
                )
                self.assertIn(
                    "repository-intelligence final result gate must run with always() "
                    "and fail closed on finalize, preserve, and workflow outcomes",
                    self.validate_workflow(mutated),
                )


if __name__ == "__main__":
    unittest.main()
