# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Semantic checks for the Repository Intelligence workflow report schema."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
import unittest
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    REPOSITORY_ROOT
    / "actions/repository-intelligence/workflow-evidence/schemas/"
    "repository-intelligence-workflow-report.schema.json"
)
SCHEMA_URL = (
    "https://egohygiene.github.io/relay/contracts/"
    "repository-intelligence-workflow-report/v1/schema.json"
)
REVISION = "a" * 40
WORKFLOW_REVISION = "b" * 40
DIGEST = f"sha256:{'d' * 64}"
STAGE_CONTRACTS = (
    (
        "success",
        "completed",
        "RIW-000",
        "repository-intelligence.workflow.success",
    ),
    (
        "failure",
        "runner-hardening",
        "RIW-001",
        "repository-intelligence.workflow.runner-hardening",
    ),
    (
        "failure",
        "trust-and-input-validation",
        "RIW-002",
        "repository-intelligence.workflow.trust-and-input-validation",
    ),
    (
        "failure",
        "checkout",
        "RIW-003",
        "repository-intelligence.workflow.checkout",
    ),
    (
        "failure",
        "generation",
        "RIW-004",
        "repository-intelligence.workflow.generation",
    ),
    (
        "failure",
        "provenance-verification",
        "RIW-005",
        "repository-intelligence.workflow.provenance-verification",
    ),
    (
        "failure",
        "site-artifact-upload",
        "RIW-006",
        "repository-intelligence.workflow.site-artifact-upload",
    ),
)


def schema_matches(value: Any, definition: dict[str, Any]) -> bool:
    """Evaluate the JSON Schema keywords used by this checked-in contract."""

    if "allOf" in definition and not all(
        schema_matches(value, branch) for branch in definition["allOf"]
    ):
        return False
    if "oneOf" in definition and sum(
        schema_matches(value, branch) for branch in definition["oneOf"]
    ) != 1:
        return False

    if "if" in definition:
        condition = schema_matches(value, definition["if"])
        selected = definition.get("then" if condition else "else")
        if selected is not None and not schema_matches(value, selected):
            return False

    expected_type = definition.get("type")
    if expected_type == "object" and not isinstance(value, dict):
        return False
    if expected_type == "array" and not isinstance(value, list):
        return False
    if expected_type == "string" and not isinstance(value, str):
        return False
    if expected_type == "integer" and (
        not isinstance(value, int) or isinstance(value, bool)
    ):
        return False
    if expected_type == "null" and value is not None:
        return False

    if "const" in definition and value != definition["const"]:
        return False
    if "enum" in definition and value not in definition["enum"]:
        return False
    if "pattern" in definition and (
        not isinstance(value, str)
        or re.search(definition["pattern"], value) is None
    ):
        return False
    if "minimum" in definition and value < definition["minimum"]:
        return False
    if "maximum" in definition and value > definition["maximum"]:
        return False

    if isinstance(value, dict):
        required = set(definition.get("required", []))
        if not required.issubset(value):
            return False
        properties = definition.get("properties", {})
        if definition.get("additionalProperties") is False and not set(value).issubset(
            properties
        ):
            return False
        for key, property_value in value.items():
            property_schema = properties.get(key)
            if property_schema is not None and not schema_matches(
                property_value, property_schema
            ):
                return False
    return True


def report(*, success: bool = True) -> dict[str, Any]:
    """Return one complete report whose semantic branch is internally consistent."""

    result, stage, code, rule = STAGE_CONTRACTS[0 if success else 4]
    return {
        "$schema": SCHEMA_URL,
        "schema": "egohygiene.relay.repository-intelligence-workflow-report/v1",
        "schema_version": 1,
        "result": result,
        "stage": stage,
        "code": code,
        "rule": rule,
        "repository": "example/repository",
        "represented_revision": REVISION,
        "run": {"id": 314159, "attempt": 2},
        "event": {
            "class": "default-branch-push",
            "invocation": "reusable-call",
            "trust": "trusted-default-branch",
            "authority": "contents-read-artifact-only",
        },
        "versions": {
            "relay": "v1.6.0",
            "called_workflow_revision": WORKFLOW_REVISION,
            "workflow_contract": "v1",
            "report_contract": "v1",
            "provenance_contract": "v1",
            "dashboard_contract": "v3",
        },
        "artifacts": {
            "site": {
                "name": (
                    "repository-intelligence-site-v1-42-"
                    f"{REVISION}-314159-2"
                ),
                "status": "uploaded" if success else "not-uploaded",
                "digest": DIGEST if success else None,
                "retention_days": 30,
            },
            "run_report": {
                "name": "relay-report-repository-intelligence-v1-314159-2",
                "status": "prepared",
                "retention_days": 30,
            },
        },
        "remediation": (
            "https://github.com/egohygiene/Relay/blob/"
            f"{WORKFLOW_REVISION}/"
            "docs/repository-intelligence-publication.md"
            "#failure-codes-and-recovery"
        ),
        "sanitization": "allowlisted-metadata-only",
    }


class RepositoryIntelligenceWorkflowReportSchemaTests(unittest.TestCase):
    """Reject report shapes that are structurally valid but semantically impossible."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def assert_valid(self, value: dict[str, Any]) -> None:
        self.assertTrue(schema_matches(value, self.schema))

    def assert_invalid(self, value: dict[str, Any]) -> None:
        self.assertFalse(schema_matches(value, self.schema))

    def test_every_stage_has_one_exact_result_code_and_rule(self) -> None:
        for index, contract in enumerate(STAGE_CONTRACTS):
            result, stage, code, rule = contract
            value = report(success=result == "success")
            value.update(result=result, stage=stage, code=code, rule=rule)
            with self.subTest(stage=stage, case="valid"):
                self.assert_valid(value)

            contradictions = {
                "result": "failure" if result == "success" else "success",
                "code": STAGE_CONTRACTS[(index + 1) % len(STAGE_CONTRACTS)][2],
                "rule": STAGE_CONTRACTS[(index + 1) % len(STAGE_CONTRACTS)][3],
            }
            for key, contradiction in contradictions.items():
                invalid = deepcopy(value)
                invalid[key] = contradiction
                with self.subTest(stage=stage, contradiction=key):
                    self.assert_invalid(invalid)

    def test_event_class_controls_trust_and_invocation(self) -> None:
        valid_events = (
            ("trusted-pull-request", "reusable-call", "untrusted-content"),
            ("fork-pull-request", "reusable-call", "untrusted-content"),
            ("default-branch-push", "reusable-call", "trusted-default-branch"),
            ("manual-rebuild", "reusable-call", "untrusted-content"),
            ("manual-rebuild", "direct-dispatch", "untrusted-content"),
            ("unsupported", "reusable-call", "untrusted-content"),
            ("unsupported", "direct-dispatch", "untrusted-content"),
        )
        for event_class, invocation, trust in valid_events:
            value = report(success=event_class != "unsupported")
            value["event"].update(
                {"class": event_class, "invocation": invocation, "trust": trust}
            )
            with self.subTest(event_class=event_class, invocation=invocation):
                self.assert_valid(value)

        invalid_events = (
            ("trusted-pull-request", "direct-dispatch", "untrusted-content"),
            ("trusted-pull-request", "reusable-call", "trusted-default-branch"),
            ("fork-pull-request", "direct-dispatch", "untrusted-content"),
            ("fork-pull-request", "reusable-call", "trusted-default-branch"),
            ("default-branch-push", "direct-dispatch", "trusted-default-branch"),
            ("default-branch-push", "reusable-call", "untrusted-content"),
            ("manual-rebuild", "direct-dispatch", "trusted-default-branch"),
            ("unsupported", "reusable-call", "trusted-default-branch"),
        )
        for event_class, invocation, trust in invalid_events:
            value = report(success=event_class != "unsupported")
            value["event"].update(
                {"class": event_class, "invocation": invocation, "trust": trust}
            )
            with self.subTest(
                event_class=event_class, invocation=invocation, trust=trust
            ):
                self.assert_invalid(value)

        unsupported_success = report()
        unsupported_success["event"].update(
            {
                "class": "unsupported",
                "invocation": "reusable-call",
                "trust": "untrusted-content",
            }
        )
        self.assert_invalid(unsupported_success)

    def test_site_status_binds_result_digest_and_retention(self) -> None:
        self.assert_valid(report())
        failure = report(success=False)
        self.assert_valid(failure)
        failure_without_retention = deepcopy(failure)
        failure_without_retention["artifacts"]["site"]["retention_days"] = None
        self.assert_valid(failure_without_retention)

        invalid_cases = []

        success_not_uploaded = report()
        success_not_uploaded["artifacts"]["site"].update(
            {"status": "not-uploaded", "digest": None}
        )
        invalid_cases.append(("success-not-uploaded", success_not_uploaded))

        failure_uploaded = report(success=False)
        failure_uploaded["artifacts"]["site"].update(
            {"status": "uploaded", "digest": DIGEST}
        )
        invalid_cases.append(("failure-uploaded", failure_uploaded))

        uploaded_without_digest = report()
        uploaded_without_digest["artifacts"]["site"]["digest"] = None
        invalid_cases.append(("uploaded-null-digest", uploaded_without_digest))

        uploaded_without_retention = report()
        uploaded_without_retention["artifacts"]["site"]["retention_days"] = None
        invalid_cases.append(("uploaded-null-retention", uploaded_without_retention))

        not_uploaded_with_digest = report(success=False)
        not_uploaded_with_digest["artifacts"]["site"]["digest"] = DIGEST
        invalid_cases.append(("not-uploaded-digest", not_uploaded_with_digest))

        for label, value in invalid_cases:
            with self.subTest(case=label):
                self.assert_invalid(value)


if __name__ == "__main__":
    unittest.main()
