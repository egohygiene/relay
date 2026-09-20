# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Tests for workflow cancellation classes and durable report adoption."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPOSITORY_ROOT / "scripts/validate_ci_run_lifecycle.py"
SPEC = importlib.util.spec_from_file_location("validate_ci_run_lifecycle", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class CIRunLifecycleTests(unittest.TestCase):
    """Keep policy, executable workflows, and proof synchronized."""

    def copied_repository(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name) / "relay"
        shutil.copytree(
            REPOSITORY_ROOT,
            root,
            ignore=shutil.ignore_patterns(".git", "__pycache__"),
        )
        return temporary, root

    def test_current_contract_is_valid(self) -> None:
        self.assertEqual(validator.validate(REPOSITORY_ROOT), [])

    def test_contract_schema_uses_relay_namespace(self) -> None:
        document = json.loads(
            (REPOSITORY_ROOT / "schemas/ci-run-lifecycle.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            document["$id"],
            "https://egohygiene.github.io/relay/contracts/ci-run-lifecycle/v1/schema.json",
        )

    def test_cancellable_write_workflow_fails_validation(self) -> None:
        temporary, root = self.copied_repository()
        self.addCleanup(temporary.cleanup)
        catalog_path = root / "catalog/ci-run-lifecycle.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        target = next(item for item in catalog["workflows"] if item["id"] == "label-sync-apply")
        target["class"] = "supersedable-check"
        catalog_path.write_text(json.dumps(catalog), encoding="utf-8")

        errors = validator.validate(root)

        self.assertTrue(any("cancellation disagrees" in error for error in errors))
        self.assertTrue(any("write authority in a read-only class" in error for error in errors))

    def test_missing_workflow_class_fails_validation(self) -> None:
        temporary, root = self.copied_repository()
        self.addCleanup(temporary.cleanup)
        catalog_path = root / "catalog/ci-run-lifecycle.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        catalog["workflows"] = catalog["workflows"][:-1]
        catalog_path.write_text(json.dumps(catalog), encoding="utf-8")

        self.assertTrue(
            any(
                "workflow lifecycle classes missing" in error
                for error in validator.validate(root)
            )
        )

    def test_disposable_failure_upload_must_remain_unconditional(self) -> None:
        temporary, root = self.copied_repository()
        self.addCleanup(temporary.cleanup)
        workflow = root / ".github/workflows/validate.yml"
        workflow.write_text(
            workflow.read_text(encoding="utf-8").replace(
                "      - name: Preserve disposable failure evidence\n"
                "        id: ci-report-lifecycle-report\n"
                '        if: "${{ always() }}"',
                "      - name: Preserve disposable failure evidence\n"
                "        id: ci-report-lifecycle-report\n"
                '        if: "${{ success() }}"',
                1,
            ),
            encoding="utf-8",
        )

        self.assertIn(
            'disposable failure smoke lacks required contract: if: "${{ always() }}"',
            validator.validate(root),
        )


if __name__ == "__main__":
    unittest.main()
