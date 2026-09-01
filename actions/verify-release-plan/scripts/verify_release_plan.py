#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Verify an Aether release declaration and a reviewable Relay release plan."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tomllib
from typing import Any


DECLARATION_SCHEMA = "egohygiene.repository-release/v1"
DECLARATION_SCHEMA_URL = "https://egohygiene.io/schemas/aether/repository-release/v1.json"
EVIDENCE_SCHEMA = "egohygiene.relay-release-plan-evidence/v1"
SEMVER = re.compile(r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
SHA = re.compile(r"^[0-9a-f]{40}$")
IDENTIFIER = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
COMPONENT_ID = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
REPOSITORY_ID = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
PROMOTED_HEADING = re.compile(
    r"^## \[(?P<version>(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\."
    r"(?:0|[1-9][0-9]*))\] - (?P<date>\d{4}-\d{2}-\d{2})$",
    re.MULTILINE,
)


class VerificationError(ValueError):
    """Raised when a candidate cannot safely advance."""


def exact_object(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    """Require one closed object with exactly the contracted keys."""

    if not isinstance(value, dict) or set(value) != keys:
        raise VerificationError(f"{label} must contain exactly {sorted(keys)}")
    return value


def read_object(path: Path) -> dict[str, Any]:
    """Read one UTF-8 JSON object."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VerificationError(f"cannot read JSON object {path}: {error}") from error
    if not isinstance(value, dict):
        raise VerificationError(f"{path} must contain a JSON object")
    return value


def repository_path(repository: Path, value: str, label: str) -> Path:
    """Resolve a strict repository-relative path."""

    candidate = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or value.startswith("/")
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise VerificationError(f"{label} is not a safe repository-relative path: {value!r}")
    resolved = (repository / Path(*candidate.parts)).resolve()
    try:
        resolved.relative_to(repository.resolve())
    except ValueError as error:
        raise VerificationError(f"{label} escapes the repository: {value!r}") from error
    return resolved


def run_git(repository: Path, *arguments: str, check: bool = True) -> str:
    """Run a bounded Git query and return stripped stdout."""

    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown Git failure"
        raise VerificationError(f"git {' '.join(arguments)} failed: {detail}")
    return result.stdout.strip()


def declaration_contract(data: dict[str, Any], repository_id: str) -> None:
    """Validate the Aether v1 identity and Relay-critical closed fields."""

    if "$schema" in data and data["$schema"] != DECLARATION_SCHEMA_URL:
        raise VerificationError("release declaration references an unsupported schema URL")
    if data.get("schema_version") != DECLARATION_SCHEMA:
        raise VerificationError("release declaration schema_version is unsupported")
    required_top_level = {
        "schema_version", "repository", "release", "changelog",
        "components", "delivery", "evidence", "automation",
    }
    if not required_top_level.issubset(data) or not set(data).issubset(
        required_top_level | {"$schema"}
    ):
        raise VerificationError("release declaration has unsupported top-level fields")
    repository = exact_object(
        data["repository"], {"id", "lifecycle", "release_profile"}, "repository"
    )
    release = exact_object(
        data["release"], {"state", "tag_prefix", "immutable_tags", "major_alias"}, "release"
    )
    changelog = exact_object(
        data["changelog"], {"path", "format", "unreleased_heading"}, "changelog"
    )
    components = data["components"]
    delivery = exact_object(data["delivery"], {"channels"}, "delivery")
    evidence = exact_object(
        data["evidence"],
        {"source", "change", "provenance", "sbom", "signature", "rollback"},
        "evidence",
    )
    automation = exact_object(
        data["automation"], {"taskfile_path", "tasks", "github"}, "automation"
    )
    if repository.get("id") != repository_id or not REPOSITORY_ID.fullmatch(repository_id):
        raise VerificationError("release declaration repository.id must match the caller repository")
    if repository.get("lifecycle") not in {"active", "incubating", "internal"}:
        raise VerificationError("archived or unsupported repository lifecycle cannot release")
    if repository.get("release_profile") not in {
        "contract", "cli-library", "python-package", "npm-package",
        "container-image", "static-site", "publication", "workspace", "internal-only",
    }:
        raise VerificationError("repository.release_profile is unsupported")
    if release.get("state") not in {"unreleased", "released"}:
        raise VerificationError("frozen repository release state cannot advance")
    if release.get("tag_prefix") != "v" or release.get("immutable_tags") is not True:
        raise VerificationError("release declaration must require immutable v-prefixed tags")
    if release.get("major_alias") not in {"disabled", "optional", "enabled"}:
        raise VerificationError("release.major_alias is unsupported")
    if not isinstance(changelog, dict) or changelog.get("format") != "keep-a-changelog/1.1":
        raise VerificationError("release declaration must select Keep a Changelog 1.1")
    if changelog.get("unreleased_heading") != "Unreleased":
        raise VerificationError("release declaration must retain the Unreleased heading")
    if not isinstance(components, list) or not components:
        raise VerificationError("release declaration must contain at least one component")
    component_kinds = {
        "repository", "crate", "python-package", "npm-package", "container-image",
        "static-site", "publication", "catalog", "workspace", "internal",
    }
    authority_kinds = {
        "git-tag", "cargo-manifest", "pyproject-project", "package-json",
        "container-tag", "publication-metadata", "catalog-record",
        "workspace-manifest", "external",
    }
    for index, component in enumerate(components):
        component = exact_object(
            component, {"id", "kind", "version_authority"}, f"components[{index}]"
        )
        if not isinstance(component["id"], str) or not COMPONENT_ID.fullmatch(component["id"]):
            raise VerificationError(f"components[{index}].id is invalid")
        if component["kind"] not in component_kinds:
            raise VerificationError(f"components[{index}].kind is unsupported")
        authority = component["version_authority"]
        if not isinstance(authority, dict) or not set(authority).issubset({"kind", "path", "selector"}) or "kind" not in authority:
            raise VerificationError(f"components[{index}].version_authority has an unsupported shape")
        if authority["kind"] not in authority_kinds:
            raise VerificationError(f"components[{index}].version_authority.kind is unsupported")
    if not isinstance(delivery.get("channels"), list) or not delivery["channels"]:
        raise VerificationError("release declaration delivery.channels must be an array")
    channel_kinds = {
        "github-release", "package-registry", "container-registry", "site-deployment",
        "publication-archive", "internal-distribution",
    }
    channel_states = {"planned", "configured", "external", "unavailable", "not-applicable"}
    for index, channel in enumerate(delivery["channels"]):
        if not isinstance(channel, dict) or not {"kind", "state"}.issubset(channel) or not set(channel).issubset({"kind", "state", "relay_profile", "notes"}):
            raise VerificationError(f"delivery.channels[{index}] has an unsupported shape")
        if channel["kind"] not in channel_kinds or channel["state"] not in channel_states:
            raise VerificationError(f"delivery.channels[{index}] has unsupported values")
    evidence_states = {"required", "available", "external", "unavailable", "not-applicable"}
    if any(evidence[key] not in evidence_states for key in ("source", "change", "provenance", "sbom", "signature")):
        raise VerificationError("release evidence contains an unsupported state")
    rollback = exact_object(evidence["rollback"], {"strategy", "instructions"}, "evidence.rollback")
    if rollback["strategy"] not in {"revert-and-successor-tag", "revoke-channel", "redeploy-prior-artifact", "freeze"}:
        raise VerificationError("release rollback strategy is unsupported")
    if not isinstance(rollback.get("instructions"), str) or not rollback["instructions"]:
        raise VerificationError("release declaration rollback instructions must not be empty")
    tasks = exact_object(
        automation["tasks"], {"plan", "prepare", "verify", "publish"}, "automation.tasks"
    )
    if tasks != {
        "plan": "release:plan", "prepare": "release:prepare",
        "verify": "release:verify", "publish": "release:publish",
    }:
        raise VerificationError("automation.tasks must expose the four standard release handoffs")
    github = exact_object(
        automation["github"], {"manual_dispatch_required", "workflow_path", "state"}, "automation.github"
    )
    if github.get("manual_dispatch_required") is not True:
        raise VerificationError("release publication must require manual GitHub dispatch")
    if github.get("state") not in {"planned", "configured", "unavailable"}:
        raise VerificationError("automation.github.state is unsupported")


def validate_declared_automation(repository: Path, data: dict[str, Any]) -> None:
    """Require the declared local handoffs and manual workflow to exist."""

    automation = data["automation"]
    taskfile = repository_path(repository, automation["taskfile_path"], "Taskfile")
    workflow = repository_path(
        repository, automation["github"]["workflow_path"], "manual release workflow"
    )
    if not taskfile.is_file():
        raise VerificationError("declared Taskfile is missing")
    if not workflow.is_file():
        raise VerificationError("declared manual release workflow is missing")
    taskfile_texts = [taskfile.read_text(encoding="utf-8")]
    for included_value in re.findall(
        r"^\s*taskfile:\s*[\"']?([^\"'\s#]+)", taskfile_texts[0], re.MULTILINE
    ):
        included = repository_path(repository, included_value, "Taskfile include")
        if included.is_file():
            taskfile_texts.append(included.read_text(encoding="utf-8"))
    taskfile_text = "\n".join(taskfile_texts)
    for task in automation["tasks"].values():
        if f"{task}:" not in taskfile_text:
            raise VerificationError(f"declared Taskfile handoff is missing: {task}")
    workflow_text = workflow.read_text(encoding="utf-8")
    if "workflow_dispatch:" not in workflow_text:
        raise VerificationError("declared release workflow is not manually dispatchable")
    if re.search(r"^\s*push:\s*$", workflow_text, re.MULTILINE):
        raise VerificationError("declared release workflow must not publish automatically on push")


def select_component(data: dict[str, Any], component_id: str) -> dict[str, Any]:
    """Select one uniquely declared component."""

    components = data["components"]
    identifiers = [value.get("id") for value in components if isinstance(value, dict)]
    if len(identifiers) != len(set(identifiers)):
        raise VerificationError("release declaration contains duplicate component ids")
    if not component_id:
        if len(components) != 1:
            raise VerificationError("component-id is required for a multi-component declaration")
        component = components[0]
    else:
        matches = [value for value in components if value.get("id") == component_id]
        if len(matches) != 1:
            raise VerificationError(f"unknown or duplicate release component: {component_id}")
        component = matches[0]
    if not isinstance(component.get("version_authority"), dict):
        raise VerificationError("selected component lacks a version authority")
    return component


def nested_value(value: Any, selector: str) -> Any:
    """Resolve a conservative dotted selector without executing expressions."""

    if not selector or any(not part or not re.fullmatch(r"[A-Za-z0-9_-]+", part) for part in selector.split(".")):
        raise VerificationError(f"unsupported version authority selector: {selector!r}")
    current = value
    for part in selector.split("."):
        if not isinstance(current, dict) or part not in current:
            raise VerificationError(f"version authority selector does not resolve: {selector}")
        current = current[part]
    return current


def authority_version(repository: Path, component: dict[str, Any], release_version: str) -> tuple[str, dict[str, str]]:
    """Read the selected component's single authoritative version."""

    authority = component["version_authority"]
    kind = authority.get("kind")
    if kind == "git-tag":
        return release_version, {"kind": kind, "path": "", "selector": ""}
    if kind == "external":
        raise VerificationError("an external version authority cannot authorize Relay publication")
    path_value = authority.get("path")
    if not isinstance(path_value, str):
        raise VerificationError("selected version authority requires a repository-relative path")
    path = repository_path(repository, path_value, "version authority")
    if not path.is_file():
        raise VerificationError(f"version authority source is missing: {path_value}")
    selector = authority.get("selector")
    if kind == "cargo-manifest":
        resolved_selector = selector or "package.version"
        value = nested_value(tomllib.loads(path.read_text(encoding="utf-8")), resolved_selector)
    elif kind == "pyproject-project":
        resolved_selector = selector or "project.version"
        value = nested_value(tomllib.loads(path.read_text(encoding="utf-8")), resolved_selector)
    else:
        resolved_selector = selector or "version"
        value = nested_value(read_object(path), resolved_selector)
    if not isinstance(value, str):
        raise VerificationError("version authority selector must resolve to one string")
    normalized = value if value.startswith("v") else f"v{value}"
    if not SEMVER.fullmatch(normalized):
        raise VerificationError(f"version authority is not exact semantic version: {value}")
    return normalized, {"kind": str(kind), "path": path_value, "selector": resolved_selector}


def validate_changelog(repository: Path, data: dict[str, Any], release_version: str, mode: str) -> dict[str, Any]:
    """Validate human-authored Unreleased and promoted release sections."""

    changelog_value = data["changelog"].get("path")
    if not isinstance(changelog_value, str):
        raise VerificationError("changelog.path must be a repository-relative path")
    path = repository_path(repository, changelog_value, "changelog")
    if not path.is_file():
        raise VerificationError(f"declared changelog is missing: {changelog_value}")
    text = path.read_text(encoding="utf-8")
    if not re.search(r"^## \[Unreleased\]\s*$", text, re.MULTILINE):
        raise VerificationError("changelog lacks the exact ## [Unreleased] heading")
    target = release_version.removeprefix("v")
    promoted = [match.groupdict() for match in PROMOTED_HEADING.finditer(text) if match.group("version") == target]
    if mode == "verify" and len(promoted) != 1:
        raise VerificationError(f"changelog must contain exactly one dated [{target}] release heading")
    if mode == "plan" and promoted:
        raise VerificationError(f"plan mode requires [{target}] to remain unpromoted")
    unreleased = re.search(
        r"^## \[Unreleased\]\s*$\n(?P<body>.*?)(?=^## \[|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    meaningful = bool(unreleased and re.search(r"^###?\s+|^[-*]\s+\S", unreleased.group("body"), re.MULTILINE))
    if mode == "plan" and not meaningful:
        raise VerificationError("Unreleased changelog section has no reviewable change entries")
    return {
        "path": changelog_value,
        "promoted": bool(promoted),
        "release_date": promoted[0]["date"] if promoted else None,
        "unreleased_has_entries": meaningful,
    }


def validate_profile(data: dict[str, Any], profile_id: str, profiles_path: Path) -> dict[str, Any]:
    """Bind the requested Relay profile to an Aether delivery channel."""

    if not IDENTIFIER.fullmatch(profile_id):
        raise VerificationError("profile must be a safe Relay profile identifier")
    catalog = read_object(profiles_path)
    matches = [item for item in catalog.get("profiles", []) if item.get("id") == profile_id]
    if len(matches) != 1:
        raise VerificationError(f"unknown or duplicate Relay release profile: {profile_id}")
    channels = data["delivery"]["channels"]
    declared = [channel for channel in channels if isinstance(channel, dict) and channel.get("relay_profile") == profile_id]
    if len(declared) != 1:
        raise VerificationError(f"release declaration must select Relay profile {profile_id} exactly once")
    if declared[0].get("state") not in {"configured", "external"}:
        raise VerificationError(f"Relay profile {profile_id} is not configured for release")
    return matches[0]


def validate_repository_state(
    repository: Path,
    release_version: str,
    source_revision: str,
    default_branch: str,
    mode: str,
) -> dict[str, Any]:
    """Bind verification to clean Git state and immutable tag identity."""

    head = run_git(repository, "rev-parse", "HEAD^{commit}")
    if head != source_revision:
        raise VerificationError("source-revision does not equal the checked-out commit")
    if mode == "verify":
        dirty = run_git(repository, "status", "--porcelain", "--untracked-files=all")
        meaningful_dirty = [
            line for line in dirty.splitlines()
            if not line.startswith("?? .relay/")
        ]
        if meaningful_dirty:
            raise VerificationError("release verification requires a clean working tree")
        if not default_branch or not re.fullmatch(r"[A-Za-z0-9._/-]+", default_branch):
            raise VerificationError("default-branch is missing or unsafe")
        run_git(repository, "fetch", "--no-tags", "origin", default_branch)
        default_head = run_git(repository, "rev-parse", "FETCH_HEAD^{commit}")
        if default_head != source_revision:
            raise VerificationError("release source is not the current default-branch head")
    remote_tag = run_git(repository, "ls-remote", "--tags", "origin", f"refs/tags/{release_version}", check=False)
    tag_state = "available"
    if remote_tag:
        existing = remote_tag.split()[0]
        run_git(repository, "fetch", "--force", "origin", f"refs/tags/{release_version}:refs/tags/{release_version}")
        existing_commit = run_git(repository, "rev-parse", f"{release_version}^{{commit}}")
        if existing_commit != source_revision:
            raise VerificationError("immutable release tag already targets another commit")
        tag_state = "resumable-identical"
    return {"head": head, "tag_state": tag_state}


def load_bundle_validator(repository_root: Path) -> Any:
    """Load the profile validator from the exact Relay action revision."""

    path = repository_root / "actions/validate-release-bundle/scripts/validate_release_bundle.py"
    spec = importlib.util.spec_from_file_location("relay_release_bundle", path)
    if spec is None or spec.loader is None:
        raise VerificationError("cannot load the exact Relay release-bundle validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_evidence(path: Path, evidence: dict[str, Any]) -> str:
    """Write canonical evidence and return its digest."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(evidence, indent=2, sort_keys=True) + "\n"
    path.write_text(payload, encoding="utf-8")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify(arguments: argparse.Namespace) -> dict[str, Any]:
    """Run all release-plan checks and return deterministic evidence."""

    repository = arguments.repository.resolve()
    declaration_path = repository_path(repository, arguments.declaration, "declaration")
    data = read_object(declaration_path)
    declaration_contract(data, arguments.repository_id)
    validate_declared_automation(repository, data)
    component = select_component(data, arguments.component_id)
    profile = validate_profile(data, arguments.profile, arguments.profiles_path)
    authoritative_version, authority = authority_version(repository, component, arguments.release_version)
    if authoritative_version != arguments.release_version:
        raise VerificationError(
            f"version authority {authoritative_version} disagrees with requested {arguments.release_version}"
        )
    changelog = validate_changelog(repository, data, arguments.release_version, arguments.mode)
    git_state = validate_repository_state(
        repository,
        arguments.release_version,
        arguments.source_revision,
        arguments.default_branch,
        arguments.mode,
    )
    bundle: dict[str, Any] | None = None
    if arguments.mode == "verify":
        if arguments.bundle_directory is None:
            raise VerificationError("verify mode requires a release bundle directory")
        validator = load_bundle_validator(arguments.relay_root)
        try:
            bundle = validator.validate_release_bundle(
                bundle_directory=arguments.bundle_directory,
                profiles_path=arguments.profiles_path,
                profile_id=arguments.profile,
                release_version=arguments.release_version,
                source_revision=arguments.source_revision,
            )
        except validator.ValidationError as error:
            raise VerificationError(f"profile evidence failed: {error}") from error
    return {
        "schema": EVIDENCE_SCHEMA,
        "status": "verified",
        "mode": arguments.mode,
        "repository": arguments.repository_id,
        "source_revision": arguments.source_revision,
        "default_branch": arguments.default_branch,
        "release_version": arguments.release_version,
        "component": {
            "id": component["id"],
            "kind": component["kind"],
            "version_authority": authority,
            "authoritative_version": authoritative_version,
        },
        "profile": {"id": profile["id"], "delivery": profile["delivery"]},
        "changelog": changelog,
        "tag_state": git_state["tag_state"],
        "bundle": bundle,
        "rollback": data["evidence"]["rollback"],
        "errors": [],
    }


def main() -> int:
    """CLI entry point that always leaves bounded success or failure evidence."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path("."))
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--declaration", default=".egohygiene/release.json")
    parser.add_argument("--component-id", default="")
    parser.add_argument("--release-version", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--default-branch", default="")
    parser.add_argument("--mode", choices=("plan", "verify"), required=True)
    parser.add_argument("--bundle-directory", type=Path)
    parser.add_argument("--profiles-path", type=Path, required=True)
    parser.add_argument(
        "--relay-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
    )
    parser.add_argument("--evidence-output", type=Path, required=True)
    parser.add_argument("--github-output", type=Path)
    arguments = parser.parse_args()
    if not SEMVER.fullmatch(arguments.release_version):
        error: Exception = VerificationError("release-version must be exact vMAJOR.MINOR.PATCH")
    elif not SHA.fullmatch(arguments.source_revision):
        error = VerificationError("source-revision must be a full lowercase Git SHA")
    else:
        error = VerificationError("")
        try:
            evidence = verify(arguments)
        except (VerificationError, OSError, ValueError, tomllib.TOMLDecodeError) as caught:
            error = caught
        else:
            digest = write_evidence(arguments.evidence_output, evidence)
            if arguments.github_output is not None:
                with arguments.github_output.open("a", encoding="utf-8") as handle:
                    handle.write(f"evidence-sha256={digest}\n")
                    handle.write("releasable=true\n")
                    handle.write(f"tag-state={evidence['tag_state']}\n")
            print(f"Verified {arguments.mode} release plan evidence_sha256={digest}")
            return 0
    failure = {
        "schema": EVIDENCE_SCHEMA,
        "status": "failed",
        "mode": arguments.mode,
        "repository": arguments.repository_id,
        "source_revision": arguments.source_revision,
        "default_branch": arguments.default_branch,
        "release_version": arguments.release_version,
        "component": None,
        "profile": {"id": arguments.profile},
        "changelog": None,
        "tag_state": "unknown",
        "bundle": None,
        "rollback": None,
        "errors": [str(error)],
    }
    write_evidence(arguments.evidence_output, failure)
    print(f"ERROR: {error}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
