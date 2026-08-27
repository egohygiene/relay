# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Structural tests for the reusable publication Pages authority boundary."""

from __future__ import annotations

from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPOSITORY_ROOT / ".github/workflows/publication-pages.yml"
VALIDATE_WORKFLOW = REPOSITORY_ROOT / ".github/workflows/validate.yml"


class PublicationPagesWorkflowTests(unittest.TestCase):
    """Keep validation, review, deployment, and verification separated."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_workflow_never_checks_out_or_builds_caller_content(self) -> None:
        self.assertNotIn("actions/checkout@", self.text)
        for command in ("make ", "task ", "pandoc", "latexmk", "npm run"):
            with self.subTest(command=command):
                self.assertNotIn(command, self.text)
        self.assertIn("Download caller-built static site", self.text)

    def test_review_job_is_read_only_and_owns_the_reviewed_bytes(self) -> None:
        review = self.text[self.text.index("  review:"):self.text.index("  deploy:")]
        self.assertIn("permissions:\n      actions: read\n      contents: read", review)
        self.assertNotIn("pages: write", review)
        self.assertNotIn("id-token: write", review)
        self.assertIn("uses: $/actions/validate-publication-site", review)
        self.assertIn(
            'expected-fallback-base-url: "${{ inputs.fallback-base-url }}"', review
        )
        self.assertIn("Upload ordinary review artifact", review)
        self.assertIn("include-hidden-files: true", review)
        self.assertIn('if: "${{ always() }}"', review)

    def test_deploy_consumes_only_the_exact_reviewed_artifact(self) -> None:
        deploy = self.text[self.text.index("  deploy:"):]
        self.assertIn("      - review", deploy)
        self.assertIn("pages: write", deploy)
        self.assertIn("id-token: write", deploy)
        self.assertIn("name: github-pages", deploy)
        self.assertIn("needs.review.outputs.review-artifact-name", deploy)
        self.assertIn(
            'expected-fallback-base-url: "${{ inputs.fallback-base-url }}"', deploy
        )
        self.assertNotIn('name: "${{ inputs.artifact-name }}"', deploy)
        revalidate = deploy.index("Revalidate downloaded publication site")
        compare = deploy.index("Confirm reviewed site-tree identity")
        preflight = deploy.index("Validate deployment and verification configuration")
        configure = deploy.index("Configure GitHub Pages")
        upload = deploy.index("Upload deployable Pages artifact")
        publish = deploy.index("Deploy GitHub Pages")
        verify = deploy.index("Verify deployed publication Pages")
        self.assertLess(revalidate, compare)
        self.assertLess(compare, preflight)
        self.assertLess(preflight, configure)
        self.assertLess(configure, upload)
        self.assertLess(upload, publish)
        self.assertLess(publish, verify)

    def test_authority_is_fail_closed_and_runs_do_not_cancel_deployments(self) -> None:
        self.assertIn("cancel-in-progress: false", self.text)
        authorize = self.text[
            self.text.index("  authorize:"):self.text.index("  review:")
        ]
        self.assertIn("permissions: {}", authorize)
        self.assertIn("Relay-reserved artifact prefix", authorize)
        self.assertIn('GITHUB_EVENT_NAME}" != "push"', self.text)
        self.assertIn('GITHUB_EVENT_NAME}" != "workflow_dispatch"', self.text)
        self.assertIn('GITHUB_REF_NAME}" != "${DEFAULT_BRANCH}', self.text)
        self.assertIn("expected-source-revision must equal the caller workflow SHA", self.text)
        self.assertIn("needs.authorize.outputs.mode == 'deploy'", self.text)

    def test_remote_dependencies_are_fully_pinned_and_evidence_outputs_are_honest(self) -> None:
        remote_uses = [
            line.strip().split("uses: ", 1)[1]
            for line in self.text.splitlines()
            if line.strip().startswith("uses: ")
            and not line.strip().startswith("uses: $/")
        ]
        self.assertTrue(remote_uses)
        for reference in remote_uses:
            with self.subTest(reference=reference):
                self.assertRegex(reference, r"^[^@]+@[0-9a-f]{40}$")
        self.assertIn(
            "jobs.deploy.outputs.evidence-artifact-name || "
            "jobs.review.outputs.evidence-artifact-name",
            self.text,
        )
        self.assertIn("jobs.review.outputs.file-count", self.text)
        self.assertIn("jobs.review.outputs.total-bytes", self.text)
        self.assertIn("Digest of the exact complete SHA256SUMS bytes", self.text)

    def test_validate_workflow_exercises_the_review_only_artifact_boundary(self) -> None:
        validate = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
        producer = validate[
            validate.index("  publication-site-fixture:"):
            validate.index("  publication-pages-smoke:")
        ]
        smoke = validate[
            validate.index("  publication-pages-smoke:"):
            validate.index("  publication-pages-smoke-outputs:")
        ]
        outputs = validate[
            validate.index("  publication-pages-smoke-outputs:"):
            validate.index("  intelligence-smoke:")
        ]
        self.assertIn("actions/upload-artifact@", producer)
        self.assertIn("include-hidden-files: true", producer)
        self.assertIn("uses: $/.github/workflows/publication-pages.yml", smoke)
        self.assertIn("deploy-enabled: false", smoke)
        self.assertNotIn("pages: write", smoke)
        self.assertNotIn("id-token: write", smoke)
        self.assertIn("permissions: {}", outputs)
        self.assertIn("needs.publication-pages-smoke.outputs.site-tree-sha256", outputs)


if __name__ == "__main__":
    unittest.main()
