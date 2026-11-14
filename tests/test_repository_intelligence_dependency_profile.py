"""Keep the active public dependency profile coherent and authenticated."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1] / "actions/repository-intelligence"


def module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


admission = module("dependency_profile_admission", "public_catalog_admission.py")
contract = module("dependency_profile_receipt", "repository_dependency_build_contract.py")


class DependencySourceProfileTests(unittest.TestCase):
    def test_admission_declarations_and_public_mirrors_share_exact_owner(self) -> None:
        public = admission.lock()
        source = json.loads((ROOT / "contracts/dependency-source.v1.lock.json").read_bytes())
        for key in ("owner", "revision", "tree"):
            self.assertEqual(public[key], source[key])
        reference_path = next(path for path in contract.PUBLIC_FILES
                              if "public-dependency-declarations.hygiene-" in path)
        raw = (ROOT / reference_path).read_bytes()
        self.assertEqual(source["public_reference_sha256"], hashlib.sha256(raw).hexdigest())
        reference = json.loads(raw)
        self.assertEqual(source["revision"], reference["revision"])
        self.assertEqual(public["files"][public["artifact_path"]], reference["public_catalog_sha256"])
        self.assertEqual(source["declarations_observed_at"], reference["declarations_observed_at"])

    def test_both_golden_consumer_edges_retain_required_policy(self) -> None:
        path = next(path for path in contract.PUBLIC_FILES
                    if "public-dependency-declarations.hygiene-" in path)
        rows = json.loads((ROOT / path).read_bytes())["declarations"]
        for producer, identifier in (("mantle", "RELATIONSHIP-006"), ("egolint", "RELATIONSHIP-008")):
            with self.subTest(producer=producer):
                row = next(row for row in rows if row["source"] == "egohygiene/empathy"
                           and row["target"] == "egohygiene/" + producer)
                self.assertFalse(row["forbidden"])
                self.assertEqual([{"id": identifier, "contract": None,
                                   "contract_status": "required", "pinning": "immutable-or-versioned"}],
                                 row["policies"])

    def test_public_identity_and_role_tampering_still_fail(self) -> None:
        original = admission.public_document()["repositories"][0]
        admission.validate_rows([original])
        for change in ("identity", "role"):
            with self.subTest(change=change):
                row = copy.deepcopy(original)
                if change == "identity":
                    row["full_name"] = "egohygiene/not-an-admitted-fixture"
                else:
                    row["role"]["owns"].append("untrusted fixture claim")
                with self.assertRaises(ValueError):
                    admission.validate_rows([row])

    def test_private_wrapper_is_denied_before_identity_access(self) -> None:
        class Private(dict):
            def get(self, key, default=None):
                if key == "full_name":
                    raise AssertionError("excluded identity was accessed")
                return super().get(key, default)

        with self.assertRaises(ValueError):
            admission.validate_rows([Private(visibility="private")])

    def test_standalone_and_embedded_schema_bind_the_active_admission(self) -> None:
        pin = admission.lock()
        standalone = json.loads((ROOT / "schemas/dependency-source-build.v1.schema.json").read_bytes())
        whole = json.loads((ROOT / "schemas/repository-intelligence-provenance.schema.json").read_bytes())
        embedded = whole["properties"]["source_collection"]["properties"]["domains"]["properties"]["dependencies"]
        for schema in (standalone, embedded):
            with self.subTest(schema=schema.get("$id", "embedded")):
                fields = schema["properties"]["inputs"]["properties"]["catalog_admission"]["properties"]
                self.assertEqual(pin["revision"], fields["revision"]["const"])
                for field, path in (("artifact_sha256", "artifact_path"),
                                    ("schema_sha256", "schema_path"), ("helper_sha256", "helper_path")):
                    self.assertEqual(pin["files"][pin[path]], fields[field]["const"])
                actual = schema["properties"]["runtime"]["properties"]["relay_files_sha256"]
                expected = {*contract.FILES, *contract.PUBLIC_FILES}
                self.assertEqual(expected, set(actual["required"]))
                self.assertEqual(expected, set(actual["properties"]))

    def test_historical_public_mirrors_remain_byte_exact(self) -> None:
        for filename, expected in (
            ("public-repositories.hygiene-49639c1.json", "af9c7186ded0bb57b18741eaa5905314b96d6adb03736946c868e0fc4aa50b26"),
            ("public-dependency-declarations.hygiene-49639c1.json", "291f4f2fdd013648144641292039b12224fc9f1341a752cfa7da0727614fa20f"),
        ):
            with self.subTest(filename=filename):
                self.assertEqual(expected, hashlib.sha256((ROOT / "contracts" / filename).read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
