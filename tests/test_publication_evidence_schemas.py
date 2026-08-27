# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Keep publication evidence payloads aligned with their versioned schemas."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tests.test_publication_pages_verification import WORKFLOW_REF, WORKFLOW_SHA, verifier
from tests.test_publication_site_validation import REVISION, build_site, validator


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LOCAL_SCHEMA = (
    REPOSITORY_ROOT
    / "actions/validate-publication-site/schemas/"
    "publication-site-validation-evidence.schema.json"
)
REMOTE_SCHEMA = (
    REPOSITORY_ROOT
    / "actions/verify-publication-pages/schemas/"
    "publication-pages-evidence.schema.json"
)
PUBLICATION_SITE_SCHEMA = (
    REPOSITORY_ROOT
    / "actions/validate-publication-site/contracts/publication-site.schema.json"
)


def assert_top_level_contract(
    testcase: unittest.TestCase,
    value: dict,
    definition: dict,
) -> None:
    """Check required keys, closed shape, and direct const values."""

    testcase.assertTrue(set(definition["required"]).issubset(value))
    testcase.assertEqual(set(value), set(definition["properties"]))
    for key, property_schema in definition["properties"].items():
        if "const" in property_schema:
            testcase.assertEqual(value[key], property_schema["const"])


class PublicationEvidenceSchemaTests(unittest.TestCase):
    """Exercise success, predeploy, and sanitized failure evidence shapes."""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.workspace = Path(temporary.name)

    def test_vendored_beacon_public_contract_is_exact_and_closed(self) -> None:
        raw = PUBLICATION_SITE_SCHEMA.read_bytes()
        schema = json.loads(raw)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), validator.PUBLIC_SCHEMA_SHA256)
        self.assertEqual(schema["$defs"]["site"]["additionalProperties"], False)
        self.assertEqual(schema["$defs"]["slot"]["additionalProperties"], False)
        self.assertEqual(schema["$defs"]["resource"]["additionalProperties"], False)
        self.assertEqual(schema["properties"]["schema"]["const"], validator.CATALOG_SCHEMA)

    def test_local_success_and_failure_match_the_closed_schema_branches(self) -> None:
        fixture, site = build_site(self.workspace, "repository-subpath")
        result = validator.validate_publication_site(
            workspace=self.workspace,
            site_directory=fixture["site_directory"],
            expected_base_url=fixture["base_url"],
            expected_source_revision=REVISION,
            required_routes_json=json.dumps(fixture["required_routes"]),
        )
        schema = json.loads(LOCAL_SCHEMA.read_text(encoding="utf-8"))
        assert_top_level_contract(self, result.evidence(), schema["$defs"]["success"])

        (site / "site.json").write_text("{invalid\n", encoding="utf-8")
        evidence_path = self.workspace / ".relay/local-failure.json"
        exit_code = validator.main(
            [
                "--workspace",
                str(self.workspace),
                "--site-directory",
                fixture["site_directory"],
                "--expected-base-url",
                fixture["base_url"],
                "--expected-source-revision",
                REVISION,
                "--evidence-output",
                ".relay/local-failure.json",
            ]
        )
        self.assertEqual(exit_code, 2)
        failure = json.loads(evidence_path.read_text(encoding="utf-8"))
        assert_top_level_contract(self, failure, schema["$defs"]["failure"])

    def test_deployment_and_predeploy_evidence_match_schema_literals(self) -> None:
        fixture, _ = build_site(self.workspace, "repository-subpath")
        validation = validator.validate_publication_site(
            workspace=self.workspace,
            site_directory=fixture["site_directory"],
            expected_base_url=fixture["base_url"],
            expected_source_revision=REVISION,
            required_routes_json=json.dumps(fixture["required_routes"]),
        )
        target = {
            "base_url": fixture["base_url"],
            "catalog_sha256": validation.catalog_sha256,
            "checksum_sha256": validation.checksum_sha256,
            "file_count": len(validation.files),
            "route_count": len(validation.routes),
            "routes": [
                {"path": path, "sha256": "d" * 64}
                for path in validation.routes
            ],
            "status": "passed",
            "target": "canonical",
        }
        deployment = verifier.verification_evidence(
            validation=validation,
            workflow_ref=WORKFLOW_REF,
            workflow_sha=WORKFLOW_SHA,
            targets=[target],
        )
        schema = json.loads(REMOTE_SCHEMA.read_text(encoding="utf-8"))
        assert_top_level_contract(
            self, deployment, schema["$defs"]["deployment"]
        )

        evidence_path = self.workspace / ".relay/predeploy.json"
        exit_code = verifier.main(
            [
                "--workspace",
                str(self.workspace),
                "--site-directory",
                fixture["site_directory"],
                "--expected-base-url",
                fixture["base_url"],
                "--expected-source-revision",
                REVISION,
                "--configuration-only",
                "true",
                "--workflow-ref",
                WORKFLOW_REF,
                "--workflow-sha",
                WORKFLOW_SHA,
                "--evidence-output",
                ".relay/predeploy.json",
            ]
        )
        self.assertEqual(exit_code, 0)
        predeploy = json.loads(evidence_path.read_text(encoding="utf-8"))
        assert_top_level_contract(self, predeploy, schema["$defs"]["predeploy"])


if __name__ == "__main__":
    unittest.main()
