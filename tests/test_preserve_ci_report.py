# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Tests for bounded durable CI report preservation."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    REPOSITORY_ROOT
    / "actions/preserve-ci-report/scripts/preserve_ci_report.py"
)
SPEC = importlib.util.spec_from_file_location("preserve_ci_report", SCRIPT_PATH)
assert SPEC is not None
assert SPEC.loader is not None
preserver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preserver)


class PreserveCIReportTests(unittest.TestCase):
    """Keep report provenance bounded and honest on success and failure."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.previous_cwd = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, self.previous_cwd)

    def arguments(self, **changes: str) -> argparse.Namespace:
        values = {
            "producer": "example-check",
            "outcome": "success",
            "repository": "example/repository",
            "represented_revision": "1" * 40,
            "run_id": "42",
            "run_attempt": "2",
            "retention_days": "30",
            "maximum_files": "100",
            "maximum_bytes": "104857600",
            "github_output": None,
        }
        values.update(changes)
        return argparse.Namespace(**values)

    def report_directory(self) -> Path:
        path = self.root / ".reports/example-check"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def test_success_creates_checksums_and_provenance(self) -> None:
        report = self.report_directory()
        (report / "result.json").write_text('{"status":"ok"}\n', encoding="utf-8")
        output = self.root / "github-output"

        outputs = preserver.prepare(self.arguments(github_output=str(output)))

        manifest = json.loads(
            (report / "relay-report-manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["completeness"], "complete")
        self.assertEqual(manifest["outcome"], "success")
        self.assertEqual(manifest["run"], {"id": 42, "attempt": 2})
        self.assertEqual([item["path"] for item in manifest["files"]], ["result.json"])
        self.assertEqual(outputs["artifact-name"], "relay-report-example-check-42-2")
        self.assertRegex(outputs["manifest-sha256"], r"^[0-9a-f]{64}$")
        self.assertIn("relay-report-manifest.json", (report / "SHA256SUMS").read_text())
        self.assertIn("completeness=complete", output.read_text(encoding="utf-8"))

    def test_failed_check_without_native_output_stays_unavailable(self) -> None:
        outputs = preserver.prepare(self.arguments(outcome="failure"))
        manifest = json.loads(
            (self.report_directory() / "relay-report-manifest.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(outputs["completeness"], "unavailable")
        self.assertEqual(manifest["files"], [])
        self.assertEqual(manifest["outcome"], "failure")

    def test_failed_check_with_output_is_partial(self) -> None:
        report = self.report_directory()
        (report / "failure.json").write_text("{}\n", encoding="utf-8")

        outputs = preserver.prepare(self.arguments(outcome="failure"))

        self.assertEqual(outputs["completeness"], "partial")

    def test_success_without_native_output_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one producer report file"):
            preserver.prepare(self.arguments())

    def test_symlink_and_bounds_fail_closed(self) -> None:
        report = self.report_directory()
        outside = self.root / "outside.txt"
        outside.write_text("secret\n", encoding="utf-8")
        (report / "linked.txt").symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "symbolic links"):
            preserver.prepare(self.arguments(outcome="failure"))

        (report / "linked.txt").unlink()
        (report / "one.txt").write_text("1", encoding="utf-8")
        (report / "two.txt").write_text("2", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "1-file limit"):
            preserver.prepare(self.arguments(outcome="failure", maximum_files="1"))

    def test_identifiers_and_retention_are_bounded(self) -> None:
        with self.assertRaisesRegex(ValueError, "kebab-case"):
            preserver.prepare(self.arguments(producer="../escape", outcome="failure"))
        with self.assertRaisesRegex(ValueError, "must not exceed 90"):
            preserver.prepare(self.arguments(outcome="failure", retention_days="91"))


if __name__ == "__main__":
    unittest.main()
