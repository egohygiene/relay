# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Exercise workflow identity, fresh evidence retention, and enforcement failures."""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from test_repository_architecture_adapter import AdapterFixture, RUNTIME, adapter
import run_architecture_validation_workflow as workflow


class ArchitectureWorkflowTests(AdapterFixture):
    def setUp(self) -> None:
        super().setUp()
        self.root.rename(self.directory / "caller")
        self.root = self.directory / "caller"
        self.runner = self.directory / "runner"
        self.runner.mkdir()
        self.env = {
            "GITHUB_REPOSITORY": "egohygiene/example", "GITHUB_SHA": self.commit(),
            "GITHUB_RUN_ID": "1234", "GITHUB_RUN_ATTEMPT": "2", "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_REF": "refs/pull/42/merge", "GITHUB_WORKSPACE": str(self.directory),
            "GITHUB_WORKFLOW_REF": "egohygiene/example/.github/workflows/architecture.yml@refs/pull/42/merge",
            "GITHUB_OUTPUT": str(self.directory / "outputs"), "GITHUB_STEP_SUMMARY": str(self.directory / "summary"),
            "RUNNER_TEMP": str(self.runner), "RELAY_ARCH_VISIBILITY": "public",
            "RELAY_ARCH_WORKFLOW_REPOSITORY": "egohygiene/relay", "RELAY_ARCH_WORKFLOW_SHA": "a" * 40,
            "RELAY_ARCH_WORKFLOW_REF": workflow.WORKFLOW + "@" + "a" * 40,
            "INPUT_CHECK_ID": "architecture", "INPUT_MODE": "advisory", "INPUT_RETENTION_DAYS": "30",
            "INPUT_CONTRACT_ADOPTION": "not-applicable", "INPUT_CONTRACTS": "[]",
            "INPUT_ADR_ADOPTION": "not-applicable", "INPUT_ADR_POLICY": "",
            "INPUT_DIAGRAM_ADOPTION": "not-applicable", "INPUT_DIAGRAM_ROOTS": "[]",
        }
        self.stages = {name: {"outcome": "success" if name in {"harden", "preflight", "checkout", "validate"} else "skipped"}
                       for name in workflow.STAGES}

    def prepare(self) -> Path:
        result = workflow.preflight(self.env)
        self.env["INPUT_WORK_DIRECTORY"] = result["work-directory"]
        return Path(result["work-directory"])

    def finalize(self) -> tuple[dict, dict]:
        self.env["INPUT_STAGES"] = json.dumps(self.stages)
        report, values = workflow.finalize(self.env)
        return report, values

    def diagram(self) -> None:
        self.put("diagrams/architecture.mmd", "graph TD\nA --> B\n%% PRIVATE_CANARY_DO_NOT_EXPORT\n")
        self.env.update({"GITHUB_SHA": self.commit(), "INPUT_DIAGRAM_ADOPTION": "present", "INPUT_DIAGRAM_ROOTS": '["diagrams"]'})

    def test_request_uses_exact_provider_identity_and_shared_profile(self) -> None:
        self.prepare()
        _work, state, request = workflow.load_state(self.env)
        self.assertEqual(request["repository"]["represented_revision"], self.env["GITHUB_SHA"])
        self.assertEqual(request["profile"]["sha256"], adapter.digest(adapter.read_file(adapter.PROFILE_PATH)))
        self.assertFalse(workflow.native_needed(request))
        self.assertEqual(state["retention_days"], 30)

    def test_rejects_mutable_or_mismatched_called_workflow(self) -> None:
        for key, value in [("RELAY_ARCH_WORKFLOW_REF", workflow.WORKFLOW + "@main"),
                           ("RELAY_ARCH_WORKFLOW_REPOSITORY", "attacker/relay"),
                           ("RELAY_ARCH_WORKFLOW_SHA", "b" * 40)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                workflow.preflight(self.env | {key: value})

    def test_event_allowlist_and_fork_pull_request_have_same_authority(self) -> None:
        workflow.preflight(self.env | {"UNTRUSTED_FORK_NAME": "attacker/repository"})
        for event in ["push", "workflow_dispatch", "schedule"]:
            workflow.preflight(self.env | {"GITHUB_EVENT_NAME": event, "GITHUB_REF": "refs/heads/master"})
        for event in ["pull_request_target", "workflow_run", "issue_comment", "repository_dispatch"]:
            with self.subTest(event=event), self.assertRaises(ValueError):
                workflow.preflight(self.env | {"GITHUB_EVENT_NAME": event})
        with self.assertRaises(ValueError):
            workflow.preflight(self.env | {"GITHUB_REF": "refs/heads/main"})

    def test_invalid_input_is_non_reflective_and_never_becomes_a_request(self) -> None:
        for key, value in [("INPUT_CONTRACTS", '["../private"]'), ("INPUT_DIAGRAM_ROOTS", "x" * 5000),
                           ("INPUT_RETENTION_DAYS", "91"), ("INPUT_RETENTION_DAYS", "1.5"),
                           ("INPUT_MODE", "::error::SECRET"), ("INPUT_CHECK_ID", "../escape"),
                           ("INPUT_ADR_ADOPTION", "present"), ("RELAY_ARCH_VISIBILITY", "unknown")]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                workflow.preflight(self.env | {key: value})

    def test_rejected_preflight_retains_fixed_failure_report(self) -> None:
        self.env.update({"INPUT_MODE": "SECRET_MODE", "INPUT_STAGES": "{}"})
        self.stages["preflight"]["outcome"] = "failure"
        report, values = self.finalize()
        self.assertEqual(report["enforcement"]["code"], "AW-INPUT")
        self.assertEqual(report["mode"], "unknown")
        self.assertEqual(report["retention_days"], 30)
        self.assertEqual(report["files"], [])
        self.assertNotIn("SECRET", json.dumps(report))
        self.assertTrue((Path(values["report-directory"]) / "workflow.json").is_file())

    def test_checkout_failure_does_not_read_stale_consumer_reports(self) -> None:
        self.prepare()
        self.put(workflow.RESULT_PATH, '{"stale":"PRIVATE_CANARY_DO_NOT_EXPORT"}')
        self.stages["checkout"]["outcome"] = "failure"
        self.stages["validate"]["outcome"] = "skipped"
        report, _values = self.finalize()
        self.assertEqual(report["enforcement"]["code"], "AW-STAGE")
        self.assertEqual(report["validation"]["evidence"], "unavailable")
        self.assertEqual(report["files"], [])

    def test_successful_diagram_run_preserves_identical_local_evidence(self) -> None:
        self.diagram()
        self.prepare()
        result = workflow.validate(self.env)
        report, values = self.finalize()
        self.assertEqual(report["enforcement"]["planned_job_outcome"], "success")
        self.assertEqual(report["validation"]["semantic_status"], "incomplete")
        self.assertEqual(report["reporting"]["artifact_upload"], "pending")
        for item in report["files"]:
            retained = adapter.read_file(Path(values["report-directory"]) / item["path"])
            self.assertEqual(retained, adapter.read_file(self.root / item["path"]))
            self.assertEqual(adapter.digest(retained), item["sha256"])
            self.assertNotIn(b"PRIVATE_CANARY", retained)
        self.assertEqual(result["coverage"]["diagram-sources"], "unavailable")

    def test_existing_extra_reports_and_runtime_files_are_not_retained(self) -> None:
        self.prepare()
        self.put(".reports/architecture-validation/secret.json", "SECRET_DO_NOT_EXPORT")
        workflow.validate(self.env)
        report, values = self.finalize()
        self.assertEqual([entry["path"] for entry in report["files"]], [workflow.RESULT_PATH])
        self.assertEqual(len(list(Path(values["report-directory"]).rglob("*.json"))), 2)

    def test_symlink_output_failure_cannot_reuse_a_previous_result(self) -> None:
        self.prepare()
        outside = self.directory / "private"
        outside.mkdir()
        (self.root / ".reports").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(adapter.AdapterError):
            workflow.validate(self.env)
        self.stages["validate"]["outcome"] = "failure"
        report, _values = self.finalize()
        self.assertEqual(report["enforcement"]["code"], "AW-EVIDENCE")
        self.assertEqual(report["files"], [])

    def test_tampered_staging_drops_all_validation_files(self) -> None:
        work = self.prepare()
        workflow.validate(self.env)
        (work / "evidence" / workflow.RESULT_PATH).write_text("{}")
        report, _values = self.finalize()
        self.assertEqual(report["enforcement"]["code"], "AW-EVIDENCE")
        self.assertEqual(report["files"], [])

    def test_changed_run_identity_rejects_replayed_evidence(self) -> None:
        self.prepare()
        workflow.validate(self.env)
        self.env["GITHUB_RUN_ATTEMPT"] = "3"
        report, _values = self.finalize()
        self.assertEqual(report["enforcement"]["planned_job_outcome"], "failure")
        self.assertEqual(report["files"], [])

    def test_missing_runtime_keeps_diagram_evidence_and_fails_execution(self) -> None:
        self.diagram()
        self.env["INPUT_CONTRACT_ADOPTION"] = "unknown"
        self.prepare()
        result = workflow.validate(self.env)
        self.stages["acquire"]["outcome"] = "failure"
        self.stages["validate"]["outcome"] = "failure"
        report, _values = self.finalize()
        self.assertEqual(report["enforcement"]["planned_job_outcome"], "failure")
        self.assertEqual(result["outcome"], "unavailable")
        self.assertTrue(any("diagram-evidence.json" in item["path"] for item in report["files"]))

    def test_required_intent_stays_unavailable_and_retains_result(self) -> None:
        self.env["INPUT_MODE"] = "required"
        self.prepare()
        result = workflow.validate(self.env)
        self.stages["validate"]["outcome"] = "failure"
        report, _values = self.finalize()
        self.assertEqual(result["outcome"], "unavailable")
        self.assertEqual(report["enforcement"]["code"], "AW-REQUIRED")
        self.assertEqual(report["validation"]["evidence"], "retained")

    def test_cancelled_and_skipped_prerequisites_cannot_pass(self) -> None:
        self.prepare()
        workflow.validate(self.env)
        for stage in ("harden", "checkout", "validate"):
            for value in ("failure", "cancelled", "skipped"):
                original = self.stages[stage]["outcome"]
                self.stages[stage]["outcome"] = value
                report, _values = self.finalize()
                self.assertNotEqual(report["enforcement"]["planned_job_outcome"], "success")
                self.stages[stage]["outcome"] = original

    def test_missing_required_acquisition_stage_cannot_pass_native_run(self) -> None:
        self.env["INPUT_CONTRACT_ADOPTION"] = "unknown"
        self.prepare()
        for name in ("hygiene", "egolint", "holon", "acquire", "build"):
            self.stages[name]["outcome"] = "success"
        for name in ("hygiene", "egolint", "holon", "acquire", "build"):
            self.stages[name]["outcome"] = "skipped"
            report, _values = self.finalize()
            self.assertEqual(report["enforcement"]["code"], "AW-STAGE")
            self.stages[name]["outcome"] = "success"

    def test_private_and_internal_reports_keep_visibility_and_exclude_source(self) -> None:
        self.diagram()
        for visibility in ("private", "internal"):
            self.env["RELAY_ARCH_VISIBILITY"] = visibility
            self.prepare()
            workflow.validate(self.env)
            report, values = self.finalize()
            self.assertEqual(report["privacy"]["classification"], visibility + "-repository")
            bundle = b"".join(path.read_bytes() for path in Path(values["report-directory"]).rglob("*") if path.is_file())
            self.assertNotIn(b"PRIVATE_CANARY", bundle)

    def test_report_names_partition_caller_workflows_and_check_ids(self) -> None:
        self.prepare()
        workflow.validate(self.env)
        _report, first = self.finalize()
        self.env["GITHUB_WORKFLOW_REF"] = self.env["GITHUB_WORKFLOW_REF"].replace("architecture.yml", "other.yml")
        self.prepare()
        workflow.validate(self.env)
        _report, second = self.finalize()
        self.assertNotEqual(first["producer"], second["producer"])
        self.env["INPUT_CHECK_ID"] = "other"
        self.prepare()
        workflow.validate(self.env)
        _report, third = self.finalize()
        self.assertNotEqual(second["producer"], third["producer"])

    def test_generic_report_lifecycle_binds_success_and_failure_bundles(self) -> None:
        self.diagram()
        self.prepare()
        workflow.validate(self.env)
        for raw_outcome in ("success", "failure"):
            self.stages["checkout"]["outcome"] = raw_outcome
            report, values = self.finalize()
            script = adapter.ROOT / "actions/preserve-ci-report/scripts/preserve_ci_report.py"
            args = [sys.executable, "-I", str(script), "--producer", values["producer"],
                    "--outcome", values["workflow-outcome"], "--repository", self.env["GITHUB_REPOSITORY"],
                    "--represented-revision", self.env["GITHUB_SHA"], "--run-id", "1234", "--run-attempt", "2",
                    "--retention-days", "30", "--maximum-files", "6", "--maximum-bytes", "6291456",
                    "--source-directory", values["report-directory"], "--runner-temp", str(self.runner)]
            subprocess.run(args, cwd=self.directory, check=True, capture_output=True)
            directory = Path(values["report-directory"])
            manifest = json.loads((directory / "relay-report-manifest.json").read_text())
            self.assertEqual(manifest["represented_revision"], report["identity"]["revision"])
            self.assertEqual(manifest["run"], {"id": 1234, "attempt": 2})
            self.assertEqual(manifest["outcome"], raw_outcome)
            for item in manifest["files"]:
                self.assertEqual(adapter.digest((directory / item["path"]).read_bytes()), item["sha256"])

    def test_closed_report_schema_rejects_extra_source_content(self) -> None:
        try:
            from jsonschema import Draft202012Validator, ValidationError
        except ImportError:
            self.skipTest("optional JSON Schema validator is unavailable")
        self.prepare()
        workflow.validate(self.env)
        report, _values = self.finalize()
        schema = json.loads((adapter.ROOT / "schemas/architecture-workflow-evidence.v1.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        validator.validate(report)
        report["source_content"] = "PRIVATE_CANARY_DO_NOT_EXPORT"
        with self.assertRaises(ValidationError):
            validator.validate(report)

    def test_summary_enforces_actual_preservation_and_digest(self) -> None:
        self.prepare()
        workflow.validate(self.env)
        _report, values = self.finalize()
        self.env["INPUT_REPORT_DIRECTORY"] = values["report-directory"]
        for upload, digest, expected in [("failure", "", 1), ("skipped", "", 1), ("cancelled", "", 1),
                                          ("success", "", 1), ("success", "b" * 64, 0)]:
            self.env.update({"INPUT_UPLOAD_OUTCOME": upload, "INPUT_ARTIFACT_DIGEST": digest})
            with redirect_stdout(io.StringIO()) as captured:
                self.assertEqual(workflow.present(self.env), expected)
            if expected:
                self.assertIn("::error title=AW-REPORT", captured.getvalue())
        self.assertIn("Evidence upload", Path(self.env["GITHUB_STEP_SUMMARY"]).read_text())

    def test_annotations_escape_commands_cap_count_and_preserve_source_locations(self) -> None:
        finding = adapter.relay_finding("UNKNOWN") | {"summary": "private%\n::error::text", "path": "docs/a,b:c.md", "line": 4}
        lines = workflow.annotations({"findings": [finding] * 30}, "AW-UNAVAILABLE")
        self.assertEqual(len(lines), 20)
        self.assertTrue(all("\n" not in line for line in lines))
        self.assertIn("file=caller/docs/a%2Cb%3Ac.md,line=4", lines[0])
        self.assertIn("private%25%0A", lines[0])
        self.assertTrue(lines[-1].startswith("::error title=AW-UNAVAILABLE"))

    def test_prepare_rejects_outside_or_symlink_work_storage(self) -> None:
        work = self.prepare()
        with self.assertRaises(ValueError):
            workflow.work_root(self.env | {"INPUT_WORK_DIRECTORY": str(self.root)})
        link = self.runner / "relay-architecture-work-link"
        link.symlink_to(work, target_is_directory=True)
        with self.assertRaises(adapter.AdapterError):
            workflow.work_root(self.env | {"INPUT_WORK_DIRECTORY": str(link)})

    def test_cli_ignores_caller_python_modules_and_environment_overrides(self) -> None:
        self.prepare()
        self.put("json.py", 'raise RuntimeError("CALLER_CODE_EXECUTED")')
        self.put("sitecustomize.py", 'raise RuntimeError("CALLER_CODE_EXECUTED")')
        env = os.environ | self.env | {"INPUT_OPERATION": "validate", "PYTHONPATH": str(self.root)}
        process = subprocess.run([sys.executable, "-I", str(adapter.ROOT / "scripts/run_architecture_validation_workflow.py")],
                                 cwd=self.root, env=env, capture_output=True, text=True, check=False)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertNotIn("CALLER_CODE_EXECUTED", process.stderr + process.stdout)

    @unittest.skipUnless(RUNTIME, "prepared native architecture runtime is explicitly required")
    def test_native_warning_is_retained_byte_compatibly_without_becoming_conformance(self) -> None:
        self.add_adrs()
        self.env.update({"GITHUB_SHA": self.commit(), "INPUT_ADR_ADOPTION": "present", "INPUT_ADR_POLICY": "policy.toml"})
        # Reuse the source-owned fixture policy path, never invent a policy in the workflow.
        self.env["INPUT_ADR_POLICY"] = self.request["inputs"]["repository_intelligence_policy"]
        self.prepare()
        result = workflow.validate(self.env, runtime=Path(RUNTIME))
        for name in workflow.STAGES:
            self.stages[name]["outcome"] = "success"
        report, values = self.finalize()
        self.assertEqual(result["coverage"]["architecture-records"], "partial")
        self.assertEqual(report["enforcement"]["planned_job_outcome"], "success")
        self.assertTrue(any(item["path"].endswith("egolint.sarif") for item in report["files"]))
        for item in report["files"]:
            self.assertEqual((Path(values["report-directory"]) / item["path"]).read_bytes(), (self.root / item["path"]).read_bytes())


class ArchitectureWorkflowPackagingTests(unittest.TestCase):
    def test_workflow_authority_source_pins_and_preservation_order(self) -> None:
        source = (adapter.ROOT / ".github/workflows/repository-architecture-validation.yml").read_text()
        try:
            import yaml
        except ImportError:
            # Relay's CI already requires Ruby/Psych for YAML validation.
            value = json.loads(subprocess.check_output(
                ["ruby", "-rjson", "-rpsych", "-e", "puts JSON.generate(Psych.safe_load(STDIN.read))"], input=source.encode()))
        else:
            value = yaml.safe_load(source)
        self.assertEqual(value["permissions"], {"contents": "read"})
        job = value["jobs"]["architecture"]
        self.assertEqual(job["permissions"], {"contents": "read"})
        self.assertEqual(job["runs-on"], "ubuntu-24.04")
        self.assertEqual(job["timeout-minutes"], 20)
        self.assertIn("${{ github.workflow_ref }}", value["concurrency"]["group"])
        self.assertIn("${{ inputs.check-id }}", value["concurrency"]["group"])
        steps = {step.get("id", "present"): step for step in job["steps"]}
        self.assertEqual(steps["checkout"]["with"]["ref"], "${{ github.sha }}")
        for step in job["steps"]:
            self.assertFalse(step["uses"].startswith("./"))
            if not step["uses"].startswith("$/"):
                self.assertRegex(step["uses"], r"@[0-9a-f]{40}$")
            self.assertNotIn("run", step)
        for name in ("checkout", "hygiene", "egolint", "holon"):
            self.assertFalse(steps[name]["with"]["persist-credentials"])
            self.assertFalse(steps[name]["with"]["submodules"])
            self.assertFalse(steps[name]["with"]["lfs"])
        for item in adapter.profile()["sources"]:
            name = item["repository"].split("/")[1]
            self.assertEqual(steps[name]["with"]["ref"], item["revision"])
        self.assertEqual(steps["finalize"]["if"], "${{ always() }}")
        self.assertIn("always()", steps["preserve"]["if"])
        self.assertIn("steps.checkout.outcome == 'success'", steps["validate"]["if"])
        self.assertIn("steps.preflight.outcome == 'success'", steps["validate"]["if"])
        self.assertNotIn("steps.build", steps["validate"]["if"])
        for name in ("hygiene", "egolint", "holon", "acquire"):
            self.assertIn("steps.preflight.outputs.native-needed == 'true'", steps[name]["if"])
        self.assertEqual(steps["build"]["if"], "${{ steps.acquire.outcome == 'success' }}")
        self.assertEqual(job["steps"][-1]["with"]["operation"], "present")
        self.assertIn("steps.preserve.outcome", job["steps"][-1]["with"]["upload-outcome"])
        for token in ("secrets:", "secrets.", "actions/cache", "pull_request_target:", "pages: write", "id-token:"):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
