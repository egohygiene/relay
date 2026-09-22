# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Create the deterministic Repository Intelligence build manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Any, Iterable

BUILD_MANIFEST_NAME = "build-manifest.json"
BUILD_MANIFEST_SCHEMA = "egohygiene.relay.repository-intelligence-build-manifest/v1"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
REPOSITORY = re.compile(
    r"^(?!\.{1,2}/)(?![^/]+/\.{1,2}$)[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
)
SEMVER = re.compile(r"^[1-9][0-9]*\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$")
MAX_FILES = 4096
MAX_TOTAL_BYTES = 64 * 1024 * 1024
ROUTED_ROUTES = (
    "/intelligence/",
    "/intelligence/compare/",
    "/intelligence/dashboard/",
    "/intelligence/decisions/",
    "/intelligence/dependencies/",
    "/intelligence/health/",
    "/intelligence/journey/",
    "/intelligence/now/",
    "/intelligence/releases/",
    "/intelligence/roadmap/",
    "/intelligence/search/",
    "/intelligence/work/",
)
CONTRACTS: dict[str, dict[str, str | int]] = {
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


class ManifestError(ValueError):
    """The generated bundle cannot be represented by the closed manifest."""


def sha256_bytes(value: bytes) -> str:
    """Return a tagged SHA-256 digest."""

    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def sha256_file(path: Path) -> str:
    """Return a tagged SHA-256 digest without loading a whole file."""

    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def portable_path(value: str) -> str:
    """Validate one canonical portable relative file path."""

    candidate = PurePosixPath(value)
    if (
        not value
        or value.startswith("/")
        or "\\" in value
        or any(part in {"", ".", ".."} for part in candidate.parts)
        or candidate.as_posix() != value
    ):
        raise ManifestError("bundle inventory contains an unsafe relative path")
    return value


def bundle_inventory(output_root: Path) -> tuple[list[dict[str, Any]], str, int]:
    """Inventory every deterministic payload file except the manifest itself."""

    files: list[dict[str, Any]] = []
    total_bytes = 0
    for path in sorted(output_root.rglob("*")):
        relative = portable_path(path.relative_to(output_root).as_posix())
        if path.is_symlink():
            raise ManifestError("bundle inventory rejects symbolic links")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ManifestError("bundle inventory rejects non-regular files")
        if relative == BUILD_MANIFEST_NAME:
            continue
        size = path.stat().st_size
        if size <= 0:
            raise ManifestError("bundle inventory rejects empty files")
        total_bytes += size
        if total_bytes > MAX_TOTAL_BYTES:
            raise ManifestError("bundle exceeds the deterministic byte limit")
        files.append({"path": relative, "bytes": size, "sha256": sha256_file(path)})
        if len(files) > MAX_FILES:
            raise ManifestError("bundle exceeds the deterministic file limit")
    if not files:
        raise ManifestError("bundle inventory is empty")
    canonical = json.dumps(files, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return files, sha256_bytes((canonical + "\n").encode("utf-8")), total_bytes


def enabled_routes(output_root: Path) -> list[str]:
    """Derive the canonical public route inventory from bundle entry points."""

    routes: list[str] = []
    for path in sorted(output_root.rglob("index.html")):
        if path.is_symlink() or not path.is_file():
            raise ManifestError("bundle route inventory rejects symbolic links")
        relative = path.relative_to(output_root).as_posix()
        route = "/intelligence/" if relative == "index.html" else f"/intelligence/{relative[:-10]}"
        routes.append(route)
    routes.sort()
    if tuple(routes) not in {("/intelligence/",), ROUTED_ROUTES}:
        raise ManifestError("bundle route inventory is incompatible with manifest v1")
    return routes


def build_manifest(
    *,
    output_root: Path,
    repository: str,
    consumer_revision: str,
    generator_revision: str,
    generator_version: str,
    source_epoch: int,
) -> dict[str, Any]:
    """Return one closed, deterministic build manifest."""

    if not REPOSITORY.fullmatch(repository):
        raise ManifestError("consumer repository must use owner/name form")
    if not FULL_SHA.fullmatch(consumer_revision):
        raise ManifestError("consumer revision must be a full lowercase SHA")
    if not FULL_SHA.fullmatch(generator_revision):
        raise ManifestError("Relay generator revision must be an immutable full SHA")
    if not SEMVER.fullmatch(generator_version):
        raise ManifestError("Relay generator version must use MAJOR.MINOR.PATCH")
    if source_epoch < 0:
        raise ManifestError("source epoch must be a non-negative integer")
    files, digest, total_bytes = bundle_inventory(output_root)
    return {
        "schema": BUILD_MANIFEST_SCHEMA,
        "schema_version": 1,
        "consumer": {"repository": repository, "revision": consumer_revision},
        "generator": {
            "repository": "egohygiene/relay",
            "revision": generator_revision,
            "version": generator_version,
        },
        "contracts": CONTRACTS,
        "source_epoch": source_epoch,
        "enabled_routes": enabled_routes(output_root),
        "bundle": {
            "algorithm": "sha256-canonical-file-inventory-v1",
            "digest": digest,
            "file_count": len(files),
            "files": files,
            "total_bytes": total_bytes,
        },
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    """Write canonical pretty JSON atomically."""

    payload = json.dumps(value, allow_nan=False, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def append_github_outputs(path: Path | None, values: dict[str, str]) -> None:
    """Append bounded scalar outputs when invoked as a composite action."""

    if path is None:
        return
    with path.open("a", encoding="utf-8", newline="") as destination:
        for name, value in values.items():
            destination.write(f"{name}={value}\n")


def parse_arguments(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    """Parse the manifest creation interface."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--consumer-revision", required=True)
    parser.add_argument("--generator-revision", required=True)
    parser.add_argument("--generator-version", required=True)
    parser.add_argument("--source-epoch", type=int, required=True)
    parser.add_argument("--github-output", type=Path)
    return parser.parse_args(arguments)


def main(arguments: Iterable[str] | None = None) -> int:
    """Create and report one manifest without exposing local paths."""

    parsed = parse_arguments(arguments)
    try:
        repository_root = parsed.repository_root.resolve(strict=True)
        output_root = parsed.output_root.resolve(strict=True)
        output_root.relative_to(repository_root)
        if output_root == repository_root or output_root.name != "intelligence":
            raise ManifestError("output root must be the consumer intelligence subtree")
        manifest = build_manifest(
            output_root=output_root,
            repository=parsed.repository,
            consumer_revision=parsed.consumer_revision,
            generator_revision=parsed.generator_revision,
            generator_version=parsed.generator_version,
            source_epoch=parsed.source_epoch,
        )
        manifest_path = output_root / BUILD_MANIFEST_NAME
        write_json(manifest_path, manifest)
        manifest_digest = sha256_file(manifest_path)
        append_github_outputs(
            parsed.github_output,
            {
                "manifest-sha256": manifest_digest,
                "bundle-digest": manifest["bundle"]["digest"],
            },
        )
    except (ManifestError, OSError, ValueError) as error:
        raise SystemExit(f"Repository Intelligence build manifest is invalid: {error}") from error
    print("Created deterministic Repository Intelligence build manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
