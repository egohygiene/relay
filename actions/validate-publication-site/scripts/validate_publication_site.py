# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Validate a complete, caller-built publication site without rendering it."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any, Iterable
from urllib.parse import urljoin, urlsplit, urlunsplit


CATALOG_SCHEMA = "beacon.publication-hub/v1"
PUBLIC_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "contracts"
    / "publication-site.schema.json"
)
PUBLIC_SCHEMA_SHA256 = (
    "458cfcdf8f24ef2c702ce592ad329cdb1a7c88954df6c7fcfe2f143d01b9c112"
)
EVIDENCE_SCHEMA = "egohygiene.relay.publication-site-validation/v1"
SLOT_STATUSES = {"planned", "draft", "available", "superseded", "withdrawn"}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REVISION = re.compile(r"^[0-9a-f]{40}$")
SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9._~-]+$")
IDENTIFIER = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PROTECTED_SITE_ROOTS = {
    ".git",
    ".github",
    ".ssh",
    "actions",
    "scripts",
    "tests",
}
MAX_SITE_FILES = 20_000
MAX_FILE_BYTES = 256 * 1024 * 1024
MAX_SITE_BYTES = 1024 * 1024 * 1024
MAX_CATALOG_BYTES = 8 * 1024 * 1024
MAX_CHECKSUM_BYTES = 16 * 1024 * 1024
MAX_DIAGNOSTIC_PATHS = 5
MAX_DIAGNOSTIC_PATH_LENGTH = 96
PLANNED_PUBLICATION_FIELDS = {
    "artifacts",
    "bytes",
    "checksum",
    "cover",
    "cover_url",
    "date_published",
    "doi",
    "identifiers",
    "issue",
    "issue_number",
    "manifest",
    "manifests",
    "preview",
    "provenance",
    "publication_date",
    "published_at",
    "release",
    "release_date",
    "release_url",
    "sha256",
    "source",
    "version",
    "zenodo",
}
CATALOG_KEYS = {
    "schema",
    "schema_version",
    "source",
    "site",
    "routes",
    "slots",
    "extensions",
}
SOURCE_KEYS = {"catalog_sha256", "repository", "revision"}
SITE_KEYS = {
    "id",
    "title",
    "description",
    "language",
    "stage",
    "publisher",
    "theme",
    "canonical_base_url",
    "fallback_base_url",
    "repository",
    "revision",
    "extensions",
}
ROUTE_KEYS = {"kind", "id", "path", "url", "fallback_url", "file"}
ROUTE_KINDS = {
    "hub",
    "downloads",
    "catalog",
    "checksum",
    "web-manifest",
    "slot",
    "artifact",
    "manifest",
    "artifact-alias",
}
RESOURCE_KEYS = {
    "id",
    "label",
    "media_type",
    "path",
    "route",
    "bytes",
    "sha256",
    "url",
    "fallback_url",
    "aliases",
    "extensions",
}
ALIAS_KEYS = {"path", "url", "fallback_url"}
LANDING_KEYS = {"mode", "resource_id"}
SLOT_SOURCE_KEYS = {"repository", "revision", "path"}
REFERENCE_KEYS = {
    "label",
    "url",
    "fallback_url",
    "resource_id",
    "media_type",
    "path",
    "bytes",
    "sha256",
}
IDENTIFIER_KEYS = {"scheme", "value", "url"}
RELEASE_KEYS = {"url", "published_at"}
ACCESSIBILITY_KEYS = {"summary", "features", "conformance", "report"}
SLOT_KEYS = {
    "accessibility",
    "artifacts",
    "extensions",
    "fallback_url",
    "id",
    "identifiers",
    "kind",
    "landing",
    "manifests",
    "order",
    "preview",
    "provenance",
    "release",
    "route",
    "source",
    "status",
    "summary",
    "superseded_by",
    "title",
    "url",
    "version",
    "withdrawal_notice",
}
MEDIA_TYPE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*$"
)


class ValidationError(ValueError):
    """A publication artifact violates the Relay boundary."""


def summarize_paths(paths: Iterable[str]) -> str:
    """Return a bounded, control-free diagnostic summary of public paths."""

    values = sorted(paths)
    sample = [
        value[:MAX_DIAGNOSTIC_PATH_LENGTH]
        for value in values[:MAX_DIAGNOSTIC_PATHS]
    ]
    suffix = ", ..." if len(values) > len(sample) else ""
    return f"count={len(values)}, sample=[{', '.join(sample)}{suffix}]"


@dataclass(frozen=True)
class ValidationResult:
    """Stable facts proven about one local publication site."""

    canonical_base_url: str
    fallback_base_url: str | None
    source_revision: str
    site_tree_sha256: str
    catalog_sha256: str
    checksum_sha256: str
    catalog_path: str
    checksum_path: str
    routes: tuple[str, ...]
    route_files: tuple[tuple[str, str], ...]
    files: tuple[tuple[str, str], ...]
    file_count: int
    total_bytes: int

    def evidence(self) -> dict[str, Any]:
        """Return deterministic validation evidence without local filesystem paths."""

        return {
            "canonical_base_url": self.canonical_base_url,
            "catalog": {
                "path": self.catalog_path,
                "sha256": self.catalog_sha256,
            },
            "catalog_schema": CATALOG_SCHEMA,
            "checksum_manifest": {
                "path": self.checksum_path,
                "sha256": self.checksum_sha256,
            },
            "fallback_base_url": self.fallback_base_url,
            "file_count": self.file_count,
            "route_count": len(self.routes),
            "routes": list(self.routes),
            "schema": EVIDENCE_SCHEMA,
            "site_tree_sha256": self.site_tree_sha256,
            "source_revision": self.source_revision,
            "status": "passed",
            "total_bytes": self.total_bytes,
        }


def sha256_bytes(value: bytes) -> str:
    """Return the lowercase SHA-256 digest of bytes."""

    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    """Stream a file into SHA-256."""

    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_vendored_contract() -> None:
    """Fail closed if the immutable Beacon v1 schema package drifts."""

    if (
        not PUBLIC_SCHEMA_PATH.is_file()
        or sha256_file(PUBLIC_SCHEMA_PATH) != PUBLIC_SCHEMA_SHA256
    ):
        raise ValidationError("vendored Beacon publication-site contract is missing or changed")


def load_object(path: Path, label: str) -> dict[str, Any]:
    """Load a JSON object with a bounded, readable failure."""

    try:
        def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, child in pairs:
                if key in result:
                    raise ValidationError(f"{label} contains a duplicate key")
                result[key] = child
            return result

        def reject_constant(_: str) -> None:
            raise ValidationError(f"{label} contains a non-finite JSON number")

        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=strict_object,
            parse_constant=reject_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValidationError(f"{label} is not valid UTF-8 JSON: {error}") from error
    if not isinstance(value, dict):
        raise ValidationError(f"{label} must contain a JSON object")
    return value


def _schema_type_matches(value: Any, expected: str) -> bool:
    """Implement the JSON types used by Beacon's frozen public schema."""

    return {
        "array": lambda item: isinstance(item, list),
        "boolean": lambda item: isinstance(item, bool),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "null": lambda item: item is None,
        "number": lambda item: isinstance(item, (int, float))
        and not isinstance(item, bool),
        "object": lambda item: isinstance(item, dict),
        "string": lambda item: isinstance(item, str),
    }.get(expected, lambda _item: False)(value)


def _schema_ref(root: dict[str, Any], reference: str) -> dict[str, Any]:
    """Resolve only local JSON pointers from the vendored schema."""

    if not reference.startswith("#/"):
        raise ValidationError("vendored schema uses an external reference")
    current: Any = root
    for token in reference[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or token not in current:
            raise ValidationError("vendored schema contains an unresolved reference")
        current = current[token]
    if not isinstance(current, dict):
        raise ValidationError("vendored schema reference is not an object")
    return current


def _schema_passes(
    value: Any,
    schema: dict[str, Any],
    root: dict[str, Any],
) -> bool:
    """Return whether one value matches one supported subschema."""

    try:
        _validate_schema_value(value, schema, root, "site catalog")
    except ValidationError:
        return False
    return True


def _validate_schema_value(
    value: Any,
    schema: dict[str, Any],
    root: dict[str, Any],
    field: str,
) -> None:
    """Validate the exact stdlib-only JSON Schema subset used by Beacon."""

    if "$ref" in schema:
        _validate_schema_value(value, _schema_ref(root, schema["$ref"]), root, field)
        return
    for subschema in schema.get("allOf", []):
        _validate_schema_value(value, subschema, root, field)
    if "anyOf" in schema and not any(
        _schema_passes(value, subschema, root) for subschema in schema["anyOf"]
    ):
        raise ValidationError(f"{field} does not match an allowed schema shape")
    if "oneOf" in schema:
        matches = sum(
            _schema_passes(value, subschema, root) for subschema in schema["oneOf"]
        )
        if matches != 1:
            raise ValidationError(f"{field} must match exactly one schema shape")
    if "not" in schema and _schema_passes(value, schema["not"], root):
        raise ValidationError(f"{field} matches a forbidden schema shape")
    if "if" in schema and _schema_passes(value, schema["if"], root):
        if "then" in schema:
            _validate_schema_value(value, schema["then"], root, field)
    elif "else" in schema:
        _validate_schema_value(value, schema["else"], root, field)

    expected = schema.get("type")
    if expected is not None:
        expected_types = [expected] if isinstance(expected, str) else expected
        if not isinstance(expected_types, list) or not any(
            isinstance(item, str) and _schema_type_matches(value, item)
            for item in expected_types
        ):
            raise ValidationError(f"{field} has the wrong JSON type")
    if "const" in schema and value != schema["const"]:
        raise ValidationError(f"{field} does not match the schema constant")
    if "enum" in schema and value not in schema["enum"]:
        raise ValidationError(f"{field} is not one of the allowed values")

    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            raise ValidationError(f"{field} is shorter than the schema minimum")
        pattern = schema.get("pattern")
        if pattern is not None and re.search(pattern, value) is None:
            raise ValidationError(f"{field} does not match its schema pattern")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise ValidationError(f"{field} is below the schema minimum")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise ValidationError(f"{field} has too few items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise ValidationError(f"{field} has too many items")
        if schema.get("uniqueItems"):
            canonical = [
                json.dumps(item, sort_keys=True, allow_nan=False) for item in value
            ]
            if len(canonical) != len(set(canonical)):
                raise ValidationError(f"{field} must contain unique items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                _validate_schema_value(item, item_schema, root, f"{field}[{index}]")
    if isinstance(value, dict):
        required = schema.get("required", [])
        missing = [key for key in required if key not in value]
        if missing:
            raise ValidationError(f"{field} is missing required schema fields")
        property_names = schema.get("propertyNames")
        if isinstance(property_names, dict):
            for key in value:
                _validate_schema_value(key, property_names, root, f"{field} key")
        properties = schema.get("properties", {})
        for key, child in value.items():
            if key in properties:
                _validate_schema_value(child, properties[key], root, f"{field}.{key}")
            elif schema.get("additionalProperties") is False:
                raise ValidationError(f"{field} has an unsupported schema field")
            elif isinstance(schema.get("additionalProperties"), dict):
                _validate_schema_value(
                    child,
                    schema["additionalProperties"],
                    root,
                    f"{field}.{key}",
                )


def validate_public_schema(value: dict[str, Any]) -> None:
    """Apply Beacon's exact frozen public schema before Relay semantics."""

    schema = load_object(PUBLIC_SCHEMA_PATH, "vendored Beacon schema")
    try:
        _validate_schema_value(value, schema, schema, "site catalog")
    except RecursionError as error:
        raise ValidationError("site catalog exceeds the schema nesting limit") from error


def require_string(value: Any, label: str) -> str:
    """Return one non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be a non-empty string")
    return value


def require_identifier(value: Any, label: str) -> str:
    """Return one lowercase kebab-case public identifier."""

    identifier = require_string(value, label)
    if not IDENTIFIER.fullmatch(identifier):
        raise ValidationError(f"{label} must be lowercase kebab-case")
    return identifier


def validate_extensions(value: Any, label: str) -> None:
    """Require a namespaced extension object with safe top-level keys."""

    if not isinstance(value, dict):
        raise ValidationError(f"{label} must be an object")
    if any(not isinstance(key, str) or not IDENTIFIER.fullmatch(key) for key in value):
        raise ValidationError(f"{label} keys must be lowercase kebab-case")


def require_known_keys(
    value: dict[str, Any],
    *,
    allowed: set[str],
    required: set[str],
    label: str,
) -> None:
    """Require the exact key surface of the versioned public contract."""

    missing = sorted(required - set(value))
    unknown = sorted(set(value) - allowed)
    if missing:
        raise ValidationError(f"{label} is missing required fields: {missing}")
    if unknown:
        raise ValidationError(f"{label} contains unsupported fields")


def reject_reserved_extension_keys(value: Any, label: str) -> None:
    """Prevent nested extensions from bypassing planned-slot honesty rules."""

    pending = [value]
    while pending:
        current = pending.pop()
        if isinstance(current, dict):
            for key, child in current.items():
                normalized = key.lower().replace("-", "_")
                if normalized in PLANNED_PUBLICATION_FIELDS:
                    raise ValidationError(
                        f"{label} cannot carry a reserved publication key"
                    )
                pending.append(child)
        elif isinstance(current, list):
            pending.extend(current)


def relative_path(value: Any, label: str, *, allow_root: bool = False) -> str:
    """Normalize a portable site-relative POSIX path."""

    if not isinstance(value, str):
        raise ValidationError(f"{label} must be a string")
    if value == "" and allow_root:
        return value
    if not value or "\\" in value or "\x00" in value or "%" in value:
        raise ValidationError(f"{label} is not a safe portable path")
    if value.startswith("/") or "//" in value:
        raise ValidationError(f"{label} must be relative and normalized")
    trailing_slash = value.endswith("/")
    parts = PurePosixPath(value).parts
    if not parts or any(
        part in {"", ".", ".."} or not SAFE_SEGMENT.fullmatch(part)
        for part in parts
    ):
        raise ValidationError(f"{label} is not a safe portable path")
    normalized = PurePosixPath(*parts).as_posix()
    if trailing_slash:
        normalized += "/"
    if normalized != value:
        raise ValidationError(f"{label} must be normalized")
    return normalized


def normalize_base_url(value: Any, label: str) -> str:
    """Require a clean HTTPS base URL ending in one slash."""

    url = require_string(value, label)
    if any(ord(character) < 33 or ord(character) == 127 for character in url):
        raise ValidationError(f"{label} contains whitespace or control characters")
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as error:
        raise ValidationError(f"{label} is malformed") from error
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValidationError(f"{label} must be a clean HTTPS URL")
    if "\\" in parsed.path or "%" in parsed.path or "//" in parsed.path:
        raise ValidationError(f"{label} contains an ambiguous path")
    segments = [segment for segment in parsed.path.split("/") if segment]
    if any(
        segment in {".", ".."} or not SAFE_SEGMENT.fullmatch(segment)
        for segment in segments
    ):
        raise ValidationError(f"{label} contains an unsafe path segment")
    path = "/" + "/".join(segments) if segments else "/"
    if not path.endswith("/"):
        path += "/"
    host = parsed.hostname.lower() if parsed.hostname else ""
    if port not in {None, 443}:
        raise ValidationError(f"{label} must use the standard HTTPS port")
    if host == "localhost" or host.endswith(".localhost"):
        raise ValidationError(f"{label} must use a public DNS hostname")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValidationError(f"{label} cannot use an IP literal")
    try:
        host.encode("ascii")
    except UnicodeEncodeError as error:
        raise ValidationError(f"{label} hostname must be ASCII/punycode") from error
    labels = host.split(".")
    if (
        len(labels) < 2
        or len(host) > 253
        or any(
            len(host_label) > 63
            or not re.fullmatch(
                r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", host_label
            )
            for host_label in labels
        )
    ):
        raise ValidationError(f"{label} must use a valid public DNS hostname")
    normalized = urlunsplit(("https", host, path, "", ""))
    if url != normalized:
        raise ValidationError(f"{label} must use its normalized HTTPS form")
    return normalized


def validate_https_url(value: Any, label: str) -> str:
    """Require a standard-port HTTPS URL on a public-looking DNS host."""

    url = require_string(value, label)
    if any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in url):
        raise ValidationError(f"{label} contains whitespace or control characters")
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as error:
        raise ValidationError(f"{label} is malformed") from error
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
    ):
        raise ValidationError(f"{label} must be a public standard-port HTTPS URL")
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise ValidationError(f"{label} must use a public DNS hostname")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValidationError(f"{label} cannot use an IP literal")
    labels = host.split(".")
    if (
        len(labels) < 2
        or len(host) > 253
        or any(
            len(host_label) > 63
            or not re.fullmatch(
                r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", host_label
            )
            for host_label in labels
        )
    ):
        raise ValidationError(f"{label} must use a valid public DNS hostname")
    return url


def validate_public_reference(
    value: Any,
    *,
    label: str,
    resources: dict[str, dict[str, Any]],
) -> None:
    """Validate an external or byte-bound slot reference."""

    if not isinstance(value, dict):
        raise ValidationError(f"{label} must be an object")
    require_known_keys(
        value,
        allowed=REFERENCE_KEYS,
        required={"label", "url"},
        label=label,
    )
    require_string(value.get("label"), f"{label}.label")
    validate_https_url(value.get("url"), f"{label}.url")
    if "media_type" in value and not MEDIA_TYPE.fullmatch(
        require_string(value["media_type"], f"{label}.media_type")
    ):
        raise ValidationError(f"{label}.media_type is invalid")
    resource_id = value.get("resource_id")
    if resource_id is None:
        forbidden = {"fallback_url", "path", "bytes", "sha256"} & set(value)
        if forbidden:
            raise ValidationError(f"{label} external reference carries resource fields")
        return
    identifier = require_identifier(resource_id, f"{label}.resource_id")
    resource = resources.get(identifier)
    if resource is None:
        raise ValidationError(f"{label} references an unknown resource")
    required_resource_fields = {
        "fallback_url",
        "media_type",
        "path",
        "bytes",
        "sha256",
    }
    if not required_resource_fields.issubset(value):
        raise ValidationError(f"{label} resource reference is incomplete")
    for field in ("url", *sorted(required_resource_fields)):
        if value.get(field) != resource.get(field):
            raise ValidationError(f"{label} does not match its declared resource")


def route_entrypoint(path: str) -> str:
    """Map a public route to the exact file GitHub Pages must serve."""

    if not path:
        return "index.html"
    return f"{path}index.html" if path.endswith("/") else path


def resolve_site_directory(workspace: Path, value: str) -> Path:
    """Resolve one owned output directory without accepting broad/protected roots."""

    relative = relative_path(value, "site-directory")
    first = PurePosixPath(relative).parts[0].lower()
    if first in PROTECTED_SITE_ROOTS:
        raise ValidationError(f"site-directory uses a protected root: {first}")
    workspace = workspace.resolve()
    site = workspace.joinpath(*PurePosixPath(relative).parts)
    try:
        resolved = site.resolve(strict=True)
    except OSError as error:
        raise ValidationError(f"site-directory does not exist: {relative}") from error
    if resolved == workspace or workspace not in resolved.parents:
        raise ValidationError("site-directory must be a child of the workspace")
    if not resolved.is_dir():
        raise ValidationError("site-directory must be a directory")
    current = workspace
    for part in PurePosixPath(relative).parts:
        current /= part
        if current.is_symlink():
            raise ValidationError(f"site-directory has a symbolic-link ancestor: {relative}")
    return resolved


def resolve_workspace_output(workspace: Path, value: str, *, site: Path) -> Path:
    """Resolve a narrow evidence file outside protected and public roots."""

    relative = relative_path(value, "evidence-output")
    first = PurePosixPath(relative).parts[0].lower()
    if first in PROTECTED_SITE_ROOTS:
        raise ValidationError(f"evidence-output uses a protected root: {first}")
    workspace = workspace.resolve()
    output = workspace.joinpath(*PurePosixPath(relative).parts)
    if output == site or site in output.parents:
        raise ValidationError("evidence-output must be outside the public site")
    current = workspace
    for part in PurePosixPath(relative).parts:
        current /= part
        if current.is_symlink():
            raise ValidationError("evidence-output cannot traverse a symbolic link")
    if output.exists() and (output.is_symlink() or not output.is_file()):
        raise ValidationError("evidence-output must identify a regular file")
    return output


def inventory_files(site: Path) -> dict[str, Path]:
    """Return all regular site files and reject links or special entries."""

    files: dict[str, Path] = {}
    directories = [site]
    entry_count = 0
    while directories:
        directory = directories.pop()
        try:
            entries = []
            with os.scandir(directory) as scanned:
                for entry in scanned:
                    entries.append(entry)
                    entry_count += 1
                    if entry_count > MAX_SITE_FILES * 2:
                        raise ValidationError("publication site exceeds the entry-count limit")
            entries.sort(key=lambda entry: entry.name)
        except OSError as error:
            raise ValidationError("publication site cannot be inventoried") from error
        for entry in reversed(entries):
            path = Path(entry.path)
            relative = path.relative_to(site).as_posix()
            if entry.is_symlink():
                raise ValidationError(
                    f"publication site cannot contain symbolic links: {relative}"
                )
            if entry.is_dir(follow_symlinks=False):
                directories.append(path)
                continue
            if not entry.is_file(follow_symlinks=False):
                raise ValidationError(
                    f"publication site contains a special file: {relative}"
                )
            relative_path(relative, f"site file {relative}")
            size = entry.stat(follow_symlinks=False).st_size
            if size > MAX_FILE_BYTES:
                raise ValidationError(
                    f"publication site file exceeds size limit: {relative}"
                )
            files[relative] = path
            if len(files) > MAX_SITE_FILES:
                raise ValidationError("publication site exceeds the file-count limit")
    if not files:
        raise ValidationError("publication site is empty")
    if "index.html" not in files:
        raise ValidationError("publication site is missing index.html")
    if sum(path.stat().st_size for path in files.values()) > MAX_SITE_BYTES:
        raise ValidationError("publication site exceeds the total-byte limit")
    return files


def parse_required_routes(value: str) -> tuple[str, ...]:
    """Parse the workflow-safe JSON array used for required public routes."""

    try:
        routes = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValidationError("required-routes must be a JSON array of strings") from error
    if not isinstance(routes, list) or any(not isinstance(item, str) for item in routes):
        raise ValidationError("required-routes must be a JSON array of strings")
    normalized = tuple(relative_path(item, "required route", allow_root=True) for item in routes)
    if len(normalized) != len(set(normalized)):
        raise ValidationError("required-routes contains duplicates")
    return normalized


def parse_checksums(
    site: Path,
    checksum_path: str,
    files: dict[str, Path],
) -> tuple[tuple[str, str], ...]:
    """Verify a complete, sorted GNU-style SHA-256 inventory."""

    manifest = files.get(checksum_path)
    if manifest is None:
        raise ValidationError(f"checksum manifest is missing: {checksum_path}")
    try:
        text = manifest.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ValidationError("checksum manifest must be UTF-8 text") from error
    if not text.endswith("\n"):
        raise ValidationError("checksum manifest must end with a newline")
    records: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if match is None:
            raise ValidationError(f"malformed checksum line {line_number}")
        digest, raw_path = match.groups()
        path = relative_path(raw_path, f"checksum line {line_number}")
        if path == checksum_path:
            raise ValidationError("checksum manifest cannot checksum itself")
        if path in seen:
            raise ValidationError(f"duplicate checksum path: {path}")
        seen.add(path)
        records.append((path, digest))
    if [path for path, _ in records] != sorted(path for path, _ in records):
        raise ValidationError("checksum manifest paths must be sorted")
    expected_paths = set(files) - {checksum_path}
    if seen != expected_paths:
        raise ValidationError(
            "checksum inventory is incomplete; "
            f"missing {summarize_paths(expected_paths - seen)}; "
            f"extra {summarize_paths(seen - expected_paths)}"
        )
    for path, expected in records:
        observed = sha256_file(files[path])
        if observed != expected:
            raise ValidationError(f"checksum mismatch: {path}")
    return tuple(records)


def validate_resource(
    resource: Any,
    *,
    label: str,
    site: Path,
    canonical_base_url: str,
    fallback_base_url: str | None,
    claimed_paths: set[str],
) -> tuple[str, str, str, tuple[str, ...]]:
    """Validate one artifact or manifest and all of its public aliases."""

    if not isinstance(resource, dict):
        raise ValidationError(f"{label} must be an object")
    require_known_keys(
        resource,
        allowed=RESOURCE_KEYS,
        required=RESOURCE_KEYS - {"extensions"},
        label=label,
    )
    path = relative_path(resource.get("path"), f"{label}.path")
    target = site.joinpath(*PurePosixPath(path).parts)
    if not target.is_file() or target.stat().st_size <= 0:
        raise ValidationError(f"{label} is missing or empty: {path}")
    if path in claimed_paths:
        raise ValidationError(f"duplicate publication resource path: {path}")
    claimed_paths.add(path)
    size = resource.get("bytes")
    if not isinstance(size, int) or isinstance(size, bool) or size != target.stat().st_size:
        raise ValidationError(f"{label}.bytes does not match {path}")
    digest = resource.get("sha256")
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        raise ValidationError(f"{label}.sha256 is invalid")
    if sha256_file(target) != digest:
        raise ValidationError(f"{label}.sha256 does not match {path}")
    identifier = require_identifier(resource.get("id"), f"{label}.id")
    require_string(resource.get("label"), f"{label}.label")
    media_type = require_string(resource.get("media_type"), f"{label}.media_type")
    if not MEDIA_TYPE.fullmatch(media_type):
        raise ValidationError(f"{label}.media_type is invalid")
    if "extensions" in resource:
        validate_extensions(resource["extensions"], f"{label}.extensions")
    route = relative_path(resource.get("route"), f"{label}.route")
    allowed_routes = {path}
    if path.endswith("/index.html"):
        allowed_routes.add(path[: -len("index.html")])
    if route not in allowed_routes:
        raise ValidationError(
            f"{label}.route must match its file path or index-page directory"
        )
    expected_url = urljoin(canonical_base_url, route)
    if resource.get("url") != expected_url:
        raise ValidationError(f"{label}.url does not match its canonical path")
    expected_fallback = urljoin(fallback_base_url, route) if fallback_base_url else None
    if resource.get("fallback_url") != expected_fallback:
        raise ValidationError(f"{label}.fallback_url does not match its path")

    aliases = resource.get("aliases", [])
    if not isinstance(aliases, list):
        raise ValidationError(f"{label}.aliases must be an array")
    alias_paths: list[str] = []
    for index, alias in enumerate(aliases):
        alias_label = f"{label}.aliases[{index}]"
        if not isinstance(alias, dict):
            raise ValidationError(f"{alias_label} must be an object")
        require_known_keys(
            alias,
            allowed=ALIAS_KEYS,
            required=ALIAS_KEYS,
            label=alias_label,
        )
        alias_path = relative_path(alias.get("path"), f"{alias_label}.path")
        alias_target = site.joinpath(*PurePosixPath(alias_path).parts)
        if not alias_target.is_file() or alias_target.stat().st_size <= 0:
            raise ValidationError(f"{alias_label} is missing or empty: {alias_path}")
        if alias_path in claimed_paths:
            raise ValidationError(f"duplicate publication resource path: {alias_path}")
        claimed_paths.add(alias_path)
        if alias_target.stat().st_size != size or sha256_file(alias_target) != digest:
            raise ValidationError(
                f"{alias_label} bytes do not match canonical resource {path}"
            )
        if alias.get("url") != urljoin(canonical_base_url, alias_path):
            raise ValidationError(f"{alias_label}.url does not match its path")
        alias_fallback = urljoin(fallback_base_url, alias_path) if fallback_base_url else None
        if alias.get("fallback_url") != alias_fallback:
            raise ValidationError(f"{alias_label}.fallback_url does not match its path")
        alias_paths.append(alias_path)
    return identifier, path, route, tuple(alias_paths)


def validate_catalog(
    catalog: dict[str, Any],
    *,
    site: Path,
    expected_base_url: str,
    expected_source_revision: str,
    required_routes: tuple[str, ...],
    catalog_path: str,
    checksum_path: str,
) -> tuple[str, str | None, str, tuple[str, ...], tuple[tuple[str, str], ...]]:
    """Validate Beacon's host-neutral publication-site catalog projection."""

    validate_public_schema(catalog)
    require_known_keys(
        catalog,
        allowed=CATALOG_KEYS,
        required=CATALOG_KEYS - {"extensions"},
        label="site catalog",
    )
    if (
        catalog.get("schema") != CATALOG_SCHEMA
        or catalog.get("schema_version") != "1.0.0"
    ):
        raise ValidationError(f"site catalog must use {CATALOG_SCHEMA}")
    if "extensions" in catalog:
        validate_extensions(catalog["extensions"], "site catalog.extensions")
    source = catalog.get("source")
    if not isinstance(source, dict):
        raise ValidationError("site catalog source must be an object")
    require_known_keys(
        source,
        allowed=SOURCE_KEYS,
        required={"catalog_sha256", "revision"},
        label="site catalog source",
    )
    revision = source.get("revision")
    if revision != expected_source_revision or not isinstance(revision, str):
        raise ValidationError("site catalog source revision does not match the request")
    source_catalog_digest = source.get("catalog_sha256")
    if not isinstance(source_catalog_digest, str) or not SHA256.fullmatch(
        source_catalog_digest
    ):
        raise ValidationError("site catalog source.catalog_sha256 is invalid")
    if "repository" in source:
        validate_https_url(source["repository"], "site catalog source.repository")

    site_record = catalog.get("site")
    if not isinstance(site_record, dict):
        raise ValidationError("site catalog site must be an object")
    require_known_keys(
        site_record,
        allowed=SITE_KEYS,
        required=SITE_KEYS - {"repository", "extensions"},
        label="site catalog site",
    )
    require_identifier(site_record.get("id"), "site.id")
    for field in ("title", "description", "language", "publisher", "theme"):
        require_string(site_record.get(field), f"site.{field}")
    if not re.fullmatch(
        r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*", site_record["language"]
    ):
        raise ValidationError("site.language is invalid")
    if site_record.get("theme") not in {"neutral", "egohygiene"}:
        raise ValidationError("site.theme is invalid")
    if "repository" in site_record:
        validate_https_url(site_record["repository"], "site.repository")
    if "extensions" in site_record:
        validate_extensions(site_record["extensions"], "site.extensions")
    canonical = normalize_base_url(
        site_record.get("canonical_base_url"), "site.canonical_base_url"
    )
    if canonical != expected_base_url:
        raise ValidationError("site canonical base URL does not match the request")
    fallback_value = site_record.get("fallback_base_url")
    fallback = (
        normalize_base_url(fallback_value, "site.fallback_base_url")
        if fallback_value is not None
        else None
    )
    if fallback is not None and fallback == canonical:
        raise ValidationError("fallback base URL cannot equal the canonical base URL")
    if site_record.get("stage") not in {"draft", "published", "archived"}:
        raise ValidationError("site.stage is invalid")
    if site_record.get("revision") != revision:
        raise ValidationError("site and source revisions do not match")

    routes = catalog.get("routes")
    if not isinstance(routes, list) or not routes:
        raise ValidationError("site catalog routes must be a non-empty array")
    route_paths: list[str] = []
    route_by_path: dict[str, dict[str, Any]] = {}
    route_file_by_path: dict[str, str] = {}
    routes_by_id: dict[str, list[dict[str, Any]]] = {}
    entrypoints: set[str] = set()
    for index, route in enumerate(routes):
        label = f"routes[{index}]"
        if not isinstance(route, dict):
            raise ValidationError(f"{label} must be an object")
        require_known_keys(
            route,
            allowed=ROUTE_KEYS,
            required=ROUTE_KEYS - {"file"},
            label=label,
        )
        path = relative_path(route.get("path"), f"{label}.path", allow_root=True)
        route_id = require_string(route.get("id"), f"{label}.id")
        if path in route_paths:
            raise ValidationError(f"duplicate route path: {path}")
        raw_file = route.get("file")
        entrypoint = (
            relative_path(raw_file, f"{label}.file")
            if raw_file is not None
            else route_entrypoint(path)
        )
        if entrypoint.endswith("/"):
            raise ValidationError(f"{label}.file must identify a file")
        if entrypoint in entrypoints:
            raise ValidationError(f"colliding route entrypoint: {entrypoint}")
        entrypoints.add(entrypoint)
        target = site.joinpath(*PurePosixPath(entrypoint).parts)
        if not target.is_file() or target.stat().st_size <= 0:
            raise ValidationError(f"declared route is missing or empty: {path}")
        if route.get("url") != urljoin(canonical, path):
            raise ValidationError(f"{label}.url does not match its canonical route")
        expected_fallback = urljoin(fallback, path) if fallback else None
        if route.get("fallback_url") != expected_fallback:
            raise ValidationError(f"{label}.fallback_url does not match its route")
        kind = require_string(route.get("kind"), f"{label}.kind")
        if kind not in ROUTE_KINDS:
            raise ValidationError(f"{label}.kind is unsupported: {kind}")
        route_paths.append(path)
        route_by_path[path] = route
        route_file_by_path[path] = entrypoint
        routes_by_id.setdefault(route_id, []).append(route)

    if routes != sorted(
        routes,
        key=lambda item: (item["path"], item["kind"], item["id"]),
    ):
        raise ValidationError("site catalog routes must be sorted by path, kind, and id")

    required_contract_routes = {
        "": ("hub", "home", "index.html"),
        "downloads/": ("downloads", "downloads", "downloads/index.html"),
        catalog_path: ("catalog", "site-json", catalog_path),
        checksum_path: ("checksum", "sha256sums", checksum_path),
        "manifest.webmanifest": (
            "web-manifest",
            "web-manifest",
            "manifest.webmanifest",
        ),
    }
    for path, (kind, route_id, physical) in required_contract_routes.items():
        route = route_by_path.get(path)
        if (
            route is None
            or route.get("kind") != kind
            or route.get("id") != route_id
            or route_file_by_path.get(path) != physical
        ):
            raise ValidationError(
                f"site catalog is missing required contract route: {path or '/'}"
            )

    for route_id, matching in routes_by_id.items():
        kinds = [route.get("kind") for route in matching]
        has_alias = "artifact-alias" in kinds
        if has_alias and (
            kinds.count("artifact") != 1
            or any(kind not in {"artifact", "artifact-alias"} for kind in kinds)
        ):
            raise ValidationError(f"duplicate incompatible route id: {route_id}")
        if len(matching) > 1 and not has_alias:
            raise ValidationError(f"duplicate incompatible route id: {route_id}")

    missing_routes = sorted(set(required_routes) - set(route_paths))
    if missing_routes:
        raise ValidationError(
            "site catalog is missing required routes: "
            f"{summarize_paths(missing_routes)}"
        )

    slots = catalog.get("slots")
    if not isinstance(slots, list):
        raise ValidationError("site catalog slots must be an array")
    slot_ids: set[str] = set()
    slot_order: list[tuple[int, str]] = []
    claimed_paths: set[str] = set()
    claimed_publication_routes: set[str] = set()
    claimed_slot_routes: set[str] = set()
    for index, slot in enumerate(slots):
        label = f"slots[{index}]"
        if not isinstance(slot, dict):
            raise ValidationError(f"{label} must be an object")
        require_known_keys(
            slot,
            allowed=SLOT_KEYS,
            required={
                "fallback_url",
                "id",
                "kind",
                "landing",
                "order",
                "route",
                "status",
                "summary",
                "title",
                "url",
            },
            label=label,
        )
        slot_id = require_identifier(slot.get("id"), f"{label}.id")
        if slot_id in slot_ids:
            raise ValidationError(f"duplicate slot id: {slot_id}")
        slot_ids.add(slot_id)
        status = slot.get("status")
        if status not in SLOT_STATUSES:
            raise ValidationError(f"{label}.status is invalid: {status}")
        slot_route = relative_path(slot.get("route"), f"{label}.route", allow_root=True)
        if not slot_route or not slot_route.endswith("/"):
            raise ValidationError(f"{label}.route must be a non-root page route")
        if slot_route not in route_paths:
            raise ValidationError(f"{label}.route is not declared in routes")
        claimed_slot_routes.add(slot_route)
        slot_route_record = route_by_path[slot_route]
        if (
            slot_route_record.get("kind") != "slot"
            or slot_route_record.get("id") != slot_id
            or route_file_by_path.get(slot_route) != f"{slot_route}index.html"
        ):
            raise ValidationError(f"{label}.route is not a compatible slot route")
        if slot.get("url") != urljoin(canonical, slot_route):
            raise ValidationError(f"{label}.url does not match its route")
        expected_fallback = urljoin(fallback, slot_route) if fallback else None
        if slot.get("fallback_url") != expected_fallback:
            raise ValidationError(f"{label}.fallback_url does not match its route")
        require_identifier(slot.get("kind"), f"{label}.kind")
        require_string(slot.get("title"), f"{label}.title")
        require_string(slot.get("summary"), f"{label}.summary")
        for optional_text_field in (
            "version",
            "superseded_by",
            "withdrawal_notice",
        ):
            if optional_text_field in slot:
                require_string(
                    slot[optional_text_field],
                    f"{label}.{optional_text_field}",
                )
        if "extensions" in slot:
            validate_extensions(slot["extensions"], f"{label}.extensions")
        if "source" in slot:
            source_record = slot["source"]
            if not isinstance(source_record, dict):
                raise ValidationError(f"{label}.source must be an object")
            require_known_keys(
                source_record,
                allowed=SLOT_SOURCE_KEYS,
                required={"repository", "revision"},
                label=f"{label}.source",
            )
            validate_https_url(
                source_record.get("repository"), f"{label}.source.repository"
            )
            source_revision = require_string(
                source_record.get("revision"), f"{label}.source.revision"
            )
            if source_revision != "WORKING_TREE" and not REVISION.fullmatch(
                source_revision
            ):
                raise ValidationError(f"{label}.source.revision is invalid")
            if "path" in source_record:
                relative_path(source_record["path"], f"{label}.source.path")
        order = slot.get("order")
        if not isinstance(order, int) or isinstance(order, bool):
            raise ValidationError(f"{label}.order must be an integer")
        slot_order.append((order, slot_id))
        artifacts = slot.get("artifacts", [])
        manifests = slot.get("manifests", [])
        if not isinstance(artifacts, list) or not isinstance(manifests, list):
            raise ValidationError(f"{label} artifacts and manifests must be arrays")
        if status == "planned":
            dishonest = sorted(
                field
                for field in PLANNED_PUBLICATION_FIELDS
                if field in slot
            )
            if dishonest:
                raise ValidationError(
                    f"planned slot {slot_id} declares publication fields: {dishonest}"
                )
            if "extensions" in slot:
                reject_reserved_extension_keys(slot["extensions"], f"{label}.extensions")
        elif status in {"draft", "withdrawn"} and (
            "artifacts" in slot or "manifests" in slot
        ):
            raise ValidationError(f"{status} slot {slot_id} cannot publish resources")
        elif status == "available" and (
            not artifacts
            or not isinstance(slot.get("version"), str)
            or not slot["version"].strip()
            or not isinstance(slot.get("source"), dict)
        ):
            raise ValidationError(
                f"available slot {slot_id} must declare source, version, and artifact"
            )
        elif status == "superseded":
            require_string(slot.get("superseded_by"), f"{label}.superseded_by")
        if status == "withdrawn":
            require_string(slot.get("withdrawal_notice"), f"{label}.withdrawal_notice")
        if status == "available":
            source_record = slot["source"]
            if not isinstance(source_record.get("revision"), str) or not REVISION.fullmatch(
                source_record["revision"]
            ):
                raise ValidationError(f"{label}.source.revision must be pinned")
        landing = slot.get("landing")
        if not isinstance(landing, dict) or landing.get("mode") not in {
            "generated",
            "resource",
        }:
            raise ValidationError(f"{label}.landing is invalid")
        mode = landing.get("mode")
        require_known_keys(
            landing,
            allowed=LANDING_KEYS,
            required={"mode", "resource_id"} if mode == "resource" else {"mode"},
            label=f"{label}.landing",
        )
        if mode == "generated" and "resource_id" in landing:
            raise ValidationError(
                f"{label}.landing.resource_id is only valid for resource mode"
            )
        landing_matched = mode == "generated"
        slot_resource_ids: set[str] = set()
        slot_resources: dict[str, dict[str, Any]] = {}
        for family, resources in (("artifacts", artifacts), ("manifests", manifests)):
            for resource_index, resource in enumerate(resources):
                resource_id, resource_path, resource_route, aliases = validate_resource(
                    resource,
                    label=f"{label}.{family}[{resource_index}]",
                    site=site,
                    canonical_base_url=canonical,
                    fallback_base_url=fallback,
                    claimed_paths=claimed_paths,
                )
                if resource_id in slot_resource_ids:
                    raise ValidationError(
                        f"{label} repeats resource id {resource_id}"
                    )
                slot_resource_ids.add(resource_id)
                slot_resources[resource_id] = resource
                expected_kind = family[:-1]
                route = route_by_path.get(resource_route)
                expected_id = f"{slot_id}:{resource_id}"
                landing_owner = (
                    resource_route == slot_route
                    and landing.get("mode") == "resource"
                    and landing.get("resource_id") == resource_id
                )
                if landing_owner:
                    landing_matched = True
                    if aliases:
                        raise ValidationError(
                            f"{label}.landing resource cannot declare aliases"
                        )
                    if resource.get("media_type") != "text/html":
                        raise ValidationError(f"{label}.landing resource must use text/html")
                    if resource_path != f"{slot_route}index.html":
                        raise ValidationError(
                            f"{label}.landing resource must own its slot index"
                        )
                compatible = route is not None and route_file_by_path.get(
                    resource_route
                ) == resource_path
                if landing_owner:
                    compatible = compatible and route.get("kind") == "slot" and route.get(
                        "id"
                    ) == slot_id
                else:
                    compatible = compatible and route.get("kind") == expected_kind and route.get(
                        "id"
                    ) == expected_id
                if not compatible:
                    raise ValidationError(
                        f"{label}.{family}[{resource_index}] has no compatible declared route"
                    )
                claimed_publication_routes.add(resource_route)
                for alias_path in aliases:
                    if len(PurePosixPath(alias_path).parts) != 1:
                        raise ValidationError(
                            f"{label}.{family}[{resource_index}] alias must be at site root"
                        )
                    alias_route = route_by_path.get(alias_path)
                    if (
                        alias_route is None
                        or alias_route.get("kind") != "artifact-alias"
                        or alias_route.get("id") != expected_id
                        or route_file_by_path.get(alias_path) != alias_path
                    ):
                        raise ValidationError(
                            f"{label}.{family}[{resource_index}] alias has no compatible route"
                        )
                    claimed_publication_routes.add(alias_path)
        if not landing_matched:
            raise ValidationError(f"{label}.landing references an unknown resource")
        identifiers = slot.get("identifiers", [])
        if not isinstance(identifiers, list):
            raise ValidationError(f"{label}.identifiers must be an array")
        identifier_values: set[tuple[str, str]] = set()
        for identifier_index, publication_identifier in enumerate(identifiers):
            identifier_label = f"{label}.identifiers[{identifier_index}]"
            if not isinstance(publication_identifier, dict):
                raise ValidationError(f"{identifier_label} must be an object")
            require_known_keys(
                publication_identifier,
                allowed=IDENTIFIER_KEYS,
                required={"scheme", "value"},
                label=identifier_label,
            )
            scheme = require_identifier(
                publication_identifier.get("scheme"), f"{identifier_label}.scheme"
            )
            value = require_string(
                publication_identifier.get("value"), f"{identifier_label}.value"
            )
            if (scheme, value) in identifier_values:
                raise ValidationError(f"{label}.identifiers contains duplicates")
            identifier_values.add((scheme, value))
            if "url" in publication_identifier:
                validate_https_url(
                    publication_identifier["url"], f"{identifier_label}.url"
                )
        if "release" in slot:
            release = slot["release"]
            if not isinstance(release, dict):
                raise ValidationError(f"{label}.release must be an object")
            require_known_keys(
                release,
                allowed=RELEASE_KEYS,
                required={"url"},
                label=f"{label}.release",
            )
            validate_https_url(release.get("url"), f"{label}.release.url")
            if "published_at" in release and not re.fullmatch(
                r"\d{4}-\d{2}-\d{2}",
                require_string(release["published_at"], f"{label}.release.published_at"),
            ):
                raise ValidationError(f"{label}.release.published_at is invalid")
        if "preview" in slot:
            validate_public_reference(
                slot["preview"], label=f"{label}.preview", resources=slot_resources
            )
        provenance = slot.get("provenance", [])
        if not isinstance(provenance, list):
            raise ValidationError(f"{label}.provenance must be an array")
        for reference_index, reference in enumerate(provenance):
            validate_public_reference(
                reference,
                label=f"{label}.provenance[{reference_index}]",
                resources=slot_resources,
            )
        if "accessibility" in slot:
            accessibility = slot["accessibility"]
            if not isinstance(accessibility, dict):
                raise ValidationError(f"{label}.accessibility must be an object")
            require_known_keys(
                accessibility,
                allowed=ACCESSIBILITY_KEYS,
                required={"summary", "features"},
                label=f"{label}.accessibility",
            )
            require_string(
                accessibility.get("summary"), f"{label}.accessibility.summary"
            )
            features = accessibility.get("features")
            if (
                not isinstance(features, list)
                or not features
                or any(not isinstance(feature, str) or not feature.strip() for feature in features)
                or len(features) != len(set(features))
            ):
                raise ValidationError(
                    f"{label}.accessibility.features must be non-empty unique strings"
                )
            if "conformance" in accessibility:
                require_string(
                    accessibility["conformance"],
                    f"{label}.accessibility.conformance",
                )
            if "report" in accessibility:
                validate_public_reference(
                    accessibility["report"],
                    label=f"{label}.accessibility.report",
                    resources=slot_resources,
                )
    if slot_order != sorted(slot_order):
        raise ValidationError("site catalog slots must be sorted by order and id")
    orphan_routes = sorted(
        path
        for path, route in route_by_path.items()
        if route.get("kind") in {"artifact", "manifest", "artifact-alias"}
        and path not in claimed_publication_routes
    )
    if orphan_routes:
        raise ValidationError(
            "site catalog has orphan publication routes: "
            f"{summarize_paths(orphan_routes)}"
        )
    expected_route_paths = (
        set(required_contract_routes)
        | claimed_slot_routes
        | claimed_publication_routes
    )
    unexpected_routes = sorted(set(route_by_path) - expected_route_paths)
    if unexpected_routes:
        raise ValidationError("site catalog contains undeclared extra routes")
    return (
        canonical,
        fallback,
        revision,
        tuple(route_paths),
        tuple((path, route_file_by_path[path]) for path in route_paths),
    )


def validate_publication_site(
    *,
    workspace: Path,
    site_directory: str,
    expected_base_url: str,
    expected_source_revision: str,
    expected_fallback_base_url: str = "",
    required_routes_json: str = "[]",
    catalog_path: str = "site.json",
    checksum_path: str = "SHA256SUMS",
) -> ValidationResult:
    """Validate one caller-built site and return its stable local evidence."""

    validate_vendored_contract()
    canonical = normalize_base_url(expected_base_url, "expected-base-url")
    expected_fallback = (
        normalize_base_url(
            expected_fallback_base_url, "expected-fallback-base-url"
        )
        if expected_fallback_base_url
        else None
    )
    if not REVISION.fullmatch(expected_source_revision):
        raise ValidationError("expected-source-revision must be a full lowercase Git SHA")
    catalog_relative = relative_path(catalog_path, "catalog-path")
    checksum_relative = relative_path(checksum_path, "checksum-path")
    if catalog_relative == checksum_relative:
        raise ValidationError("catalog-path and checksum-path must differ")
    reserved_contract_paths = {
        "downloads/",
        "downloads/index.html",
        "index.html",
        "manifest.webmanifest",
    }
    if (
        catalog_relative in reserved_contract_paths
        or checksum_relative in reserved_contract_paths
    ):
        raise ValidationError(
            "catalog-path and checksum-path cannot replace a core publication route"
        )
    required_routes = parse_required_routes(required_routes_json)
    site = resolve_site_directory(workspace, site_directory)
    files = inventory_files(site)
    catalog_file = files.get(catalog_relative)
    if catalog_file is None:
        raise ValidationError(f"site catalog is missing: {catalog_relative}")
    if catalog_file.stat().st_size > MAX_CATALOG_BYTES:
        raise ValidationError("site catalog exceeds the metadata size limit")
    checksum_file = files.get(checksum_relative)
    if checksum_file is None:
        raise ValidationError(f"checksum manifest is missing: {checksum_relative}")
    if checksum_file.stat().st_size > MAX_CHECKSUM_BYTES:
        raise ValidationError("checksum manifest exceeds the metadata size limit")
    records = parse_checksums(site, checksum_relative, files)
    catalog = load_object(catalog_file, "site catalog")
    observed_canonical, fallback, revision, routes, route_files = validate_catalog(
        catalog,
        site=site,
        expected_base_url=canonical,
        expected_source_revision=expected_source_revision,
        required_routes=required_routes,
        catalog_path=catalog_relative,
        checksum_path=checksum_relative,
    )
    if expected_fallback is not None and fallback != expected_fallback:
        raise ValidationError("site fallback base URL does not match the request")
    return ValidationResult(
        canonical_base_url=observed_canonical,
        fallback_base_url=fallback,
        source_revision=revision,
        site_tree_sha256=sha256_bytes(files[checksum_relative].read_bytes()),
        catalog_sha256=sha256_file(catalog_file),
        checksum_sha256=sha256_file(files[checksum_relative]),
        catalog_path=catalog_relative,
        checksum_path=checksum_relative,
        routes=routes,
        route_files=route_files,
        files=records,
        file_count=len(files),
        total_bytes=sum(path.stat().st_size for path in files.values()),
    )


def write_json(path: Path, value: dict[str, Any]) -> None:
    """Write deterministic JSON, creating only the requested parent directory."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_github_outputs(path: Path, result: ValidationResult) -> None:
    """Append single-line action outputs."""

    with path.open("a", encoding="utf-8") as output:
        output.write(f"canonical-base-url={result.canonical_base_url}\n")
        output.write(f"fallback-base-url={result.fallback_base_url or ''}\n")
        output.write(f"file-count={result.file_count}\n")
        output.write(f"route-count={len(result.routes)}\n")
        output.write(f"site-tree-sha256={result.site_tree_sha256}\n")
        output.write(f"source-revision={result.source_revision}\n")
        output.write(f"total-bytes={result.total_bytes}\n")


def parse_arguments(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    """Parse the standalone validator CLI."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--site-directory", required=True)
    parser.add_argument("--expected-base-url", required=True)
    parser.add_argument("--expected-source-revision", required=True)
    parser.add_argument("--expected-fallback-base-url", default="")
    parser.add_argument("--required-routes", default="[]")
    parser.add_argument("--catalog-path", default="site.json")
    parser.add_argument("--checksum-path", default="SHA256SUMS")
    parser.add_argument("--evidence-output", default="")
    parser.add_argument("--github-output", default="")
    return parser.parse_args(arguments)


def main(arguments: Iterable[str] | None = None) -> int:
    """Run local publication validation for the composite action or a developer."""

    parsed = parse_arguments(arguments)
    evidence_path: Path | None = None
    try:
        workspace = Path(parsed.workspace)
        site_relative = relative_path(parsed.site_directory, "site-directory")
        site_candidate = workspace.resolve().joinpath(
            *PurePosixPath(site_relative).parts
        )
        if parsed.evidence_output:
            evidence_path = resolve_workspace_output(
                workspace, parsed.evidence_output, site=site_candidate
            )
        result = validate_publication_site(
            workspace=workspace,
            site_directory=parsed.site_directory,
            expected_base_url=parsed.expected_base_url,
            expected_source_revision=parsed.expected_source_revision,
            expected_fallback_base_url=parsed.expected_fallback_base_url,
            required_routes_json=parsed.required_routes,
            catalog_path=parsed.catalog_path,
            checksum_path=parsed.checksum_path,
        )
        if evidence_path is not None:
            write_json(evidence_path, result.evidence())
        if parsed.github_output:
            write_github_outputs(Path(parsed.github_output), result)
    except ValidationError as error:
        if evidence_path is not None:
            write_json(
                evidence_path,
                {
                    "error": "publication-site-validation-failed",
                    "reason": "contract-rejected",
                    "schema": EVIDENCE_SCHEMA,
                    "stage": "local-validation",
                    "status": "failed",
                },
            )
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(
        f"Validated {result.file_count} files and {len(result.routes)} routes "
        f"for {result.canonical_base_url}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
