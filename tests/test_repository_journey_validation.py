"""Exact native inspection of bounded histories crossing a merge boundary."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "actions/repository-intelligence/scripts/collect_repository_journey.py"
spec = importlib.util.spec_from_file_location("journey_validation_test", SCRIPT)
assert spec and spec.loader
journey = importlib.util.module_from_spec(spec)
spec.loader.exec_module(journey)


def commit(message: str, parents: tuple[str, ...] = ()) -> tuple[str, bytes]:
    raw = (
        "tree " + "0" * 40 + "\n"
        + "".join("parent " + parent + "\n" for parent in parents)
        + "author Fixture <fixture@example.invalid> 1767225600 +0000\n"
        + "committer Fixture <fixture@example.invalid> 1767225600 +0000\n\n"
        + message + "\n"
    ).encode()
    sha = hashlib.sha1(b"commit " + str(len(raw)).encode() + b"\0" + raw, usedforsecurity=False).hexdigest()
    return sha, raw


class JourneyValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.runtime = self.root / "runtime"
        catalog = self.runtime / "egolint/.config/rules/repository-intelligence.v1.toml"
        catalog.parent.mkdir(parents=True)
        catalog.write_text(
            'catalog-version = "fixture"\n'
            '[[upstream-contracts]]\nid = "egohygiene.repository-intelligence/v1"\n'
            'version = "1.0.0-alpha.1"\n'
            '[[compatible-upstream-contracts]]\nid = "egohygiene.repository-intelligence/v1"\n'
            'version = "1.0.0-alpha.2"\n'
        )
        self.pins = [{"id": "egohygiene.repository-intelligence/v1", "version": "1.0.0-alpha.2"}]
        schema = self.runtime / "egolint/schemas/repository-intelligence-report.schema.json"
        schema.parent.mkdir(parents=True)
        schema.write_text(json.dumps({
            "type": "object", "required": ["repository", "represented_commit", "catalog_version",
                                                   "contracts", "summary", "diagnostics", "status"],
            "properties": {
                "status": {"enum": ["valid", "invalid", "incomplete"]},
                "summary": {"type": "object", "required": ["commits_inspected"],
                            "properties": {"commits_inspected": {"type": "integer", "minimum": 0}}},
                "diagnostics": {"type": "array"},
            },
        }))
        outside, _ = commit("outside selection")
        self.hidden, hidden_raw = commit("selected branch")
        merge, merge_raw = commit("truncated merge", (outside, self.hidden))
        self.source, source_raw = commit("represented source", (merge,))
        self.objects = {self.source: source_raw, merge: merge_raw, self.hidden: hidden_raw}
        self.args = argparse.Namespace(
            runtime=self.runtime, maximum_commits=3, source_commit=self.source,
            repository="egohygiene/fixture", visibility="public", repository_root=self.root / "consumer",
            observed_at="2026-11-14T00:03:18Z", collected_at=None, maximum_age_seconds=86400,
            since=None, until=None, public_subjects=False,
        )
        self.native_roots: list[str] = []
        self.timeouts: list[float] = []
        self.change_report = lambda report, root: None
        self.original_run = journey.base.run
        self.clock: float | None = None
        self.after_first_clock: float | None = None
        self.skip_write: str | None = None

    def execute(self, argv, **kwargs):
        if self.skip_write and "hash-object" in argv:
            raw = kwargs["data"]
            sha = hashlib.sha1(b"commit " + str(len(raw)).encode() + b"\0" + raw, usedforsecurity=False).hexdigest()
            if sha == self.skip_write:
                return (sha + "\n").encode()
        if Path(argv[0]).name != "egolint-bin":
            return self.original_run(argv, **kwargs)
        workspace = Path(argv[argv.index("--workspace") + 1])
        root = argv[argv.index("--represented-commit") + 1]
        # Use actual Git traversal, including the real all-parent shallow rule.
        reachable = journey.base.git(workspace, "rev-list", root, "--").decode().splitlines()
        self.native_roots.append(root)
        self.timeouts.append(kwargs["timeout"])
        report = {
            "repository": self.args.repository, "represented_commit": {"revision": root},
            "catalog_version": "fixture", "contracts": copy.deepcopy(self.pins),
            "status": "incomplete", "summary": {"commits_inspected": len(reachable)}, "diagnostics": [],
        }
        self.change_report(report, root)
        target = workspace / ".reports/egolint/repository-intelligence.json"
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps(report))
        if len(self.native_roots) == 1 and self.after_first_clock is not None:
            self.clock = self.after_first_clock
        return b""

    def validate(self, objects=None):
        with patch.object(journey.base, "run", side_effect=self.execute):
            return journey.source_validate(self.args, self.objects if objects is None else objects)

    def test_real_shallow_merge_counterexample_and_disjoint_complete_inspection(self):
        legacy = self.root / "legacy"
        legacy.mkdir()
        journey.base.git(legacy, "init", "--quiet")
        for raw in self.objects.values():
            journey.base.git(legacy, "hash-object", "-t", "commit", "-w", "--stdin", data=raw)
        merge = next(sha for sha in self.objects if sha not in {self.source, self.hidden})
        (legacy / ".git/shallow").write_text(merge + "\n")
        before = journey.base.git(legacy, "rev-list", self.source, "--").decode().splitlines()
        self.assertEqual(2, len(before))
        self.assertNotIn(self.hidden, before)
        result = self.validate()
        self.assertEqual([self.source, self.hidden], self.native_roots)
        inspected = [sha for item in result["inspections"] for sha in item["commits"]]
        self.assertEqual(set(self.objects), set(inspected))
        self.assertEqual(3, len(inspected))
        self.assertEqual([2, 1], [item["commits_inspected"] for item in result["inspections"]])
        self.assertEqual("incomplete", result["status"])

    def test_ordinary_linear_history_needs_one_native_pass(self):
        first, a = commit("first")
        second, b = commit("second", (first,))
        last, c = commit("last", (second,))
        self.args.source_commit = last
        result = self.validate({last: c, second: b, first: a})
        self.assertEqual([last], self.native_roots)
        self.assertEqual(3, result["inspections"][0]["commits_inspected"])

    def test_single_shallow_selected_object_stays_within_caller_cap(self):
        self.args.maximum_commits = 1
        result = self.validate({self.source: self.objects[self.source]})
        self.assertEqual(1, result["inspections"][0]["commits_inspected"])
        self.assertEqual([self.source], self.native_roots)

    def test_supplemental_pass_preserves_native_invalid_status(self):
        def invalid(report, root):
            if root == self.hidden:
                report["status"] = "invalid"
                report["diagnostics"] = [{"rule_id": "EGO-INTEL-TRAILER-001", "message": "private prose",
                                           "location": {"path": "commit:" + root, "line": 1}}]
        self.change_report = invalid
        result = self.validate()
        self.assertEqual("invalid", result["status"])
        self.assertEqual(1, len(result["diagnostics"]))

    def test_native_identity_catalog_contract_schema_and_count_mismatches_deny(self):
        mutations = {
            "source": lambda r: r["represented_commit"].update(revision="a" * 40),
            "repository": lambda r: r.update(repository="other/repository"),
            "catalog": lambda r: r.update(catalog_version="wrong"),
            "contracts": lambda r: r.update(contracts=[]),
            "count missing": lambda r: r["summary"].update(commits_inspected=r["summary"]["commits_inspected"] - 1),
            "count extra": lambda r: r["summary"].update(commits_inspected=r["summary"]["commits_inspected"] + 1),
            "schema": lambda r: r.update(status="invented"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                self.change_report = lambda report, root: mutate(report) if root == self.hidden else None
                with self.assertRaisesRegex(journey.base.CollectorError, "^RUNTIME$"):
                    self.validate()

    def test_tampered_original_object_is_rejected(self):
        objects = dict(self.objects)
        objects[self.hidden] += b"changed\n"
        with self.assertRaisesRegex(journey.base.CollectorError, "^INPUT$"):
            self.validate(objects)

    def test_missing_private_corpus_object_is_rejected(self):
        self.skip_write = self.hidden
        with self.assertRaisesRegex(journey.base.CollectorError, "^RUNTIME$"):
            self.validate()

    def test_unrelated_object_cannot_become_a_supplemental_root(self):
        extra, raw = commit("not in represented graph")
        with self.assertRaisesRegex(journey.base.CollectorError, "^INPUT$"):
            self.validate({**self.objects, extra: raw})

    def test_missing_original_root_and_excess_selection_deny(self):
        with self.assertRaisesRegex(journey.base.CollectorError, "^INPUT$"):
            self.validate({self.hidden: self.objects[self.hidden]})
        self.args.maximum_commits = 2
        with self.assertRaisesRegex(journey.base.CollectorError, "^INPUT$"):
            self.validate()

    def test_all_passes_share_one_native_deadline(self):
        self.clock, self.after_first_clock = 0, 30
        with patch.object(journey.time, "monotonic", side_effect=lambda: self.clock):
            self.validate()
        self.assertEqual([60, 30], self.timeouts)

    def test_exhausted_total_deadline_denies_before_supplemental_pass(self):
        self.clock, self.after_first_clock = 0, 61
        with patch.object(journey.time, "monotonic", side_effect=lambda: self.clock):
            with self.assertRaisesRegex(journey.base.CollectorError, "^RUNTIME$"):
                self.validate()
        self.assertEqual([self.source], self.native_roots)

    def test_public_collection_keeps_all_records_and_partial_scope_without_private_inspection_data(self):
        records = [{"sha": sha, "occurred_at": "2026-01-01T00:00:00Z", "title": "Commit " + sha[:12]}
                   for sha in self.objects]
        scope = {"shallow": False, "truncated": True, "time_filtered": False, "withheld_timestamps": False}
        with patch.object(journey.base, "run", side_effect=self.execute), \
                patch.object(journey.base, "runtime_files", return_value=({}, {})), \
                patch.object(journey, "inventory", return_value=(records, scope, self.objects)), \
                patch.object(journey.native, "normalize", return_value=({}, {"hygiene": "valid", "coverage": "valid", "observatory": "normalized"})):
            result = journey.collect(self.args)
        self.assertEqual(3, len(result["projection_candidate"]["events"]))
        self.assertEqual(3, len(result["inputs"]["commits"]))
        self.assertEqual("partial", result["status"])
        self.assertTrue(result["scope"]["truncated"])
        self.assertEqual("incomplete", result["validation"]["egolint"])
        self.assertNotIn("inspections", json.dumps(result))
        self.assertNotIn("Fixture <", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
