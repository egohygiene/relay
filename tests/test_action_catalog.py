# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Tests for Relay action discovery and catalog integrity."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPOSITORY_ROOT / "scripts/validate_actions.py"
SPEC = importlib.util.spec_from_file_location("validate_actions", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class ActionCatalogTests(unittest.TestCase):
    """Require every public action to remain packaged and discoverable."""

    def test_catalog_matches_discovered_actions(self) -> None:
        self.assertEqual(validator.validate_catalog(REPOSITORY_ROOT), [])

    def test_expected_first_release_actions_are_present(self) -> None:
        self.assertEqual(
            validator.discovered_action_paths(REPOSITORY_ROOT),
            {
                "actions/normalize-repository-report",
                "actions/publish-report-snapshot",
                "actions/repository-intelligence",
            },
        )

    def test_reusable_workflow_resolves_its_own_relay_revision(self) -> None:
        workflow = (
            REPOSITORY_ROOT / ".github/workflows/repository-intelligence.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("uses: $/actions/repository-intelligence", workflow)
        self.assertNotIn("uses: ./actions/repository-intelligence", workflow)
        self.assertEqual(
            validator.discovered_reusable_workflows(REPOSITORY_ROOT),
            {".github/workflows/repository-intelligence.yml"},
        )

    def test_dashboard_action_guards_artifact_path_scope(self) -> None:
        action = (
            REPOSITORY_ROOT / "actions/repository-intelligence/action.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("^[A-Za-z0-9._-]+(/[A-Za-z0-9._-]+)*$", action)
        self.assertIn("reports-directory and output-directory must not overlap", action)
        self.assertIn("repository must not override the GitHub workflow repository", action)
        self.assertEqual(
            action.count(
                "${INPUT_WORK_DIRECTORY},${INPUT_REPORTS_DIRECTORY},${INPUT_OUTPUT_DIRECTORY}"
            ),
            2,
        )
        workflow_identity = action.index(
            'if [[ "${RELAY_WORKFLOW_REPOSITORY}" == "egohygiene/relay"'
        )
        direct_action_identity = action.index(
            'elif [[ "${generator_repository}" == "egohygiene/relay"'
        )
        self.assertLess(workflow_identity, direct_action_identity)
        self.assertIn(
            "egohygiene/relay/.github/workflows/repository-intelligence.yml@*",
            action,
        )
        self.assertIn("INPUT_MAX_DEPTH > 20", action)

    def test_validation_and_release_gates_are_present(self) -> None:
        validation = (REPOSITORY_ROOT / ".github/workflows/validate.yml").read_text(
            encoding="utf-8"
        )
        release = (REPOSITORY_ROOT / ".github/workflows/release.yml").read_text(
            encoding="utf-8"
        )
        reusable = (
            REPOSITORY_ROOT / ".github/workflows/repository-intelligence.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("python3 -m unittest discover", validation)
        self.assertIn("python3 -m compileall", validation)
        self.assertIn("bash -n", validation)
        self.assertIn("uses: $/.github/workflows/repository-intelligence.yml", validation)
        self.assertIn("Verify reusable-workflow generator provenance", reusable)
        self.assertIn('EXPECTED_WORKFLOW_REF: "${{ job.workflow_ref }}"', reusable)
        self.assertIn("workflow_dispatch:", release)
        self.assertIn("release.json", release)
        self.assertIn("git tag --annotate", release)
        self.assertIn("gh release create", release)

    def test_extracted_v1_contract_ids_remain_compatible(self) -> None:
        expected_ids = {
            "actions/repository-intelligence/schemas/repository-analytics.schema.json":
                "https://egohygiene.github.io/contracts/repository-analytics/v1/schema.json",
            "actions/repository-intelligence/schemas/repository-tree.schema.json":
                "https://egohygiene.github.io/contracts/repository-tree/v1/schema.json",
            "actions/repository-intelligence/schemas/repository-intelligence-dashboard.schema.json":
                "https://egohygiene.dev/schemas/repository-intelligence-dashboard/v3.json",
            "actions/normalize-repository-report/schemas/repository-report-summary.schema.json":
                "https://egohygiene.dev/schemas/repository-report-summary/v1.json",
        }

        for relative_path, expected_id in expected_ids.items():
            document = json.loads(
                (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
            )
            self.assertEqual(document["$id"], expected_id)

    def test_new_provenance_contract_uses_the_relay_namespace(self) -> None:
        document = json.loads(
            (
                REPOSITORY_ROOT
                / "actions/repository-intelligence/schemas/"
                "repository-intelligence-provenance.schema.json"
            ).read_text(encoding="utf-8")
        )

        self.assertEqual(
            document["$id"],
            "https://egohygiene.github.io/relay/contracts/"
            "repository-intelligence-provenance/v1/schema.json",
        )
        self.assertEqual(
            document["properties"]["schema"]["const"],
            "egohygiene.relay.repository-intelligence-provenance/v1",
        )


if __name__ == "__main__":
    unittest.main()
