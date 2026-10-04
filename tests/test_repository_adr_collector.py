# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Canonical ADR collection, immutable replay, and owner-native integration."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "actions/repository-intelligence/scripts/collect_repository_adrs.py"
FIXTURE = ROOT / "tests/fixtures/repository-adr-collector/canonical"
POLICY = "docs/decisions/policy-reference.json"
INDEX = "docs/decisions/README.md"
FIRST = "docs/decisions/ADR-001-validation-contract.md"
OLD = "docs/decisions/ADR-002-legacy-projection.md"
NEW = "docs/decisions/ADR-003-versioned-projection.md"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:
    collector = load("adr_collector", SCRIPT)
except ModuleNotFoundError as error:
    if error.name not in {"jsonschema", "yaml"}:
        raise
    raise unittest.SkipTest("install roadmap-collector-requirements.txt for native collection tests") from error


def git(root, *args):
    environment = {**collector.base.environment(), "GIT_AUTHOR_DATE": "2026-10-04T12:00:00Z",
                   "GIT_COMMITTER_DATE": "2026-10-04T12:00:00Z"}
    return subprocess.check_output(["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
        "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test", "-C", str(root), *args],
        env=environment, stderr=subprocess.PIPE).decode().strip()


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_bounded_yaml_rejects_aliases_duplicate_keys_tags_and_malformed_documents(self):
        for metadata in ("id: A\nid: B", "id: &a A\nrelated: [*a]", "id: !!str A", "[not, a, mapping]"):
            with self.subTest(metadata=metadata), self.assertRaises((ValueError, collector.yaml.YAMLError)):
                collector.front_matter("---\n" + metadata + "\n---\n")
        self.assertIsNone(collector.front_matter("# Legacy ADR\nStatus: Accepted"))
        parsed = collector.front_matter("---\ndate: 2026-10-04\napproval: null\nrelated: []\n---\n")
        self.assertEqual(parsed, {"date": "2026-10-04", "approval": None, "related": []})

    def test_relative_paths_reject_traversal_reserved_outputs_and_git_metadata(self):
        for path in ("../private", "/tmp/private", "docs//decisions", "docs/./decisions", ".git/config",
                     ".reports/egolint/report.json", "docs/../secret", "docs/decisions/", "docs/evil\nname"):
            with self.subTest(path=path), self.assertRaises(collector.base.CollectorError):
                collector.relative(path)

    def test_private_unknown_and_internal_requests_replace_prior_output_with_closed_denial(self):
        consumer = self.root / "consumer"
        consumer.mkdir()
        output = self.root / collector.OUTPUT_NAME
        for visibility in ("private", "unknown", "internal"):
            output.write_text("previous candidate")
            result = subprocess.run([sys.executable, str(SCRIPT), "collect", "--runtime", str(self.root),
                "--repository-root", str(consumer), "--repository", "protected/hidden", "--visibility", visibility,
                "--source-commit", "a" * 40, "--observed-at", "2026-10-04T21:00:00Z", "--adoption", "present",
                "--output", str(output)], capture_output=True)
            self.assertEqual(result.returncode, 3)
            exported = output.read_text() + result.stdout.decode() + result.stderr.decode()
            for sensitive in ("protected/hidden", str(self.root), "a" * 40, "previous candidate"):
                self.assertNotIn(sensitive, exported)
            value = json.loads(output.read_text())
            self.assertEqual(set(value), {"schema", "status", "publication", "diagnostics"})
            self.assertEqual(value["diagnostics"][0]["code"], "VISIBILITY")

    def test_unsafe_output_paths_never_modify_consumer_or_symlink_targets(self):
        consumer = self.root / "consumer"
        consumer.mkdir()
        result = {"schema": collector.SCHEMA, "status": "denied", "publication": "denied", "diagnostics": []}
        with self.assertRaises(collector.base.CollectorError):
            collector.write_result(consumer / collector.OUTPUT_NAME, result, consumer)
        target = self.root / "keep"
        target.write_text("untouched")
        output = self.root / collector.OUTPUT_NAME
        output.symlink_to(target)
        with self.assertRaises(collector.base.CollectorError):
            collector.write_result(output, result, consumer)
        self.assertEqual(target.read_text(), "untouched")

    def test_closed_review_schema_rejects_extra_fields_and_denied_payloads(self):
        schema = json.loads((SCRIPT.parent.parent / "schemas/adr-collection-review.v1.schema.json").read_text())
        collector.jsonschema.Draft202012Validator.check_schema(schema)
        validator = collector.jsonschema.Draft202012Validator(schema)
        denied = {"schema": collector.SCHEMA, "status": "denied", "publication": "denied", "diagnostics": []}
        self.assertTrue(validator.is_valid(denied))
        self.assertFalse(validator.is_valid(dict(denied, repository="egohygiene/relay")))
        self.assertFalse(validator.is_valid(dict(denied, extra="payload")))


@unittest.skipUnless(os.environ.get("RELAY_ADR_RUNTIME"), "prepare the locked ADR runtime and set RELAY_ADR_RUNTIME")
class NativeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runtime = Path(os.environ["RELAY_ADR_RUNTIME"])
        self.consumer = self.root / "consumer"
        shutil.copytree(FIXTURE, self.consumer)
        git(self.consumer, "init", "--quiet", "--initial-branch", "main")
        self.commit()

    def commit(self):
        git(self.consumer, "add", "--all")
        git(self.consumer, "commit", "--quiet", "--allow-empty", "--message", "test: immutable ADR corpus")
        return git(self.consumer, "rev-parse", "HEAD")

    def args(self, **changes):
        args = collector.parser().parse_args(["collect", "--runtime", str(self.runtime),
            "--repository-root", str(self.consumer), "--repository", "egohygiene/relay", "--visibility", "public",
            "--source-commit", git(self.consumer, "rev-parse", "HEAD"), "--observed-at", "2026-10-04T21:00:00Z",
            "--adoption", "present", "--output", str(self.root / collector.OUTPUT_NAME)])
        for key, value in changes.items():
            setattr(args, key, value)
        return args

    def collect(self, **changes):
        args = self.args(**changes)
        result = collector.collect(args)
        collector.write_result(args.output, result, args.repository_root)
        return result

    def change(self, path, old, new):
        target = self.consumer / path
        target.write_text(target.read_text().replace(old, new))
        self.commit()

    def test_actual_native_pipeline_preserves_authority_lineage_and_existing_decisions_fragment(self):
        result = self.collect()
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["publication"], "denied")
        self.assertEqual(result["validation"], {"egolint": "incomplete", "hygiene": "valid", "coverage": "valid",
                         "observatory": "normalized", "diagnostics_truncated": False})
        snapshot = result["snapshot_candidate"]
        records = {r["key"]: r for r in snapshot["graph"]["entities"] if r["kind"] == "architecture_decision"}
        self.assertEqual(set(records), {"ADR-001", "ADR-002", "ADR-003"})
        self.assertIsNone(records["ADR-001"]["attributes"]["approval"])
        self.assertEqual(records["ADR-003"]["attributes"]["implementation_status"], "implemented")
        self.assertEqual(records["ADR-003"]["state"]["value"], "accepted")
        self.assertIn("/pull/24", records["ADR-003"]["attributes"]["approval"]["evidence"])
        self.assertEqual(len(snapshot["graph"]["relationships"]), 1)
        decisions = {d["entity"]["key"]: d for d in snapshot["views"]["decisions"]["decisions"]}
        self.assertEqual(decisions["ADR-002"]["superseded_by"][0]["key"], "ADR-003")
        self.assertEqual(result["coverage"]["decisions"]["collection"], "observed")
        for name, claim in result["coverage"].items():
            if name != "decisions":
                self.assertEqual(claim["collection"], "uncollected")
        self.assertEqual(snapshot["graph"]["events"], [])
        site = load("adr_site", SCRIPT.with_name("generate_repository_intelligence_site.py"))
        fragment = site.decisions_body(snapshot)
        for text in ("ADR-001", "ADR-002", "ADR-003", "Use a versioned projection"):
            self.assertIn(text, fragment)
        # Fragment rendering is not alpha.2 shell adoption; checkpoint 2 owns it.
        with self.assertRaises(site.SiteInputError):
            site.validate_snapshot(result, "egohygiene/relay", self.args().source_commit)

    def test_whole_envelopes_replay_across_checkout_names_and_ignore_dirty_worktrees(self):
        first = self.collect()
        clone = self.root / "elsewhere" / "different-name"
        clone.parent.mkdir()
        git(self.root, "clone", "--quiet", str(self.consumer), str(clone))
        (clone / FIRST).write_text("dirty data must not enter the projection")
        marker = self.root / "consumer-code-executed"
        hook = clone / ".git/hooks/pre-commit"
        hook.write_text(f"#!/bin/sh\ntouch {marker}\n")
        hook.chmod(0o700)
        before = git(clone, "status", "--porcelain")
        second = self.collect(repository_root=clone)
        self.assertEqual(collector.base.json_bytes(first), collector.base.json_bytes(second))
        self.assertEqual(git(clone, "status", "--porcelain"), before)
        self.assertFalse(marker.exists())
        self.assertNotIn(str(self.root), collector.base.json_bytes(second).decode())
        self.assertNotIn("fixture@example.test", collector.base.json_bytes(second).decode())

    def test_real_cli_and_exit_status_match_library_without_source_mutation(self):
        args = self.args()
        before = git(self.consumer, "status", "--porcelain")
        result = subprocess.run([sys.executable, str(SCRIPT), "collect", "--runtime", str(self.runtime),
            "--repository-root", str(self.consumer), "--repository", args.repository, "--visibility", "public",
            "--source-commit", args.source_commit, "--observed-at", args.observed_at, "--adoption", "present",
            "--output", str(args.output)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(json.loads(args.output.read_text()), collector.collect(args))
        self.assertEqual(git(self.consumer, "status", "--porcelain"), before)

    def test_duplicate_ids_broken_index_and_lineage_remain_owner_findings(self):
        self.change(FIRST, "ADR-001", "ADR-003")
        result = self.collect()
        self.assertEqual(result["status"], "invalid")
        codes = {d["code"] for d in result["diagnostics"]}
        self.assertIn("EGO-INTEL-ADR-METADATA-001", codes)
        self.assertIn("EGO-INTEL-ADR-INDEX-001", codes)
        self.assertNotIn("ADR-003", [e["key"] for e in result["projection_candidate"]["entities"]])

    def test_reciprocal_supersession_is_checked_by_egolint(self):
        self.change(OLD, "superseded_by: [ADR-003]", "superseded_by: [ADR-999]")
        result = self.collect()
        self.assertEqual(result["status"], "invalid")
        self.assertIn("EGO-INTEL-ADR-LINEAGE-001", {d["code"] for d in result["diagnostics"]})

    def test_missing_approval_is_never_inferred_from_implemented_state(self):
        self.change(NEW, "approval:\n  date: 2026-08-25\n  by: egohygiene-maintainer\n  evidence: https://github.com/egohygiene/relay/pull/24", "approval: null")
        result = self.collect()
        self.assertEqual(result["status"], "invalid")
        self.assertIn("EGO-INTEL-ADR-LIFECYCLE-001", {d["code"] for d in result["diagnostics"]})
        self.assertNotIn("ADR-003", [e["key"] for e in result["projection_candidate"]["entities"]])

    def test_missing_and_unsupported_policy_are_not_repaired(self):
        (self.consumer / POLICY).unlink()
        self.commit()
        result = self.collect()
        self.assertEqual(result["status"], "invalid")
        self.assertFalse((self.consumer / POLICY).exists())
        self.assertNotIn(POLICY, [s["path"] for s in result["inputs"]["sources"]])
        shutil.copyfile(FIXTURE / POLICY, self.consumer / POLICY)
        self.change(POLICY, "c589587395750cd1c79c6fa0bef010189c547249", "a" * 40)
        result = self.collect()
        self.assertIn("EGO-INTEL-CONTRACT-001", {d["code"] for d in result["diagnostics"]})

    def test_empty_observed_unknown_unavailable_and_inapplicable_remain_distinct(self):
        for path in (FIRST, OLD, NEW):
            (self.consumer / path).unlink()
        (self.consumer / INDEX).write_text("# Decisions\n\nNo ADRs recorded at this revision.\n")
        self.commit()
        self.assertEqual(self.collect()["coverage"]["decisions"]["collection"], "observed_empty")
        self.assertEqual(self.collect(adoption="unknown")["coverage"]["decisions"]["collection"], "uncollected")
        self.assertEqual(self.collect(adoption="not-applicable")["coverage"]["decisions"]["collection"], "not_applicable")
        (self.consumer / INDEX).unlink()
        self.commit()
        self.assertEqual(self.collect()["coverage"]["decisions"]["collection"], "unavailable")

    def test_not_applicable_cannot_hide_records(self):
        with self.assertRaises(collector.base.CollectorError):
            self.collect(adoption="not-applicable")

    def test_legacy_and_unrecognized_records_cannot_become_observed_empty(self):
        for path in (FIRST, OLD, NEW):
            (self.consumer / path).write_text("# Legacy decision\n\nStatus: Accepted\n")
        self.commit()
        result = self.collect(adoption="legacy")
        self.assertEqual(result["coverage"]["decisions"]["collection"], "partial")
        self.assertEqual(result["snapshot_candidate"]["views"]["decisions"]["decisions"], [])
        self.assertEqual(result["status"], "invalid")

    def test_unknown_extension_payloads_are_withheld_and_coverage_is_partial(self):
        policy = json.loads((self.consumer / POLICY).read_text())
        policy["extensions"] = [{"id": "egohygiene.example/v1", "kind": "metadata",
                                 "schema": "schemas/example.json", "required": False}]
        (self.consumer / POLICY).write_text(json.dumps(policy))
        self.change(FIRST, "extensions: {}", "extensions:\n  egohygiene.example/v1:\n    note: UNREVIEWED_EXTENSION_PAYLOAD")
        result = self.collect()
        self.assertEqual(result["coverage"]["decisions"]["collection"], "partial")
        self.assertNotIn("UNREVIEWED_EXTENSION_PAYLOAD", collector.base.json_bytes(result).decode())

    def test_external_links_remain_declared_references_without_invented_entities(self):
        self.change(FIRST, "related: []", "related: [egohygiene/hygiene#ADR-002]")
        result = self.collect()
        self.assertEqual(result["status"], "invalid")
        self.assertEqual({e["repository"] for e in result["projection_candidate"]["entities"]}, {"egohygiene/relay"})
        record = next(e for e in result["projection_candidate"]["entities"] if e["key"] == "ADR-001")
        self.assertEqual(record["attributes"]["related"], ["egohygiene/hygiene#ADR-002"])

    def test_stale_collection_preserves_decision_dates_and_explicit_freshness(self):
        result = self.collect(collected_at="2026-10-01T12:00:00Z")
        self.assertEqual(result["coverage"]["decisions"]["freshness"], "stale")
        decision = next(e for e in result["snapshot_candidate"]["graph"]["entities"] if e["key"] == "ADR-001")
        self.assertEqual(decision["attributes"]["date"], "2026-08-25")
        with self.assertRaises(collector.base.CollectorError):
            self.collect(collected_at="2026-10-05T12:00:00Z")

    def test_private_record_and_sensitive_text_fail_before_any_public_result(self):
        for visibility in ("private", "unknown", "internal"):
            text = (FIXTURE / FIRST).read_text().replace("visibility: public", "visibility: " + visibility)
            (self.consumer / FIRST).write_text(text)
            self.commit()
            with self.assertRaises(collector.base.CollectorError) as error:
                self.collect()
            self.assertEqual(str(error.exception), "VISIBILITY")
        (self.consumer / FIRST).write_text((FIXTURE / FIRST).read_text() + "\nsecret: sensitive-value\n")
        self.commit()
        with self.assertRaises(collector.base.CollectorError):
            self.collect()

    def test_git_symlinks_and_oversized_blobs_fail_closed(self):
        (self.consumer / FIRST).unlink()
        (self.consumer / FIRST).symlink_to("/private/secret")
        self.commit()
        with self.assertRaises(collector.base.CollectorError):
            self.collect()
        (self.consumer / FIRST).unlink()
        (self.consumer / FIRST).write_bytes(b"a" * (collector.base.MAX_SOURCE + 1))
        self.commit()
        with self.assertRaises(collector.base.CollectorError):
            self.collect()

    def test_file_count_total_bytes_and_gitlinks_are_bounded(self):
        for index in range(257):
            (self.consumer / f"docs/decisions/extra-{index}.md").write_text("bounded input")
        self.commit()
        with self.assertRaises(collector.base.CollectorError):
            self.collect()
        for path in (self.consumer / "docs/decisions").glob("extra-*.md"):
            path.unlink()
        for index in range(9):
            (self.consumer / f"docs/decisions/large-{index}.md").write_bytes(b"a" * collector.base.MAX_SOURCE)
        self.commit()
        with self.assertRaises(collector.base.CollectorError):
            self.collect()
        for path in (self.consumer / "docs/decisions").glob("large-*.md"):
            path.unlink()
        self.commit()
        git(self.consumer, "update-index", "--add", "--cacheinfo", "160000," + git(self.consumer, "rev-parse", "HEAD") + ",docs/decisions/foreign")
        git(self.consumer, "commit", "--quiet", "--message", "test: gitlink is untrusted input")
        with self.assertRaises(collector.base.CollectorError):
            self.collect()

    def test_four_digit_canonical_identity_and_filename_are_not_rewritten(self):
        target = self.consumer / FIRST
        target.write_text(target.read_text().replace("ADR-001", "ADR-0001"))
        target.rename(target.with_name("ADR-0001-validation-contract.md"))
        self.change(INDEX, "ADR-001", "ADR-0001")
        result = self.collect()
        decision = next(e for e in result["projection_candidate"]["entities"] if e["key"] == "ADR-0001")
        self.assertTrue(decision["id"].endswith(":ADR-0001"))
        self.assertTrue(decision["canonical_url"].endswith("/ADR-0001-validation-contract.md"))

    def test_unrecognized_markdown_prevents_a_false_empty_inventory(self):
        for path in (FIRST, OLD, NEW):
            (self.consumer / path).unlink()
        (self.consumer / INDEX).write_text("# Decisions\n")
        (self.consumer / "docs/decisions/old-design.md").write_text("# Historical choice\n")
        self.commit()
        result = self.collect()
        self.assertEqual(result["coverage"]["decisions"]["collection"], "partial")
        self.assertEqual(result["snapshot_candidate"]["views"]["decisions"]["decisions"], [])

    def test_tampered_runtime_artifact_and_stale_receipt_are_rejected(self):
        original = collector.base.read_file
        target = self.runtime / "hygiene/schemas/repository-intelligence.alpha2.schema.json"
        with patch.object(collector.base, "read_file", side_effect=lambda path, *args: b"changed" if path == target else original(path, *args)):
            with self.assertRaises(collector.base.CollectorError):
                self.collect()
        stale = self.root / "stale-runtime"
        stale.mkdir()
        (stale / "runtime.json").write_text(json.dumps({"lock_sha256": "0" * 64, "egolint_sha256": "0" * 64}))
        with self.assertRaises(collector.base.CollectorError):
            self.collect(runtime=stale)

    @unittest.skipUnless(os.environ.get("RELAY_ADR_CANARY"), "set RELAY_ADR_CANARY to the acquired Hygiene clone")
    def test_real_hygiene_corpus_retains_approval_and_reports_existing_migration_gaps(self):
        result = self.collect(repository_root=Path(os.environ["RELAY_ADR_CANARY"]), repository="egohygiene/hygiene",
            source_commit="639a003d5ddc4d242c2cf190eeb59a9fc522d199", adoption="legacy")
        self.assertEqual(result["status"], "invalid")
        self.assertEqual(result["coverage"]["decisions"]["collection"], "partial")
        self.assertEqual(result["validation"]["hygiene"], "valid")
        self.assertEqual(result["validation"]["coverage"], "valid")
        records = [e for e in result["snapshot_candidate"]["graph"]["entities"] if e["kind"] == "architecture_decision"]
        self.assertEqual(len(records), 12)
        foundation = next(e for e in records if e["key"] == "ADR-002")
        self.assertEqual(foundation["state"]["value"], "accepted")
        self.assertEqual(foundation["attributes"]["approval"]["by"], "szmyty")
        self.assertIn("issuecomment-5647398908", foundation["attributes"]["approval"]["evidence"])
        self.assertNotIn("ADR-0001", [e["key"] for e in records])


if __name__ == "__main__":
    unittest.main()
