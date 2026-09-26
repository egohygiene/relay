# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Prove bounded discovery without claiming format-owned diagram conformance."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import unittest
from unittest import mock

from test_repository_architecture_adapter import AdapterFixture, RUNTIME, ROOT, adapter

diagrams = adapter.diagrams


class DiagramFixture(AdapterFixture):
    def setUp(self) -> None:
        super().setUp()
        self.request["adoption"] = {"repository-contracts": "not-applicable",
                                    "architecture-records": "not-applicable", "diagram-sources": "present"}
        self.request["inputs"]["diagram_roots"] = ["diagrams"]
        self.runtime = self.directory / "not-required-for-discovery"

    def evidence(self, result: dict) -> dict:
        value = self.artifact(result, "diagram_evidence")
        diagrams.validate(value, self.request)
        return value


class DiagramDiscoveryTests(DiagramFixture):
    def test_standalone_formats_preserve_exact_identity_without_native_runtime(self) -> None:
        inputs = {
            "diagrams/a.mmd": ("mermaid", "flowchart LR\n A --> B\n"),
            "diagrams/b.MERMAID": ("mermaid", "sequenceDiagram\n A->>B: Hi\n"),
            "diagrams/c.puml": ("plantuml", "@startuml\nA -> B\n@enduml\n"),
            "diagrams/d.plantuml": ("plantuml", "not syntax checked\n"),
            "diagrams/e.pu": ("plantuml", "@startuml\n@enduml\n"),
            "diagrams/f.excalidraw": ("excalidraw", "{\"type\":\"excalidraw\"}\n"),
            "diagrams/g.excalidraw.json": ("excalidraw", "deliberately invalid JSON\n"),
        }
        for name, (_, content) in inputs.items():
            self.put(name, content)
        self.commit()
        with mock.patch.object(adapter, "run_engine", side_effect=AssertionError("native engine not requested")):
            result = self.invoke()
        evidence = self.evidence(result)
        self.assertEqual(evidence["inventory_status"], "complete")
        self.assertEqual(result["semantic_status"], "incomplete")
        self.assertEqual(result["coverage"]["diagram-sources"], "unavailable")
        self.assertIsNone(result["artifacts"]["egolint_run"])
        self.assertEqual([source["path"] for source in evidence["sources"]], sorted(inputs))
        for source in evidence["sources"]:
            kind, content = inputs[source["path"]]
            self.assertEqual(source["format"], kind)
            self.assertEqual(source["bytes"], len(content.encode()))
            self.assertEqual(source["sha256"], hashlib.sha256(content.encode()).hexdigest())
            self.assertEqual(source["validation_status"], "unavailable")
            self.assertIsNone(source["validator"])

    def test_markdown_fences_ignore_examples_and_preserve_crlf_and_eof_ranges(self) -> None:
        content = (b"# Example\r\n```mermaid\r\nflowchart TD\r\nA --> B\r\n```\r\n"
                   b"````markdown\r\n```mermaid\r\nnot a diagram source\r\n```\r\n````\r\n"
                   b"~~~plantuml\r\n@startuml\r\n@enduml\r\n~~~~\r\n"
                   b"```puml\r\n@startuml\r\n@enduml\r\n")
        self.put("diagrams/design.md", "")
        (self.root / "diagrams/design.md").write_bytes(content)
        evidence = self.evidence(self.invoke())
        self.assertEqual([(s["format"], s["start_line"], s["end_line"]) for s in evidence["sources"]],
                         [("mermaid", 2, 5), ("plantuml", 11, 14), ("plantuml", 15, 17)])
        self.assertEqual(evidence["sources"][0]["sha256"], hashlib.sha256(b"flowchart TD\r\nA --> B\r\n").hexdigest())

    def test_fence_matching_honors_marker_length_indent_and_case(self) -> None:
        self.put("diagrams/design.markdown", "    ```mermaid\nignored indentation\n"
                 "   ````MeRmAiD\nA --> B\n```\n~~~~\n````\n"
                 "~~~python\n```mermaid\nnot a source\n```\n~~~\n")
        evidence = self.evidence(self.invoke())
        self.assertEqual(len(evidence["sources"]), 1)
        self.assertEqual(evidence["sources"][0]["start_line"], 3)
        self.assertEqual(evidence["sources"][0]["end_line"], 7)

    def test_only_declared_roots_are_discovered_and_generated_images_are_ignored(self) -> None:
        self.put("diagrams/a.mmd", "A --> B\n")
        self.put("elsewhere/outside.mmd", "PRIVATE_CANARY_OUTSIDE\n")
        self.put("diagrams/generated.svg", "<svg>PRIVATE_CANARY_IMAGE</svg>\n")
        self.put("diagrams/unrelated.json", "{}\n")
        evidence = self.evidence(self.invoke())
        self.assertEqual([s["path"] for s in evidence["sources"]], ["diagrams/a.mmd"])
        self.assertEqual(evidence["bounds"]["ignored_files"], 2)
        self.assertNotIn("elsewhere", json.dumps(evidence))

    def test_explicit_file_roots_and_empty_inventory_are_supported(self) -> None:
        self.put("docs/diagram-free.md", "# No diagram sources\n")
        self.request["inputs"]["diagram_roots"] = ["docs/diagram-free.md"]
        result = self.invoke()
        evidence = self.evidence(result)
        self.assertEqual(evidence["inventory_status"], "complete")
        self.assertEqual(evidence["sources"], [])
        self.assertEqual(evidence["validation_status"], "unavailable")
        self.assertEqual(result["semantic_status"], "incomplete")

    def test_missing_roots_reject_the_whole_inventory(self) -> None:
        evidence = self.evidence(self.invoke())
        self.assertEqual(evidence["inventory_status"], "rejected")
        self.assertEqual(evidence["diagnostics"], [{"code": "missing-root", "path": "diagrams"}])
        self.assertEqual(evidence["sources"], [])

    def test_overlapping_roots_are_rejected_instead_of_silently_deduplicated(self) -> None:
        self.put("diagrams/nested/a.mmd", "A --> B\n")
        self.request["inputs"]["diagram_roots"] = ["diagrams/nested", "diagrams"]
        evidence = self.evidence(self.invoke())
        self.assertEqual(evidence["diagnostics"][0]["code"], "overlapping-roots")
        self.assertEqual(evidence["sources"], [])

    def test_duplicate_and_traversing_roots_fail_request_validation(self) -> None:
        for roots in (["diagrams", "diagrams"], ["../outside"], ["diagrams/../outside"]):
            with self.subTest(roots=roots):
                self.request["inputs"]["diagram_roots"] = roots
                with self.assertRaises(adapter.AdapterError):
                    self.invoke()

    def test_symlink_never_reads_target_and_retains_snapshot_failure(self) -> None:
        self.put("diagrams/placeholder.md", "# Diagrams\n")
        outside = self.directory / "outside"
        outside.write_text("PRIVATE_CANARY")
        (self.root / "diagrams/link.mmd").symlink_to(outside)
        self.commit()
        result = self.invoke()
        evidence = self.evidence(result)
        self.assertEqual(evidence["diagnostics"][0]["code"], "snapshot-unavailable")
        self.assertEqual(result["findings"][0]["id"], "RELAY-ARCH-PATH-001")
        self.assertNotIn("PRIVATE_CANARY", json.dumps(evidence))

    def test_oversized_file_cannot_be_a_partial_inventory_pass(self) -> None:
        self.put("diagrams/large.mmd", "x" * (diagrams.MAX_FILE_BYTES + 1))
        evidence = self.evidence(self.invoke())
        self.assertEqual(evidence["inventory_status"], "rejected")
        self.assertEqual(evidence["diagnostics"][0]["code"], "bound-exceeded")
        self.assertTrue(evidence["bounds"]["truncated"])
        self.assertEqual(evidence["sources"], [])

    def test_source_count_bound_drops_the_incomplete_inventory(self) -> None:
        self.put("diagrams/many.md", "```mermaid\nA --> B\n```\n" * (diagrams.MAX_SOURCES + 1))
        evidence = self.evidence(self.invoke())
        self.assertEqual(evidence["inventory_status"], "rejected")
        self.assertEqual(evidence["bounds"]["observed_sources"], diagrams.MAX_SOURCES + 1)
        self.assertEqual(evidence["bounds"]["retained_sources"], 0)
        self.assertTrue(evidence["bounds"]["truncated"])

    def test_whole_snapshot_bounds_prevent_diagram_scanning(self) -> None:
        self.put("diagrams/a.mmd", "A --> B\n")
        self.request["bounds"]["maximum_scanned_files"] = 1
        result = self.invoke()
        evidence = self.evidence(result)
        self.assertTrue(result["bounds"]["scan_truncated"])
        self.assertEqual(evidence["bounds"]["examined_files"], 0)
        self.assertEqual(evidence["diagnostics"][0]["code"], "snapshot-unavailable")

    def test_invalid_markdown_encoding_is_explicit(self) -> None:
        self.put("diagrams/binary.md", "")
        (self.root / "diagrams/binary.md").write_bytes(b"```mermaid\n\xffPRIVATE_CANARY\n```\n")
        evidence = self.evidence(self.invoke())
        self.assertEqual(evidence["diagnostics"][0]["code"], "invalid-markdown-encoding")
        self.assertEqual(evidence["sources"], [])

    def test_private_source_directives_and_payloads_never_execute_or_escape(self) -> None:
        marker = self.directory / "executed"
        self.put("diagrams/a.puml", "!include https://example.invalid/PRIVATE_CANARY\n!include /PRIVATE_CANARY\n")
        self.put("diagrams/b.mmd", "%%{init: PRIVATE_CANARY}%%\nclick A callback\n")
        self.put("diagrams/c.excalidraw", "{\"files\":{\"dataURL\":\"PRIVATE_CANARY\"}}\n")
        self.put("diagrams/run.sh", f"touch {marker}\n")
        self.request["repository"]["visibility"] = "private"
        result = self.invoke()
        self.assertEqual(len(self.evidence(result)["sources"]), 3)
        self.assertFalse(marker.exists())
        for path in (self.root / ".reports").rglob("*"):
            if path.is_file():
                self.assertNotIn(b"PRIVATE_CANARY", path.read_bytes())
                self.assertNotIn(str(self.directory).encode(), path.read_bytes())

    def test_unknown_not_applicable_and_legacy_are_not_conflated(self) -> None:
        self.request["adoption"]["diagram-sources"] = "unknown"
        self.request["inputs"]["diagram_roots"] = []
        self.assertEqual(self.evidence(self.invoke())["inventory_status"], "unknown")
        self.request["adoption"]["diagram-sources"] = "not-applicable"
        result = self.invoke()
        self.assertEqual(result["semantic_status"], "not-applicable")
        self.assertIsNone(result["artifacts"]["diagram_evidence"])
        self.request["adoption"]["diagram-sources"] = "legacy"
        self.request["inputs"]["diagram_roots"] = ["diagrams"]
        self.put("diagrams/a.mmd", "A --> B\n")
        result = self.invoke()
        self.assertEqual(result["semantic_status"], "legacy")
        self.assertEqual(self.evidence(result)["inventory_status"], "complete")

    def test_immutable_complete_bundles_ignore_later_edits_and_checkout_names(self) -> None:
        self.put("diagrams/a.mmd", "A --> B\n")
        self.commit()
        before = adapter.git(self.root, "status", "--porcelain=v1")
        first = self.invoke()
        self.assertEqual(before, adapter.git(self.root, "status", "--porcelain=v1"))
        original = self.root
        self.root = self.directory / "different-checkout-name"
        shutil.copytree(original, self.root)
        self.put("diagrams/a.mmd", "different uncommitted content\n")
        second = self.invoke()
        self.assertEqual(first, second)
        for path in first["artifacts"].values():
            if path:
                self.assertEqual((original / path).read_bytes(), (self.root / path).read_bytes())

    def test_working_tree_tracks_changed_bytes_without_immutable_conformance(self) -> None:
        self.put("diagrams/a.mmd", "A --> B\n")
        first = self.evidence(self.invoke())
        self.put("diagrams/a.mmd", "A --> C\n")
        result = self.invoke()
        second = self.evidence(result)
        self.assertNotEqual(first["sources"][0]["sha256"], second["sources"][0]["sha256"])
        self.assertEqual(result["semantic_status"], "incomplete")

    def test_native_runtime_failure_preserves_independent_diagram_evidence(self) -> None:
        self.put("diagrams/a.mmd", "A --> B\n")
        self.request["adoption"]["repository-contracts"] = "unknown"
        result = self.invoke()
        self.assertEqual(result["semantic_status"], "unavailable")
        self.assertEqual(self.evidence(result)["inventory_status"], "complete")
        self.assertIsNone(result["artifacts"]["egolint_run"])

    def test_closed_evidence_rejects_prose_duplicates_and_false_validity(self) -> None:
        self.put("diagrams/a.mmd", "A --> B\n")
        original = self.evidence(self.invoke())
        mutations = []
        value = deepcopy(original)
        value["body"] = "PRIVATE_CANARY"
        mutations.append(value)
        value = deepcopy(original)
        value["sources"] *= 2
        value["bounds"]["observed_sources"] = value["bounds"]["retained_sources"] = 2
        mutations.append(value)
        value = deepcopy(original)
        value["validation_status"] = "valid"
        mutations.append(value)
        value = deepcopy(original)
        value["sources"][0]["validator"] = "unreviewed-binary"
        mutations.append(value)
        value = deepcopy(original)
        value["sources"][0]["path"] = "elsewhere/a.mmd"
        mutations.append(value)
        value = deepcopy(original)
        value["bounds"]["examined_bytes"] = self.request["bounds"]["maximum_scanned_bytes"] + 1
        mutations.append(value)
        for value in mutations:
            with self.subTest(value=value), self.assertRaises(ValueError):
                diagrams.validate(value, self.request)

    def test_json_schema_agrees_with_complete_and_rejected_evidence(self) -> None:
        try:
            import jsonschema
        except ImportError:
            self.skipTest("install the pinned schema dependencies for JSON Schema cross-checking")
        schema = json.loads((ROOT / "schemas/architecture-diagram-evidence.v1.schema.json").read_bytes())
        jsonschema.Draft202012Validator.check_schema(schema)
        for content in ("A --> B\n", "x" * (diagrams.MAX_FILE_BYTES + 1)):
            self.put("diagrams/a.mmd", content)
            jsonschema.Draft202012Validator(schema).validate(self.evidence(self.invoke()))


@unittest.skipUnless(RUNTIME, "set RELAY_ARCHITECTURE_RUNTIME to exercise native evidence composition")
class DiagramNativeCompositionTests(DiagramFixture):
    def test_native_report_failure_retains_already_validated_diagram_metadata(self) -> None:
        self.runtime = Path(RUNTIME)
        self.add_contract()
        self.put("diagrams/a.mmd", "A --> B\n")
        self.commit()
        with mock.patch.object(adapter, "sanitize_sarif", side_effect=adapter.AdapterError("RUNTIME")):
            result = self.invoke()
        self.assertEqual(result["semantic_status"], "unavailable")
        self.assertEqual(self.evidence(result)["inventory_status"], "complete")
        self.assertIsNone(result["artifacts"]["egolint_run"])

    def test_rejected_diagram_inventory_preserves_native_contract_evidence(self) -> None:
        self.runtime = Path(RUNTIME)
        self.add_contract()
        self.commit()
        result = self.invoke()
        self.assertEqual(result["coverage"]["repository-contracts"], "passed")
        self.assertIsNotNone(result["artifacts"]["egolint_run"])
        self.assertEqual(self.evidence(result)["inventory_status"], "rejected")
        self.assertEqual(result["semantic_status"], "incomplete")

    def test_invalid_native_contract_preserves_complete_diagram_inventory(self) -> None:
        self.runtime = Path(RUNTIME)
        self.add_contract()
        self.put("diagrams/a.mmd", "A --> B\n")
        (self.root / "README.md").unlink()
        self.commit()
        result = self.invoke()
        self.assertEqual(result["semantic_status"], "nonconformant")
        self.assertEqual(self.evidence(result)["inventory_status"], "complete")
        self.assertIn("EGO-CONTRACT-FILE-001", [f["id"] for f in result["findings"]])


if __name__ == "__main__":
    unittest.main()
