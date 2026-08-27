# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Tests for the host-neutral publication-site validation boundary."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from urllib.parse import urljoin


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    REPOSITORY_ROOT
    / "actions/validate-publication-site/scripts/validate_publication_site.py"
)
SPEC = importlib.util.spec_from_file_location("publication_site_validation", SCRIPT)
assert SPEC is not None
assert SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
import sys

sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)
FIXTURE_ROOT = REPOSITORY_ROOT / "tests/fixtures/publication-sites"
REVISION = "a" * 40


def write(path: Path, value: str | bytes) -> None:
    """Create a fixture file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, bytes):
        path.write_bytes(value)
    else:
        path.write_text(value, encoding="utf-8")


def resource(
    site: Path,
    *,
    identifier: str,
    label: str,
    media_type: str,
    path: str,
    route: str | None = None,
    base_url: str,
    fallback_base_url: str | None,
    aliases: list[str] | None = None,
) -> dict:
    """Describe a real fixture resource."""

    target = site / path
    public_route = route or path
    return {
        "aliases": [
            {
                "fallback_url": (
                    urljoin(fallback_base_url, alias)
                    if fallback_base_url is not None
                    else None
                ),
                "path": alias,
                "url": urljoin(base_url, alias),
            }
            for alias in aliases or []
        ],
        "bytes": target.stat().st_size,
        "fallback_url": (
            urljoin(fallback_base_url, public_route)
            if fallback_base_url is not None
            else None
        ),
        "id": identifier,
        "label": label,
        "media_type": media_type,
        "path": path,
        "route": public_route,
        "sha256": validator.sha256_file(target),
        "url": urljoin(base_url, public_route),
    }


def build_site(
    workspace: Path,
    fixture_name: str,
    *,
    revision: str = REVISION,
) -> tuple[dict, Path]:
    """Materialize one checked host-topology fixture with deterministic bytes."""

    fixture = json.loads(
        (FIXTURE_ROOT / f"{fixture_name}.json").read_text(encoding="utf-8")
    )
    site = workspace / fixture["site_directory"]
    base_url = fixture["base_url"]
    fallback = fixture["fallback_base_url"]
    pages = {
        "index.html": "<!doctype html><html><title>Hub</title><h1>Hub</h1></html>\n",
        "paper/index.html": "<!doctype html><html><title>Paper</title><h1>Paper</h1></html>\n",
        "magazine/index.html": "<!doctype html><html><title>Magazine</title><h1>Planned</h1></html>\n",
        "downloads/index.html": "<!doctype html><html><title>Downloads</title><h1>Downloads</h1></html>\n",
        "manifest.webmanifest": (
            '{"description":"Fixture","id":"./","name":"Fixture",'
            '"scope":"./","short_name":"Fixture","start_url":"./"}\n'
        ),
        "publication.json": '{"schema":"fixture.publication/v1"}\n',
        "files/paper.pdf": b"%PDF-1.4 fixture\n%%EOF\n",
        "antidote.pdf": b"%PDF-1.4 fixture\n%%EOF\n",
        ".nojekyll": b"",
    }
    for relative, value in pages.items():
        write(site / relative, value)

    paper = resource(
        site,
        identifier="paper-pdf",
        label="Paper PDF",
        media_type="application/pdf",
        path="files/paper.pdf",
        base_url=base_url,
        fallback_base_url=fallback,
        aliases=["antidote.pdf"],
    )
    accessible = resource(
        site,
        identifier="accessible-web",
        label="Accessible web paper",
        media_type="text/html",
        path="paper/index.html",
        route="paper/",
        base_url=base_url,
        fallback_base_url=fallback,
    )
    manifest = resource(
        site,
        identifier="paper-manifest",
        label="Paper manifest",
        media_type="application/json",
        path="publication.json",
        base_url=base_url,
        fallback_base_url=fallback,
    )
    catalog = {
        "routes": sorted(
            [
                {
                    "fallback_url": urljoin(fallback, route) if fallback else None,
                    "id": identifier,
                    "kind": kind,
                    "path": route,
                    "url": urljoin(base_url, route),
                }
                for identifier, kind, route in (
                    ("home", "hub", ""),
                    ("downloads", "downloads", "downloads/"),
                    ("web-manifest", "web-manifest", "manifest.webmanifest"),
                    ("sha256sums", "checksum", "SHA256SUMS"),
                    ("site-json", "catalog", "site.json"),
                    ("paper", "slot", "paper/"),
                    ("magazine", "slot", "magazine/"),
                    ("paper:paper-pdf", "artifact", "files/paper.pdf"),
                    ("paper:paper-pdf", "artifact-alias", "antidote.pdf"),
                    ("paper:paper-manifest", "manifest", "publication.json"),
                )
            ],
            key=lambda item: (item["path"], item["kind"], item["id"]),
        ),
        "schema": "beacon.publication-hub/v1",
        "schema_version": "1.0.0",
        "site": {
            "canonical_base_url": base_url,
            "description": "Fixture publication hub",
            "fallback_base_url": fallback,
            "id": "fixture-publication",
            "language": "en",
            "publisher": "Fixture",
            "revision": revision,
            "stage": "published",
            "theme": "neutral",
            "title": "Fixture publication",
        },
        "slots": [
            {
                "artifacts": [accessible, paper],
                "fallback_url": urljoin(fallback, "paper/") if fallback else None,
                "id": "paper",
                "kind": "research-paper",
                "landing": {"mode": "resource", "resource_id": "accessible-web"},
                "manifests": [manifest],
                "order": 1,
                "route": "paper/",
                "status": "available",
                "summary": "Available paper",
                "source": {
                    "repository": "https://github.com/example/publication",
                    "revision": revision,
                },
                "title": "Paper",
                "url": urljoin(base_url, "paper/"),
                "version": "0.1.0",
            },
            {
                "fallback_url": (
                    urljoin(fallback, "magazine/") if fallback else None
                ),
                "id": "magazine",
                "kind": "magazine",
                "landing": {"mode": "generated"},
                "order": 2,
                "route": "magazine/",
                "status": "planned",
                "summary": "Magazine is planned",
                "title": "Magazine",
                "url": urljoin(base_url, "magazine/"),
            },
        ],
        "source": {
            "catalog_sha256": "b" * 64,
            "repository": "https://github.com/example/publication",
            "revision": revision,
        },
    }
    write(site / "site.json", json.dumps(catalog, indent=2, sort_keys=True) + "\n")
    checksum_files = sorted(
        (
            path
            for path in site.rglob("*")
            if path.is_file() and path.name != "SHA256SUMS"
        ),
        key=lambda item: item.relative_to(site).as_posix(),
    )
    lines = [
        f"{validator.sha256_file(path)}  {path.relative_to(site).as_posix()}"
        for path in checksum_files
    ]
    write(site / "SHA256SUMS", "\n".join(lines) + "\n")
    return fixture, site


class PublicationSiteValidationTests(unittest.TestCase):
    """Keep Relay's local trust boundary strict and host-neutral."""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.workspace = Path(temporary.name)

    def validate(self, fixture: dict) -> object:
        """Validate a materialized fixture."""

        return validator.validate_publication_site(
            workspace=self.workspace,
            site_directory=fixture["site_directory"],
            expected_base_url=fixture["base_url"],
            expected_source_revision=REVISION,
            required_routes_json=json.dumps(fixture["required_routes"]),
        )

    def test_custom_domain_fixture_passes_with_empty_nojekyll(self) -> None:
        fixture, _ = build_site(self.workspace, "custom-domain")

        result = self.validate(fixture)

        self.assertEqual(result.canonical_base_url, fixture["base_url"])
        self.assertEqual(result.fallback_base_url, fixture["fallback_base_url"])
        self.assertEqual(result.source_revision, REVISION)
        self.assertEqual(len(result.routes), 10)
        self.assertEqual(result.file_count, 11)
        self.assertGreater(result.total_bytes, 0)
        self.assertRegex(result.site_tree_sha256, r"^[0-9a-f]{64}$")

    def test_repository_subpath_fixture_passes_without_fallback(self) -> None:
        fixture, _ = build_site(self.workspace, "repository-subpath")

        result = self.validate(fixture)

        self.assertEqual(result.canonical_base_url, fixture["base_url"])
        self.assertIsNone(result.fallback_base_url)
        self.assertIn(("paper/", "paper/index.html"), result.route_files)

    def test_planned_slot_cannot_claim_issue_or_artifact(self) -> None:
        fixture, site = build_site(self.workspace, "custom-domain")
        catalog_path = site / "site.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        magazine = next(slot for slot in catalog["slots"] if slot["id"] == "magazine")
        magazine["issue_number"] = "1"
        catalog_path.write_text(
            json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        self.refresh_checksums(site)

        with self.assertRaisesRegex(
            validator.ValidationError,
            "planned slot|unsupported (?:schema )?field",
        ):
            self.validate(fixture)

        fixture, site = build_site(self.workspace, "repository-subpath")
        catalog_path = site / "site.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        magazine = next(slot for slot in catalog["slots"] if slot["id"] == "magazine")
        magazine["extensions"] = {"nested": {"release-url": "not-published"}}
        catalog_path.write_text(
            json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        self.refresh_checksums(site)
        with self.assertRaisesRegex(validator.ValidationError, "reserved publication key"):
            self.validate(fixture)

    def test_available_slot_requires_evidence_and_alias_bytes_must_match(self) -> None:
        fixture, site = build_site(self.workspace, "custom-domain")
        catalog_path = site / "site.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        paper = next(slot for slot in catalog["slots"] if slot["id"] == "paper")
        paper["artifacts"] = []
        paper["manifests"] = []
        catalog_path.write_text(
            json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        self.refresh_checksums(site)
        with self.assertRaisesRegex(
            validator.ValidationError,
            "version, and artifact|too few items",
        ):
            self.validate(fixture)

        fixture, site = build_site(self.workspace, "repository-subpath")
        (site / "antidote.pdf").write_bytes(b"different alias bytes\n")
        self.refresh_checksums(site)
        with self.assertRaisesRegex(validator.ValidationError, "alias.*bytes"):
            self.validate(fixture)

    def test_resource_route_claims_duplicate_json_and_evidence_paths_fail(self) -> None:
        fixture, site = build_site(self.workspace, "custom-domain")
        catalog_path = site / "site.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        artifact_route = next(
            route for route in catalog["routes"] if route["path"] == "files/paper.pdf"
        )
        artifact_route["kind"] = "slot"
        catalog_path.write_text(
            json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        self.refresh_checksums(site)
        with self.assertRaisesRegex(
            validator.ValidationError, "compatible declared route|incompatible route id"
        ):
            self.validate(fixture)

        fixture, site = build_site(self.workspace, "repository-subpath")
        raw = (site / "site.json").read_text(encoding="utf-8")
        (site / "site.json").write_text(
            raw.replace('"schema":', '"schema": "duplicate",\n  "schema":', 1),
            encoding="utf-8",
        )
        self.refresh_checksums(site)
        with self.assertRaisesRegex(validator.ValidationError, "duplicate key"):
            self.validate(fixture)

        fixture, site = build_site(self.workspace, "custom-domain")
        for value, message in (
            ("../outside.json", "safe portable path"),
            (f"{fixture['site_directory']}/evidence.json", "outside the public site"),
            (".github/evidence.json", "protected root"),
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(validator.ValidationError, message):
                    validator.resolve_workspace_output(
                        self.workspace, value, site=site
                    )

        linked = self.workspace / "linked-evidence"
        linked.symlink_to(self.workspace / "outside-evidence")
        with self.assertRaisesRegex(validator.ValidationError, "symbolic link"):
            validator.resolve_workspace_output(
                self.workspace, "linked-evidence/result.json", site=site
            )

    def test_landing_resource_ids_routes_and_aliases_are_closed_world(self) -> None:
        mutations = {
            "dangling-landing": lambda catalog: catalog["slots"][1].update(
                {"landing": {"mode": "resource", "resource_id": "missing"}}
            ),
            "generated-resource-id": lambda catalog: catalog["slots"][1][
                "landing"
            ].update({"resource_id": "missing"}),
            "duplicate-resource-id": lambda catalog: catalog["slots"][0][
                "manifests"
            ][0].update({"id": "paper-pdf"}),
            "orphan-resource-route": lambda catalog: catalog["routes"].append(
                {
                    "fallback_url": None,
                    "id": "paper:orphan",
                    "kind": "artifact",
                    "path": "orphan.pdf",
                    "url": "https://example.github.io/publication/orphan.pdf",
                }
            ),
            "ghost-slot-route": lambda catalog: catalog["routes"].append(
                {
                    "fallback_url": None,
                    "id": "ghost",
                    "kind": "slot",
                    "path": "ghost/",
                    "url": "https://example.github.io/publication/ghost/",
                }
            ),
            "slot-file-drift": lambda catalog: next(
                route
                for route in catalog["routes"]
                if route["path"] == "magazine/"
            ).update({"file": "other.html"}),
        }
        messages = {
            "dangling-landing": "unknown resource",
            "generated-resource-id": "only valid for resource mode|schema shape",
            "duplicate-resource-id": "repeats resource id",
            "orphan-resource-route": "missing or empty|orphan publication route",
            "ghost-slot-route": "undeclared extra routes",
            "slot-file-drift": "compatible slot route",
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                child = self.workspace / name
                child.mkdir()
                fixture, site = build_site(child, "repository-subpath")
                fixture["site_directory"] = f"{name}/{fixture['site_directory']}"
                catalog_path = site / "site.json"
                catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
                if name == "orphan-resource-route":
                    write(site / "orphan.pdf", b"orphan\n")
                elif name == "ghost-slot-route":
                    write(site / "ghost/index.html", "<h1>Ghost</h1>\n")
                elif name == "slot-file-drift":
                    write(site / "other.html", "<h1>Wrong landing</h1>\n")
                mutate(catalog)
                catalog["routes"].sort(
                    key=lambda item: (item["path"], item["kind"], item["id"])
                )
                catalog_path.write_text(
                    json.dumps(catalog, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                self.refresh_checksums(site)
                with self.assertRaisesRegex(
                    validator.ValidationError, messages[name]
                ):
                    self.validate(fixture)

        fixture, site = build_site(self.workspace, "custom-domain")
        catalog_path = site / "site.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        paper = catalog["slots"][0]
        alias = paper["artifacts"][1]["aliases"][0]
        alias.update(
            {
                "path": "aliases/antidote.pdf",
                "url": urljoin(fixture["base_url"], "aliases/antidote.pdf"),
                "fallback_url": urljoin(
                    fixture["fallback_base_url"], "aliases/antidote.pdf"
                ),
            }
        )
        write(site / "aliases/antidote.pdf", (site / "antidote.pdf").read_bytes())
        alias_route = next(
            route for route in catalog["routes"] if route["path"] == "antidote.pdf"
        )
        alias_route.update(
            {
                "path": "aliases/antidote.pdf",
                "url": urljoin(fixture["base_url"], "aliases/antidote.pdf"),
                "fallback_url": urljoin(
                    fixture["fallback_base_url"], "aliases/antidote.pdf"
                ),
            }
        )
        catalog["routes"].sort(
            key=lambda item: (item["path"], item["kind"], item["id"])
        )
        catalog_path.write_text(
            json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        self.refresh_checksums(site)
        with self.assertRaisesRegex(
            validator.ValidationError,
            "alias must be at site root|schema pattern",
        ):
            self.validate(fixture)

        child = self.workspace / "alias-route-drift"
        child.mkdir()
        fixture, site = build_site(child, "repository-subpath")
        fixture["site_directory"] = f"alias-route-drift/{fixture['site_directory']}"
        write(site / "other.bin", b"different public route bytes\n")
        catalog_path = site / "site.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        alias_route = next(
            route for route in catalog["routes"] if route["path"] == "antidote.pdf"
        )
        alias_route["file"] = "other.bin"
        catalog_path.write_text(
            json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        self.refresh_checksums(site)
        with self.assertRaisesRegex(validator.ValidationError, "alias has no compatible route"):
            self.validate(fixture)

        child = self.workspace / "landing-alias"
        child.mkdir()
        fixture, site = build_site(child, "repository-subpath")
        fixture["site_directory"] = f"landing-alias/{fixture['site_directory']}"
        write(site / "paper.html", (site / "paper/index.html").read_bytes())
        catalog_path = site / "site.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        accessible = catalog["slots"][0]["artifacts"][0]
        accessible["aliases"].append(
            {
                "fallback_url": None,
                "path": "paper.html",
                "url": urljoin(fixture["base_url"], "paper.html"),
            }
        )
        catalog["routes"].append(
            {
                "fallback_url": None,
                "id": "paper:accessible-web",
                "kind": "artifact-alias",
                "path": "paper.html",
                "url": urljoin(fixture["base_url"], "paper.html"),
            }
        )
        catalog["routes"].sort(
            key=lambda item: (item["path"], item["kind"], item["id"])
        )
        catalog_path.write_text(
            json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        self.refresh_checksums(site)
        with self.assertRaisesRegex(validator.ValidationError, "incompatible route id"):
            self.validate(fixture)

    def test_inventory_cap_and_sanitized_failure_evidence(self) -> None:
        fixture, site = build_site(self.workspace, "repository-subpath")
        original_limit = validator.MAX_SITE_FILES
        validator.MAX_SITE_FILES = 2
        self.addCleanup(setattr, validator, "MAX_SITE_FILES", original_limit)
        with self.assertRaisesRegex(validator.ValidationError, "entry-count|file-count"):
            validator.inventory_files(site)

        validator.MAX_SITE_FILES = original_limit
        catalog_path = site / "site.json"
        catalog_path.write_text("{not-json\n", encoding="utf-8")
        self.refresh_checksums(site)
        evidence = self.workspace / ".relay/failure.json"
        result = validator.main(
            [
                "--workspace",
                str(self.workspace),
                "--site-directory",
                fixture["site_directory"],
                "--expected-base-url",
                fixture["base_url"],
                "--expected-source-revision",
                REVISION,
                "--evidence-output",
                ".relay/failure.json",
            ]
        )
        self.assertEqual(result, 2)
        failure = evidence.read_text(encoding="utf-8")
        self.assertIn("publication-site-validation-failed", failure)
        self.assertNotIn(str(self.workspace), failure)
        self.assertNotIn("not-json", failure)

    def test_base_urls_reject_output_injection_and_ambiguous_paths(self) -> None:
        for value in (
            "https://example.test/\nforged=value/",
            "https://example.test/%2e%2e/",
            "https://example.test/a//b/",
            "https://example.test/a\\b/",
            "https://localhost/",
            "https://127.0.0.1/",
            "https://example.test:8443/",
            "https://internal/",
        ):
            with self.subTest(value=value):
                with self.assertRaises(validator.ValidationError):
                    validator.normalize_base_url(value, "fixture")

    def test_symlink_and_protected_output_are_rejected(self) -> None:
        fixture, site = build_site(self.workspace, "custom-domain")
        outside = self.workspace / "outside.txt"
        outside.write_text("private\n", encoding="utf-8")
        (site / "linked.txt").symlink_to(outside)
        self.refresh_checksums(site, skip_symlinks=True)

        with self.assertRaisesRegex(validator.ValidationError, "symbolic links"):
            self.validate(fixture)

        protected = self.workspace / ".github"
        shutil.copytree(site, protected, symlinks=True)
        with self.assertRaisesRegex(validator.ValidationError, "protected root"):
            validator.validate_publication_site(
                workspace=self.workspace,
                site_directory=".github",
                expected_base_url=fixture["base_url"],
                expected_source_revision=REVISION,
            )

    def test_incomplete_unsorted_and_mismatched_checksums_fail(self) -> None:
        for mode, message in (
            ("incomplete", "incomplete"),
            ("unsorted", "sorted"),
            ("mismatch", "checksum mismatch"),
        ):
            with self.subTest(mode=mode):
                child = self.workspace / mode
                child.mkdir()
                fixture, site = build_site(child, "repository-subpath")
                fixture["site_directory"] = f"{mode}/{fixture['site_directory']}"
                manifest = site / "SHA256SUMS"
                lines = manifest.read_text(encoding="utf-8").splitlines()
                if mode == "incomplete":
                    lines.pop()
                elif mode == "unsorted":
                    lines[0], lines[1] = lines[1], lines[0]
                else:
                    target = site / lines[0].split("  ", 1)[1]
                    target.write_bytes(target.read_bytes() + b"changed")
                manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
                with self.assertRaisesRegex(validator.ValidationError, message):
                    self.validate(fixture)

        child = self.workspace / "bounded-incomplete-diagnostic"
        child.mkdir()
        fixture, site = build_site(child, "repository-subpath")
        fixture["site_directory"] = (
            f"bounded-incomplete-diagnostic/{fixture['site_directory']}"
        )
        for index in range(50):
            write(site / f"unlisted-{index:02d}.txt", "unlisted\n")
        with self.assertRaises(validator.ValidationError) as caught:
            self.validate(fixture)
        message = str(caught.exception)
        self.assertIn("missing count=50", message)
        self.assertLess(len(message), 500)

    def test_required_route_base_and_revision_must_match(self) -> None:
        fixture, _ = build_site(self.workspace, "custom-domain")

        for replacement, message in (
            ({"required_routes": ["missing/"]}, "missing required routes"),
            ({"base_url": "https://other.example.test/"}, "canonical base URL"),
        ):
            changed = {**fixture, **replacement}
            with self.subTest(replacement=replacement):
                with self.assertRaisesRegex(validator.ValidationError, message):
                    self.validate(changed)
        with self.assertRaisesRegex(validator.ValidationError, "source revision"):
            validator.validate_publication_site(
                workspace=self.workspace,
                site_directory=fixture["site_directory"],
                expected_base_url=fixture["base_url"],
                expected_source_revision="c" * 40,
            )

        with self.assertRaisesRegex(validator.ValidationError, "fallback base URL"):
            validator.validate_publication_site(
                workspace=self.workspace,
                site_directory=fixture["site_directory"],
                expected_base_url=fixture["base_url"],
                expected_source_revision=REVISION,
                expected_fallback_base_url="https://wrong.example.test/",
            )

        fixture, _ = build_site(self.workspace, "repository-subpath")
        with self.assertRaisesRegex(validator.ValidationError, "fallback base URL"):
            validator.validate_publication_site(
                workspace=self.workspace,
                site_directory=fixture["site_directory"],
                expected_base_url=fixture["base_url"],
                expected_source_revision=REVISION,
                expected_fallback_base_url="https://fallback.example.test/",
            )

    def test_non_finite_json_numbers_are_rejected(self) -> None:
        for index, constant in enumerate(("NaN", "Infinity", "-Infinity")):
            with self.subTest(constant=constant):
                child = self.workspace / f"nonfinite-{index}"
                child.mkdir()
                fixture, site = build_site(child, "repository-subpath")
                fixture["site_directory"] = (
                    f"nonfinite-{index}/{fixture['site_directory']}"
                )
                catalog_path = site / "site.json"
                raw = catalog_path.read_text(encoding="utf-8")
                catalog_path.write_text(
                    raw.replace(
                        '"schema":',
                        f'"extensions": {{"unsafe": {constant}}},\n  "schema":',
                        1,
                    ),
                    encoding="utf-8",
                )
                self.refresh_checksums(site)
                with self.assertRaisesRegex(
                    validator.ValidationError, "non-finite JSON number"
                ):
                    self.validate(fixture)

    def test_optional_publication_metadata_matches_the_v1_contract(self) -> None:
        def paper(catalog: dict) -> dict:
            return next(slot for slot in catalog["slots"] if slot["id"] == "paper")

        mutations = {
            "site-repository": lambda catalog: catalog["site"].update(
                {"repository": "file:///etc/passwd"}
            ),
            "theme": lambda catalog: catalog["site"].update({"theme": "untrusted"}),
            "source-repository": lambda catalog: paper(catalog)["source"].update(
                {"repository": "not-a-url"}
            ),
            "identifiers": lambda catalog: paper(catalog).update(
                {"identifiers": "bogus"}
            ),
            "release": lambda catalog: paper(catalog).update(
                {"release": {"url": "http://localhost/release"}}
            ),
            "preview": lambda catalog: paper(catalog).update(
                {"preview": "not-an-object"}
            ),
            "provenance": lambda catalog: paper(catalog).update(
                {"provenance": "not-an-array"}
            ),
            "accessibility": lambda catalog: paper(catalog).update(
                {
                    "accessibility": {
                        "summary": "Accessible",
                        "features": ["Tagged headings"],
                        "report": {
                            "label": "Report",
                            "url": "http://127.0.0.1/report",
                        },
                    }
                }
            ),
            "resource-reference": lambda catalog: paper(catalog).update(
                {
                    "preview": {
                        "label": "Preview",
                        "resource_id": "missing",
                        "url": "https://example.github.io/publication/paper/",
                        "fallback_url": None,
                        "media_type": "text/html",
                        "path": "paper/index.html",
                        "bytes": 1,
                        "sha256": "f" * 64,
                    }
                }
            ),
            "version-type": lambda catalog: paper(catalog).update(
                {"version": 7}
            ),
            "superseded-by-type": lambda catalog: paper(catalog).update(
                {"superseded_by": {"id": "later"}}
            ),
            "withdrawal-notice-type": lambda catalog: paper(catalog).update(
                {"withdrawal_notice": ["not withdrawn"]}
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                child = self.workspace / f"metadata-{name}"
                child.mkdir()
                fixture, site = build_site(child, "repository-subpath")
                fixture["site_directory"] = (
                    f"metadata-{name}/{fixture['site_directory']}"
                )
                catalog_path = site / "site.json"
                catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
                mutate(catalog)
                catalog_path.write_text(
                    json.dumps(catalog, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                self.refresh_checksums(site)
                with self.assertRaises(validator.ValidationError):
                    self.validate(fixture)

    @staticmethod
    def refresh_checksums(site: Path, *, skip_symlinks: bool = False) -> None:
        """Refresh a deliberately mutated test site's inventory."""

        paths = [
            path
            for path in site.rglob("*")
            if path.is_file()
            and path.name != "SHA256SUMS"
            and not (skip_symlinks and path.is_symlink())
        ]
        lines = [
            f"{validator.sha256_file(path)}  {path.relative_to(site).as_posix()}"
            for path in sorted(paths, key=lambda item: item.relative_to(site).as_posix())
        ]
        (site / "SHA256SUMS").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    unittest.main()
