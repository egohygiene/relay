#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Validate bounded release artifacts and render deterministic release evidence."""

from __future__ import annotations

import argparse
from fnmatch import fnmatchcase
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any


PROFILE_SCHEMA = "egohygiene.relay-release-profiles/v1"
EVIDENCE_SCHEMA = "egohygiene.relay-release-evidence/v1"
CHECKSUM_LINE = re.compile(r"^([0-9a-f]{64})  ([A-Za-z0-9][A-Za-z0-9._/-]*)$")
SEMVER = re.compile(r"^v[1-9][0-9]*\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
SHA = re.compile(r"^[0-9a-f]{40}$")
MAX_FILE_COUNT = 1_024
MAX_TOTAL_BYTES = 512 * 1024 * 1024


class ValidationError(ValueError):
    """Raised when a release bundle cannot safely produce evidence."""


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest for one regular file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(128 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json_object(path: Path) -> dict[str, Any]:
    """Read a UTF-8 JSON object without accepting arrays or scalar values."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValidationError(f"cannot read JSON object {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValidationError(f"{path} must contain a JSON object")
    return value


def validate_relative_path(value: str) -> str:
    """Return one strict, normalized POSIX-relative artifact path."""

    candidate = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or value.startswith("/")
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise ValidationError(f"unsafe bundle path: {value!r}")
    return candidate.as_posix()


def load_profile(path: Path, profile_id: str) -> dict[str, Any]:
    """Load one unique release profile from the versioned Relay catalog."""

    catalog = read_json_object(path)
    if catalog.get("schema") != PROFILE_SCHEMA or catalog.get("schema_version") != 1:
        raise ValidationError("release profile catalog has an unsupported schema")
    profiles = catalog.get("profiles")
    if not isinstance(profiles, list):
        raise ValidationError("release profile catalog profiles must be an array")
    matches = [profile for profile in profiles if isinstance(profile, dict) and profile.get("id") == profile_id]
    if len(matches) != 1:
        raise ValidationError(f"unknown or duplicate release profile: {profile_id}")
    profile = matches[0]
    required = {
        "id",
        "repository_classes",
        "delivery",
        "required_paths",
        "required_globs",
        "required_any_globs",
        "rollback",
    }
    if set(profile) != required:
        raise ValidationError(f"release profile {profile_id} has an unsupported shape")
    if not isinstance(profile["rollback"], dict) or set(profile["rollback"]) != {"strategy", "instructions"}:
        raise ValidationError(f"release profile {profile_id} lacks complete rollback instructions")
    for key in ("repository_classes", "required_paths", "required_globs", "required_any_globs"):
        if not isinstance(profile[key], list):
            raise ValidationError(f"release profile {profile_id}.{key} must be an array")
    return profile


def safe_regular_files(bundle_directory: Path) -> dict[str, Path]:
    """Return all bounded regular files and reject symlinked or oversized bundles."""

    if not bundle_directory.is_dir() or bundle_directory.is_symlink():
        raise ValidationError(f"bundle-directory must be a non-symlink directory: {bundle_directory}")
    files: dict[str, Path] = {}
    total_bytes = 0
    for path in sorted(bundle_directory.rglob("*")):
        relative = path.relative_to(bundle_directory).as_posix()
        if path.is_symlink():
            raise ValidationError(f"release bundle must not contain symlinks: {relative}")
        if not path.is_file():
            continue
        files[validate_relative_path(relative)] = path
        total_bytes += path.stat().st_size
        if len(files) > MAX_FILE_COUNT:
            raise ValidationError(f"release bundle exceeds {MAX_FILE_COUNT} files")
        if total_bytes > MAX_TOTAL_BYTES:
            raise ValidationError(f"release bundle exceeds {MAX_TOTAL_BYTES} bytes")
    if not files:
        raise ValidationError("release bundle has no regular files")
    return files


def parse_checksums(files: dict[str, Path]) -> dict[str, str]:
    """Require an exact, complete, sorted SHA256SUMS inventory."""

    checksum_path = files.get("SHA256SUMS")
    if checksum_path is None:
        raise ValidationError("release bundle must include SHA256SUMS")
    try:
        lines = checksum_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise ValidationError(f"cannot read SHA256SUMS: {error}") from error
    if not lines:
        raise ValidationError("SHA256SUMS must not be empty")
    checksums: dict[str, str] = {}
    ordered_paths: list[str] = []
    for line in lines:
        match = CHECKSUM_LINE.fullmatch(line)
        if match is None:
            raise ValidationError("SHA256SUMS has an invalid line; use '<sha256><two spaces><relative path>'")
        digest, relative = match.groups()
        relative = validate_relative_path(relative)
        if relative == "SHA256SUMS":
            raise ValidationError("SHA256SUMS must not checksum itself")
        if relative in checksums:
            raise ValidationError(f"SHA256SUMS has a duplicate path: {relative}")
        checksums[relative] = digest
        ordered_paths.append(relative)
    if ordered_paths != sorted(ordered_paths):
        raise ValidationError("SHA256SUMS entries must be sorted by relative path")
    expected_paths = set(files) - {"SHA256SUMS"}
    if set(checksums) != expected_paths:
        missing = sorted(expected_paths - set(checksums))
        extra = sorted(set(checksums) - expected_paths)
        details = []
        if missing:
            details.append(f"missing {missing}")
        if extra:
            details.append(f"unknown {extra}")
        raise ValidationError(f"SHA256SUMS must cover every bundle file exactly once ({'; '.join(details)})")
    for relative, expected_digest in checksums.items():
        actual_digest = sha256_file(files[relative])
        if actual_digest != expected_digest:
            raise ValidationError(f"checksum mismatch: {relative}")
    return checksums


def validate_profile_files(profile: dict[str, Any], files: dict[str, Path]) -> None:
    """Require the profile's evidence files and payload patterns."""

    names = sorted(files)
    for required in profile["required_paths"]:
        normalized = validate_relative_path(required)
        if normalized not in files:
            raise ValidationError(f"profile {profile['id']} requires {normalized}")
    for pattern in profile["required_globs"]:
        if not isinstance(pattern, str) or not pattern or not any(fnmatchcase(name, pattern) for name in names):
            raise ValidationError(f"profile {profile['id']} requires a file matching {pattern!r}")
    for alternatives in profile["required_any_globs"]:
        if (
            not isinstance(alternatives, list)
            or not alternatives
            or not any(
                isinstance(pattern, str)
                and pattern
                and any(fnmatchcase(name, pattern) for name in names)
                for pattern in alternatives
            )
        ):
            raise ValidationError(
                f"profile {profile['id']} requires a file matching one of {alternatives!r}"
            )


def render_evidence(
    *,
    profile: dict[str, Any],
    release_version: str,
    source_revision: str,
    files: dict[str, Path],
    checksums: dict[str, str],
) -> dict[str, Any]:
    """Return deterministic public evidence for one validated release bundle."""

    file_entries = [
        {
            "bytes": files[relative].stat().st_size,
            "path": relative,
            "sha256": sha256_file(files[relative]),
        }
        for relative in sorted(files)
    ]
    return {
        "schema": EVIDENCE_SCHEMA,
        "profile": {
            "delivery": profile["delivery"],
            "id": profile["id"],
            "repository_classes": profile["repository_classes"],
        },
        "release_version": release_version,
        "rollback": profile["rollback"],
        "source_revision": source_revision,
        "bundle": {
            "file_count": len(file_entries),
            "files": file_entries,
            "sha256sums_sha256": sha256_file(files["SHA256SUMS"]),
            "total_bytes": sum(entry["bytes"] for entry in file_entries),
            "verified_checksum_count": len(checksums),
        },
    }


def validate_release_bundle(
    *,
    bundle_directory: Path,
    profiles_path: Path,
    profile_id: str,
    release_version: str,
    source_revision: str,
) -> dict[str, Any]:
    """Validate one release bundle and return its canonical evidence document."""

    if not SEMVER.fullmatch(release_version):
        raise ValidationError("release-version must be an exact vMAJOR.MINOR.PATCH value")
    if not SHA.fullmatch(source_revision):
        raise ValidationError("source-revision must be a full lowercase Git SHA")
    profile = load_profile(profiles_path, profile_id)
    files = safe_regular_files(bundle_directory)
    checksums = parse_checksums(files)
    validate_profile_files(profile, files)
    return render_evidence(
        profile=profile,
        release_version=release_version,
        source_revision=source_revision,
        files=files,
        checksums=checksums,
    )


def write_json(path: Path, document: dict[str, Any]) -> str:
    """Write canonical JSON and return its SHA-256 digest."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, indent=2, sort_keys=True) + "\n"
    path.write_text(payload, encoding="utf-8")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> int:
    """Run release-bundle validation as a deterministic command-line contract."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-directory", type=Path, required=True)
    parser.add_argument("--evidence-output", type=Path, required=True)
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--profiles-path", type=Path, required=True)
    parser.add_argument("--release-version", required=True)
    parser.add_argument("--source-revision", required=True)
    arguments = parser.parse_args()
    try:
        evidence = validate_release_bundle(
            bundle_directory=arguments.bundle_directory,
            profiles_path=arguments.profiles_path,
            profile_id=arguments.profile,
            release_version=arguments.release_version,
            source_revision=arguments.source_revision,
        )
        evidence_digest = write_json(arguments.evidence_output, evidence)
    except ValidationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if arguments.github_output is not None:
        bundle = evidence["bundle"]
        with arguments.github_output.open("a", encoding="utf-8") as handle:
            handle.write(f"file-count={bundle['file_count']}\n")
            handle.write(f"release-evidence-sha256={evidence_digest}\n")
            handle.write(f"sha256sums-sha256={bundle['sha256sums_sha256']}\n")
            handle.write(f"total-bytes={bundle['total_bytes']}\n")
    print(
        "Validated release bundle "
        f"profile={evidence['profile']['id']} files={evidence['bundle']['file_count']} "
        f"evidence_sha256={evidence_digest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
