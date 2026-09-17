# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Contract tests for the reusable Repository Intelligence artifact workflow."""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPOSITORY_ROOT / ".github/workflows/repository-intelligence.yml"
VALIDATION_PATH = REPOSITORY_ROOT / ".github/workflows/validate.yml"
CATALOG_PATH = REPOSITORY_ROOT / "workflow-catalog.json"
PUBLICATION_DOC = REPOSITORY_ROOT / "docs/repository-intelligence-publication.md"


class RepositoryIntelligenceWorkflowTests(unittest.TestCase):
    """Keep reusable orchestration aligned with the current action boundary."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        cls.validation = VALIDATION_PATH.read_text(encoding="utf-8")
        cls.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        cls.documentation = PUBLICATION_DOC.read_text(encoding="utf-8")

    def repository_intelligence_catalog_entry(self) -> dict[str, object]:
        """Return the single machine-readable reusable workflow declaration."""

        matches = [
            entry
            for entry in self.catalog["workflows"]
            if entry["id"] == "repository-intelligence"
        ]
        self.assertEqual(len(matches), 1)
        return matches[0]

    def test_workflow_exposes_both_observatory_inputs_for_call_and_dispatch(self) -> None:
        """Require snapshot/comparison parity on both public invocation surfaces."""

        for input_name in ("observatory-snapshot", "observatory-comparison"):
            with self.subTest(input_name=input_name):
                self.assertEqual(
                    len(re.findall(rf"^      {re.escape(input_name)}:$", self.workflow, re.MULTILINE)),
                    2,
                )
        self.assertGreaterEqual(self.workflow.count('default: ""'), 6)

    def test_workflow_forwards_observatory_inputs_without_local_semantics(self) -> None:
        """Forward normalized evidence paths to the exact-revision action unchanged."""

        self.assertIn("uses: $/actions/repository-intelligence", self.workflow)
        self.assertNotIn("uses: ./actions/repository-intelligence", self.workflow)
        self.assertIn(
            'observatory-snapshot: "${{ inputs.observatory-snapshot }}"',
            self.workflow,
        )
        self.assertIn(
            'observatory-comparison: "${{ inputs.observatory-comparison }}"',
            self.workflow,
        )
        self.assertNotIn("compare_snapshots", self.workflow)
        self.assertNotIn("score:", self.workflow)

    def test_workflow_remains_read_only_and_artifact_only(self) -> None:
        """Keep consumer-owned deployment authority outside this workflow."""

        top_level = self.workflow.split("\njobs:\n", maxsplit=1)[0]
        self.assertIn("permissions:\n  contents: read", top_level)
        self.assertNotIn("contents: write", self.workflow)
        self.assertNotIn("pages: write", self.workflow)
        self.assertNotIn("id-token: write", self.workflow)
        self.assertNotIn("actions/deploy-pages@", self.workflow)
        self.assertNotIn("actions/upload-pages-artifact@", self.workflow)
        self.assertIn("actions/upload-artifact@", self.workflow)

    def test_catalog_declares_current_observatory_workflow_inputs(self) -> None:
        """Keep the machine-readable workflow contract synchronized with YAML."""

        entry = self.repository_intelligence_catalog_entry()
        inputs = {
            parameter["name"]: parameter
            for parameter in entry["inputs"]
        }
        for input_name in ("observatory-snapshot", "observatory-comparison"):
            with self.subTest(input_name=input_name):
                self.assertIn(input_name, inputs)
                self.assertEqual(inputs[input_name]["type"], "string")
                self.assertFalse(inputs[input_name]["required"])
                self.assertEqual(inputs[input_name]["default"], "")

    def test_existing_smoke_call_remains_the_partial_adoption_canary(self) -> None:
        """No-snapshot workflow execution must stay a first-class tested path."""

        match = re.search(
            r"^  intelligence-smoke:\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:|\Z)",
            self.validation,
            re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match)
        body = match.group("body")
        self.assertIn("uses: $/.github/workflows/repository-intelligence.yml", body)
        self.assertNotIn("observatory-snapshot:", body)
        self.assertNotIn("observatory-comparison:", body)

    def test_documentation_preserves_direct_action_and_workflow_boundaries(self) -> None:
        """Document real consumer composition without implying Relay deployment authority."""

        for required in (
            "Existing site or Pages build: use the composite action",
            "Standalone review artifact: use the reusable workflow",
            "observatory-snapshot",
            "observatory-comparison",
            "egohygiene/empathy",
            "egohygiene/akashic",
            "consumer repository remains the only owner",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.documentation)


if __name__ == "__main__":
    unittest.main()
