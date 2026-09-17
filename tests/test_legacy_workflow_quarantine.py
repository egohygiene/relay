# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Guard the non-executable legacy workflow intake boundary."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import stat
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPOSITORY_ROOT / "tests/fixtures/legacy-workflows"
QUARANTINE_ROOT = FIXTURE_ROOT / "quarantine"
ARCHIVE_ROOT = FIXTURE_ROOT / "archive"
ACTIVE_WORKFLOW_ROOT = REPOSITORY_ROOT / ".github/workflows"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
REDACTED_STUB = b"# Redacted legacy workflow; body retained in authorized evidence.\n"
LIFECYCLE_ROOTS = {
    "quarantined": QUARANTINE_ROOT,
    "rejected": ARCHIVE_ROOT / "rejected",
    "superseded": ARCHIVE_ROOT / "superseded",
    "graduated": ARCHIVE_ROOT / "graduated",
}
VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "validate_actions",
    REPOSITORY_ROOT / "scripts/validate_actions.py",
)
assert VALIDATOR_SPEC is not None and VALIDATOR_SPEC.loader is not None
validator = importlib.util.module_from_spec(VALIDATOR_SPEC)
VALIDATOR_SPEC.loader.exec_module(validator)


class LegacyWorkflowQuarantineTests(unittest.TestCase):
    """Prove that retained legacy bytes cannot become active by placement."""

    @classmethod
    def record_directories(cls) -> list[tuple[str, Path]]:
        records: list[tuple[str, Path]] = []
        for state, root in LIFECYCLE_ROOTS.items():
            if root.is_dir():
                records.extend(
                    (state, path) for path in sorted(root.iterdir()) if path.is_dir()
                )
        return records

    def test_every_candidate_pairs_one_manifest_with_one_disabled_workflow(self) -> None:
        records = self.record_directories()
        self.assertTrue(records, "at least one representative candidate is required")
        expected_directories = {directory.resolve() for _, directory in records}
        observed_manifest_directories = {
            path.parent.resolve() for path in FIXTURE_ROOT.rglob("candidate.json")
        }
        observed_artifact_directories = {
            path.parent.resolve()
            for pattern in ("*.yml.disabled", "*.yaml.disabled")
            for path in FIXTURE_ROOT.rglob(pattern)
        }
        self.assertEqual(expected_directories, observed_manifest_directories)
        self.assertEqual(expected_directories, observed_artifact_directories)
        expected_files = {
            path.resolve()
            for directory in expected_directories
            for path in (
                directory / "candidate.json",
                *directory.glob("*.yml.disabled"),
                *directory.glob("*.yaml.disabled"),
            )
        }
        observed_files = {
            path.resolve()
            for path in FIXTURE_ROOT.rglob("*")
            if path.is_file() or path.is_symlink()
        }
        self.assertEqual(expected_files, observed_files)

        identifiers = []

        for expected_state, directory in records:
            with self.subTest(candidate=directory.name):
                self.assertFalse(directory.is_symlink())
                manifest_path = directory / "candidate.json"
                self.assertTrue(manifest_path.is_file())
                self.assertFalse(manifest_path.is_symlink())
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                identifiers.append(manifest["id"])
                self.assertEqual(expected_state, manifest["lifecycle"]["state"])
                self.assertEqual(expected_state, manifest["disposition"]["state"])
                self.assertRegex(
                    manifest["lifecycle"]["reviewed_at"], r"^\d{4}-\d{2}-\d{2}$"
                )
                self.assertTrue(manifest["lifecycle"]["reviewer_role"].strip())

                artifacts = sorted(directory.glob("*.yml.disabled")) + sorted(
                    directory.glob("*.yaml.disabled")
                )
                self.assertEqual(1, len(artifacts))
                self.assertEqual(artifacts[0].name, manifest["artifact"]["path"])
                self.assertTrue(artifacts[0].is_file())
                self.assertFalse(artifacts[0].is_symlink())
                self.assertEqual(0, artifacts[0].stat().st_mode & stat.S_IXUSR)
                self.assertEqual(0, artifacts[0].stat().st_mode & stat.S_IXGRP)
                self.assertEqual(0, artifacts[0].stat().st_mode & stat.S_IXOTH)
                self.assertEqual([], list(directory.glob("*.yml")))
                self.assertEqual([], list(directory.glob("*.yaml")))
                self.assertEqual(
                    {Path("candidate.json"), Path(manifest["artifact"]["path"])},
                    {
                        path.relative_to(directory)
                        for path in directory.rglob("*")
                        if path.is_file() or path.is_symlink()
                    },
                )
                self.assertEqual([], [path for path in directory.iterdir() if path.is_dir()])

                if expected_state in {"rejected", "superseded", "graduated"}:
                    self.assertTrue(manifest["disposition"]["reason"].strip())
                if expected_state in {"superseded", "graduated"}:
                    replacement = manifest["disposition"]["replacement"]
                    self.assertIsInstance(replacement, dict)
                    self.assertTrue(replacement["catalog_ids"])
                    self.assertTrue(replacement["paths"])
                    self.assertRegex(
                        replacement["immutable_release"],
                        r"^https://github\.com/egohygiene/relay/releases/tag/v\d+\.\d+\.\d+$",
                    )

        self.assertEqual(len(identifiers), len(set(identifiers)))

    def test_manifests_bind_provenance_and_exact_disabled_bytes(self) -> None:
        for expected_state, directory in self.record_directories():
            with self.subTest(candidate=directory.name):
                manifest = json.loads((directory / "candidate.json").read_text(encoding="utf-8"))
                self.assertEqual(
                    "egohygiene.relay-legacy-workflow-candidate/v1-internal",
                    manifest["schema"],
                )
                self.assertEqual(directory.name, manifest["id"])
                self.assertEqual("legacy-github-actions-workflow", manifest["kind"])
                self.assertEqual(expected_state, manifest["lifecycle"]["state"])
                self.assertEqual(expected_state, manifest["disposition"]["state"])

                source = manifest["source"]
                self.assertRegex(
                    source["observed_at"],
                    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$",
                )
                self.assertTrue(source["license"].strip())

                artifact_path = Path(manifest["artifact"]["path"])
                self.assertFalse(artifact_path.is_absolute())
                self.assertEqual(artifact_path.name, str(artifact_path))
                artifact = (directory / artifact_path).resolve(strict=True)
                self.assertIn(directory.resolve(), artifact.parents)
                self.assertEqual(".disabled", artifact.suffix)
                self.assertFalse(manifest["artifact"]["executable"])
                artifact_bytes = artifact.read_bytes()
                self.assertEqual(
                    hashlib.sha256(artifact_bytes).hexdigest(),
                    manifest["artifact"]["sha256"],
                )
                self.assertRegex(manifest["review"]["issue"], r"^https://github\.com/")
                self.assertTrue(
                    {
                        "triggers",
                        "permissions",
                        "token_sources",
                        "secret_interfaces",
                        "dependencies",
                        "mutations",
                        "deployment_behavior",
                        "repository_assumptions",
                        "reusable_suitability",
                        "findings",
                    }.issubset(manifest["review"])
                )
                self.assertIsInstance(manifest["review"]["secret_interfaces"], list)
                self.assertIsInstance(manifest["review"]["deployment_behavior"], dict)

                capture = manifest["capture"]
                self.assertIn(
                    capture["mode"],
                    {"verbatim-public-source", "sanitized-public-source", "opaque-restricted-source"},
                )
                self.assertIsInstance(capture["transformations"], list)
                self.assertIsInstance(capture["redactions"], list)
                self.assertIn(capture["content_state"], {"verbatim", "sanitized", "metadata-only"})
                if source["visibility"] == "public":
                    self.assertIn(capture["content_state"], {"verbatim", "sanitized"})
                    self.assertRegex(source["observed_revision"], FULL_SHA)
                    self.assertRegex(source["blob_sha"], FULL_SHA)
                    self.assertEqual(
                        f"https://github.com/{source['repository']}/blob/"
                        f"{source['observed_revision']}/{source['path']}",
                        source["url"],
                    )
                    if capture["content_state"] == "verbatim":
                        self.assertEqual("verbatim-public-source", capture["mode"])
                        git_header = f"blob {len(artifact_bytes)}\0".encode("ascii")
                        self.assertEqual(
                            hashlib.sha1(git_header + artifact_bytes).hexdigest(),
                            source["blob_sha"],
                        )
                        self.assertEqual([], capture["transformations"])
                        self.assertEqual([], capture["redactions"])
                    else:
                        self.assertEqual("sanitized-public-source", capture["mode"])
                        self.assertTrue(
                            capture["transformations"] or capture["redactions"]
                        )
                else:
                    self.assertIn(source["visibility"], {"private", "restricted"})
                    self.assertTrue(source["opaque_reference"].strip())
                    self.assertTrue(capture["redaction_reason"].strip())
                    self.assertEqual("metadata-only", capture["content_state"])
                    self.assertEqual("opaque-restricted-source", capture["mode"])
                    self.assertEqual(REDACTED_STUB, artifact_bytes)
                    self.assertTrue(capture["redactions"])
                    for forbidden in (
                        "repository",
                        "path",
                        "observed_revision",
                        "blob_sha",
                        "url",
                    ):
                        self.assertNotIn(forbidden, source)

    def test_candidates_are_outside_active_workflows_and_catalogs(self) -> None:
        workflow_catalog = json.loads(
            (REPOSITORY_ROOT / "workflow-catalog.json").read_text(encoding="utf-8")
        )
        action_catalog = json.loads(
            (REPOSITORY_ROOT / "action-catalog.json").read_text(encoding="utf-8")
        )
        catalog_text = json.dumps([workflow_catalog, action_catalog], sort_keys=True)
        supported_paths = {
            entry["id"]: entry["path"] for entry in workflow_catalog["workflows"]
        }
        for entry in action_catalog["workflows"]:
            self.assertIn(entry["id"], supported_paths)
            self.assertEqual(supported_paths[entry["id"]], entry["path"])

        for _, directory in self.record_directories():
            manifest = json.loads((directory / "candidate.json").read_text(encoding="utf-8"))
            artifact = (directory / manifest["artifact"]["path"]).resolve()
            with self.subTest(candidate=directory.name):
                self.assertNotIn(ACTIVE_WORKFLOW_ROOT.resolve(), artifact.parents)
                self.assertNotIn(manifest["id"], catalog_text)
                self.assertNotIn(str(artifact.relative_to(REPOSITORY_ROOT)), catalog_text)
                replacement = manifest["disposition"]["replacement"]
                if replacement is not None:
                    self.assertEqual(
                        len(replacement["catalog_ids"]), len(replacement["paths"])
                    )
                    for catalog_id, path in zip(
                        replacement["catalog_ids"], replacement["paths"], strict=True
                    ):
                        self.assertIn(catalog_id, supported_paths)
                        self.assertEqual(path, supported_paths[catalog_id])

        discovered = validator.discovered_workflow_paths(REPOSITORY_ROOT)
        self.assertFalse(any("legacy-workflows" in path for path in discovered))

    def test_active_automation_never_references_legacy_evidence(self) -> None:
        active_sources = []
        for root in (
            ACTIVE_WORKFLOW_ROOT,
            REPOSITORY_ROOT / "actions",
            REPOSITORY_ROOT / "scripts",
            REPOSITORY_ROOT / "examples/workflows",
        ):
            for path in root.rglob("*"):
                if path.is_symlink():
                    self.assertNotIn(
                        FIXTURE_ROOT.resolve(),
                        path.resolve(strict=True).parents,
                    )
                if path.is_file():
                    active_sources.append(path)

        records = []
        for _, directory in self.record_directories():
            manifest = json.loads((directory / "candidate.json").read_text(encoding="utf-8"))
            records.append(
                (
                    manifest["id"],
                    str((directory / manifest["artifact"]["path"]).relative_to(REPOSITORY_ROOT)),
                )
            )

        for path in active_sources:
            with self.subTest(path=path.relative_to(REPOSITORY_ROOT)):
                self.assertNotIn(FIXTURE_ROOT.resolve(), path.resolve(strict=True).parents)
                try:
                    source = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                self.assertNotIn("tests/fixtures/legacy-workflows", source)
                for candidate_id, artifact_path in records:
                    self.assertNotIn(candidate_id, source)
                    self.assertNotIn(artifact_path, source)

    def test_representative_fixture_retains_the_reviewed_risk_markers(self) -> None:
        candidate = (
            ARCHIVE_ROOT
            / "superseded"
            / "relay-automatic-release-v1"
            / "workflow.yml.disabled"
        ).read_text(encoding="utf-8")

        for marker in (
            "  push:\n",
            "  workflow_dispatch:\n",
            "  contents: write\n",
            "      - release.json\n",
            "          persist-credentials: true\n",
            'git push origin "refs/tags/${VERSION}"',
            'gh release create "${VERSION}"',
            'git push --force origin "refs/tags/${MAJOR_ALIAS}"',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, candidate)
        self.assertIn("    timeout-minutes: 20\n", candidate)
        self.assertIn(
            "uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            candidate,
        )


if __name__ == "__main__":
    unittest.main()
