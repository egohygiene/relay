# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Tests for the artifact-budget action contract and adapters."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    REPOSITORY_ROOT
    / "actions"
    / "artifact-budget"
    / "scripts"
    / "artifact_budget.py"
)
SPEC = importlib.util.spec_from_file_location("artifact_budget", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
budget = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(budget)

CURRENT_REVISION = "a" * 40
BASELINE_REVISION = "b" * 40


class ArtifactBudgetTests(unittest.TestCase):
    """Exercise deterministic measurement, comparison, and enforcement states."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.environment = mock.patch.dict(
            os.environ,
            {"GITHUB_WORKSPACE": str(self.root)},
            clear=False,
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def arguments(self, **overrides: str) -> object:
        """Return parsed action arguments with safe defaults."""

        values = {
            "adapter": "filesystem",
            "artifact_kind": "file",
            "subject": "artifact",
            "current_path": "current.bin",
            "baseline_path": "",
            "current_revision": CURRENT_REVISION,
            "baseline_revision": "",
            "mode": "advisory",
            "maximum_bytes": "",
            "maximum_increase_bytes": "",
            "maximum_increase_percent": "",
            "warning_threshold_percent": "90",
            "maximum_files": "10000",
            "maximum_items": "100",
            "scan_maximum_bytes": "1073741824",
            "output": "report.json",
            "github_output": "",
        }
        values.update(overrides)
        cli: list[str] = []
        for key, value in values.items():
            cli.extend([f"--{key.replace('_', '-')}", value])
        return budget.create_parser().parse_args(cli)

    def write_bytes(self, relative: str, count: int) -> Path:
        """Create one bounded binary fixture."""

        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * count)
        return path

    def write_json(self, relative: str, value: object) -> Path:
        """Create one JSON fixture."""

        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_filesystem_reports_absolute_and_baseline_deltas(self) -> None:
        self.write_bytes("current.bin", 120)
        self.write_bytes("baseline.bin", 100)
        report, output = budget.build_report(
            self.arguments(
                baseline_path="baseline.bin",
                baseline_revision=BASELINE_REVISION,
                maximum_bytes="200",
                maximum_increase_bytes="30",
                maximum_increase_percent="25",
            )
        )

        self.assertEqual(output, self.root / "report.json")
        measurement = report["measurements"][0]
        self.assertEqual(measurement["current_bytes"], 120)
        self.assertEqual(measurement["baseline_bytes"], 100)
        self.assertEqual(measurement["delta_bytes"], 20)
        self.assertEqual(measurement["delta_percent"], 20.0)
        self.assertEqual(measurement["state"], "pass")
        self.assertEqual(report["summary"]["state"], "pass")

    def test_warning_band_is_visible_without_blocking(self) -> None:
        self.write_bytes("current.bin", 95)
        report, _ = budget.build_report(
            self.arguments(maximum_bytes="100", mode="blocking")
        )

        self.assertEqual(report["measurements"][0]["state"], "warn")
        self.assertFalse(report["summary"]["blocking_failure"])

    def test_absolute_budget_failure_is_advisory_or_blocking_by_mode(self) -> None:
        self.write_bytes("current.bin", 101)
        advisory, _ = budget.build_report(
            self.arguments(maximum_bytes="100", mode="advisory")
        )
        blocking, _ = budget.build_report(
            self.arguments(maximum_bytes="100", mode="blocking")
        )

        self.assertEqual(advisory["summary"]["state"], "fail")
        self.assertFalse(advisory["summary"]["blocking_failure"])
        self.assertTrue(blocking["summary"]["blocking_failure"])

    def test_missing_baseline_is_explicit_for_regression_budget(self) -> None:
        self.write_bytes("current.bin", 10)
        report, _ = budget.build_report(
            self.arguments(maximum_increase_bytes="1", mode="blocking")
        )

        self.assertEqual(report["measurements"][0]["state"], "missing-baseline")
        self.assertIn(
            "regression-budget-requires-baseline",
            report["measurements"][0]["reasons"],
        )
        self.assertTrue(report["summary"]["blocking_failure"])

    def test_zero_baseline_percentage_is_unsupported_not_infinite(self) -> None:
        self.write_bytes("current.bin", 10)
        self.write_bytes("baseline.bin", 0)
        report, _ = budget.build_report(
            self.arguments(
                baseline_path="baseline.bin",
                baseline_revision=BASELINE_REVISION,
                maximum_increase_percent="5",
            )
        )

        measurement = report["measurements"][0]
        self.assertIsNone(measurement["delta_percent"])
        self.assertEqual(measurement["state"], "unsupported")

    def test_directory_measurement_is_bounded_and_complete(self) -> None:
        self.write_bytes("site/z.txt", 7)
        self.write_bytes("site/a.txt", 5)
        report, _ = budget.build_report(
            self.arguments(
                artifact_kind="static-site",
                current_path="site",
                maximum_files="2",
            )
        )

        self.assertEqual(report["coverage"]["current"]["file_count"], 2)
        self.assertEqual(report["coverage"]["current"]["total_bytes"], 12)
        self.assertEqual(report["measurements"][0]["current_bytes"], 12)

    def test_directory_rejects_file_and_byte_ceiling_overruns(self) -> None:
        self.write_bytes("site/a.txt", 5)
        self.write_bytes("site/b.txt", 5)
        with self.assertRaisesRegex(budget.ContractError, "maximum-files"):
            budget.build_report(
                self.arguments(
                    artifact_kind="directory",
                    current_path="site",
                    maximum_files="1",
                )
            )
        with self.assertRaisesRegex(budget.ContractError, "scan-maximum-bytes"):
            budget.build_report(
                self.arguments(
                    artifact_kind="directory",
                    current_path="site",
                    scan_maximum_bytes="9",
                )
            )

        (self.root / "empty-tree/one").mkdir(parents=True)
        (self.root / "empty-tree/two").mkdir()
        with self.assertRaisesRegex(budget.ContractError, "maximum-files"):
            budget.build_report(
                self.arguments(
                    artifact_kind="directory",
                    current_path="empty-tree",
                    maximum_files="1",
                )
            )

    def test_symlinked_sources_and_nested_outputs_are_rejected(self) -> None:
        outside = self.write_bytes("outside.bin", 1)
        (self.root / "linked.bin").symlink_to(outside)
        with self.assertRaisesRegex(budget.ContractError, "symbolic links"):
            budget.build_report(self.arguments(current_path="linked.bin"))

        self.write_bytes("site/a.txt", 1)
        with self.assertRaisesRegex(budget.ContractError, "nested inside"):
            budget.build_report(
                self.arguments(
                    artifact_kind="directory",
                    current_path="site",
                    output="site/report.json",
                )
            )

    def test_size_limit_normalizes_named_checks_in_stable_order(self) -> None:
        self.write_json(
            "current.json",
            [
                {"name": "z-bundle", "size": 25, "sizeLimit": 50, "passed": True},
                {
                    "name": "a-bundle",
                    "size": 40,
                    "sizeLimit": 100,
                    "passed": True,
                    "loading": 0.2,
                    "running": 0.1,
                },
            ],
        )
        report, _ = budget.build_report(
            self.arguments(
                adapter="size-limit-json",
                artifact_kind="javascript-bundle",
                current_path="current.json",
            )
        )

        self.assertEqual(
            [item["id"] for item in report["measurements"]],
            ["a-bundle", "z-bundle"],
        )
        self.assertEqual(report["summary"]["current_total_bytes"], 65)
        self.assertEqual(report["measurements"][0]["source"]["loading_seconds"], 0.2)

    def test_size_limit_preserves_upstream_failure(self) -> None:
        self.write_json(
            "current.json",
            [{"name": "bundle", "size": 110, "sizeLimit": 100, "passed": False}],
        )
        report, _ = budget.build_report(
            self.arguments(
                adapter="size-limit-json",
                artifact_kind="javascript-bundle",
                current_path="current.json",
            )
        )

        measurement = report["measurements"][0]
        self.assertEqual(measurement["state"], "fail")
        self.assertIn("size-limit-reported-failure", measurement["reasons"])
        self.assertIn("size-limit-maximum-bytes", measurement["reasons"])

    def test_size_limit_baseline_matches_by_name_and_detects_missing_entries(self) -> None:
        self.write_json(
            "current.json",
            [
                {"name": "matched", "size": 120},
                {"name": "new", "size": 10},
            ],
        )
        self.write_json(
            "baseline.json",
            [{"name": "matched", "size": 100}],
        )
        report, _ = budget.build_report(
            self.arguments(
                adapter="size-limit-json",
                artifact_kind="javascript-bundle",
                current_path="current.json",
                baseline_path="baseline.json",
                baseline_revision=BASELINE_REVISION,
            )
        )

        by_id = {item["id"]: item for item in report["measurements"]}
        self.assertEqual(by_id["matched"]["delta_bytes"], 20)
        self.assertEqual(by_id["new"]["state"], "missing-baseline")
        self.assertEqual(report["summary"]["state"], "missing-baseline")

    def test_runtime_only_size_limit_check_is_explicitly_unsupported(self) -> None:
        self.write_json(
            "current.json",
            [{"name": "runtime", "running": 0.2, "loading": 0.3}],
        )
        report, _ = budget.build_report(
            self.arguments(
                adapter="size-limit-json",
                artifact_kind="javascript-bundle",
                current_path="current.json",
            )
        )

        self.assertEqual(report["measurements"][0]["state"], "unsupported")
        self.assertIsNone(report["summary"]["current_total_bytes"])

    def test_size_limit_rejects_duplicate_names_and_error_payloads(self) -> None:
        self.write_json(
            "duplicate.json",
            [{"name": "same", "size": 1}, {"name": "same", "size": 2}],
        )
        with self.assertRaisesRegex(budget.ContractError, "duplicate"):
            budget.build_report(
                self.arguments(
                    adapter="size-limit-json",
                    artifact_kind="javascript-bundle",
                    current_path="duplicate.json",
                )
            )

        self.write_json("error.json", {"error": "consumer stack trace"})
        with self.assertRaisesRegex(budget.ContractError, "execution error"):
            budget.build_report(
                self.arguments(
                    adapter="size-limit-json",
                    artifact_kind="javascript-bundle",
                    current_path="error.json",
                )
            )

    def test_size_limit_rejects_unknown_fields_and_item_overruns(self) -> None:
        self.write_json("unknown.json", [{"name": "bundle", "size": 1, "path": "x"}])
        with self.assertRaisesRegex(budget.ContractError, "unsupported shape"):
            budget.build_report(
                self.arguments(
                    adapter="size-limit-json",
                    artifact_kind="javascript-bundle",
                    current_path="unknown.json",
                )
            )

        self.write_json(
            "many.json",
            [{"name": f"bundle-{index}", "size": index} for index in range(2)],
        )
        with self.assertRaisesRegex(budget.ContractError, "maximum-items"):
            budget.build_report(
                self.arguments(
                    adapter="size-limit-json",
                    artifact_kind="javascript-bundle",
                    current_path="many.json",
                    maximum_items="1",
                )
            )

        self.write_json(
            "unsafe-number.json",
            [{"name": "bundle", "size": budget.MAX_EXACT_JSON_INTEGER + 1}],
        )
        with self.assertRaisesRegex(budget.ContractError, "supported non-negative"):
            budget.build_report(
                self.arguments(
                    adapter="size-limit-json",
                    artifact_kind="javascript-bundle",
                    current_path="unsafe-number.json",
                )
            )

        with self.assertRaisesRegex(budget.ContractError, "supported integer range"):
            budget.build_report(
                self.arguments(maximum_bytes=str(budget.MAX_EXACT_JSON_INTEGER + 1))
            )

    def test_size_limit_input_is_byte_bounded_and_partial_totals_are_hidden(self) -> None:
        current = self.write_json(
            "current.json",
            [
                {"name": "bundle", "size": 10, "passed": True},
                {"name": "runtime", "running": 0.2, "passed": True},
            ],
        )
        report, _ = budget.build_report(
            self.arguments(
                adapter="size-limit-json",
                artifact_kind="javascript-bundle",
                current_path=current.name,
            )
        )
        self.assertIsNone(report["coverage"]["current"]["total_bytes"])
        self.assertIsNone(report["summary"]["current_total_bytes"])

        with self.assertRaisesRegex(budget.ContractError, "scan-maximum-bytes"):
            budget.build_report(
                self.arguments(
                    adapter="size-limit-json",
                    artifact_kind="javascript-bundle",
                    current_path=current.name,
                    scan_maximum_bytes="10",
                )
            )

    def test_revision_and_baseline_pairing_are_immutable(self) -> None:
        self.write_bytes("current.bin", 1)
        self.write_bytes("baseline.bin", 1)
        with self.assertRaisesRegex(budget.ContractError, "current-revision"):
            budget.build_report(self.arguments(current_revision="main"))
        with self.assertRaisesRegex(budget.ContractError, "baseline-revision"):
            budget.build_report(self.arguments(baseline_path="baseline.bin"))
        with self.assertRaisesRegex(budget.ContractError, "requires baseline-path"):
            budget.build_report(
                self.arguments(baseline_revision=BASELINE_REVISION)
            )

    def test_report_bytes_are_deterministic_and_hash_bound(self) -> None:
        self.write_bytes("current.bin", 12)
        report, output = budget.build_report(self.arguments())
        first_digest = budget.write_report(output, report)
        first_bytes = output.read_bytes()
        second_digest = budget.write_report(output, report)

        self.assertEqual(first_bytes, output.read_bytes())
        self.assertEqual(first_digest, second_digest)
        self.assertEqual(len(first_digest), 64)
        self.assertNotIn(str(self.root).encode(), first_bytes)

    def test_blocking_main_writes_evidence_before_returning_failure(self) -> None:
        self.write_bytes("current.bin", 101)
        code = budget.main(
            [
                "--adapter",
                "filesystem",
                "--artifact-kind",
                "file",
                "--subject",
                "artifact",
                "--current-path",
                "current.bin",
                "--current-revision",
                CURRENT_REVISION,
                "--mode",
                "blocking",
                "--maximum-bytes",
                "100",
                "--output",
                "report.json",
            ]
        )

        self.assertEqual(code, 1)
        self.assertEqual(
            json.loads((self.root / "report.json").read_text(encoding="utf-8"))[
                "summary"
            ]["state"],
            "fail",
        )

    def test_github_outputs_remain_bounded_scalars(self) -> None:
        self.write_bytes("current.bin", 12)
        output_file = self.root / "github-output"
        report, output = budget.build_report(self.arguments())
        digest = budget.write_report(output, report)
        budget.write_github_output(str(output_file), report, digest)

        values = dict(
            line.split("=", maxsplit=1)
            for line in output_file.read_text(encoding="utf-8").splitlines()
        )
        self.assertEqual(values["status"], "pass")
        self.assertEqual(values["report-sha256"], digest)
        self.assertEqual(values["current-total-bytes"], "12")


if __name__ == "__main__":
    unittest.main()
