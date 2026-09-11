# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Keep continuity pull-request orchestration read-only and fork-safe."""

from pathlib import Path
import hashlib
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ContinuityPreflightWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.reusable = (ROOT / ".github/workflows/continuity-preflight.yml").read_text(encoding="utf-8")
        cls.dogfood = (ROOT / ".github/workflows/continuity-preflight-dogfood.yml").read_text(encoding="utf-8")
        cls.documentation = (ROOT / "docs/repository-continuity-preflight.md").read_text(encoding="utf-8")

    def test_reusable_workflow_is_read_only_and_immutable(self) -> None:
        self.assertIn("workflow_call:", self.reusable)
        self.assertNotIn("pull_request_target:", self.reusable + self.dogfood)
        self.assertNotIn("contents: write", self.reusable + self.dogfood)
        self.assertIn("persist-credentials: false", self.reusable)
        self.assertIn("fc6f0c0496c8b8d4c0690fdd2fdb69a9538866fa", self.reusable)
        self.assertIn("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1", self.reusable)
        self.assertIn("actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a", self.reusable)
        self.assertIn('EXCEPTION_REFERENCE: "${{ inputs.exception-reference }}"', self.reusable)
        self.assertIn('os.environ["EXCEPTION_REFERENCE"] or None', self.reusable)

    def test_evidence_is_bounded_and_failure_preserved(self) -> None:
        self.assertIn("retention-days: \"${{ inputs.artifact-retention-days }}\"", self.reusable)
        self.assertIn("finding in result[\"findings\"][:20]", self.reusable)
        self.assertIn("if: \"${{ always() }}\"", self.reusable)
        self.assertIn("if-no-files-found: error", self.reusable)
        for forbidden in ("git push", "gh pr", "pull_request_target", "contents: write"):
            self.assertNotIn(forbidden, self.reusable)

    def test_history_concurrency_and_timeout_are_explicit(self) -> None:
        self.assertIn("fetch-depth: 0", self.reusable)
        self.assertIn('ref: "${{ github.event.pull_request.head.sha || github.sha }}"', self.reusable)
        self.assertIn("timeout-minutes: 15", self.reusable)
        self.assertIn("cancel-in-progress: true", self.reusable + self.dogfood)
        self.assertIn("artifact-retention-days:", self.reusable)

    def test_dogfood_is_a_thin_pull_request_caller(self) -> None:
        self.assertIn("pull_request:", self.dogfood)
        self.assertIn("uses: $/.github/workflows/continuity-preflight.yml", self.dogfood)
        self.assertIn("base-revision: \"${{ github.event.pull_request.base.sha }}\"", self.dogfood)
        self.assertIn("live-evidence-references:", self.dogfood)
        self.assertNotIn("timeout-minutes:", self.dogfood)

    def test_private_and_retry_behavior_is_documented(self) -> None:
        self.assertIn("Public, private, or internal caller visibility", self.reusable)
        self.assertIn("Private and\ninternal repository results", self.documentation)
        self.assertIn("retry begins fresh", self.documentation)

    def test_dogfood_vendor_bytes_match_reviewed_contracts(self) -> None:
        expected = {
            "vendor/hygiene/repository-continuity-policy.v1.json": "a17178482d67e141009b07d6715727612fbf7f372be8c471a124149752c2ca64",
            "vendor/aether/aether.repository-continuity.v1.schema.json": "a725e004fe0db2bf96a968c6e3f300d37ecf8b00b9a0923be5c5f4c529655916",
            "vendor/aether/repository-continuity.INSTRUCTION.md": "dc2fb66bd5268af2416389fef469d2a13c91d1a6f179e6fc10a21d4f890876a8",
            "vendor/aether/CONTINUITY.template.md": "494de90d0c344db9ff41b78998445b9e9c02f23a69c25d48442d2af1de1343f2",
        }
        for path, digest in expected.items():
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest)

if __name__ == "__main__":
    unittest.main()
