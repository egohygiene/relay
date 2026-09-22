# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Executable fixtures for Repository Intelligence workflow trust evidence."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ACTION_ROOT = REPOSITORY_ROOT / "actions/repository-intelligence/workflow-evidence"
SCRIPT_PATH = ACTION_ROOT / "scripts/repository_intelligence_workflow_evidence.py"
SCHEMA_PATH = (
    ACTION_ROOT
    / "schemas/repository-intelligence-workflow-report.schema.json"
)
FIXTURE_PATH = (
    REPOSITORY_ROOT
    / "tests/fixtures/repository-intelligence-workflow/cases.v1.json"
)
SPEC = importlib.util.spec_from_file_location(
    "repository_intelligence_workflow_evidence",
    SCRIPT_PATH,
)
assert SPEC is not None
assert SPEC.loader is not None
evidence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evidence)


def assert_schema_value(
    testcase: unittest.TestCase,
    value: Any,
    definition: dict[str, Any],
    label: str,
) -> None:
    """Exercise the checked-in report schema without an external dependency."""

    if "oneOf" in definition:
        matches = 0
        for candidate in definition["oneOf"]:
            try:
                assert_schema_value(testcase, value, candidate, label)
            except AssertionError:
                continue
            matches += 1
        testcase.assertEqual(matches, 1, f"{label} must match exactly one schema branch")
        return

    expected_type = definition.get("type")
    if expected_type == "object":
        testcase.assertIsInstance(value, dict, label)
    elif expected_type == "array":
        testcase.assertIsInstance(value, list, label)
    elif expected_type == "string":
        testcase.assertIsInstance(value, str, label)
    elif expected_type == "integer":
        testcase.assertIsInstance(value, int, label)
        testcase.assertNotIsInstance(value, bool, label)
    elif expected_type == "null":
        testcase.assertIsNone(value, label)

    if "const" in definition:
        testcase.assertEqual(value, definition["const"], label)
    if "enum" in definition:
        testcase.assertIn(value, definition["enum"], label)
    if "pattern" in definition and isinstance(value, str):
        testcase.assertIsNotNone(re.search(definition["pattern"], value), label)
    if "minimum" in definition:
        testcase.assertGreaterEqual(value, definition["minimum"], label)
    if "maximum" in definition:
        testcase.assertLessEqual(value, definition["maximum"], label)

    if isinstance(value, dict) and "properties" in definition:
        required = set(definition.get("required", []))
        testcase.assertTrue(required.issubset(value), f"{label} is missing required keys")
        properties = definition["properties"]
        if definition.get("additionalProperties") is False:
            testcase.assertEqual(set(value), set(properties), f"{label} is not closed")
        for key, child in value.items():
            if key in properties:
                assert_schema_value(testcase, child, properties[key], f"{label}.{key}")


class RepositoryIntelligenceWorkflowEvidenceTests(unittest.TestCase):
    """Prove every supported event and bounded failure shape offline."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixtures = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        if cls.fixtures.get("schema") != (
            "egohygiene.relay.repository-intelligence-workflow-fixtures/v1"
        ):
            raise AssertionError("unsupported Repository Intelligence workflow fixture")

    def arguments(
        self,
        changes: dict[str, str] | None = None,
        *,
        runner_temp: Path | None = None,
        github_output: Path | None = None,
    ) -> argparse.Namespace:
        """Return one complete helper invocation from fixture defaults."""

        values = dict(self.fixtures["defaults"])
        values.update(changes or {})
        values.update(
            {
                "operation": "finalize",
                "action_path": ACTION_ROOT.as_posix(),
                "runner_temp": runner_temp.as_posix() if runner_temp else "",
                "github_output": github_output.as_posix() if github_output else "",
            }
        )
        return argparse.Namespace(**values)

    def finalize(
        self,
        changes: dict[str, str] | None = None,
    ) -> tuple[dict[str, str], dict[str, Any]]:
        """Finalize one isolated report and return action outputs plus JSON."""

        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        runner_temp = Path(temporary.name)
        outputs = evidence.finalize(
            self.arguments(changes, runner_temp=runner_temp),
            ACTION_ROOT,
        )
        report = json.loads(Path(outputs["report-path"]).read_text(encoding="utf-8"))
        return outputs, report

    def test_all_five_supported_event_and_invocation_scenarios_execute(self) -> None:
        """Classify and report every event/invocation scenario named by issue 104."""

        self.assertEqual(len(self.fixtures["event_cases"]), 5)
        for case in self.fixtures["event_cases"]:
            with self.subTest(case=case["id"]):
                prepared = evidence.prepare(self.arguments(case["changes"]))
                _, report = self.finalize(case["changes"])
                expected = case["expected"]
                self.assertEqual(prepared["event-class"], expected["event_class"])
                self.assertEqual(
                    prepared["invocation-class"], expected["invocation_class"]
                )
                self.assertEqual(prepared["trust-class"], expected["trust_class"])
                self.assertEqual(report["event"]["class"], expected["event_class"])
                self.assertEqual(
                    report["event"]["invocation"], expected["invocation_class"]
                )
                self.assertEqual(report["event"]["trust"], expected["trust_class"])
                self.assertEqual(report["event"]["authority"], expected["authority"])

    def test_trusted_and_fork_pull_requests_share_the_same_authority_ceiling(self) -> None:
        """A same-repository PR never becomes a privileged execution route."""

        cases = {case["id"]: case for case in self.fixtures["event_cases"]}
        _, trusted = self.finalize(cases["trusted-pull-request"]["changes"])
        _, fork = self.finalize(cases["fork-pull-request"]["changes"])

        self.assertEqual(trusted["event"]["trust"], "untrusted-content")
        self.assertEqual(fork["event"]["trust"], "untrusted-content")
        self.assertEqual(trusted["event"]["authority"], fork["event"]["authority"])
        self.assertEqual(trusted["event"]["authority"], "contents-read-artifact-only")

    def test_every_stage_maps_to_a_stable_result(self) -> None:
        """First failed or skipped stage selects one closed code and rule."""

        for case in self.fixtures["stage_cases"]:
            with self.subTest(case=case["id"]):
                outputs, report = self.finalize(case["changes"])
                expected = case["expected"]
                for key in ("result", "stage", "code", "rule"):
                    self.assertEqual(report[key], expected[key])
                self.assertEqual(outputs["workflow-outcome"], expected["result"])
                self.assertEqual(outputs["error-code"], expected["code"])
                self.assertEqual(outputs["rule-id"], expected["rule"])
                self.assertEqual(
                    outputs["failed-stage"],
                    "" if expected["result"] == "success" else expected["stage"],
                )

    def test_success_and_failure_reports_match_the_closed_schema(self) -> None:
        """Exercise both report outcomes against every checked-in schema rule."""

        cases = {case["id"]: case for case in self.fixtures["stage_cases"]}
        for case_id in ("success", "generation-failure"):
            with self.subTest(case=case_id):
                _, report = self.finalize(cases[case_id]["changes"])
                assert_schema_value(self, report, self.schema, "report")

    def test_every_pattern_contract_is_explicitly_string_typed(self) -> None:
        """Avoid JSON Schema pattern branches that silently accept non-strings."""

        def visit(value: Any, label: str) -> None:
            if isinstance(value, dict):
                if "pattern" in value:
                    self.assertEqual(value.get("type"), "string", label)
                for key, child in value.items():
                    visit(child, f"{label}.{key}")
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    visit(child, f"{label}[{index}]")

        visit(self.schema, "schema")

    def test_artifact_identity_retention_and_digest_are_bounded(self) -> None:
        """Bind success and failure evidence to revision, contract, and run identity."""

        expected_site_name = (
            "repository-intelligence-site-v1-42-"
            f"{'a' * 40}-314159-2"
        )
        expected_report_name = "relay-report-repository-intelligence-v1-314159-2"
        _, success = self.finalize()
        _, failure = self.finalize(
            {
                "generation_outcome": "failure",
                "provenance_outcome": "skipped",
                "site_upload_outcome": "skipped",
                "site_artifact_digest": "",
            }
        )

        self.assertEqual(success["artifacts"]["site"]["name"], expected_site_name)
        self.assertEqual(success["artifacts"]["site"]["status"], "uploaded")
        self.assertEqual(
            success["artifacts"]["site"]["digest"],
            f"sha256:{'d' * 64}",
        )
        self.assertEqual(success["artifacts"]["site"]["retention_days"], 30)
        self.assertEqual(failure["artifacts"]["site"]["status"], "not-uploaded")
        self.assertIsNone(failure["artifacts"]["site"]["digest"])
        for report in (success, failure):
            self.assertEqual(
                report["artifacts"]["run_report"]["name"], expected_report_name
            )
            self.assertEqual(report["artifacts"]["run_report"]["retention_days"], 30)

    def test_failure_report_does_not_attribute_a_stale_site_digest(self) -> None:
        """Never bind a digest when the report says the site was not uploaded."""

        _, report = self.finalize(
            {
                "generation_outcome": "failure",
                "provenance_outcome": "skipped",
                "site_upload_outcome": "skipped",
                "site_artifact_digest": "e" * 64,
            }
        )

        self.assertEqual(report["artifacts"]["site"]["status"], "not-uploaded")
        self.assertIsNone(report["artifacts"]["site"]["digest"])

    def test_all_stage_outcomes_are_validated_before_failure_selection(self) -> None:
        """A malformed later provider outcome cannot hide behind an earlier failure."""

        arguments = self.arguments(
            {
                "hardening_outcome": "failure",
                "generation_outcome": "not-a-provider-outcome",
            }
        )
        with self.assertRaises(evidence.ContractError) as raised:
            evidence.result_for_stages(arguments)
        self.assertEqual(raised.exception.code, "RIW-STAGE-OUTCOME")

    def test_stage_outcomes_cannot_recover_after_a_failure(self) -> None:
        """Provider outcomes must describe one monotonic executed-then-skipped path."""

        arguments = self.arguments(
            {
                "hardening_outcome": "failure",
                "preflight_outcome": "success",
                "checkout_outcome": "skipped",
                "generation_outcome": "skipped",
                "provenance_outcome": "skipped",
                "site_upload_outcome": "skipped",
            }
        )
        with self.assertRaises(evidence.ContractError) as raised:
            evidence.result_for_stages(arguments)
        self.assertEqual(raised.exception.code, "RIW-STAGE-SEQUENCE")

    def test_invalid_inputs_fail_with_stable_non_reflective_codes(self) -> None:
        """Execute malformed retention, path, comparison, and event fixtures."""

        for case in self.fixtures["invalid_cases"]:
            with self.subTest(case=case["id"]), self.assertRaises(
                evidence.ContractError
            ) as raised:
                evidence.prepare(self.arguments(case["changes"]))
            self.assertEqual(raised.exception.code, case["expected_code"])

    def test_invalid_success_digest_becomes_durable_failure_evidence(self) -> None:
        """Preserve a sanitized RIW-006 report when upload digest evidence is invalid."""

        for case in self.fixtures["finalize_invalid_cases"]:
            with tempfile.TemporaryDirectory() as temporary, self.subTest(case=case["id"]):
                outputs = evidence.finalize(
                    self.arguments(
                        case["changes"],
                        runner_temp=Path(temporary),
                    ),
                    ACTION_ROOT,
                )
                report = json.loads(
                    Path(outputs["report-path"]).read_text(encoding="utf-8")
                )
            for key, value in case["expected"].items():
                self.assertEqual(report[key], value)
            self.assertEqual(outputs["workflow-outcome"], "failure")
            self.assertEqual(outputs["error-code"], "RIW-006")
            self.assertEqual(report["artifacts"]["site"]["status"], "not-uploaded")
            self.assertIsNone(report["artifacts"]["site"]["digest"])

    def test_finalize_downgrades_impossible_success_to_preflight_failure(self) -> None:
        """An invalid event or input cannot coexist with a successful report."""

        cases = (
            ({"event_name": "pull_request_target"}, 30),
            ({"artifact_retention_days": "91"}, None),
            ({"caller_workflow_ref": "not-a-provider-workflow-ref"}, 30),
        )
        for changes, expected_retention in cases:
            with self.subTest(changes=changes):
                _, report = self.finalize(changes)
                self.assertEqual(report["result"], "failure")
                self.assertEqual(report["stage"], "trust-and-input-validation")
                self.assertEqual(report["code"], "RIW-002")
                self.assertEqual(
                    report["rule"],
                    "repository-intelligence.workflow.trust-and-input-validation",
                )
                self.assertEqual(
                    report["artifacts"]["site"]["status"], "not-uploaded"
                )
                self.assertIsNone(report["artifacts"]["site"]["digest"])
                self.assertEqual(
                    report["artifacts"]["site"]["retention_days"],
                    expected_retention,
                )

    def test_repository_local_mutable_resolution_is_revision_bound(self) -> None:
        """Permit local dogfood only when called code is the represented revision."""

        local = {
            "repository": "egohygiene/Relay",
            "represented_revision": "b" * 40,
            "caller_workflow_ref": (
                "egohygiene/relay/.github/workflows/validate.yml@refs/heads/main"
            ),
            "called_workflow_ref": (
                "egohygiene/relay/.github/workflows/"
                "repository-intelligence.yml@refs/heads/main"
            ),
        }
        prepared = evidence.prepare(self.arguments(local))
        self.assertEqual(prepared["invocation-class"], "reusable-call")

        with self.assertRaises(evidence.ContractError) as raised:
            evidence.prepare(
                self.arguments({**local, "represented_revision": "a" * 40})
            )
        self.assertEqual(raised.exception.code, "RIW-IDENTITY-WORKFLOW-PIN")

    def test_caller_workflow_identity_is_structured_and_repository_bound(self) -> None:
        """Do not infer trust from arbitrary or cross-repository caller strings."""

        for caller in (
            "sentinel",
            "other/repository/.github/workflows/validate.yml@" + "a" * 40,
            "example/repository/.github/workflows/nested/validate.yml@" + "a" * 40,
        ):
            with self.subTest(caller=caller), self.assertRaises(
                evidence.ContractError
            ) as raised:
                evidence.prepare(self.arguments({"caller_workflow_ref": caller}))
            self.assertEqual(raised.exception.code, "RIW-INVOCATION-IDENTITY")

        at_ref = (
            "example/repository/.github/workflows/validate.yml@"
            "refs/heads/release@candidate"
        )
        prepared = evidence.prepare(
            self.arguments({"caller_workflow_ref": at_ref})
        )
        self.assertEqual(prepared["invocation-class"], "reusable-call")

    def test_git_forbidden_branch_names_never_become_trusted_pushes(self) -> None:
        """Reject ref names Git itself would refuse before assigning trust."""

        for branch in (
            "main~1",
            "main@{upstream}",
            "main\x7fhidden",
            "feature//double",
            ".hidden",
            "release.lock",
        ):
            with self.subTest(branch=branch), self.assertRaises(
                evidence.ContractError
            ) as raised:
                evidence.prepare(
                    self.arguments(
                        {
                            "event_default_branch": branch,
                            "ref": f"refs/heads/{branch}",
                        }
                    )
                )
            self.assertEqual(raised.exception.code, "RIW-EVENT-NONDEFAULT-PUSH")

    def test_cli_parser_failure_is_stable_and_non_reflective(self) -> None:
        """Dash-prefixed values cannot escape into argparse diagnostics."""

        sentinel = "--TOP_SECRET_REPOSITORY_INTELLIGENCE_SENTINEL"
        with self.assertRaises(evidence.ContractError) as raised:
            evidence.parser().parse_args(
                ["--operation", "prepare", "--activity-since", sentinel]
            )
        self.assertEqual(raised.exception.code, "RIW-CLI")

        manifest = (ACTION_ROOT / "action.yml").read_text(encoding="utf-8")
        argument_lines = [
            line.strip()
            for line in manifest.splitlines()
            if re.match(r"^\s+--[a-z]", line)
        ]
        self.assertGreaterEqual(len(argument_lines), 30)
        for line in argument_lines:
            self.assertRegex(line, r'^--[a-z-]+="\$\{[A-Z0-9_]+\}"(?: \\)?$')

    def test_malicious_values_never_enter_report_or_action_outputs(self) -> None:
        """Keep diagnostics allowlisted instead of reflecting untrusted inputs."""

        fixture = self.fixtures["sanitization"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            github_output = root / "github-output"
            outputs = evidence.finalize(
                self.arguments(
                    fixture["changes"],
                    runner_temp=root,
                    github_output=github_output,
                ),
                ACTION_ROOT,
            )
            report_bytes = Path(outputs["report-path"]).read_text(encoding="utf-8")
            output_bytes = github_output.read_text(encoding="utf-8")

        self.assertNotIn(fixture["sentinel"], report_bytes)
        self.assertNotIn(fixture["sentinel"], output_bytes)
        self.assertNotIn(temporary, report_bytes)
        output_values = dict(
            line.split("=", maxsplit=1)
            for line in output_bytes.splitlines()
        )
        self.assertTrue(output_values["report-directory"].startswith(temporary))
        self.assertTrue(output_values["report-path"].startswith(temporary))

    def test_isolated_cli_ignores_hostile_checkout_shadow_modules(self) -> None:
        """Execute the helper exactly as its action manifest does under hostile cwd."""

        with tempfile.TemporaryDirectory() as temporary:
            checkout = Path(temporary)
            shadow_marker = checkout / "shadow-imported"
            shadow_source = (
                f"with open({str(shadow_marker)!r}, \"a\", encoding=\"utf-8\") as marker:\n"
                "    marker.write(__name__ + \"\\n\")\n"
                "raise RuntimeError(\"hostile checkout shadow module imported\")\n"
            )
            for filename in (
                "json.py",
                "datetime.py",
                "pathlib.py",
                "sitecustomize.py",
            ):
                (checkout / filename).write_text(shadow_source, encoding="utf-8")
            github_output = checkout / "github-output"
            defaults = self.fixtures["defaults"]
            command = [
                sys.executable,
                "-I",
                str(SCRIPT_PATH),
                "--operation",
                "prepare",
                "--action-path",
                str(ACTION_ROOT),
                "--github-output",
                str(github_output),
            ]
            for name in (
                "repository",
                "repository_id",
                "represented_revision",
                "run_id",
                "run_attempt",
                "event_name",
                "ref",
                "event_default_branch",
                "pull_request_head_repository",
                "caller_workflow_ref",
                "called_workflow_ref",
                "called_workflow_repository",
                "called_workflow_revision",
                "output_directory",
                "work_directory",
                "reports_directory",
                "observatory_snapshot",
                "observatory_comparison",
                "default_branch",
                "activity_since",
                "max_depth",
                "artifact_retention_days",
            ):
                command.extend([f"--{name.replace('_', '-')}", defaults[name]])
            completed = subprocess.run(
                command,
                cwd=checkout,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertFalse(shadow_marker.exists())
            self.assertIn("event-class=default-branch-push", github_output.read_text())


if __name__ == "__main__":
    unittest.main()
