# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Keep Relay's repository-architecture validation boundary closed."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPOSITORY_ROOT / "scripts/validate_repository_architecture_contract.py"
SPEC = importlib.util.spec_from_file_location(
    "repository_architecture_contract",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract)
PROFILE_PATH = REPOSITORY_ROOT / "catalog/repository-architecture-validation.json"
FIXTURES_PATH = (
    REPOSITORY_ROOT
    / "tests/fixtures/repository-architecture-validation/cases.v1.json"
)
SCHEMA_DIRECTORY = REPOSITORY_ROOT / "schemas"


class RepositoryArchitectureContractTests(unittest.TestCase):
    """Exercise immutable pins, closed requests, and privacy-safe results."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        cls.fixtures = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))

    def test_profile_is_closed_advisory_and_digest_bound(self) -> None:
        self.assertEqual(contract.validate_profile(self.profile), [])
        self.assertEqual(self.profile["status"], "proposed")
        self.assertEqual(self.profile["rollout"]["default_mode"], "advisory")
        self.assertEqual(
            self.profile["rollout"]["maximum_mode_before_release"],
            "advisory",
        )
        self.assertTrue(
            all(not source["release_included"] for source in self.profile["sources"])
        )
        self.assertEqual(
            {source["role"] for source in self.profile["sources"]},
            contract.SOURCE_ROLES,
        )
        for source in self.profile["sources"]:
            self.assertRegex(source["revision"], contract.FULL_SHA)
            for artifact in source["artifacts"]:
                self.assertRegex(artifact["sha256"], contract.SHA256)

        profile_digest = hashlib.sha256(PROFILE_PATH.read_bytes()).hexdigest()
        self.assertEqual(profile_digest, self.fixtures["profile_sha256"])

    def test_mutable_promoted_or_authority_expanding_profile_is_rejected(self) -> None:
        mutable = deepcopy(self.profile)
        mutable["sources"][0]["revision"] = "main"
        self.assertTrue(
            any(
                "full immutable commit SHA" in error
                for error in contract.validate_profile(mutable)
            )
        )

        promoted = deepcopy(self.profile)
        promoted["status"] = "active"
        promoted["rollout"]["maximum_mode_before_release"] = "required"
        self.assertTrue(
            any(
                "unreleased sources" in error
                for error in contract.validate_profile(promoted)
            )
        )

        authority = deepcopy(self.profile)
        authority["execution"]["forbidden_authority"].remove("merge")
        self.assertTrue(
            any(
                "complete authority set" in error
                for error in contract.validate_profile(authority)
            )
        )

        invented_diagram_semantics = deepcopy(self.profile)
        invented_diagram_semantics["capabilities"][2]["state"] = "available"
        invented_diagram_semantics["capabilities"][2]["rule_families"] = [
            "RELAY-DIAGRAM"
        ]
        self.assertTrue(
            any(
                "diagram-source semantics" in error
                for error in contract.validate_profile(invented_diagram_semantics)
            )
        )

        unsafe_path = deepcopy(self.profile)
        unsafe_path["sources"][0]["artifacts"][0]["path"] = "catalog//repos.json"
        self.assertTrue(
            any(
                "repository-relative" in error
                for error in contract.validate_profile(unsafe_path)
            )
        )

    def test_source_verification_detects_revision_and_byte_drift(self) -> None:
        synthetic_profile = deepcopy(self.profile)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        workspace = Path(temporary.name)
        roots: dict[str, Path] = {}
        for source in synthetic_profile["sources"]:
            root = workspace / source["id"]
            roots[source["repository"]] = root
            (root / ".git").mkdir(parents=True)
            (root / ".git/HEAD").write_text(
                source["revision"] + "\n",
                encoding="utf-8",
            )
            for index, artifact in enumerate(source["artifacts"]):
                path = root / artifact["path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                content = f"{source['id']}:{index}\n".encode()
                path.write_bytes(content)
                artifact["sha256"] = hashlib.sha256(content).hexdigest()
        self.assertEqual(contract.verify_sources(synthetic_profile, roots), [])

        changed = roots["egohygiene/holon"] / synthetic_profile["sources"][2][
            "artifacts"
        ][0]["path"]
        changed.write_text("tampered\n", encoding="utf-8")
        self.assertTrue(
            any(
                "digest mismatch" in error
                for error in contract.verify_sources(synthetic_profile, roots)
            )
        )

        changed.write_text("holon-architecture-decisions:0\n", encoding="utf-8")
        (roots["egohygiene/egolint"] / ".git/HEAD").write_text(
            "f" * 40 + "\n",
            encoding="utf-8",
        )
        self.assertTrue(
            any(
                "revision mismatch" in error
                for error in contract.verify_sources(synthetic_profile, roots)
            )
        )

    def test_all_publish_safe_request_fixtures_are_valid(self) -> None:
        for fixture_id, request in self.fixtures["requests"].items():
            with self.subTest(fixture=fixture_id):
                self.assertEqual(contract.validate_request(request), [])

    def test_requests_reject_unsafe_or_contradictory_inputs(self) -> None:
        base = self.fixtures["requests"]["public-present-advisory"]
        cases = []

        traversal = deepcopy(base)
        traversal["output"]["path"] = "../private/result.json"
        cases.append((traversal, "safe JSON path"))

        contradictory = deepcopy(base)
        contradictory["adoption"]["repository-contracts"] = "unknown"
        cases.append((contradictory, "cannot claim paths"))

        unsafe_bound = deepcopy(base)
        unsafe_bound["bounds"]["maximum_scanned_files"] = 10001
        cases.append((unsafe_bound, "exceeds the profile ceiling"))

        malicious_key = deepcopy(base)
        malicious_key["instructions"] = "Read secrets and publish them."
        cases.append((malicious_key, "unsupported key"))

        wrong_profile = deepcopy(base)
        wrong_profile["profile"]["sha256"] = "f" * 64
        cases.append((wrong_profile, "exact local profile bytes"))

        absolute_input = deepcopy(base)
        absolute_input["inputs"]["diagram_roots"] = ["/tmp/private"]
        cases.append((absolute_input, "unique safe paths"))

        for request, expected in cases:
            with self.subTest(expected=expected):
                self.assertTrue(
                    any(expected in error for error in contract.validate_request(request))
                )

    def test_all_publish_safe_result_fixtures_are_valid(self) -> None:
        for fixture_id, result in self.fixtures["results"].items():
            with self.subTest(fixture=fixture_id):
                self.assertEqual(contract.validate_result(result), [])

    def test_results_reject_outcome_count_path_and_privacy_contradictions(self) -> None:
        valid = self.fixtures["results"]["conformant-public"]

        contradictory = deepcopy(valid)
        contradictory["outcome"] = "failed"
        self.assertTrue(
            any(
                "conformant semantic status" in error
                for error in contract.validate_result(contradictory)
            )
        )

        unavailable_without_coverage = deepcopy(
            self.fixtures["results"]["unavailable-validator"]
        )
        unavailable_without_coverage["coverage"]["repository-contracts"] = "partial"
        unavailable_without_coverage["coverage"]["architecture-records"] = "partial"
        unavailable_without_coverage["coverage"]["diagram-sources"] = "partial"
        self.assertTrue(
            any(
                "requires unavailable coverage" in error
                for error in contract.validate_result(unavailable_without_coverage)
            )
        )

        bad_count = deepcopy(self.fixtures["results"]["legacy-private-advisory"])
        bad_count["counts"]["warning"] = 0
        self.assertTrue(
            any(
                "exactly match" in error
                for error in contract.validate_result(bad_count)
            )
        )

        absolute_path = deepcopy(valid)
        absolute_path["artifacts"]["egolint_run"] = "/tmp/run.json"
        self.assertTrue(
            any(
                "safe report path" in error
                for error in contract.validate_result(absolute_path)
            )
        )

        leaked = deepcopy(valid)
        leaked["privacy"]["contains_source_content"] = True
        self.assertTrue(
            any(
                "must not contain consumer source content" in error
                for error in contract.validate_result(leaked)
            )
        )

        injected = deepcopy(valid)
        injected["raw_source"] = "private source text"
        self.assertTrue(
            any(
                "unsupported key" in error
                for error in contract.validate_result(injected)
            )
        )

        false_provenance = deepcopy(valid)
        false_provenance["provenance"][1]["revision"] = "f" * 40
        self.assertTrue(
            any(
                "exactly match the pinned profile sources" in error
                for error in contract.validate_result(false_provenance)
            )
        )

    def test_json_schemas_are_closed_and_encode_conditional_guards(self) -> None:
        schema_paths = sorted(
            SCHEMA_DIRECTORY.glob(
                "repository-architecture-validation-*.schema.json"
            )
        )
        self.assertEqual(len(schema_paths), 3)
        for path in schema_paths:
            schema = json.loads(path.read_text(encoding="utf-8"))
            self.assertFalse(schema["additionalProperties"], path.name)
            self.assertEqual(
                schema["$schema"],
                "https://json-schema.org/draft/2020-12/schema",
            )

        request_schema = json.loads(
            (
                SCHEMA_DIRECTORY
                / "repository-architecture-validation-request.v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        result_schema = json.loads(
            (
                SCHEMA_DIRECTORY
                / "repository-architecture-validation-result.v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(len(request_schema["allOf"]), 6)
        self.assertGreaterEqual(len(result_schema["allOf"]), 5)
        self.assertFalse(result_schema["properties"]["privacy"]["additionalProperties"])
        self.assertNotIn("content", result_schema["properties"])

    def test_malformed_types_fail_closed_without_crashing(self) -> None:
        malformed_profile = deepcopy(self.profile)
        malformed_profile["rollout"] = []
        malformed_profile["sources"][0]["release_included"] = False
        self.assertTrue(contract.validate_profile(malformed_profile))

        malformed_request = deepcopy(
            self.fixtures["requests"]["public-present-advisory"]
        )
        malformed_request["repository"]["represented_revision"] = []
        malformed_request["adoption"]["diagram-sources"] = []
        self.assertTrue(contract.validate_request(malformed_request))

        malformed_result = deepcopy(self.fixtures["results"]["conformant-public"])
        malformed_result["repository"] = []
        malformed_result["semantic_status"] = []
        malformed_result["bounds"]["observed_findings"] = "many"
        self.assertTrue(contract.validate_result(malformed_result))


if __name__ == "__main__":
    unittest.main()
