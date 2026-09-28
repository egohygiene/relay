# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Compose native fixtures through retention, presentation, and fresh retry.

Provider stages and upload outcomes below are synthetic test inputs. Only the
native validator, normalized bytes, and local report lifecycle actually run.
"""

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

from test_architecture_validation_workflow import ArchitectureWorkflowFixture, workflow
from test_repository_architecture_adapter import RUNTIME, adapter


@unittest.skipUnless(RUNTIME, "prepare the pinned runtime; use tests/run_architecture_acceptance.py for a no-skip run")
class ArchitectureAcceptanceTests(ArchitectureWorkflowFixture):
    def scenario(self, name: str) -> None:
        """Reuse the existing native fixtures; add only the scenario's boundary."""
        self.name = name
        if name in {"conformant", "invalid", "partial", "malicious"}:
            self.add_contract()
            self.env.update({"INPUT_CONTRACT_ADOPTION": "present", "INPUT_CONTRACTS": '["policy/contract.toml"]'})
        if name == "invalid":
            (self.root / "README.md").unlink()
        if name == "legacy":
            self.add_adrs()
            self.env.update({"INPUT_ADR_ADOPTION": "legacy", "INPUT_ADR_POLICY": "policy/intelligence.toml"})
        if name in {"unknown", "unavailable"}:
            self.env.update({"INPUT_CONTRACT_ADOPTION": "unknown", "INPUT_ADR_ADOPTION": "unknown"})
        if name in {"partial", "unavailable", "malicious"}:
            self.diagram()
        if name == "malicious":
            outside = self.directory / "protected-source"
            outside.write_text("PRIVATE_CANARY_DO_NOT_EXPORT")
            (self.root / "diagrams/escape.mmd").symlink_to(outside)
        self.put("sitecustomize.py", 'raise RuntimeError("CALLER_CODE_EXECUTED")\n')
        self.env["GITHUB_SHA"] = self.commit()

    def execute(self, *, unavailable: bool = False) -> tuple[dict, dict, dict]:
        self.prepare()
        for name in workflow.STAGES:
            self.stages[name]["outcome"] = "success"
        if self.env["INPUT_MODE"] == "required":
            for name in ("hygiene", "egolint", "holon", "acquire", "build"):
                self.stages[name]["outcome"] = "skipped"
        if unavailable:
            self.stages["acquire"]["outcome"] = "failure"
            self.stages["build"]["outcome"] = "skipped"
        runtime = self.directory / "unavailable-runtime" if unavailable else self.runtime
        result = workflow.validate(self.env, runtime=runtime)
        self.stages["validate"]["outcome"] = "failure" if result["outcome"] in {"failed", "unavailable"} else "success"
        report, values = self.finalize()
        return result, report, values

    def retain(self, report: dict, values: dict, label: str) -> tuple[dict, dict[str, bytes]]:
        """Run the real #6 packager and verify the exact closed evidence bundle."""
        from jsonschema import Draft202012Validator

        schema = json.loads((adapter.ROOT / "schemas/architecture-workflow-evidence.v1.schema.json").read_bytes())
        Draft202012Validator(schema).validate(report)
        directory = Path(values["report-directory"])
        script = adapter.ROOT / "actions/preserve-ci-report/scripts/preserve_ci_report.py"
        subprocess.run([
            sys.executable, "-I", str(script), "--producer", values["producer"],
            "--outcome", values["workflow-outcome"], "--repository", self.env["GITHUB_REPOSITORY"],
            "--represented-revision", self.env["GITHUB_SHA"], "--run-id", self.env["GITHUB_RUN_ID"],
            "--run-attempt", self.env["GITHUB_RUN_ATTEMPT"], "--retention-days", str(values["retention-days"]),
            "--maximum-files", "6", "--maximum-bytes", "6291456", "--source-directory", str(directory),
            "--runner-temp", str(self.runner),
        ], cwd=self.directory, capture_output=True, check=True)
        manifest = json.loads((directory / "relay-report-manifest.json").read_bytes())
        self.assertEqual(manifest["run"], {"id": int(self.env["GITHUB_RUN_ID"]), "attempt": int(self.env["GITHUB_RUN_ATTEMPT"])})
        self.assertEqual(manifest["represented_revision"], self.env["GITHUB_SHA"])
        self.assertEqual(manifest["outcome"], report["enforcement"]["planned_job_outcome"])
        self.assertEqual(manifest["completeness"], "complete" if values["workflow-outcome"] == "success" else "partial")
        self.assertEqual({item["path"] for item in manifest["files"]}, {"workflow.json", *(item["path"] for item in report["files"])})
        for item in manifest["files"]:
            data = (directory / item["path"]).read_bytes()
            self.assertEqual(len(data), item["size_bytes"])
            self.assertEqual(adapter.digest(data), item["sha256"])
        for line in (directory / "SHA256SUMS").read_text().splitlines():
            digest, path = line.split("  ", 1)
            self.assertEqual(adapter.digest((directory / path).read_bytes()), digest)
        bundle = {path.relative_to(directory).as_posix(): path.read_bytes() for path in directory.rglob("*") if path.is_file()}
        for data in bundle.values():
            self.assertNotIn(b"PRIVATE_CANARY", data)
            self.assertNotIn(b"CALLER_CODE_EXECUTED", data)
            self.assertNotIn(str(self.directory).encode(), data)
        self.assertEqual(report["reporting"]["artifact_upload"], "pending")
        export = os.environ.get("RELAY_ARCHITECTURE_ACCEPTANCE_EVIDENCE")
        if export:
            shutil.copytree(directory, Path(export) / label)
        return manifest, bundle

    def present(self, values: dict, *, upload: str = "success") -> tuple[int, str]:
        # This is an explicit upload fixture, never a claim of GitHub retention.
        env = self.env | {"INPUT_REPORT_DIRECTORY": values["report-directory"],
                          "INPUT_UPLOAD_OUTCOME": upload, "INPUT_ARTIFACT_DIGEST": "b" * 64 if upload == "success" else ""}
        with redirect_stdout(io.StringIO()) as captured:
            outcome = workflow.present(env)
        return outcome, captured.getvalue()

    def check_case(self, name: str, status: str, outcome: str, code: str) -> None:
        self.scenario(name)
        before = adapter.git(self.root, "status", "--porcelain=v1")
        result, report, values = self.execute(unavailable=name == "unavailable")
        self.assertEqual(result["semantic_status"], status)
        self.assertEqual(result["outcome"], outcome)
        self.assertEqual(report["enforcement"]["code"], code)
        self.assertEqual(report["validation"]["evidence"], "retained")
        self.assertEqual(adapter.git(self.root, "status", "--porcelain=v1"), before)
        self.retain(report, values, name)
        for item in report["files"]:
            self.assertEqual((self.root / item["path"]).read_bytes(), (Path(values["report-directory"]) / item["path"]).read_bytes())
        exit_code, annotations = self.present(values)
        self.assertEqual(exit_code, int(code != "AW-OK"))
        self.assertLessEqual(len(annotations.splitlines()), 20)
        self.assertNotIn("PRIVATE_CANARY", annotations)
        if name == "legacy":
            self.assertEqual(result["coverage"]["architecture-records"], "partial")
            self.assertIn("RELAY-ARCH-COMPAT-001", {item["id"] for item in result["findings"]})
        if name == "invalid":
            self.assertIn("::warning", annotations)
            self.assertNotIn("::error", annotations)
        if name in {"partial", "unavailable"}:
            diagram = self.artifact(result, "diagram_evidence")
            self.assertEqual(diagram["inventory_status"], "complete")
            self.assertEqual(result["coverage"]["diagram-sources"], "unavailable")

        # Every repository shape is denied required mode before native execution.
        self.env.update({"INPUT_MODE": "required", "GITHUB_RUN_ATTEMPT": "3"})
        result, report, values = self.execute()
        self.assertEqual(result["outcome"], "unavailable")
        self.assertEqual(result["findings"][0]["id"], "RELAY-ARCH-MODE-001")
        self.assertEqual(result["bounds"]["observed_scanned_files"], 0)
        self.assertEqual(report["enforcement"]["code"], "AW-REQUIRED")
        self.retain(report, values, name + "-required")
        self.assertEqual(self.present(values)[0], 1)

    def test_conformant_contract(self) -> None:
        self.check_case("conformant", "conformant", "passed", "AW-OK")

    def test_invalid_contract(self) -> None:
        self.check_case("invalid", "nonconformant", "warning", "AW-OK")

    def test_legacy_adr_is_never_conformant(self) -> None:
        self.check_case("legacy", "legacy", "warning", "AW-OK")

    def test_unknown_adoption(self) -> None:
        self.check_case("unknown", "incomplete", "warning", "AW-OK")

    def test_unavailable_execution_retains_independent_diagrams(self) -> None:
        self.check_case("unavailable", "unavailable", "unavailable", "AW-STAGE")

    def test_malicious_source_is_rejected_and_retained(self) -> None:
        self.check_case("malicious", "incomplete", "warning", "AW-OK")

    def test_partial_native_and_diagram_coverage(self) -> None:
        self.check_case("partial", "incomplete", "warning", "AW-OK")

    def test_complete_validation_and_workflow_bytes_reproduce_across_locations(self) -> None:
        self.scenario("partial")
        _result, first, first_values = self.execute()
        manifest, bundle = self.retain(first, first_values, "determinism-first")
        relocated = self.directory / "unrelated-checkout-name"
        relocated.mkdir()
        shutil.copytree(self.root, relocated / "caller")
        self.root = relocated / "caller"
        self.env["GITHUB_WORKSPACE"] = str(relocated)
        _result, second, second_values = self.execute()
        again_manifest, again_bundle = self.retain(second, second_values, "determinism-second")
        self.assertEqual(first, second)
        # Generic #6 metadata intentionally records wall-clock packaging time.
        # Compare every deterministic file, then every manifest field except that time.
        for metadata in ("relay-report-manifest.json", "SHA256SUMS"):
            del bundle[metadata], again_bundle[metadata]
        self.assertEqual(bundle, again_bundle)
        manifest.pop("generated_at")
        again_manifest.pop("generated_at")
        self.assertEqual(manifest, again_manifest)

    def test_private_native_diagnostics_and_presentation_exclude_source(self) -> None:
        self.scenario("conformant")
        self.add_contract('''[[requirements]]
id = "source-marker"
path = "README.md"
kind = "file"
ownership = "generated"
markers = ["PRIVATE_CANARY_DO_NOT_EXPORT"]
''')
        self.env["GITHUB_SHA"] = self.commit()
        for visibility in ("private", "internal"):
            self.env["RELAY_ARCH_VISIBILITY"] = visibility
            result, report, values = self.execute()
            self.assertEqual(result["semantic_status"], "nonconformant")
            self.assertEqual(report["privacy"]["classification"], visibility + "-repository")
            self.retain(report, values, visibility)
            exit_code, annotations = self.present(values)
            self.assertEqual(exit_code, 0)
            self.assertNotIn("PRIVATE_CANARY", annotations)
            self.assertNotIn("PRIVATE_CANARY", Path(self.env["GITHUB_STEP_SUMMARY"]).read_text())

    def test_fresh_retry_recovers_without_reusing_failed_attempt(self) -> None:
        self.scenario("partial")
        _result, failed, failed_values = self.execute(unavailable=True)
        _manifest, original_bytes = self.retain(failed, failed_values, "retry-failed")
        self.assertEqual(self.present(failed_values)[0], 1)
        old_work = self.env["INPUT_WORK_DIRECTORY"]
        self.env["GITHUB_RUN_ATTEMPT"] = "3"
        _result, recovered, recovered_values = self.execute()
        self.assertNotEqual(self.env["INPUT_WORK_DIRECTORY"], old_work)
        self.assertEqual(recovered["enforcement"]["code"], "AW-OK")
        self.retain(recovered, recovered_values, "retry-recovered")
        self.assertEqual(self.present(recovered_values)[0], 0)
        for path, data in original_bytes.items():
            self.assertEqual((Path(failed_values["report-directory"]) / path).read_bytes(), data)
        self.assertNotEqual(Path(failed_values["report-directory"]), Path(recovered_values["report-directory"]))

    def test_cancelled_attempt_and_early_failure_keep_only_current_stage_evidence(self) -> None:
        self.scenario("partial")
        self.execute()
        for stage, outcome in (("checkout", "failure"), ("validate", "cancelled")):
            # A new attempt with stale caller .reports, but no current validation receipt.
            self.env["GITHUB_RUN_ATTEMPT"] = str(int(self.env["GITHUB_RUN_ATTEMPT"]) + 1)
            self.prepare()
            for name in workflow.STAGES:
                self.stages[name]["outcome"] = "skipped"
            self.stages["harden"]["outcome"] = "success"
            self.stages["preflight"]["outcome"] = "success"
            self.stages[stage]["outcome"] = outcome
            report, values = self.finalize()
            self.assertEqual(report["files"], [])
            self.assertEqual(report["validation"]["evidence"], "unavailable")
            self.retain(report, values, "early-" + outcome)
            self.assertEqual(self.present(values)[0], 1)

    def test_upload_outage_keeps_local_manifest_but_cannot_pass(self) -> None:
        self.scenario("conformant")
        _result, report, values = self.execute()
        self.retain(report, values, "upload-outage")
        for upload in ("failure", "cancelled", "skipped"):
            exit_code, annotations = self.present(values, upload=upload)
            self.assertEqual(exit_code, 1)
            self.assertIn("::error title=AW-REPORT", annotations)
        self.assertTrue((Path(values["report-directory"]) / "relay-report-manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
