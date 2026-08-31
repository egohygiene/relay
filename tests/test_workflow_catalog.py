# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Tests for the complete Relay workflow contract and security policy."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPOSITORY_ROOT / "scripts/validate_actions.py"
SPEC = importlib.util.spec_from_file_location("validate_actions", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class WorkflowCatalogTests(unittest.TestCase):
    """Keep workflow intent and executable authority synchronized."""

    def copied_repository(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        """Return an isolated repository copy without Git object storage."""

        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name) / "relay"
        shutil.copytree(
            REPOSITORY_ROOT,
            root,
            ignore=shutil.ignore_patterns(".git", "__pycache__"),
        )
        return temporary, root

    def test_catalog_inventories_every_current_workflow(self) -> None:
        catalog = json.loads(
            (REPOSITORY_ROOT / "workflow-catalog.json").read_text(encoding="utf-8")
        )

        self.assertEqual(catalog["schema"], "egohygiene.relay-workflow-catalog/v1")
        self.assertEqual(catalog["owner"], "egohygiene/relay")
        self.assertEqual(
            {entry["path"] for entry in catalog["workflows"]},
            validator.discovered_workflow_paths(REPOSITORY_ROOT),
        )
        self.assertEqual(
            {
                entry["consumer_ref"]
                for entry in catalog["workflows"]
                if entry["audience"] == "reusable"
            },
            {
                "egohygiene/relay/.github/workflows/"
                "publication-pages.yml@v1",
                "egohygiene/relay/.github/workflows/"
                "publication-review.yml@v1",
                "egohygiene/relay/.github/workflows/"
                "release-artifact.yml@v1",
                "egohygiene/relay/.github/workflows/"
                "repository-intelligence.yml@v1"
            },
        )

    def test_schema_uses_the_relay_contract_namespace(self) -> None:
        schema = json.loads(
            (REPOSITORY_ROOT / "schemas/workflow-catalog.schema.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            schema["$id"],
            "https://egohygiene.github.io/relay/contracts/"
            "workflow-catalog/v1/schema.json",
        )

    def test_conventional_primary_branch_triggers_support_main_and_master(self) -> None:
        validation = (
            REPOSITORY_ROOT / ".github/workflows/validate.yml"
        ).read_text(encoding="utf-8")
        release = (
            REPOSITORY_ROOT / ".github/workflows/release.yml"
        ).read_text(encoding="utf-8")
        compatible_trigger = "  push:\n    branches:\n      - main\n      - master\n"

        self.assertIn(compatible_trigger, validation)
        self.assertIn(compatible_trigger, release)
        self.assertNotIn('default-branch: "main"', validation)

    def test_release_branch_compatibility_preserves_default_branch_gate(self) -> None:
        release = (
            REPOSITORY_ROOT / ".github/workflows/release.yml"
        ).read_text(encoding="utf-8")

        self.assertIn(
            'if: "${{ github.ref_name == github.event.repository.default_branch }}"',
            release,
        )
        self.assertIn(
            'DEFAULT_BRANCH: "${{ github.event.repository.default_branch }}"',
            release,
        )
        self.assertIn('git fetch origin "${DEFAULT_BRANCH}"', release)
        self.assertNotIn('git fetch origin "main"', release)
        self.assertNotIn('git fetch origin "master"', release)

    def test_mutable_adoption_reference_fails_validation(self) -> None:
        temporary, root = self.copied_repository()
        self.addCleanup(temporary.cleanup)
        example = root / "examples/workflows/repository-intelligence.yml"
        example.write_text(
            example.read_text(encoding="utf-8").replace(
                "@46cf1d66a7e66ca5a35d2c99cbaed5ccfb67573f",
                "@v1",
            ),
            encoding="utf-8",
        )

        self.assertIn(
            "adoption example is not pinned to a full SHA: "
            f"{example}",
            validator.validate_catalog(root),
        )

    def test_uncataloged_workflow_fails_validation(self) -> None:
        temporary, root = self.copied_repository()
        self.addCleanup(temporary.cleanup)
        workflow = root / ".github/workflows/uncataloged.yml"
        workflow.write_text(
            "---\nname: Uncataloged\non:\n  workflow_dispatch:\n"
            "permissions:\n  contents: read\njobs: {}\n",
            encoding="utf-8",
        )

        errors = validator.validate_catalog(root)
        self.assertTrue(
            any("workflows missing from workflow catalog" in error for error in errors)
        )

    def test_write_all_and_missing_timeout_fail_validation(self) -> None:
        temporary, root = self.copied_repository()
        self.addCleanup(temporary.cleanup)
        validation = root / ".github/workflows/validate.yml"
        validation.write_text(
            validation.read_text(encoding="utf-8").replace(
                "permissions:\n  contents: read",
                "permissions: write-all",
                1,
            ),
            encoding="utf-8",
        )
        reusable = root / ".github/workflows/repository-intelligence.yml"
        reusable.write_text(
            reusable.read_text(encoding="utf-8").replace(
                "    timeout-minutes: 15\n",
                "",
                1,
            ),
            encoding="utf-8",
        )

        errors = validator.validate_catalog(root)
        self.assertTrue(any("grants write-all permissions" in error for error in errors))
        self.assertTrue(any("workflow job lacks a timeout" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
