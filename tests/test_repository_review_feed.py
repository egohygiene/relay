# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT
"""Exercise the real pinned typed owner and denial boundaries."""

from contextlib import redirect_stderr, redirect_stdout
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "actions/repository-intelligence-review-feed/scripts/review_feed.py"
spec = importlib.util.spec_from_file_location("test_native_typed_review_feed", SCRIPT)
feed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feed)


class TypedReviewFeedTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name)
        self.source = self.parent / "consumer"
        self.source.mkdir()
        self.git("init", "--quiet")
        (self.source / "README.md").write_text("Public disposable source fixture\n")
        self.git("add", "README.md")
        environment = dict(os.environ, GIT_AUTHOR_DATE="2026-01-01T00:00:00Z",
            GIT_COMMITTER_DATE="2026-01-01T00:00:00Z")
        self.git("-c", "user.name=Synthetic fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "--quiet", "-m", "source fixture", env=environment)
        self.revision = self.git("rev-parse", "HEAD").strip()

    def git(self, *args, **kwargs):
        return subprocess.check_output(["git", "-C", str(self.source), *args], text=True,
            stderr=subprocess.DEVNULL, **kwargs)

    def run_feed(self, *, repository="egohygiene/empathy", source=None, output=".cache/feed"):
        argv = [str(SCRIPT), "--source-root", str(source or self.source), "--plan", "review-plan.json",
            "--repository", repository, "--represented-commit", self.revision,
            "--as-of", "2026-01-01T00:00:01Z", "--runtime-parent", str(self.parent),
            "--output-directory", output]
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", argv), redirect_stdout(stdout), redirect_stderr(stderr):
            result = feed.main()
        return result, stdout.getvalue(), stderr.getvalue()

    def test_empty_native_feed_uses_its_locked_admission_profile(self):
        result, stdout, stderr = self.run_feed()
        self.assertEqual((result, stderr), (0, ""))
        receipt = json.loads((self.source / ".cache/feed/review-feed-receipt.json").read_bytes())
        self.assertEqual(receipt["admission"]["revision"], feed.contract.HYGIENE)
        self.assertEqual(receipt["admission"]["artifact_sha256"], feed.contract.CATALOG)
        self.assertEqual(receipt["reports"], [])
        self.assertEqual(receipt["plan"]["state"], "missing")
        self.assertEqual(len(list((self.source / ".cache/feed").iterdir())), 5)
        for key in feed.contract.MODELS:
            feed.contract.validate_model_bytes(receipt, key, (self.source / ".cache/feed" / (key + ".json")).read_bytes())
        # The independent dependency profile must remain upgraded; there is no
        # rollback of the shared profile merely to accommodate typed reviews.
        shared = feed.module("test_current_admission", ROOT / "actions/repository-intelligence/scripts/public_catalog_admission.py")
        shared.public_document()
        self.assertEqual(shared.lock()["revision"], "627b448f655afb2f4366654ba3ca3050389e464a")
        current = dict(receipt["admission"], revision=shared.lock()["revision"],
            artifact_sha256=shared.digest(shared.PUBLIC_ARTIFACT.read_bytes()))
        substituted = copy.deepcopy(receipt)
        substituted["admission"] = current
        with self.assertRaises(ValueError):
            feed.contract.validate_receipt(substituted, admission=current,
                expected_implementation=feed.implementation(), repository="egohygiene/empathy")
        self.assertIn("receipt-path", json.loads(stdout))

    def test_unknown_identity_denies_before_git_or_source_hashes(self):
        with patch.object(feed, "source_frame", side_effect=AssertionError("consumer Git read")) as frame, \
                patch.object(feed, "blob", side_effect=AssertionError("consumer blob read")) as blob:
            result, stdout, stderr = self.run_feed(repository="egohygiene/synthetic-private-fixture")
        self.assertEqual(result, 1)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr.strip(), feed.DENIAL)
        frame.assert_not_called()
        blob.assert_not_called()
        self.assertFalse((self.source / ".cache").exists())

    def test_source_alias_denies_before_runtime_allocation(self):
        alias = self.parent / "alias"
        alias.symlink_to(self.source, target_is_directory=True)
        with patch.object(feed.tempfile, "TemporaryDirectory", side_effect=AssertionError("allocated runtime")) as allocated:
            result, stdout, stderr = self.run_feed(source=alias)
        self.assertEqual(result, 1)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr.strip(), feed.DENIAL)
        allocated.assert_not_called()

    def test_runtime_inside_source_denies_before_allocation(self):
        with patch.object(feed.tempfile, "TemporaryDirectory", side_effect=AssertionError("allocated runtime")) as allocated:
            with self.assertRaises(feed.contract.FeedError):
                feed.runtime(self.source, self.source)
        allocated.assert_not_called()

    def test_tampered_owner_resource_denies_before_consumer_git(self):
        original = feed.read
        lock = feed.contract.parse(original(feed.LOCK))
        selected = feed.RELAY / next(iter(lock["files"].values()))["vendored"]
        def altered(path, *args, **kwargs):
            content = original(path, *args, **kwargs)
            return content + b" " if Path(path) == selected else content
        with patch.object(feed, "read", side_effect=altered), \
                patch.object(feed, "source_frame", side_effect=AssertionError("consumer Git read")) as frame:
            result, stdout, stderr = self.run_feed()
        self.assertEqual(result, 1)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr.strip(), feed.DENIAL)
        frame.assert_not_called()

    def test_collection_admission_equality_stays_strict(self):
        original = feed.collect
        def mismatch(*args, **kwargs):
            models, plan, reports, admission = original(*args, **kwargs)
            return models, plan, reports, dict(admission, revision="0" * 40)
        with patch.object(feed, "collect", side_effect=mismatch):
            result, stdout, stderr = self.run_feed()
        self.assertEqual(result, 1)
        self.assertEqual(stderr.strip(), feed.DENIAL)
        output = self.source / ".cache/feed"
        self.assertEqual([p.name for p in output.iterdir()], ["review-feed-denial.json"])
        self.assertEqual(json.loads((output / "review-feed-denial.json").read_bytes())["diagnostic"], "PIN")
        self.assertNotIn("repository-audits", json.loads(stdout))


if __name__ == "__main__":
    unittest.main()
