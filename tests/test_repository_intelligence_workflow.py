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
GENERATOR_MANIFEST = REPOSITORY_ROOT / "actions/repository-intelligence/action.yml"
EVIDENCE_MANIFEST = (
    REPOSITORY_ROOT / "actions/repository-intelligence/workflow-evidence/action.yml"
)


class RepositoryIntelligenceWorkflowTests(unittest.TestCase):
    """Keep reusable orchestration aligned with the current action boundary."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        cls.validation = VALIDATION_PATH.read_text(encoding="utf-8")
        cls.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        cls.documentation = PUBLICATION_DOC.read_text(encoding="utf-8")
        cls.generator_manifest = GENERATOR_MANIFEST.read_text(encoding="utf-8")
        cls.evidence_manifest = EVIDENCE_MANIFEST.read_text(encoding="utf-8")

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

        generate = self.workflow.split("\n  generate:\n", maxsplit=1)[1]
        self.assertIn("    permissions:\n      contents: read", generate)
        for forbidden in (
            "contents: write",
            "pages: write",
            "id-token: write",
            "pull_request_target:",
            "actions/cache@",
            "restore-keys:",
            "secrets: inherit",
            "${{ github.token }}",
            "actions/deploy-pages@",
            "actions/upload-pages-artifact@",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.workflow)

    def test_exact_revision_actions_and_remote_pins_are_closed(self) -> None:
        """Resolve Relay helpers internally and pin every third-party action."""

        self.assertEqual(
            self.workflow.count(
                "uses: $/actions/repository-intelligence/workflow-evidence"
            ),
            2,
        )
        self.assertEqual(
            self.workflow.count("uses: $/actions/repository-intelligence\n"),
            1,
        )
        self.assertEqual(
            self.workflow.count("uses: $/actions/preserve-ci-report"),
            1,
        )
        self.assertNotIn("uses: ./actions/", self.workflow)

        references = re.findall(r"^\s*uses:\s*([^\s#]+)", self.workflow, re.MULTILINE)
        remote = [
            reference
            for reference in references
            if not reference.startswith(("./", "$/"))
        ]
        self.assertGreaterEqual(len(remote), 3)
        for reference in remote:
            with self.subTest(reference=reference):
                self.assertRegex(reference, r"@[0-9a-f]{40}$")

    def test_checkout_and_failure_evidence_are_explicit(self) -> None:
        """Bind source bytes and preserve evidence before reasserting failure."""

        checkout = re.search(
            r"      - name: Checkout caller repository with complete history\n"
            r"(?P<body>.*?)(?=\n      - name:)",
            self.workflow,
            re.DOTALL,
        )
        self.assertIsNotNone(checkout)
        self.assertIn('ref: "${{ github.sha }}"', checkout.group("body"))
        self.assertIn("persist-credentials: false", checkout.group("body"))
        self.assertIn("fetch-depth: 0", checkout.group("body"))
        self.assertIn("continue-on-error: true", checkout.group("body"))

        self.assertIn('id: finalize\n        if: "${{ always() }}"', self.workflow)
        self.assertIn(
            'id: preserve\n        if: "${{ always() && steps.finalize.outcome == \'success\' }}"',
            self.workflow,
        )
        self.assertIn(
            "producer: repository-intelligence-v1",
            self.workflow,
        )
        self.assertIn(
            'source-directory: "${{ steps.finalize.outputs.report-directory }}"',
            self.workflow,
        )
        self.assertIn("retention-days: 30", self.workflow)
        self.assertIn(
            "Reassert Repository Intelligence result after evidence preservation",
            self.workflow,
        )
        self.assertGreaterEqual(self.workflow.count('if: "${{ always() }}"'), 3)
        self.assertIn("steps.preserve.outcome", self.workflow)
        self.assertIn("steps.finalize.outputs.workflow-outcome", self.workflow)

    def test_concurrency_is_partitioned_by_contract_workflow_ref_and_target_ref(self) -> None:
        """Cancel only superseded work for one logical caller target."""

        expression = (
            "relay-intelligence-v1-${{ github.repository }}-"
            "${{ github.workflow_ref }}-${{ github.ref }}"
        )
        self.assertIn(f'group: "{expression}"', self.workflow)
        self.assertIn("cancel-in-progress: true", self.workflow)

        def key(
            repository: str,
            workflow_ref: str,
            target_ref: str,
            contract: str = "v1",
        ) -> str:
            return (
                f"relay-intelligence-{contract}-{repository}-"
                f"{workflow_ref}-{target_ref}"
            )

        caller = "example/one/.github/workflows/ci.yml@refs/heads/main"
        baseline = key("example/one", caller, "refs/heads/main")
        self.assertEqual(baseline, key("example/one", caller, "refs/heads/main"))
        self.assertNotEqual(baseline, key("example/two", caller, "refs/heads/main"))
        self.assertNotEqual(
            baseline,
            key(
                "example/one",
                "example/one/.github/workflows/review.yml@refs/heads/main",
                "refs/heads/main",
            ),
        )
        self.assertNotEqual(baseline, key("example/one", caller, "refs/heads/review"))
        self.assertNotEqual(baseline, key("example/one", caller, "refs/heads/main", "v2"))

    def test_repository_intelligence_python_entrypoints_are_isolated(self) -> None:
        """Prevent caller checkout modules from shadowing inline Python imports."""

        manifests = {
            WORKFLOW_PATH: self.workflow,
            GENERATOR_MANIFEST: self.generator_manifest,
            EVIDENCE_MANIFEST: self.evidence_manifest,
        }
        for path, manifest in manifests.items():
            for number, line in enumerate(manifest.splitlines(), start=1):
                if "python3" in line and "<<" in line:
                    with self.subTest(path=path, line=number):
                        self.assertRegex(line, r"\bpython3\s+-I\s+-(?:\s|$)")
                if re.search(r"\bpython3\s+-\s", line):
                    self.fail(f"unisolated Python stdin execution in {path}:{number}")
        self.assertIn(
            'python3 -I "${GITHUB_ACTION_PATH}/scripts/'
            'repository_intelligence_workflow_evidence.py"',
            self.evidence_manifest,
        )

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

    def test_smoke_consumer_validates_durable_artifact_evidence_outputs(self) -> None:
        """Exercise both site and run-report output identities after the smoke call."""

        match = re.search(
            r"^  intelligence-smoke-outputs:\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:|\Z)",
            self.validation,
            re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match)
        body = match.group("body")
        self.assertIn("needs: intelligence-smoke", body)
        self.assertIn("permissions: {}", body)
        for output in (
            "build-manifest-sha256",
            "bundle-digest",
            "report-artifact-digest",
            "report-artifact-name",
            "report-manifest-sha256",
            "artifact-digest",
            "artifact-name",
        ):
            with self.subTest(output=output):
                self.assertIn(
                    f"needs.intelligence-smoke.outputs.{output}",
                    body,
                )
        for expected_pattern in (
            "^repository-intelligence-site-v1-",
            "^(sha256:)?[0-9a-f]{64}$",
            "^relay-report-repository-intelligence-v1-",
            "^[0-9a-f]{64}$",
        ):
            with self.subTest(pattern=expected_pattern):
                self.assertIn(expected_pattern, body)

    def test_deployment_provenance_smoke_is_fixture_only_and_read_only(self) -> None:
        """Exercise the action wrapper without granting deployment authority."""

        match = re.search(
            r"^  intelligence-deployment-provenance-smoke:\n"
            r"(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:|\Z)",
            self.validation,
            re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match)
        body = match.group("body")
        self.assertIn("actions: read\n      contents: read", body)
        self.assertEqual(
            body.count("uses: ./actions/repository-intelligence-deployment-provenance"),
            3,
        )
        self.assertIn("operation: capture-baseline", body)
        self.assertIn("operation: record-receipt", body)
        self.assertIn("operation: verify-receipt", body)
        self.assertIn("deployment-environment: fixture-only", body)
        self.assertIn("repository-intelligence-deployment-provenance-fixture-", body)
        for forbidden in (
            "pages: write",
            "id-token: write",
            "contents: write",
            "actions/deploy-pages@",
            "secrets.",
            "github.token",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, body)

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
