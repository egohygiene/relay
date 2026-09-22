# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Verify Repository Intelligence composition and record consumer deployment provenance."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
from html.parser import HTMLParser
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit

BUILD_MANIFEST_SCHEMA = "egohygiene.relay.repository-intelligence-build-manifest/v1"
BASELINE_SCHEMA = "egohygiene.relay.repository-intelligence-consumer-route-baseline/v1"
VERIFICATION_SCHEMA = "egohygiene.relay.repository-intelligence-composition-verification/v1"
RECEIPT_SCHEMA = "egohygiene.relay.repository-intelligence-deployment-receipt/v1"
BUILD_MANIFEST_NAME = "build-manifest.json"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
REPOSITORY = re.compile(
    r"^(?!\.{1,2}/)(?![^/]+/\.{1,2}$)[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
)
ENVIRONMENT = re.compile(r"^[A-Za-z0-9._ -]{1,64}$")
MAX_FILES = 10000
MAX_ROUTES = 1000
MAX_TOTAL_BYTES = 256 * 1024 * 1024
MAX_JSON_BYTES = 1024 * 1024
BUILD_CONTRACTS: dict[str, dict[str, str | int]] = {
    "action_inputs": {
        "schema": "egohygiene.relay.repository-intelligence-inputs/v1",
        "version": 1,
    },
    "analytics": {"schema": "egohygiene.repository-analytics/v1", "version": 1},
    "build_manifest": {"schema": BUILD_MANIFEST_SCHEMA, "version": 1},
    "dashboard": {
        "schema": "egohygiene.repository-intelligence-dashboard/v3",
        "version": 1,
    },
    "observatory_comparison": {
        "schema": "egohygiene.observatory.repository-intelligence-compare/v1",
        "version": "1.0.0-alpha.1",
    },
    "observatory_snapshot": {
        "schema": "egohygiene.observatory.repository-intelligence-read-model/v1",
        "version": 1,
    },
    "provenance": {
        "schema": "egohygiene.relay.repository-intelligence-provenance/v1",
        "version": 1,
    },
    "repository_report": {
        "schema": "egohygiene.repository-report-summary/v1",
        "version": 1,
    },
    "repository_tree": {"schema": "egohygiene.repository-tree/v1", "version": 1},
}


class ProvenanceError(ValueError):
    """Consumer composition or deployment evidence failed closed."""


class AliasTargetParser(HTMLParser):
    """Recognize explicit static redirect or canonical references."""

    def __init__(self, target: str) -> None:
        super().__init__(convert_charrefs=True)
        self.target = target
        self.found = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): value for key, value in attrs}
        if tag.lower() == "meta" and (attributes.get("http-equiv") or "").lower() == "refresh":
            content = attributes.get("content") or ""
            match = re.fullmatch(r"\s*[0-9]+\s*;\s*url\s*=\s*([^\s]+)\s*", content, re.IGNORECASE)
            if match and match.group(1).strip("'\"") == self.target:
                self.found = True
        if tag.lower() in {"a", "link"} and attributes.get("href") == self.target:
            self.found = True


def require_exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    """Reject missing and unknown members without exposing payload values."""

    if set(value) != expected:
        raise ProvenanceError(f"{label} is incomplete or incompatible")


def require_object(value: Any, label: str) -> dict[str, Any]:
    """Return one object or reject it with a stable diagnostic."""

    if not isinstance(value, dict):
        raise ProvenanceError(f"{label} must be an object")
    return value


def duplicate_safe_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate JSON members."""

    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProvenanceError("JSON contains duplicate members")
        result[key] = value
    return result


def load_json(path: Path, label: str) -> dict[str, Any]:
    """Load one bounded strict JSON object."""

    try:
        if path.stat().st_size > MAX_JSON_BYTES:
            raise ProvenanceError(f"{label} exceeds the metadata size limit")
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=duplicate_safe_object,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ProvenanceError("JSON contains a non-standard number")
            ),
        )
    except ProvenanceError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise ProvenanceError(f"{label} must contain valid UTF-8 JSON") from error
    return require_object(value, label)


def write_json(path: Path, value: dict[str, Any]) -> None:
    """Write deterministic JSON atomically."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, allow_nan=False, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as destination:
            destination.write(payload)
            destination.flush()
            os.fsync(destination.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def sha256_bytes(value: bytes) -> str:
    """Return a tagged SHA-256 digest."""

    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def sha256_file(path: Path) -> str:
    """Return a tagged SHA-256 digest for one regular file."""

    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def relative_path(value: str, label: str) -> str:
    """Validate a canonical portable repository-relative path."""

    candidate = PurePosixPath(value)
    if (
        not value
        or value.startswith("/")
        or "\\" in value
        or candidate.as_posix() != value
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise ProvenanceError(f"{label} must be a canonical relative path")
    return value


def resolve_directory(workspace: Path, value: str, label: str) -> Path:
    """Resolve one existing directory without crossing the workspace boundary."""

    relative = relative_path(value, label)
    lexical = workspace.joinpath(*PurePosixPath(relative).parts)
    if lexical.is_symlink() or not lexical.is_dir():
        raise ProvenanceError(f"{label} is unavailable")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(workspace)
    except ValueError as error:
        raise ProvenanceError(f"{label} escapes the workspace") from error
    current = workspace
    for part in PurePosixPath(relative).parts:
        current /= part
        if current.is_symlink():
            raise ProvenanceError(f"{label} contains a symbolic link")
    return resolved


def resolve_evidence_path(workspace: Path, value: str, site: Path, label: str) -> Path:
    """Resolve one output or input evidence path outside the deployed site."""

    relative = relative_path(value, label)
    lexical = workspace.joinpath(*PurePosixPath(relative).parts)
    try:
        lexical.relative_to(site)
    except ValueError:
        pass
    else:
        raise ProvenanceError(f"{label} must remain outside the composed site")
    current = workspace
    for part in PurePosixPath(relative).parts[:-1]:
        current /= part
        if current.is_symlink():
            raise ProvenanceError(f"{label} contains a symbolic link")
        if current.exists():
            if not current.is_dir():
                raise ProvenanceError(f"{label} parent is not a directory")
        else:
            current.mkdir()
        try:
            current.resolve(strict=True).relative_to(workspace)
        except ValueError as error:
            raise ProvenanceError(f"{label} escapes the workspace") from error
    if lexical.is_symlink():
        raise ProvenanceError(f"{label} must not be a symbolic link")
    if lexical.exists() and not lexical.is_file():
        raise ProvenanceError(f"{label} must name a regular file")
    return lexical


def route(value: str, label: str) -> str:
    """Validate one normalized absolute directory route."""

    if (
        not isinstance(value, str)
        or not value.startswith("/")
        or not value.endswith("/")
        or "//" in value
        or "\\" in value
        or "?" in value
        or "#" in value
        or len(value) > 256
    ):
        raise ProvenanceError(f"{label} must be a canonical absolute directory route")
    parts = [part for part in value.split("/") if part]
    if any(part in {".", ".."} or not re.fullmatch(r"[A-Za-z0-9._-]+", part) for part in parts):
        raise ProvenanceError(f"{label} contains an unsafe route segment")
    return "/" + "/".join(parts) + "/" if parts else "/"


def entrypoint_for_route(value: str) -> str:
    """Map a normalized route to its static entry point."""

    return "index.html" if value == "/" else f"{value.strip('/')}/index.html"


def route_for_entrypoint(value: str) -> str:
    """Map an index entry point to its normalized route."""

    relative = relative_path(value, "route entrypoint")
    if relative == "index.html":
        return "/"
    if not relative.endswith("/index.html"):
        raise ProvenanceError("route entrypoint must name index.html")
    return route(f"/{relative[:-10]}", "published route")


def file_inventory(root: Path, *, exclude: set[str] | None = None) -> list[dict[str, Any]]:
    """Return a bounded canonical inventory of regular files."""

    excluded = exclude or set()
    records: list[dict[str, Any]] = []
    total = 0
    for path in sorted(root.rglob("*")):
        relative = relative_path(path.relative_to(root).as_posix(), "site file")
        if path.is_symlink():
            raise ProvenanceError("site inventory rejects symbolic links")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ProvenanceError("site inventory rejects non-regular files")
        if relative in excluded:
            continue
        size = path.stat().st_size
        total += size
        if total > MAX_TOTAL_BYTES:
            raise ProvenanceError("site inventory exceeds the byte limit")
        records.append({"path": relative, "bytes": size, "sha256": sha256_file(path)})
        if len(records) > MAX_FILES:
            raise ProvenanceError("site inventory exceeds the file limit")
    if not records:
        raise ProvenanceError("site inventory is empty")
    return records


def inventory_digest(records: list[dict[str, Any]]) -> str:
    """Digest the canonical JSON representation of an inventory."""

    canonical = json.dumps(records, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return sha256_bytes((canonical + "\n").encode("utf-8"))


def route_inventory(site: Path) -> list[dict[str, str]]:
    """Return public directory routes with entrypoint digests."""

    records: list[dict[str, str]] = []
    for path in sorted(site.rglob("index.html")):
        if path.is_symlink() or not path.is_file():
            raise ProvenanceError("published route inventory rejects symbolic links")
        entrypoint = relative_path(path.relative_to(site).as_posix(), "route entrypoint")
        records.append(
            {
                "route": route_for_entrypoint(entrypoint),
                "entrypoint": entrypoint,
                "sha256": sha256_file(path),
            }
        )
        if len(records) > MAX_ROUTES:
            raise ProvenanceError("published route inventory exceeds the route limit")
    records.sort(key=lambda item: item["route"])
    if len({item["route"] for item in records}) != len(records):
        raise ProvenanceError("published route inventory contains duplicates")
    return records


def parse_json_array(value: str, label: str) -> list[Any]:
    """Parse one bounded inline JSON array."""

    if len(value.encode("utf-8")) > 32768:
        raise ProvenanceError(f"{label} exceeds the input size limit")
    try:
        parsed = json.loads(value, object_pairs_hook=duplicate_safe_object)
    except (json.JSONDecodeError, ProvenanceError) as error:
        raise ProvenanceError(f"{label} must be a JSON array") from error
    if not isinstance(parsed, list):
        raise ProvenanceError(f"{label} must be a JSON array")
    return parsed


def parse_required_routes(value: str) -> list[str]:
    """Parse sorted unique required routes."""

    parsed = parse_json_array(value, "required-routes")
    if any(not isinstance(item, str) for item in parsed):
        raise ProvenanceError("required-routes must contain only strings")
    normalized = sorted(route(item, "required route") for item in parsed)
    if len(set(normalized)) != len(normalized):
        raise ProvenanceError("required-routes contains duplicates")
    return normalized


def parse_aliases(value: str) -> list[dict[str, str]]:
    """Parse consumer-owned redirect aliases."""

    parsed = parse_json_array(value, "aliases")
    aliases: list[dict[str, str]] = []
    for item in parsed:
        record = require_object(item, "alias")
        require_exact_keys(record, {"route", "target"}, "alias")
        aliases.append(
            {
                "route": route(record.get("route"), "alias.route"),
                "target": route(record.get("target"), "alias.target"),
            }
        )
    aliases.sort(key=lambda item: (item["route"], item["target"]))
    if len({item["route"] for item in aliases}) != len(aliases):
        raise ProvenanceError("aliases contains duplicate routes")
    return aliases


def validate_alias_target(site: Path, alias: dict[str, str]) -> None:
    """Prove a consumer alias entrypoint references its declared target."""

    entrypoint = site.joinpath(*PurePosixPath(entrypoint_for_route(alias["route"])).parts)
    try:
        if entrypoint.stat().st_size > MAX_JSON_BYTES:
            raise ProvenanceError("consumer alias entrypoint exceeds the size limit")
        contents = entrypoint.read_text(encoding="utf-8")
    except ProvenanceError:
        raise
    except (OSError, UnicodeError) as error:
        raise ProvenanceError("consumer alias entrypoint must be public-safe UTF-8 HTML") from error
    parser = AliasTargetParser(alias["target"])
    try:
        parser.feed(contents)
        parser.close()
    except ValueError as error:
        raise ProvenanceError("consumer alias entrypoint is invalid HTML") from error
    if not parser.found:
        raise ProvenanceError("consumer alias entrypoint does not reference its declared target")


def validate_public_url(value: str, label: str) -> str:
    """Accept a credential-free standard-port public HTTPS URL."""

    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as error:
        raise ProvenanceError(f"{label} must be a valid HTTPS URL") from error
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or port not in {None, 443}
    ):
        raise ProvenanceError(f"{label} must be a credential-free standard-port HTTPS URL")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".localhost"):
        raise ProvenanceError(f"{label} must use a public hostname")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ProvenanceError(f"{label} must use a public hostname")
    normalized_path = parsed.path or "/"
    if "\\" in normalized_path or "%" in normalized_path or "//" in normalized_path:
        raise ProvenanceError(f"{label} contains an ambiguous path")
    if any(part in {".", ".."} for part in normalized_path.split("/")):
        raise ProvenanceError(f"{label} contains an unsafe path")
    if not normalized_path.endswith("/"):
        normalized_path += "/"
    return urlunsplit(("https", hostname, normalized_path, "", ""))


def validate_timestamp(value: str, label: str) -> str:
    """Validate a timezone-aware RFC 3339 timestamp."""

    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except (TypeError, ValueError) as error:
        raise ProvenanceError(f"{label} must be an RFC 3339 timestamp") from error
    if parsed.tzinfo is None:
        raise ProvenanceError(f"{label} must include a timezone")
    return value


def capture_baseline(
    *,
    site: Path,
    repository: str,
    revision: str,
    managed_route_prefix: str,
) -> dict[str, Any]:
    """Capture consumer-owned route bytes before Intelligence composition."""

    routes = [
        item
        for item in route_inventory(site)
        if not item["route"].startswith(managed_route_prefix)
    ]
    managed_path_prefix = managed_route_prefix.strip("/") + "/"
    files = [
        item
        for item in file_inventory(site)
        if not item["path"].startswith(managed_path_prefix)
    ]
    return {
        "schema": BASELINE_SCHEMA,
        "schema_version": 1,
        "consumer": {"repository": repository, "revision": revision},
        "managed_route_prefix": managed_route_prefix,
        "files": files,
        "routes": routes,
    }


def validate_baseline(
    baseline: dict[str, Any],
    *,
    site: Path,
    repository: str,
    revision: str,
    managed_route_prefix: str,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Prove every unrelated route survived composition byte-for-byte."""

    require_exact_keys(
        baseline,
        {
            "schema",
            "schema_version",
            "consumer",
            "managed_route_prefix",
            "files",
            "routes",
        },
        "consumer route baseline",
    )
    if baseline.get("schema") != BASELINE_SCHEMA or baseline.get("schema_version") != 1:
        raise ProvenanceError("consumer route baseline uses an incompatible version")
    if baseline.get("consumer") != {"repository": repository, "revision": revision}:
        raise ProvenanceError("consumer route baseline revision drift")
    if baseline.get("managed_route_prefix") != managed_route_prefix:
        raise ProvenanceError("consumer route baseline managed prefix is incompatible")
    baseline_files = baseline.get("files")
    if not isinstance(baseline_files, list) or not baseline_files:
        raise ProvenanceError("consumer route baseline files are incomplete")
    previous_path = ""
    managed_path_prefix = managed_route_prefix.strip("/") + "/"
    for item in baseline_files:
        record = require_object(item, "consumer route baseline file")
        require_exact_keys(
            record,
            {"path", "bytes", "sha256"},
            "consumer route baseline file",
        )
        path_value = relative_path(record.get("path"), "baseline file path")
        size = record.get("bytes")
        digest = record.get("sha256")
        if (
            path_value <= previous_path
            or path_value.startswith(managed_path_prefix)
            or not isinstance(size, int)
            or isinstance(size, bool)
            or size < 0
            or not isinstance(digest, str)
            or not DIGEST.fullmatch(digest)
        ):
            raise ProvenanceError("consumer route baseline file is incompatible")
        previous_path = path_value
        target = site.joinpath(*PurePosixPath(path_value).parts)
        if target.is_symlink() or not target.is_file():
            raise ProvenanceError("consumer-owned file was removed during composition")
        if target.stat().st_size != size or sha256_file(target) != digest:
            raise ProvenanceError("consumer-owned file was clobbered during composition")
    records = baseline.get("routes")
    if not isinstance(records, list):
        raise ProvenanceError("consumer route baseline routes are incomplete")
    preserved: list[dict[str, str]] = []
    previous = ""
    for item in records:
        record = require_object(item, "consumer route baseline entry")
        require_exact_keys(record, {"route", "entrypoint", "sha256"}, "consumer route baseline entry")
        route_value = route(record.get("route"), "baseline route")
        entrypoint = relative_path(record.get("entrypoint"), "baseline entrypoint")
        digest = record.get("sha256")
        if entrypoint_for_route(route_value) != entrypoint or not isinstance(digest, str) or not DIGEST.fullmatch(digest):
            raise ProvenanceError("consumer route baseline entry is incompatible")
        if route_value <= previous or route_value.startswith(managed_route_prefix):
            raise ProvenanceError("consumer route baseline ordering or ownership is invalid")
        previous = route_value
        target = site.joinpath(*PurePosixPath(entrypoint).parts)
        if target.is_symlink() or not target.is_file():
            raise ProvenanceError("consumer-owned route was removed during composition")
        if sha256_file(target) != digest:
            raise ProvenanceError("consumer-owned route was clobbered during composition")
        preserved.append({"route": route_value, "sha256": digest})
    return preserved, {
        "file_count": len(baseline_files),
        "digest": inventory_digest(baseline_files),
    }


def validate_build_manifest(
    manifest: dict[str, Any],
    *,
    intelligence: Path,
    repository: str,
    consumer_revision: str,
    relay_revision: str,
    verified_epoch: int,
    maximum_age: int,
) -> None:
    """Validate manifest versions, identities, freshness, routes, and payload digest."""

    require_exact_keys(
        manifest,
        {"schema", "schema_version", "consumer", "generator", "contracts", "source_epoch", "enabled_routes", "bundle"},
        "build manifest",
    )
    if manifest.get("schema") != BUILD_MANIFEST_SCHEMA or manifest.get("schema_version") != 1:
        raise ProvenanceError("unsupported build manifest version")
    if manifest.get("consumer") != {"repository": repository, "revision": consumer_revision}:
        raise ProvenanceError("build manifest consumer revision drift")
    generator = require_object(manifest.get("generator"), "build manifest generator")
    require_exact_keys(generator, {"repository", "revision", "version"}, "build manifest generator")
    if generator.get("repository") != "egohygiene/relay" or generator.get("revision") != relay_revision:
        raise ProvenanceError("build manifest Relay revision drift")
    if not isinstance(generator.get("version"), str) or not re.fullmatch(
        r"^[1-9][0-9]*\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$", generator["version"]
    ):
        raise ProvenanceError("build manifest generator version is incompatible")
    if manifest.get("contracts") != BUILD_CONTRACTS:
        raise ProvenanceError("build manifest contract versions are incompatible")
    source_epoch = manifest.get("source_epoch")
    if not isinstance(source_epoch, int) or isinstance(source_epoch, bool) or source_epoch < 0:
        raise ProvenanceError("build manifest source epoch is incompatible")
    if verified_epoch < source_epoch or verified_epoch - source_epoch > maximum_age:
        raise ProvenanceError("build manifest is stale for this deployment")
    enabled = manifest.get("enabled_routes")
    if (
        not isinstance(enabled, list)
        or not enabled
        or enabled != sorted(enabled)
        or len(set(enabled)) != len(enabled)
        or any(route(item, "enabled route") != item for item in enabled)
    ):
        raise ProvenanceError("build manifest enabled routes are incompatible")
    bundle = require_object(manifest.get("bundle"), "build manifest bundle")
    require_exact_keys(bundle, {"algorithm", "digest", "file_count", "files", "total_bytes"}, "build manifest bundle")
    records = file_inventory(intelligence, exclude={BUILD_MANIFEST_NAME})
    expected = {
        "algorithm": "sha256-canonical-file-inventory-v1",
        "digest": inventory_digest(records),
        "file_count": len(records),
        "files": records,
        "total_bytes": sum(item["bytes"] for item in records),
    }
    if bundle != expected:
        raise ProvenanceError("build manifest bundle digest mismatch")
    actual_routes = sorted(
        "/intelligence/" if item["route"] == "/" else f"/intelligence/{item['route'].lstrip('/')}"
        for item in route_inventory(intelligence)
    )
    if enabled != actual_routes:
        raise ProvenanceError("build manifest route inventory mismatch")


def verify_composition(
    *,
    site: Path,
    intelligence: Path,
    manifest_path: Path,
    baseline_path: Path,
    repository: str,
    consumer_revision: str,
    relay_revision: str,
    verified_epoch: int,
    maximum_age: int,
    required_routes: list[str],
    aliases: list[dict[str, str]],
) -> dict[str, Any]:
    """Verify the exact build handoff and consumer-owned composed site."""

    manifest = load_json(manifest_path, "build manifest")
    validate_build_manifest(
        manifest,
        intelligence=intelligence,
        repository=repository,
        consumer_revision=consumer_revision,
        relay_revision=relay_revision,
        verified_epoch=verified_epoch,
        maximum_age=maximum_age,
    )
    baseline = load_json(baseline_path, "consumer route baseline")
    preserved, preserved_files = validate_baseline(
        baseline,
        site=site,
        repository=repository,
        revision=consumer_revision,
        managed_route_prefix="/intelligence/",
    )
    published = [item["route"] for item in route_inventory(site)]
    manifest_routes = manifest["enabled_routes"]
    missing = sorted(set(required_routes) - set(published))
    missing.extend(sorted(set(manifest_routes) - set(published)))
    if missing:
        raise ProvenanceError("composed site is missing required routes")
    for alias in aliases:
        if alias["route"] not in published:
            raise ProvenanceError("composed site is missing a declared alias route")
        if alias["target"] not in manifest_routes:
            raise ProvenanceError("declared alias target is not an enabled Intelligence route")
        if alias["route"].startswith("/intelligence/"):
            raise ProvenanceError("consumer aliases must remain outside the Intelligence subtree")
        validate_alias_target(site, alias)
    site_records = file_inventory(site)
    manifest_relative = manifest_path.relative_to(site).as_posix()
    return {
        "schema": VERIFICATION_SCHEMA,
        "schema_version": 1,
        "consumer": {"repository": repository, "revision": consumer_revision},
        "generator": {"repository": "egohygiene/relay", "revision": relay_revision},
        "source_epoch": manifest["source_epoch"],
        "verified_epoch": verified_epoch,
        "maximum_source_age_seconds": maximum_age,
        "build_manifest": {
            "path": manifest_relative,
            "sha256": sha256_file(manifest_path),
            "bundle_digest": manifest["bundle"]["digest"],
        },
        "composition": {
            "site_digest": inventory_digest(site_records),
            "published_routes": published,
            "preserved_consumer_routes": preserved,
            "preserved_consumer_files": preserved_files,
        },
        "aliases": aliases,
    }


def build_receipt(arguments: argparse.Namespace, verification: dict[str, Any]) -> dict[str, Any]:
    """Build a closed consumer-owned deployment receipt."""

    try:
        run_id = int(arguments.workflow_run_id)
        run_attempt = int(arguments.workflow_run_attempt)
    except ValueError as error:
        raise ProvenanceError("workflow run and attempt must be positive integers") from error
    if run_id < 1 or run_attempt < 1:
        raise ProvenanceError("workflow run and attempt must be positive integers")
    if not ENVIRONMENT.fullmatch(arguments.deployment_environment):
        raise ProvenanceError("deployment environment is invalid")
    if arguments.deployment_conclusion not in {"success", "failure", "cancelled"}:
        raise ProvenanceError("deployment conclusion is invalid")
    recorded_at = validate_timestamp(arguments.recorded_at, "recorded-at")
    return {
        "schema": RECEIPT_SCHEMA,
        "schema_version": 1,
        "consumer": verification["consumer"],
        "generator": verification["generator"],
        "build_manifest": verification["build_manifest"],
        "workflow": {"run_id": run_id, "run_attempt": run_attempt},
        "deployment": {
            "environment": arguments.deployment_environment,
            "url": validate_public_url(arguments.deployment_url, "deployment-url"),
            "conclusion": arguments.deployment_conclusion,
            "recorded_at": recorded_at,
        },
        "composition": verification["composition"],
        "aliases": verification["aliases"],
        "rollback": {
            "consumer_revision": validate_revision(arguments.rollback_revision, "rollback revision"),
            "site_digest": validate_digest(arguments.rollback_site_digest, "rollback site digest"),
            "deployment_url": validate_public_url(arguments.rollback_url, "rollback-url"),
        },
        "verification": {
            "source_epoch": verification["source_epoch"],
            "verified_epoch": verification["verified_epoch"],
            "maximum_source_age_seconds": verification["maximum_source_age_seconds"],
        },
    }


def validate_revision(value: str, label: str) -> str:
    """Validate one immutable Git revision."""

    if not FULL_SHA.fullmatch(value):
        raise ProvenanceError(f"{label} must be a full lowercase SHA")
    return value


def validate_digest(value: str, label: str) -> str:
    """Validate one tagged SHA-256 digest."""

    if not DIGEST.fullmatch(value):
        raise ProvenanceError(f"{label} must be a tagged SHA-256 digest")
    return value


def append_outputs(path: Path | None, values: dict[str, str]) -> None:
    """Append bounded single-line GitHub Action outputs."""

    if path is None:
        return
    with path.open("a", encoding="utf-8", newline="") as destination:
        for key, value in values.items():
            if "\n" in value or "\r" in value:
                raise ProvenanceError("action output contains a control character")
            destination.write(f"{key}={value}\n")


def parse_arguments(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    """Parse the four-operation consumer provenance interface."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--operation",
        choices=("capture-baseline", "verify-composition", "record-receipt", "verify-receipt"),
        required=True,
    )
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--site-directory", required=True)
    parser.add_argument("--intelligence-directory", required=True)
    parser.add_argument("--baseline-path", required=True)
    parser.add_argument("--verification-path", required=True)
    parser.add_argument("--receipt-path", required=True)
    parser.add_argument("--consumer-repository", required=True)
    parser.add_argument("--consumer-revision", required=True)
    parser.add_argument("--relay-revision", default="")
    parser.add_argument("--verified-epoch", default="0")
    parser.add_argument("--maximum-source-age-seconds", default="604800")
    parser.add_argument("--required-routes", default="[]")
    parser.add_argument("--aliases", default="[]")
    parser.add_argument("--workflow-run-id", default="")
    parser.add_argument("--workflow-run-attempt", default="")
    parser.add_argument("--deployment-environment", default="")
    parser.add_argument("--deployment-url", default="")
    parser.add_argument("--deployment-conclusion", default="")
    parser.add_argument("--recorded-at", default="")
    parser.add_argument("--rollback-revision", default="")
    parser.add_argument("--rollback-site-digest", default="")
    parser.add_argument("--rollback-url", default="")
    parser.add_argument("--github-output", type=Path)
    return parser.parse_args(arguments)


def main(arguments: Iterable[str] | None = None) -> int:
    """Run the requested bounded operation."""

    parsed = parse_arguments(arguments)
    try:
        workspace = parsed.workspace.resolve(strict=True)
        site = resolve_directory(workspace, parsed.site_directory, "site-directory")
        intelligence_relative = relative_path(
            parsed.intelligence_directory, "intelligence-directory"
        )
        intelligence_lexical = workspace.joinpath(
            *PurePosixPath(intelligence_relative).parts
        )
        intelligence = (
            intelligence_lexical.resolve(strict=False)
            if parsed.operation == "capture-baseline"
            else resolve_directory(
                workspace, parsed.intelligence_directory, "intelligence-directory"
            )
        )
        if intelligence_lexical.is_symlink():
            raise ProvenanceError("intelligence-directory must not be a symbolic link")
        try:
            intelligence.relative_to(site)
        except ValueError as error:
            raise ProvenanceError("intelligence-directory must be inside site-directory") from error
        repository = parsed.consumer_repository
        if not REPOSITORY.fullmatch(repository):
            raise ProvenanceError("consumer repository must use owner/name form")
        consumer_revision = validate_revision(parsed.consumer_revision, "consumer revision")
        baseline_path = resolve_evidence_path(
            workspace, parsed.baseline_path, site, "baseline-path"
        )
        verification_path = resolve_evidence_path(
            workspace, parsed.verification_path, site, "verification-path"
        )
        receipt_path = resolve_evidence_path(
            workspace, parsed.receipt_path, site, "receipt-path"
        )
        if len({baseline_path, verification_path, receipt_path}) != 3:
            raise ProvenanceError("evidence output paths must be distinct")
        if parsed.operation == "capture-baseline":
            baseline = capture_baseline(
                site=site,
                repository=repository,
                revision=consumer_revision,
                managed_route_prefix="/intelligence/",
            )
            write_json(baseline_path, baseline)
            append_outputs(
                parsed.github_output,
                {"baseline-path": baseline_path.relative_to(workspace).as_posix()},
            )
            print("Captured consumer-owned route baseline")
            return 0

        relay_revision = validate_revision(parsed.relay_revision, "Relay revision")
        try:
            verified_epoch = int(parsed.verified_epoch)
            maximum_age = int(parsed.maximum_source_age_seconds)
        except ValueError as error:
            raise ProvenanceError("freshness inputs must be integers") from error
        if verified_epoch < 0 or maximum_age < 0 or maximum_age > 31536000:
            raise ProvenanceError("freshness inputs are outside supported bounds")
        required_routes = parse_required_routes(parsed.required_routes)
        aliases = parse_aliases(parsed.aliases)
        manifest_path = intelligence / BUILD_MANIFEST_NAME
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise ProvenanceError("build manifest is unavailable")
        verification = verify_composition(
            site=site,
            intelligence=intelligence,
            manifest_path=manifest_path,
            baseline_path=baseline_path,
            repository=repository,
            consumer_revision=consumer_revision,
            relay_revision=relay_revision,
            verified_epoch=verified_epoch,
            maximum_age=maximum_age,
            required_routes=required_routes,
            aliases=aliases,
        )
        write_json(verification_path, verification)
        receipt: dict[str, Any] | None = None
        if parsed.operation in {"record-receipt", "verify-receipt"}:
            expected_receipt = build_receipt(parsed, verification)
            if parsed.operation == "record-receipt":
                write_json(receipt_path, expected_receipt)
            try:
                receipt = load_json(receipt_path, "deployment receipt")
                if receipt != expected_receipt:
                    raise ProvenanceError("deployment receipt is incomplete or inconsistent")
            except ProvenanceError as error:
                raise ProvenanceError("deployment receipt is incomplete or inconsistent") from error
        outputs = {
            "verification-path": verification_path.relative_to(workspace).as_posix(),
            "build-manifest-sha256": verification["build_manifest"]["sha256"],
            "bundle-digest": verification["build_manifest"]["bundle_digest"],
            "composed-site-digest": verification["composition"]["site_digest"],
            "published-routes": json.dumps(
                verification["composition"]["published_routes"], separators=(",", ":")
            ),
        }
        if receipt is not None:
            outputs["receipt-path"] = receipt_path.relative_to(workspace).as_posix()
            outputs["receipt-sha256"] = sha256_file(receipt_path)
        append_outputs(parsed.github_output, outputs)
        print(
            "Verified Repository Intelligence deployment receipt"
            if receipt is not None
            else "Verified Repository Intelligence composition"
        )
        return 0
    except (OSError, ProvenanceError, ValueError) as error:
        raise SystemExit(f"Repository Intelligence deployment provenance failed: {error}") from error


if __name__ == "__main__":
    raise SystemExit(main())
