# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Tests for normalized repository-intelligence producer summaries."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ACTION_ROOT = REPOSITORY_ROOT / "actions/normalize-repository-report"
FIXTURE_ROOT = REPOSITORY_ROOT / "tests/fixtures/repository-reports"
MODULE_PATH = ACTION_ROOT / "scripts/normalize_repository_report.py"
SPEC = importlib.util.spec_from_file_location("normalize_repository_report", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
normalizer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(normalizer)

COMMIT = "1" * 40


def arguments(
    producer: str,
    input_path: Path,
    *,
    policy_path: Path | None = None,
    api_path: Path | None = None,
) -> argparse.Namespace:
    """Build deterministic arguments for one normalization case."""

    return argparse.Namespace(
        producer=producer,
        input=str(input_path),
        output="unused.json",
        repository="example/repository",
        commit=COMMIT,
        generated_at="2026-08-14T12:00:00Z",
        event="push",
        workflow="Repository report test",
        run_id="42",
        run_attempt=1,
        server_url="https://github.com",
        stale_after_days=8,
        detail_url=None,
        policy_input=str(policy_path) if policy_path else None,
        scorecard_api_input=str(api_path) if api_path else None,
    )


class RepositoryReportNormalizationTests(unittest.TestCase):
    """Keep producer status, policy, provenance, and freshness deterministic."""

    def test_osv_success_separates_execution_from_blocking_findings(self) -> None:
        summary = normalizer.normalize(arguments("osv", FIXTURE_ROOT / "osv-success.json"))

        self.assertEqual(summary["execution"]["state"], "success")
        self.assertEqual(summary["findings"]["state"], "blocked")
        self.assertEqual(summary["findings"]["total"], 3)
        self.assertEqual(summary["findings"]["blocking"], 1)
        self.assertEqual(summary["findings"]["advisory"], 2)
        self.assertEqual(summary["freshness"]["expires_at"], "2026-08-22T12:00:00Z")
        self.assertIn("scanner_step_outcomes", summary["osv"])

    def test_megalinter_distinguishes_findings_from_execution_errors(self) -> None:
        summary = normalizer.normalize(
            arguments(
                "megalinter",
                FIXTURE_ROOT / "megalinter-failure.json",
                policy_path=FIXTURE_ROOT / "megalinter-policy.json",
            )
        )

        self.assertEqual(summary["execution"]["state"], "failure")
        self.assertEqual(summary["findings"]["state"], "blocked")
        self.assertEqual(summary["findings"]["total"], 2)
        self.assertEqual(summary["findings"]["blocking"], 1)
        self.assertEqual(summary["megalinter"]["tools"]["execution_errors"], 1)
        self.assertEqual(summary["megalinter"]["diagnostics"]["warnings"], 3)

    def test_scorecard_uses_only_commit_matched_api_aggregate(self) -> None:
        summary = normalizer.normalize(
            arguments(
                "scorecard",
                FIXTURE_ROOT / "scorecard.sarif",
                api_path=FIXTURE_ROOT / "scorecard-api-current.json",
            )
        )

        self.assertEqual(summary["execution"]["state"], "success")
        self.assertEqual(summary["findings"]["state"], "attention")
        self.assertEqual(summary["scorecard"]["api_status"], "matched")
        self.assertEqual(summary["scorecard"]["aggregate_score"], 6.4)
        self.assertEqual(summary["scorecard"]["checks_total"], 3)
        self.assertEqual(
            [check["name"] for check in summary["scorecard"]["weakest_checks"]],
            ["Branch-Protection", "Signed-Releases"],
        )

    def test_scorecard_rejects_stale_api_aggregate(self) -> None:
        summary = normalizer.normalize(
            arguments(
                "scorecard",
                FIXTURE_ROOT / "scorecard.sarif",
                api_path=FIXTURE_ROOT / "scorecard-api-stale.json",
            )
        )

        self.assertEqual(summary["scorecard"]["api_status"], "stale")
        self.assertIsNone(summary["scorecard"]["aggregate_score"])
        self.assertEqual(summary["scorecard"]["check_source"], "sarif")

    def test_missing_input_is_unknown_instead_of_green(self) -> None:
        summary = normalizer.normalize(arguments("osv", FIXTURE_ROOT / "missing.json"))

        self.assertEqual(summary["execution"]["state"], "unknown")
        self.assertEqual(summary["findings"]["state"], "unknown")
        self.assertEqual(summary["osv"]["status"], "unavailable")

    def test_malformed_input_is_an_execution_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            malformed = Path(temporary_directory) / "malformed.json"
            malformed.write_text("{not-json}\n", encoding="utf-8")
            summary = normalizer.normalize(arguments("scorecard", malformed))

        self.assertEqual(summary["execution"]["state"], "failure")
        self.assertEqual(summary["findings"]["state"], "unknown")
        self.assertEqual(summary["scorecard"]["status"], "invalid")

    def test_wrong_numeric_types_become_a_failure_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            malformed = Path(temporary_directory) / "osv.json"
            document = json.loads(
                (FIXTURE_ROOT / "osv-success.json").read_text(encoding="utf-8")
            )
            document["scan"]["severity"]["high"] = "abc"
            malformed.write_text(json.dumps(document), encoding="utf-8")

            summary = normalizer.normalize(arguments("osv", malformed))

        self.assertEqual(summary["execution"]["state"], "failure")
        self.assertEqual(summary["findings"]["state"], "unknown")
        self.assertEqual(summary["osv"]["status"], "invalid")

    def test_wrong_sarif_shapes_become_a_failure_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            malformed = Path(temporary_directory) / "scorecard.sarif"
            malformed.write_text(
                json.dumps({"version": "2.1.0", "runs": [{"tool": []}]}),
                encoding="utf-8",
            )

            summary = normalizer.normalize(arguments("scorecard", malformed))

        self.assertEqual(summary["execution"]["state"], "failure")
        self.assertEqual(summary["findings"]["state"], "unknown")
        self.assertEqual(summary["scorecard"]["status"], "invalid")

    def test_nonstandard_json_numbers_become_a_failure_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            malformed = Path(temporary_directory) / "osv.json"
            malformed.write_text(
                '{"scan":{"severity":{"high":NaN}},"severity_threshold":"high"}',
                encoding="utf-8",
            )

            summary = normalizer.normalize(arguments("osv", malformed))

        self.assertEqual(summary["execution"]["state"], "failure")
        self.assertEqual(summary["findings"]["state"], "unknown")

    def test_workspace_boundary_rejects_symlink_escapes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workspace = root / "repository"
            outside = root / "outside"
            workspace.mkdir()
            outside.mkdir()
            (workspace / "linked").symlink_to(outside, target_is_directory=True)
            unsafe = argparse.Namespace(
                workspace=str(workspace),
                input="linked/input.json",
                output="reports/summary.json",
                policy_input=None,
                scorecard_api_input=None,
            )

            with self.assertRaises(normalizer.PathValidationError):
                normalizer.resolve_workspace_paths(unsafe)

    def test_workspace_boundary_keeps_all_paths_inside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory).resolve()
            safe = argparse.Namespace(
                workspace=str(workspace),
                input="reports/native.json",
                output=".reports/osv/summary.json",
                policy_input="policy/tools.json",
                scorecard_api_input=None,
            )

            paths = normalizer.resolve_workspace_paths(safe)

        for label in ("input", "output", "policy_input"):
            self.assertTrue(paths[label].is_relative_to(workspace))

    def test_atomic_writer_rejects_non_finite_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "summary.json"

            with self.assertRaises(normalizer.ReportInputError):
                normalizer.atomic_write_summary(output, {"score": float("nan")})

            self.assertFalse(output.exists())

    def test_same_inputs_produce_the_same_summary(self) -> None:
        args = arguments("osv", FIXTURE_ROOT / "osv-success.json")
        self.assertEqual(normalizer.normalize(args), normalizer.normalize(args))

    def test_checked_in_schema_declares_the_common_contract(self) -> None:
        schema = json.loads(
            (ACTION_ROOT / "schemas/repository-report-summary.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(schema["properties"]["schema"]["const"], normalizer.SCHEMA_NAME)
        self.assertIn("execution", schema["required"])
        self.assertIn("findings", schema["required"])
        self.assertIn("freshness", schema["required"])

    def test_action_passes_relative_paths_to_workspace_guard(self) -> None:
        action = (ACTION_ROOT / "action.yml").read_text(encoding="utf-8")

        self.assertIn('--workspace "${GITHUB_WORKSPACE}"', action)
        self.assertIn('--input "${INPUT_PATH}"', action)
        self.assertNotIn('--input "${GITHUB_WORKSPACE}/${INPUT_PATH}"', action)


if __name__ == "__main__":
    unittest.main()
