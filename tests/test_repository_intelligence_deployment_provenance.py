# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Tests for the Repository Intelligence build-to-deployment handoff."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = REPOSITORY_ROOT / "actions/repository-intelligence"
DEPLOYMENT_ROOT = REPOSITORY_ROOT / "actions/repository-intelligence-deployment-provenance"
CONSUMER_REVISION = "1" * 40
RELAY_REVISION = "2" * 40
ROLLBACK_REVISION = "3" * 40
SOURCE_EPOCH = 1_800_000_000
ROUTES = (
    "",
    "compare",
    "dashboard",
    "decisions",
    "dependencies",
    "health",
    "journey",
    "now",
    "releases",
    "roadmap",
    "search",
    "work",
)


def load_module(name: str, path: Path):
    """Load a repository script without changing process import paths."""

    specification = importlib.util.spec_from_file_location(name, path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


build_manifest = load_module(
    "deployment_build_manifest",
    BUILD_ROOT / "scripts/create_repository_intelligence_build_manifest.py",
)
deployment = load_module(
    "repository_intelligence_deployment_provenance",
    DEPLOYMENT_ROOT / "scripts/repository_intelligence_deployment_provenance.py",
)


class RepositoryIntelligenceDeploymentProvenanceTests(unittest.TestCase):
    """Prove revision, digest, freshness, route, receipt, and recovery gates."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.workspace = Path(self.temporary_directory.name)
        self.site = self.workspace / "dist"
        self.site.mkdir()
        (self.site / "index.html").write_text("consumer root\n", encoding="utf-8")
        (self.site / "docs").mkdir()
        (self.site / "docs/index.html").write_text("consumer docs\n", encoding="utf-8")
        self.baseline = self.workspace / ".relay/consumer-route-baseline.json"
        self.verification = self.workspace / ".relay/composition-verification.json"
        self.receipt = self.workspace / ".relay/deployment-receipt.json"
        self.capture_baseline()
        self.intelligence = self.site / "intelligence"
        for route_name in ROUTES:
            destination = self.intelligence / route_name / "index.html"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(f"Repository Intelligence {route_name or 'overview'}\n", encoding="utf-8")
        (self.intelligence / "site.css").write_text("body { color: #fff; }\n", encoding="utf-8")
        manifest = build_manifest.build_manifest(
            output_root=self.intelligence,
            repository="example/consumer",
            consumer_revision=CONSUMER_REVISION,
            generator_revision=RELAY_REVISION,
            generator_version="1.6.0",
            source_epoch=SOURCE_EPOCH,
        )
        build_manifest.write_json(
            self.intelligence / build_manifest.BUILD_MANIFEST_NAME,
            manifest,
        )
        (self.site / "health").mkdir()
        (self.site / "health/index.html").write_text(
            '<meta http-equiv="refresh" content="0; url=/intelligence/health/">\n',
            encoding="utf-8",
        )

    def operation_arguments(self, operation: str, **overrides: str) -> list[str]:
        """Return a complete deterministic action-script invocation."""

        values = {
            "operation": operation,
            "workspace": str(self.workspace),
            "site-directory": "dist",
            "intelligence-directory": "dist/intelligence",
            "baseline-path": ".relay/consumer-route-baseline.json",
            "verification-path": ".relay/composition-verification.json",
            "receipt-path": ".relay/deployment-receipt.json",
            "consumer-repository": "example/consumer",
            "consumer-revision": CONSUMER_REVISION,
            "relay-revision": RELAY_REVISION,
            "verified-epoch": str(SOURCE_EPOCH + 60),
            "maximum-source-age-seconds": "120",
            "required-routes": '["/","/docs/","/intelligence/","/intelligence/now/"]',
            "aliases": '[{"route":"/health/","target":"/intelligence/health/"}]',
            "workflow-run-id": "42",
            "workflow-run-attempt": "2",
            "deployment-environment": "github-pages",
            "deployment-url": "https://example.test/consumer/",
            "deployment-conclusion": "success",
            "recorded-at": "2027-01-15T08:01:00Z",
            "rollback-revision": ROLLBACK_REVISION,
            "rollback-site-digest": "sha256:" + "4" * 64,
            "rollback-url": "https://example.test/consumer/",
        }
        values.update(overrides)
        arguments: list[str] = []
        for key, value in values.items():
            arguments.extend((f"--{key}", value))
        return arguments

    def capture_baseline(self) -> None:
        """Capture the two consumer-owned routes before composition."""

        result = deployment.main(
            [
                "--operation",
                "capture-baseline",
                "--workspace",
                str(self.workspace),
                "--site-directory",
                "dist",
                "--intelligence-directory",
                "dist/intelligence",
                "--baseline-path",
                ".relay/consumer-route-baseline.json",
                "--verification-path",
                ".relay/composition-verification.json",
                "--receipt-path",
                ".relay/deployment-receipt.json",
                "--consumer-repository",
                "example/consumer",
                "--consumer-revision",
                CONSUMER_REVISION,
            ]
        )
        self.assertEqual(result, 0)

    def test_record_and_verify_receipt_preserves_deterministic_bundle(self) -> None:
        """Deployment-only metadata stays outside the deterministic Relay subtree."""

        manifest_path = self.intelligence / "build-manifest.json"
        manifest_before = manifest_path.read_bytes()
        bundle_before = json.loads(manifest_before)["bundle"]["digest"]

        self.assertEqual(deployment.main(self.operation_arguments("verify-composition")), 0)
        self.assertEqual(deployment.main(self.operation_arguments("record-receipt")), 0)
        self.assertEqual(deployment.main(self.operation_arguments("verify-receipt")), 0)

        evidence = json.loads(self.verification.read_text(encoding="utf-8"))
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(manifest_path.read_bytes(), manifest_before)
        self.assertEqual(receipt["build_manifest"]["bundle_digest"], bundle_before)
        self.assertEqual(receipt["build_manifest"], evidence["build_manifest"])
        self.assertEqual(receipt["workflow"], {"run_id": 42, "run_attempt": 2})
        self.assertEqual(receipt["deployment"]["environment"], "github-pages")
        self.assertIn("/docs/", receipt["composition"]["published_routes"])
        self.assertEqual(
            [item["route"] for item in receipt["composition"]["preserved_consumer_routes"]],
            ["/", "/docs/"],
        )
        self.assertEqual(receipt["composition"]["preserved_consumer_files"]["file_count"], 2)
        self.assertEqual(
            receipt["aliases"],
            [{"route": "/health/", "target": "/intelligence/health/"}],
        )
        self.assertEqual(receipt["rollback"]["consumer_revision"], ROLLBACK_REVISION)
        self.assertNotIn(str(self.workspace), self.receipt.read_text(encoding="utf-8"))

    def test_revision_drift_is_rejected(self) -> None:
        with self.assertRaisesRegex(SystemExit, "consumer revision drift"):
            deployment.main(
                self.operation_arguments(
                    "verify-composition", **{"consumer-revision": "9" * 40}
                )
            )

    def test_digest_mismatch_is_rejected(self) -> None:
        (self.intelligence / "site.css").write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(SystemExit, "bundle digest mismatch"):
            deployment.main(self.operation_arguments("verify-composition"))

    def test_incompatible_manifest_version_is_rejected(self) -> None:
        path = self.intelligence / "build-manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["schema_version"] = 2
        build_manifest.write_json(path, manifest)
        with self.assertRaisesRegex(SystemExit, "unsupported build manifest version"):
            deployment.main(self.operation_arguments("verify-composition"))

    def test_missing_required_route_is_rejected(self) -> None:
        with self.assertRaisesRegex(SystemExit, "missing required routes"):
            deployment.main(
                self.operation_arguments(
                    "verify-composition",
                    **{"required-routes": '["/intelligence/missing/"]'},
                )
            )

    def test_alias_target_mismatch_is_rejected(self) -> None:
        (self.site / "health/index.html").write_text(
            '<meta http-equiv="refresh" content="0; url=/intelligence/work/">\n',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(SystemExit, "does not reference its declared target"):
            deployment.main(self.operation_arguments("verify-composition"))

    def test_stale_manifest_is_rejected(self) -> None:
        with self.assertRaisesRegex(SystemExit, "stale"):
            deployment.main(
                self.operation_arguments(
                    "verify-composition",
                    **{"verified-epoch": str(SOURCE_EPOCH + 121)},
                )
            )

    def test_non_clobber_failure_is_rejected(self) -> None:
        (self.site / "docs/index.html").write_text("clobbered\n", encoding="utf-8")
        with self.assertRaisesRegex(SystemExit, "clobbered"):
            deployment.main(self.operation_arguments("verify-composition"))

    def test_non_route_consumer_file_clobber_is_rejected(self) -> None:
        (self.site / "consumer.css").write_text("original\n", encoding="utf-8")
        self.capture_baseline()
        (self.site / "consumer.css").write_text("clobbered\n", encoding="utf-8")
        with self.assertRaisesRegex(SystemExit, "consumer-owned file was clobbered"):
            deployment.main(self.operation_arguments("verify-composition"))

    def test_incomplete_receipt_is_rejected(self) -> None:
        self.assertEqual(deployment.main(self.operation_arguments("record-receipt")), 0)
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        receipt.pop("rollback")
        deployment.write_json(self.receipt, receipt)
        with self.assertRaisesRegex(SystemExit, "receipt is incomplete"):
            deployment.main(self.operation_arguments("verify-receipt"))

    def test_receipt_rejects_non_public_or_secret_bearing_urls(self) -> None:
        with self.assertRaisesRegex(SystemExit, "credential-free"):
            deployment.main(
                self.operation_arguments(
                    "record-receipt",
                    **{"deployment-url": "https://example.test/consumer/?token=secret"},
                )
            )

    def test_checked_in_fixture_catalog_covers_required_failure_modes(self) -> None:
        fixture = json.loads(
            (
                REPOSITORY_ROOT
                / "tests/fixtures/repository-intelligence-deployment-provenance/cases.v1.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            fixture["schema"],
            "egohygiene.relay.repository-intelligence-deployment-fixtures/v1",
        )
        self.assertEqual(
            {case["id"] for case in fixture["cases"]},
            {
                "deterministic-receipt-separation",
                "revision-drift",
                "digest-mismatch",
                "incompatible-version",
                "missing-route",
                "stale-artifact",
                "non-clobber",
                "alias-target-mismatch",
                "incomplete-receipt",
                "unsafe-url",
            },
        )


if __name__ == "__main__":
    unittest.main()
