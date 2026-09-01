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
SEMVER = re.compile(r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
SHA = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PYTHON_DISTRIBUTION = re.compile(r"^[A-Za-z0-9]+(?:[-_.][A-Za-z0-9]+)*$")
PYTHON_PACKAGE_SCHEMA = "egohygiene.relay-python-package-release/v1"
PYTHON_PACKAGE_SCHEMA_URL = (
    "https://egohygiene.github.io/relay/contracts/python-package-release/v1/schema.json"
)
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


def require_exact_object(
    value: Any,
    *,
    label: str,
    keys: set[str],
) -> dict[str, Any]:
    """Return an object only when it has the exact contracted keys."""

    if not isinstance(value, dict) or set(value) != keys:
        raise ValidationError(f"{label} must contain exactly {sorted(keys)}")
    return value


def validate_python_artifact(
    value: Any,
    *,
    label: str,
    suffix: str,
    files: dict[str, Path],
    checksums: dict[str, str],
) -> dict[str, str]:
    """Validate one declared Python distribution against the checked bundle."""

    artifact = require_exact_object(value, label=label, keys={"path", "sha256"})
    relative = artifact.get("path")
    digest = artifact.get("sha256")
    if not isinstance(relative, str):
        raise ValidationError(f"{label}.path must be a relative path")
    relative = validate_relative_path(relative)
    if not relative.endswith(suffix):
        raise ValidationError(f"{label}.path must end with {suffix}")
    if relative not in files:
        raise ValidationError(f"{label}.path is absent from the release bundle: {relative}")
    if not isinstance(digest, str) or DIGEST.fullmatch(digest) is None:
        raise ValidationError(f"{label}.sha256 must be a lowercase SHA-256 digest")
    if checksums.get(relative) != digest:
        raise ValidationError(f"{label} digest mismatch for {relative}")
    return {"path": relative, "sha256": digest}


def canonical_python_distribution(value: str) -> str:
    """Return the comparison form defined by Python distribution naming rules."""

    return re.sub(r"[-_.]+", "-", value).lower()


def validate_python_artifact_names(
    *,
    distribution: str,
    version: str,
    sdist: dict[str, str],
    wheels: list[dict[str, str]],
) -> None:
    """Bind wheel and sdist filenames to the declared distribution and version."""

    expected_distribution = canonical_python_distribution(distribution)
    sdist_filename = PurePosixPath(sdist["path"]).name.removesuffix(".tar.gz")
    if "-" not in sdist_filename:
        raise ValidationError("Python sdist filename must contain its name and version")
    sdist_name, sdist_version = sdist_filename.rsplit("-", 1)
    if (
        canonical_python_distribution(sdist_name) != expected_distribution
        or sdist_version != version
    ):
        raise ValidationError("Python sdist filename does not match component name and version")
    for wheel in wheels:
        wheel_parts = PurePosixPath(wheel["path"]).name.removesuffix(".whl").split("-")
        if (
            len(wheel_parts) < 5
            or canonical_python_distribution(wheel_parts[0]) != expected_distribution
            or wheel_parts[1] != version
        ):
            raise ValidationError("Python wheel filename does not match component name and version")


def validate_python_package(
    *,
    files: dict[str, Path],
    checksums: dict[str, str],
    release_version: str,
) -> dict[str, Any]:
    """Validate a Python component, its distributions, and external registry state."""

    document = require_exact_object(
        read_json_object(files["python-package.json"]),
        label="python-package.json",
        keys={"$schema", "schema", "component", "artifacts", "registry"},
    )
    if document["$schema"] != PYTHON_PACKAGE_SCHEMA_URL:
        raise ValidationError("python-package.json references an unsupported JSON Schema")
    if document["schema"] != PYTHON_PACKAGE_SCHEMA:
        raise ValidationError("python-package.json has an unsupported semantic schema")

    component = require_exact_object(
        document["component"],
        label="python-package.json.component",
        keys={"id", "distribution", "version", "version_authority"},
    )
    component_id = component.get("id")
    distribution = component.get("distribution")
    version = component.get("version")
    if not isinstance(component_id, str) or IDENTIFIER.fullmatch(component_id) is None:
        raise ValidationError("python-package.json.component.id must be a kebab-case identifier")
    if not isinstance(distribution, str) or PYTHON_DISTRIBUTION.fullmatch(distribution) is None:
        raise ValidationError("python-package.json.component.distribution is invalid")
    if version != release_version.removeprefix("v"):
        raise ValidationError(
            "python-package.json.component.version must equal release version "
            f"{release_version.removeprefix('v')}"
        )
    authority = require_exact_object(
        component["version_authority"],
        label="python-package.json.component.version_authority",
        keys={"kind", "path"},
    )
    if authority.get("kind") != "pyproject-project":
        raise ValidationError("Python package version authority must be pyproject-project")
    authority_path = authority.get("path")
    if not isinstance(authority_path, str):
        raise ValidationError("Python package version authority path must be relative")
    authority_path = validate_relative_path(authority_path)
    if not authority_path.endswith("pyproject.toml"):
        raise ValidationError("Python package version authority must identify pyproject.toml")

    artifacts = require_exact_object(
        document["artifacts"],
        label="python-package.json.artifacts",
        keys={"sdist", "wheels"},
    )
    sdist = validate_python_artifact(
        artifacts["sdist"],
        label="python-package.json.artifacts.sdist",
        suffix=".tar.gz",
        files=files,
        checksums=checksums,
    )
    wheels_value = artifacts["wheels"]
    if not isinstance(wheels_value, list) or not wheels_value:
        raise ValidationError("python-package.json.artifacts.wheels must be a non-empty array")
    wheels = [
        validate_python_artifact(
            wheel,
            label=f"python-package.json.artifacts.wheels[{index}]",
            suffix=".whl",
            files=files,
            checksums=checksums,
        )
        for index, wheel in enumerate(wheels_value)
    ]
    validate_python_artifact_names(
        distribution=distribution,
        version=version,
        sdist=sdist,
        wheels=wheels,
    )
    declared_paths = [sdist["path"], *(wheel["path"] for wheel in wheels)]
    if len(declared_paths) != len(set(declared_paths)):
        raise ValidationError("python-package.json declares a distribution artifact more than once")
    package_paths = sorted(
        relative
        for relative in files
        if relative.endswith(".whl") or relative.endswith(".tar.gz")
    )
    if sorted(declared_paths) != package_paths:
        raise ValidationError("python-package.json must declare every wheel and sdist exactly once")

    registry = require_exact_object(
        document["registry"],
        label="python-package.json.registry",
        keys={"provider", "state"},
    )
    if registry.get("provider") not in {"pypi", "other"}:
        raise ValidationError("python-package.json.registry.provider must be pypi or other")
    if registry.get("state") not in {"external", "unavailable"}:
        raise ValidationError("Python package registry state must be external or unavailable")

    return {
        "component_id": component_id,
        "distribution": distribution,
        "registry_provider": registry["provider"],
        "registry_state": registry["state"],
        "sdist": sdist,
        "version": version,
        "version_authority": {
            "kind": authority["kind"],
            "path": authority_path,
        },
        "wheels": wheels,
    }


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
    evidence = render_evidence(
        profile=profile,
        release_version=release_version,
        source_revision=source_revision,
        files=files,
        checksums=checksums,
    )
    if profile_id == "python-package":
        evidence["package"] = validate_python_package(
            files=files,
            checksums=checksums,
            release_version=release_version,
        )
    return evidence


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
