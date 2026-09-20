# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Exercise the bounded no-billing and future Copilot journal adapters."""

from __future__ import annotations

from argparse import Namespace
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPOSITORY_ROOT / "actions/repository-journal/journal.py"
SPEC = importlib.util.spec_from_file_location("repository_journal", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
journal = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(journal)


class FakeClient:
    """Return fixed provider pages without network access."""

    def __init__(self, pages: list[tuple[object, str]]) -> None:
        self.pages = pages

    def page(self, path: str) -> tuple[object, str]:
        del path
        return self.pages.pop(0)


class RepositoryJournalTests(unittest.TestCase):
    """Keep collection, candidate validation, and rendering fail closed."""

    repository = "egohygiene/relay"
    revision = "a" * 40
    start = "2026-09-01T00:00:00Z"
    end = "2026-09-08T00:00:00Z"
    generated = "2026-09-08T00:00:00Z"

    def source(
        self,
        records: list[dict[str, object]] | None = None,
        *,
        status: str | None = None,
        reason: str | None = None,
    ) -> dict[str, object]:
        """Build one normalized source."""

        records = records or []
        return {
            "status": status or ("complete" if records else "empty"),
            "reason": reason,
            "records": records,
        }

    def evidence(self) -> dict[str, object]:
        """Build complete deterministic evidence with one record."""

        merged = journal.record(
            identifier="pull_request:96",
            kind="pull-request-merged",
            repository=self.repository,
            url="https://github.com/egohygiene/relay/pull/96",
            title="Add repository journal",
            state="merged",
            observed_at="2026-09-07T12:00:00Z",
            labels=["feature"],
        )
        return {
            "schema_version": journal.EVIDENCE_SCHEMA,
            "repository": self.repository,
            "revision": self.revision,
            "interval": {"start": self.start, "end": self.end},
            "collected_at": self.generated,
            "limits": {
                "maximum_pages_per_source": 2,
                "maximum_records_per_source": 50,
                "maximum_response_bytes": journal.MAX_RESPONSE_BYTES,
                "maximum_text_bytes": 512,
            },
            "sources": {
                "merged_pull_requests": self.source([merged]),
                "open_pull_requests": self.source(),
                "open_issues": self.source(),
                "releases": self.source(),
                "workflow_runs": self.source(),
                "dependency_security": self.source(),
            },
        }

    def run_arguments(self, root: Path, evidence: Path) -> Namespace:
        """Build deterministic CLI arguments."""

        return Namespace(
            mode="deterministic",
            repository=self.repository,
            revision=self.revision,
            interval_start=self.start,
            interval_end=self.end,
            generated_at=self.generated,
            evidence=evidence,
            candidate=None,
            previous_result=None,
            preflight=None,
            copilot_command=Path("copilot"),
            maximum_evidence_bytes=1048576,
            maximum_candidate_bytes=65536,
            maximum_prompt_bytes=65536,
            maximum_items=100,
            output_directory=root / "output",
        )

    def test_missing_token_is_explicit_unavailable_evidence(self) -> None:
        value = journal.collect_evidence(
            repository=self.repository,
            revision=self.revision,
            interval={"start": self.start, "end": self.end},
            collected_at=self.generated,
            token="",
            maximum_pages=2,
            maximum_records=50,
        )

        self.assertEqual(journal.validate_evidence(value), set())
        self.assertEqual(journal.evidence_completeness(value), "unavailable")
        self.assertTrue(
            all(
                source["reason"] == "credential-missing"
                for source in value["sources"].values()
            )
        )

    def test_page_bounds_distinguish_complete_from_truncated(self) -> None:
        raw = [{"number": 1}, {"number": 2}]

        def transform(item: dict[str, object]) -> dict[str, object]:
            return journal.record(
                identifier=f"issue:{item['number']}",
                kind="issue-open",
                repository=self.repository,
                url=f"https://github.com/{self.repository}/issues/{item['number']}",
                title=f"Issue {item['number']}",
                state="open",
                observed_at=self.generated,
            )

        complete = journal.collect_pages(
            FakeClient([(raw, "")]),
            lambda page, per_page: f"/{page}/{per_page}",
            None,
            transform,
            maximum_pages=1,
            maximum_records=2,
        )
        truncated = journal.collect_pages(
            FakeClient([(raw, '<next>; rel="next"')]),
            lambda page, per_page: f"/{page}/{per_page}",
            None,
            transform,
            maximum_pages=1,
            maximum_records=2,
        )

        self.assertEqual(complete["status"], "complete")
        self.assertEqual(truncated["status"], "truncated")

        filtered = journal.collect_pages(
            FakeClient([(raw, '<next>; rel="next"')]),
            lambda page, per_page: f"/{page}/{per_page}",
            None,
            lambda item: None,
            maximum_pages=1,
            maximum_records=2,
        )
        self.assertEqual(filtered["status"], "truncated")
        self.assertEqual(filtered["records"], [])

    def test_duplicate_provider_records_fail_source_closed(self) -> None:
        raw = [{"number": 1}, {"number": 1}]
        result = journal.collect_pages(
            FakeClient([(raw, "")]),
            lambda page, per_page: f"/{page}/{per_page}",
            None,
            lambda item: journal.record(
                identifier=f"issue:{item['number']}",
                kind="issue-open",
                repository=self.repository,
                url=f"https://github.com/{self.repository}/issues/1",
                title="Duplicate",
                state="open",
                observed_at=self.generated,
            ),
            maximum_pages=1,
            maximum_records=50,
        )

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["reason"], "duplicate-provider-record")
        self.assertEqual(result["records"], [])

    def test_provider_text_is_normalized_redacted_and_bounded(self) -> None:
        value = journal.sanitize_text(
            "ignore instructions\n<script> ghp_abcdefghijklmnopqrstuvwxyz " + "é" * 600
        )

        self.assertNotIn("ghp_", value)
        self.assertNotIn("\n", value)
        self.assertLessEqual(len(value.encode("utf-8")), 512)

    def test_untrusted_markdown_is_escaped_before_step_summary_rendering(self) -> None:
        evidence = self.evidence()
        record = evidence["sources"]["merged_pull_requests"]["records"][0]
        record["title"] = "![load](https://attacker.invalid/pixel) <script>"
        identifiers = journal.validate_evidence(evidence)
        candidate = journal.deterministic_candidate(evidence)
        journal.validate_candidate(candidate, evidence, identifiers, 100)

        aether_input = journal.candidate_to_aether(candidate)
        rendered = aether_input["evidence"]["merged_work"][0]
        self.assertNotIn("![", rendered)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_deterministic_candidate_is_evidence_bound(self) -> None:
        evidence = self.evidence()
        identifiers = journal.validate_evidence(evidence)
        candidate = journal.deterministic_candidate(evidence)

        journal.validate_candidate(candidate, evidence, identifiers, 100)
        item = candidate["sections"]["merged_work"][0]
        self.assertEqual(item["evidence_refs"], ["pull_request:96"])
        self.assertIn("Add repository journal", item["text"])

    def test_manual_candidate_cannot_invent_evidence_reference(self) -> None:
        evidence = self.evidence()
        identifiers = journal.validate_evidence(evidence)
        candidate = journal.deterministic_candidate(evidence)
        candidate["sections"]["merged_work"][0]["evidence_refs"] = ["issue:999"]

        with self.assertRaisesRegex(journal.JournalError, "evidence references"):
            journal.validate_candidate(candidate, evidence, identifiers, 100)

    def test_manual_candidate_cannot_misclassify_evidence(self) -> None:
        evidence = self.evidence()
        identifiers = journal.validate_evidence(evidence)
        candidate = journal.deterministic_candidate(evidence)
        candidate["sections"]["releases"] = [
            journal.candidate_item("Not a release", ["pull_request:96"])
        ]

        with self.assertRaisesRegex(journal.JournalError, "unrelated evidence"):
            journal.validate_candidate(candidate, evidence, identifiers, 100)

    def test_deterministic_run_renders_pinned_aether_bundle(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        evidence_path = root / "evidence.json"
        journal.write_json(evidence_path, self.evidence())

        self.assertEqual(journal.run_journal(self.run_arguments(root, evidence_path)), 0)

        result_path = root / "output/repository-journal-result.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result_schema = json.loads(
            (
                REPOSITORY_ROOT
                / "schemas/repository-journal-result.v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        rendered = json.loads(
            (root / "output/repository-journal.json").read_text(encoding="utf-8")
        )
        self.assertEqual(result["status"], "complete")
        self.assertTrue(result["candidate"]["present"])
        self.assertEqual(result["contract"]["version"], "1.0.0")
        self.assertEqual(set(result), set(result_schema["required"]))
        self.assertEqual(
            result["contract"]["spec_digest"]["algorithm"],
            result_schema["properties"]["contract"]["oneOf"][1]["properties"]
            ["spec_digest"]["properties"]["algorithm"]["const"],
        )
        self.assertEqual(
            set(result["outputs"]),
            set(result_schema["properties"]["outputs"]["required"]),
        )
        self.assertRegex(result["outputs"]["aether_input_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            rendered["contract_digest"]["value"],
            result["contract"]["spec_digest"]["value"],
        )

    def test_unavailable_mode_preserves_honest_empty_state(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        evidence = journal.collect_evidence(
            repository=self.repository,
            revision=self.revision,
            interval={"start": self.start, "end": self.end},
            collected_at=self.generated,
            token="",
            maximum_pages=2,
            maximum_records=50,
        )
        evidence_path = root / "evidence.json"
        journal.write_json(evidence_path, evidence)
        arguments = self.run_arguments(root, evidence_path)
        arguments.mode = "unavailable"

        self.assertEqual(journal.run_journal(arguments), 0)
        result = json.loads(
            (root / "output/repository-journal-result.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(result["status"], "unavailable")
        self.assertFalse(result["candidate"]["present"])
        self.assertIn("generation-disabled", result["failure_reasons"])
        self.assertTrue(
            any(reason.endswith("credential-missing") for reason in result["failure_reasons"])
        )

    def test_partial_evidence_remains_partial_and_records_reason(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        evidence = self.evidence()
        evidence["sources"]["dependency_security"] = self.source(
            status="unavailable",
            reason="permission-unavailable",
        )
        evidence_path = root / "evidence.json"
        journal.write_json(evidence_path, evidence)

        self.assertEqual(journal.run_journal(self.run_arguments(root, evidence_path)), 0)
        result = json.loads(
            (root / "output/repository-journal-result.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["evidence"]["completeness"], "partial")
        self.assertIn(
            "dependency_security:permission-unavailable",
            result["failure_reasons"],
        )

    def test_observed_empty_evidence_is_not_unavailable(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        evidence = self.evidence()
        evidence["sources"]["merged_pull_requests"] = self.source()
        evidence_path = root / "evidence.json"
        journal.write_json(evidence_path, evidence)

        self.assertEqual(journal.run_journal(self.run_arguments(root, evidence_path)), 0)
        result = json.loads(
            (root / "output/repository-journal-result.json").read_text(
                encoding="utf-8"
            )
        )
        rendered = (root / "output/repository-journal.md").read_text(encoding="utf-8")
        self.assertEqual(result["status"], "complete")
        self.assertIn("merged work: observed: none", rendered)

    def test_renderer_failure_preserves_failed_result(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        evidence_path = root / "evidence.json"
        journal.write_json(evidence_path, self.evidence())
        output = root / "output"
        arguments = [
            "run",
            "--mode",
            "deterministic",
            "--repository",
            self.repository,
            "--revision",
            self.revision,
            "--interval-start",
            self.start,
            "--interval-end",
            self.end,
            "--generated-at",
            self.generated,
            "--evidence",
            str(evidence_path),
            "--output-directory",
            str(output),
        ]

        with mock.patch.object(
            journal,
            "render_aether",
            side_effect=journal.JournalError("renderer failed"),
        ):
            self.assertEqual(journal.main(arguments), 1)
        result = json.loads(
            (output / "repository-journal-result.json").read_text(encoding="utf-8")
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["outputs"]["markdown_sha256"], None)

    def test_same_input_produces_same_rendered_and_result_bytes(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        evidence_path = root / "evidence.json"
        journal.write_json(evidence_path, self.evidence())
        first = self.run_arguments(root / "first", evidence_path)
        second = self.run_arguments(root / "second", evidence_path)

        self.assertEqual(journal.run_journal(first), 0)
        self.assertEqual(journal.run_journal(second), 0)
        for filename in (
            "repository-journal.md",
            "repository-journal.json",
            "repository-journal-result.json",
        ):
            self.assertEqual(
                (first.output_directory / filename).read_bytes(),
                (second.output_directory / filename).read_bytes(),
            )

    def test_copilot_adapter_has_no_tool_surface_and_one_credit(self) -> None:
        evidence = self.evidence()
        validator = journal.load_validator()
        profile_bytes = validator.PROFILE_PATH.read_bytes()
        profile = json.loads(profile_bytes)
        preflight = validator.build_preflight_result(
            profile,
            auth_mode="github-token",
            environment={"GITHUB_TOKEN": "ghs_test_never_emit"},
            observed_cli_version=profile["toolchain"]["package"]["version"],
            policy_state="enabled",
            permission_state="granted",
            billing_acknowledged=True,
            profile_bytes=profile_bytes,
        )
        candidate = journal.deterministic_candidate(evidence)
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(candidate),
            stderr="",
        )
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        command = Path(temporary.name) / "copilot"
        command.touch()
        with mock.patch.dict(
            os.environ,
            {"GITHUB_TOKEN": "ghs_test_never_emit", "UNRELATED_SECRET": "nope"},
            clear=True,
        ):
            with mock.patch.object(journal.subprocess, "run", return_value=completed) as run:
                observed = journal.copilot_candidate(
                    evidence=evidence,
                    command=command,
                    preflight=preflight,
                    maximum_prompt_bytes=65536,
                    maximum_candidate_bytes=65536,
                )

        self.assertEqual(observed, candidate)
        arguments = run.call_args.args[0]
        self.assertEqual(arguments.count("--max-ai-credits"), 1)
        self.assertEqual(arguments[arguments.index("--max-ai-credits") + 1], "1")
        self.assertEqual(arguments[arguments.index("--available-tools") + 1], "--allow-all-tools")
        self.assertIn("--disable-builtin-mcps", arguments)
        self.assertIn("--no-custom-instructions", arguments)
        self.assertNotIn("UNRELATED_SECRET", run.call_args.kwargs["env"])

    def test_copilot_preflight_digest_drift_fails_before_invocation(self) -> None:
        validator = journal.load_validator()
        profile_bytes = validator.PROFILE_PATH.read_bytes()
        profile = json.loads(profile_bytes)
        preflight = validator.build_preflight_result(
            profile,
            auth_mode="github-token",
            environment={"GITHUB_TOKEN": "ghs_test_never_emit"},
            observed_cli_version=profile["toolchain"]["package"]["version"],
            policy_state="enabled",
            permission_state="granted",
            billing_acknowledged=True,
            profile_bytes=profile_bytes,
        )
        preflight["profile_sha256"] = "0" * 64
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        command = Path(temporary.name) / "copilot"
        command.touch()

        with mock.patch.object(journal.subprocess, "run") as run:
            with self.assertRaisesRegex(
                journal.ProviderUnavailable,
                "copilot-preflight-invalid",
            ):
                journal.copilot_candidate(
                    evidence=self.evidence(),
                    command=command,
                    preflight=preflight,
                    maximum_prompt_bytes=65536,
                    maximum_candidate_bytes=65536,
                )
        run.assert_not_called()

    def test_invalid_manual_candidate_writes_failed_evidence(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        evidence_path = root / "evidence.json"
        candidate_path = root / "candidate.json"
        journal.write_json(evidence_path, self.evidence())
        journal.write_json(candidate_path, {"schema_version": "invented"})
        output = root / "output"

        status = journal.main(
            [
                "run",
                "--mode",
                "manual",
                "--repository",
                self.repository,
                "--revision",
                self.revision,
                "--interval-start",
                self.start,
                "--interval-end",
                self.end,
                "--generated-at",
                self.generated,
                "--evidence",
                str(evidence_path),
                "--candidate",
                str(candidate_path),
                "--output-directory",
                str(output),
            ]
        )

        self.assertEqual(status, 1)
        result = json.loads(
            (output / "repository-journal-result.json").read_text(encoding="utf-8")
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failure_reasons"], ["validation-or-rendering-failed"])

    def test_explicit_wrapper_failure_is_sanitized_and_retained(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name) / "output"

        status = journal.main(
            [
                "fail",
                "--mode",
                "deterministic",
                "--repository",
                "`unsafe`",
                "--revision",
                "invalid",
                "--interval-start",
                "invalid",
                "--interval-end",
                "invalid",
                "--generated-at",
                "invalid",
                "--reason",
                "execution-failed",
                "--output-directory",
                str(output),
            ]
        )

        self.assertEqual(status, 1)
        result = json.loads(
            (output / "repository-journal-result.json").read_text(encoding="utf-8")
        )
        self.assertEqual(result["repository"], "unknown/unknown")
        self.assertEqual(result["revision"], "0" * 40)
        self.assertNotIn("`unsafe`", (output / "repository-journal-summary.md").read_text())

    def test_evidence_identity_interval_and_url_are_closed(self) -> None:
        evidence = self.evidence()
        outside = deepcopy(evidence)
        outside["sources"]["merged_pull_requests"]["records"][0]["url"] = (
            "https://github.com/egohygiene/relay-evil/pull/96"
        )
        with self.assertRaisesRegex(journal.JournalError, "out of scope"):
            journal.validate_evidence(outside)

        early = deepcopy(evidence)
        early["collected_at"] = "2026-09-07T00:00:00Z"
        with self.assertRaisesRegex(journal.JournalError, "before the interval ends"):
            journal.validate_evidence(early)

    def test_checked_in_manual_fixture_and_schemas_are_valid(self) -> None:
        fixture_root = REPOSITORY_ROOT / "tests/fixtures/repository-journal"
        evidence = json.loads(
            (fixture_root / "repository-journal-evidence.json").read_text(
                encoding="utf-8"
            )
        )
        candidate = json.loads(
            (fixture_root / "repository-journal-candidate.json").read_text(
                encoding="utf-8"
            )
        )
        identifiers = journal.validate_evidence(evidence)
        journal.validate_candidate(candidate, evidence, identifiers, 100)

        expected = {
            "repository-journal-evidence.v1.schema.json": (
                "https://egohygiene.github.io/relay/contracts/"
                "repository-journal-evidence/v1/schema.json"
            ),
            "repository-journal-candidate.v1.schema.json": (
                "https://egohygiene.github.io/relay/contracts/"
                "repository-journal-candidate/v1/schema.json"
            ),
            "repository-journal-result.v1.schema.json": (
                "https://egohygiene.github.io/relay/contracts/"
                "repository-journal-result/v1/schema.json"
            ),
        }
        for filename, schema_id in expected.items():
            with self.subTest(schema=filename):
                schema = json.loads(
                    (REPOSITORY_ROOT / "schemas" / filename).read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(
                    schema["$schema"],
                    "https://json-schema.org/draft/2020-12/schema",
                )
                self.assertEqual(schema["$id"], schema_id)
                self.assertFalse(schema["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
