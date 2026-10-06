"""Read-only collection, reviewed input binding, and real EgoLint composition."""

from copy import deepcopy
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
SCRIPT = ROOT / "scripts/preview_issue_titles.py"
spec = importlib.util.spec_from_file_location("issue_title_preview", SCRIPT)
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)
FIXTURE = ROOT / "tests/fixtures/issue-title-preview"
REPOSITORY = "egohygiene/aether"
STAMP = "2026-10-06T17:00:00Z"


def snapshot():
    return json.loads((FIXTURE / "snapshot.json").read_text())


def reviews(value):
    result = preview.empty_reviews(value)
    result["issues"] = [{"id": row["id"], "number": row["number"],
                          "type": "feature", "subject": "[CHK-07] Keep MiXeD case — café"}
                         for row in value["issues"] if row["number"] == 2]
    return result


def provider_issue(number):
    return {"id": 1000 + number, "number": number, "title": f"Task {number}",
            "html_url": f"https://github.com/{REPOSITORY}/issues/{number}",
            "state": "open", "updated_at": STAMP, "labels": []}


class Boundaries(unittest.TestCase):
    def test_captured_inputs_are_closed_and_require_label_completeness(self):
        for mutate in (lambda v: v["issues"][0].pop("labels"),
                       lambda v: v.update(unexpected=True),
                       lambda v: v["issues"][0].update(complete="true"),
                       lambda v: v["issues"].append(v["issues"][0])):
            value = snapshot()
            mutate(value)
            with self.assertRaises(preview.base.CollectorError):
                preview.validate_snapshot(value, REPOSITORY)

    def test_repository_allowlist_and_canonical_issue_identity(self):
        with self.assertRaisesRegex(preview.base.CollectorError, "REPOSITORY"):
            preview.selection("elsewhere/project")
        value = snapshot()
        value["issues"][0]["url"] = "https://example.test/issues/1"
        with self.assertRaisesRegex(preview.base.CollectorError, "REPOSITORY"):
            preview.validate_snapshot(value, REPOSITORY)

    def test_claimed_complete_pagination_requires_terminal_page(self):
        for mutate in (lambda v: v["coverage"]["issues"].update(pages=[]),
                       lambda v: v["coverage"]["issues"]["pages"][0].update(number=2),
                       lambda v: v["coverage"]["issues"]["pages"][0].update(records=100),
                       lambda v: v["coverage"]["issues"].update(error="HTTP_403")):
            value = snapshot()
            mutate(value)
            with self.assertRaises(preview.base.CollectorError):
                preview.validate_snapshot(value, REPOSITORY)

    def test_inventory_race_is_not_claimed_complete(self):
        value = snapshot()
        value["labels"] = []
        value["coverage"]["labels"]["pages"][0]["records"] = 0
        with self.assertRaisesRegex(preview.base.CollectorError, "INVENTORY_CHANGED"):
            preview.validate_snapshot(value, REPOSITORY)

    def test_stale_and_duplicate_reviews_are_rejected_before_tool_execution(self):
        value = snapshot()
        for mutate in (lambda r: r.update(snapshot_sha256="0" * 64),
                       lambda r: r["issues"][0].update(id=99),
                       lambda r: r["issues"].append(r["issues"][0])):
            reviewed = reviews(value)
            mutate(reviewed)
            with patch.object(preview, "Egolint") as engine:
                with self.assertRaises(preview.base.CollectorError):
                    preview.preview(value, reviewed, REPOSITORY, Path("absent"))
                engine.assert_not_called()

    def test_missing_runtime_retains_every_issue_and_explicit_failure(self):
        value = snapshot()
        result = preview.preview(value, reviews(value), REPOSITORY, Path("absent"))
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["summary"]["unavailable"], len(value["issues"]))
        self.assertIsNone(result["provenance"]["runtime"])
        self.assertTrue(all(row["proposal"] is None for row in result["rows"]))

    def test_source_preparation_does_not_accept_missing_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = preview.parser().parse_args(["prepare", "--egolint", temporary,
                                                "--output", temporary + "/runtime"])
            with self.assertRaises(preview.base.CollectorError):
                preview.base.prepare(args, lock_path=preview.LOCK)
            self.assertFalse((Path(temporary) / "runtime").exists())

    def test_collects_multiple_pages_and_excludes_pull_requests(self):
        calls = []
        first = [provider_issue(number) for number in range(1, 101)]
        first[-1]["pull_request"] = {"url": "not-followed"}

        def get(path):
            calls.append(path)
            if path == f"/repos/{REPOSITORY}":
                return {"full_name": REPOSITORY, "id": 1, "private": False}
            if "/labels?" in path:
                return []
            return first if "page=1" in path else [provider_issue(101)]

        value = preview.collect(REPOSITORY, get=get, now=lambda: STAMP)
        self.assertEqual(len(value["issues"]), 100)
        self.assertEqual(value["excluded_pull_requests"], 1)
        self.assertEqual(value["coverage"]["issues"]["status"], "complete")
        self.assertEqual(len(value["coverage"]["issues"]["pages"]), 2)
        self.assertEqual(len(calls), 4)
        self.assertTrue(all(path.startswith(f"/repos/{REPOSITORY}") for path in calls))

    def test_failed_later_page_keeps_earlier_evidence_partial(self):
        def get(path):
            if path == f"/repos/{REPOSITORY}":
                return {"full_name": REPOSITORY, "id": 1, "private": False}
            if "/labels?" in path:
                preview.base.fail("HTTP_403")
            if "page=2" in path:
                preview.base.fail("HTTP_429")
            return [provider_issue(number) for number in range(1, 101)]

        value = preview.collect(REPOSITORY, get=get, now=lambda: STAMP)
        self.assertEqual(len(value["issues"]), 100)
        self.assertEqual(value["coverage"]["issues"]["status"], "partial")
        self.assertEqual(value["coverage"]["issues"]["error"], "HTTP_429")
        self.assertEqual(value["coverage"]["labels"]["status"], "unavailable")

    def test_duplicate_page_is_detected_without_double_counting(self):
        def get(path):
            if path == f"/repos/{REPOSITORY}":
                return {"full_name": REPOSITORY, "id": 1, "private": False}
            if "/labels?" in path:
                return []
            return [provider_issue(number) for number in range(1, 101)]

        value = preview.collect(REPOSITORY, get=get, now=lambda: STAMP)
        self.assertEqual(len(value["issues"]), 100)
        self.assertEqual(value["coverage"]["issues"]["error"], "DUPLICATE_RECORD")

    def test_public_collection_denies_private_or_mismatched_repository(self):
        for metadata in ({"full_name": REPOSITORY, "id": 1, "private": True},
                         {"full_name": "other/repository", "id": 1, "private": False}):
            with self.assertRaisesRegex(preview.base.CollectorError, "REPOSITORY"):
                preview.collect(REPOSITORY, get=lambda _: metadata, now=lambda: STAMP)

    def test_new_output_cannot_clobber_inputs_or_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "input.json"
            source.write_bytes(b"keep")
            with self.assertRaises(FileExistsError):
                preview.write_new(source, b"changed")
            self.assertEqual(source.read_bytes(), b"keep")
            link = root / "link"
            link.symlink_to(source)
            with self.assertRaises(preview.base.CollectorError):
                preview.write_new(link, b"changed")

    def test_json_rejects_duplicate_keys_and_nonfinite_numbers(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}'):
            with self.assertRaises(preview.base.CollectorError):
                preview.base.load_json(raw)


@unittest.skipUnless(os.environ.get("RELAY_ISSUE_TITLE_RUNTIME"),
                     "prepare the pinned runtime and set RELAY_ISSUE_TITLE_RUNTIME")
class Native(unittest.TestCase):
    def setUp(self):
        self.runtime = Path(os.environ["RELAY_ISSUE_TITLE_RUNTIME"])
        self.value = snapshot()

    def run_preview(self, value=None, reviewed=None):
        value = self.value if value is None else value
        return preview.preview(value, reviews(value) if reviewed is None else reviewed,
                               REPOSITORY, self.runtime)

    def test_actual_cli_classification_noop_legacy_and_preserved_checkpoint(self):
        before = deepcopy(self.value)
        result = self.run_preview()
        rows = {row["number"]: row for row in result["rows"]}
        self.assertEqual(rows[1]["status"], "unchanged")
        self.assertEqual(rows[2]["status"], "proposed")
        self.assertEqual(rows[2]["proposal"]["snapshot"]["title"],
                         "✨ [feature] [CHK-07] Keep MiXeD case — café")
        self.assertEqual(rows[2]["current"]["labels"], rows[2]["proposal"]["snapshot"]["labels"])
        self.assertEqual(rows[3]["validation"]["status"], "needs-classification")
        self.assertEqual(rows[4]["validation"]["status"], "unsupported-type")
        self.assertEqual(rows[5]["validation"]["status"], "conflict")
        self.assertEqual(rows[6]["status"], "needs-review")
        self.assertEqual(self.value, before)

    def test_partial_inventory_and_incomplete_issue_are_not_complete(self):
        self.value["coverage"]["issues"].update(status="partial", error="PAGE_LIMIT")
        self.value["issues"][1]["complete"] = False
        result = self.run_preview()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["rows"][1]["validation"]["status"], "unavailable")
        self.assertIsNone(result["rows"][1]["proposal"])

    def test_missing_provider_label_does_not_turn_formatted_title_into_adoption(self):
        reviewed = reviews(self.value)
        reviewed["issues"] = [{"id": 103, "number": 3, "type": "maintenance", "subject": "Original words"}]
        result = self.run_preview(reviewed=reviewed)
        row = result["rows"][2]
        self.assertEqual(row["status"], "blocked")
        self.assertEqual(row["proposal"]["provider_label"], "missing")
        self.assertEqual(row["proposal"]["format_validation"]["status"], "conformant")
        self.assertEqual(row["proposal"]["validation"]["status"], "needs-classification")
        self.assertEqual(row["proposal"]["snapshot"]["labels"], [])

    def test_unknown_label_inventory_stays_unavailable(self):
        self.value["labels"] = []
        self.value["coverage"]["labels"] = {"status": "unavailable", "pages": [], "error": "HTTP_403"}
        result = self.run_preview()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["rows"][1]["proposal"]["provider_label"], "unavailable")

    def test_unknown_and_conflicting_labels_are_never_removed(self):
        reviewed = reviews(self.value)
        reviewed["issues"] = [{"id": 100 + n, "number": n, "type": "feature", "subject": "Keep labels"}
                              for n in (4, 5)]
        result = self.run_preview(reviewed=reviewed)
        for row in result["rows"][3:5]:
            self.assertEqual(row["status"], "blocked")
            self.assertEqual(row["proposal"]["snapshot"]["labels"], row["current"]["labels"])

    def test_formatter_rejects_unreviewable_type_or_subject(self):
        for key, value in (("type", "future"), ("subject", " padded")):
            reviewed = reviews(self.value)
            reviewed["issues"][0][key] = value
            result = self.run_preview(reviewed=reviewed)
            self.assertEqual(result["rows"][1]["status"], "unavailable")
            self.assertIn("INVALID_REVIEW", result["rows"][1]["reasons"])

    def test_no_legacy_parser_strips_reviewed_decoration(self):
        reviewed = reviews(self.value)
        reviewed["issues"][0]["subject"] = "🧭 [Legacy] Preserve exactly"
        result = self.run_preview(reviewed=reviewed)
        self.assertEqual(result["rows"][1]["proposal"]["snapshot"]["title"],
                         "✨ [feature] 🧭 [Legacy] Preserve exactly")

    def test_mismatched_native_report_provenance_is_unavailable(self):
        run = preview.base.run

        def stale(*args, **kwargs):
            result = json.loads(run(*args, **kwargs))
            result["contract"]["revision"] = "0" * 40
            return preview.base.json_bytes(result)

        with patch.object(preview.base, "run", stale):
            result = self.run_preview()
        self.assertEqual(result["status"], "unavailable")
        self.assertTrue(all("PIN" in row["reasons"] for row in result["rows"]))

    def test_stale_receipt_and_missing_runtime_source_are_unavailable(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "runtime"
            shutil.copytree(self.runtime, destination)
            receipt = destination / "runtime.json"
            original = receipt.read_bytes()
            value = json.loads(original)
            value["lock_sha256"] = "0" * 64
            receipt.write_text(json.dumps(value))
            result = preview.preview(self.value, reviews(self.value), REPOSITORY, destination)
            self.assertEqual(result["status"], "unavailable")
            receipt.write_bytes(original)
            (destination / "egolint/schemas/issue-title-report.schema.json").unlink()
            result = preview.preview(self.value, reviews(self.value), REPOSITORY, destination)
            self.assertEqual(result["status"], "unavailable")

    def test_repeat_and_real_cli_output_are_identical_across_locations(self):
        result = self.run_preview()
        self.assertEqual(preview.base.json_bytes(result), preview.base.json_bytes(self.run_preview()))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            value_path = root / "snapshot.json"
            reviews_path = root / "reviews.json"
            value_path.write_bytes(preview.base.json_bytes(self.value))
            reviews_path.write_bytes(preview.base.json_bytes(reviews(self.value)))
            before = value_path.read_bytes(), reviews_path.read_bytes()
            for name in ("first", "other-location"):
                completed = subprocess.run([sys.executable, str(SCRIPT), "preview", "--repository", REPOSITORY,
                                            "--snapshot", str(value_path), "--reviews", str(reviews_path),
                                            "--runtime", str(self.runtime), "--output-dir", str(root / name)],
                                           capture_output=True, check=False)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual((root / name / "plan.json").read_bytes(), preview.base.json_bytes(result))
            self.assertEqual((root / "first/preview.md").read_bytes(), (root / "other-location/preview.md").read_bytes())
            self.assertEqual(before, (value_path.read_bytes(), reviews_path.read_bytes()))

    def test_untrusted_titles_cannot_inject_markdown_or_html(self):
        self.value["issues"][0]["title"] = "<script>alert(1)</script> | [bad](https://example.test)"
        text = preview.markdown(self.run_preview())
        self.assertNotIn("<script>", text)
        self.assertNotIn("[bad](", text)
        self.assertIn("\\|", text)


if __name__ == "__main__":
    unittest.main()
