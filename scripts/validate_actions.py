# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Validate Relay's discoverable action catalog and package boundaries."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import Any

CATALOG_SCHEMA = "egohygiene.relay-action-catalog/v1"
ACTION_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
REMOTE_USES = re.compile(r"^\s*uses:\s*([^\s#]+)", re.MULTILINE)
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SEMVER_TAG = re.compile(r"^v[1-9][0-9]*\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$")


def load_object(path: Path) -> dict[str, Any]:
    """Load one JSON object or raise a readable validation error."""

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def discovered_action_paths(repository_root: Path) -> set[str]:
    """Return every first-level public action package containing action.yml."""

    return {
        path.parent.relative_to(repository_root).as_posix()
        for path in (repository_root / "actions").glob("*/action.yml")
    }


def discovered_reusable_workflows(repository_root: Path) -> set[str]:
    """Return workflow packages exposing the workflow_call contract."""

    workflow_root = repository_root / ".github/workflows"
    return {
        path.relative_to(repository_root).as_posix()
        for path in (*workflow_root.glob("*.yml"), *workflow_root.glob("*.yaml"))
        if "workflow_call:" in path.read_text(encoding="utf-8")
    }


def validate_action_manifest(action_path: Path, errors: list[str]) -> None:
    """Validate one composite action's minimum portable package contract."""

    manifest = action_path / "action.yml"
    readme = action_path / "README.md"
    if not manifest.is_file():
        errors.append(f"missing action manifest: {manifest}")
        return
    if not readme.is_file():
        errors.append(f"missing action README: {readme}")
    text = manifest.read_text(encoding="utf-8")
    if "SPDX-License-Identifier: MIT" not in text:
        errors.append(f"manifest lacks SPDX identifier: {manifest}")
    if not re.search(r"^name:\s*.+$", text, re.MULTILINE):
        errors.append(f"manifest lacks name: {manifest}")
    if not re.search(r"^description:\s*(?:>|.+)$", text, re.MULTILINE):
        errors.append(f"manifest lacks description: {manifest}")
    if not re.search(r"^\s+using:\s*[\"']?composite[\"']?\s*$", text, re.MULTILINE):
        errors.append(f"action must use the composite runtime: {manifest}")
    for reference in REMOTE_USES.findall(text):
        if reference.startswith(("./", "$/")):
            continue
        version = reference.rsplit("@", maxsplit=1)[-1] if "@" in reference else ""
        if not FULL_SHA.fullmatch(version):
            errors.append(f"remote action is not pinned to a full SHA in {manifest}: {reference}")

    for relative_script in re.findall(r'\$\{GITHUB_ACTION_PATH\}/([^"\s]+)', text):
        if not (action_path / relative_script).is_file():
            errors.append(f"manifest references missing file: {action_path / relative_script}")


def validate_workflow_metadata(repository_root: Path, errors: list[str]) -> None:
    """Validate reusable, CI, and release workflow publication boundaries."""

    workflow_root = repository_root / ".github/workflows"
    workflows = sorted((*workflow_root.glob("*.yml"), *workflow_root.glob("*.yaml")))
    if not workflows:
        errors.append("no GitHub workflows were discovered")
        return
    for workflow in workflows:
        text = workflow.read_text(encoding="utf-8")
        if "SPDX-License-Identifier: MIT" not in text:
            errors.append(f"workflow lacks SPDX identifier: {workflow}")
        if "yaml-language-server:" not in text:
            errors.append(f"workflow lacks YAML schema declaration: {workflow}")
        if not re.search(r"^name:\s*.+$", text, re.MULTILINE):
            errors.append(f"workflow lacks name: {workflow}")
        if not re.search(r"^on:\s*$", text, re.MULTILINE):
            errors.append(f"workflow lacks on mapping: {workflow}")
        if not re.search(r"^permissions:\s*$", text, re.MULTILINE):
            errors.append(f"workflow lacks explicit permissions: {workflow}")
        for reference in REMOTE_USES.findall(text):
            if reference.startswith(("./", "$/")):
                continue
            version = reference.rsplit("@", maxsplit=1)[-1] if "@" in reference else ""
            if not FULL_SHA.fullmatch(version):
                errors.append(
                    f"remote action/workflow is not pinned to a full SHA in {workflow}: "
                    f"{reference}"
                )

    reusable = (workflow_root / "repository-intelligence.yml").read_text(encoding="utf-8")
    if "workflow_call:" not in reusable:
        errors.append("repository-intelligence workflow is not callable")
    if "uses: $/actions/repository-intelligence" not in reusable:
        errors.append("reusable workflow must invoke the action from its exact Relay revision")
    if "uses: ./actions/repository-intelligence" in reusable:
        errors.append("reusable workflow must not resolve the action from the caller checkout")

    release = (workflow_root / "release.yml").read_text(encoding="utf-8")
    for required in (
        "workflow_dispatch:",
        "release.json",
        "contents: write",
        "vMAJOR.MINOR.PATCH",
        "git tag --annotate",
        "gh release create",
    ):
        if required not in release:
            errors.append(f"release workflow lacks required contract: {required}")


def validate_catalog(repository_root: Path) -> list[str]:
    """Return every catalog/package validation error."""

    errors: list[str] = []
    catalog_path = repository_root / "action-catalog.json"
    try:
        catalog = load_object(catalog_path)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        return [f"invalid action catalog: {error}"]
    if catalog.get("schema") != CATALOG_SCHEMA or catalog.get("schema_version") != 1:
        errors.append("action catalog uses an unsupported schema")

    try:
        release_manifest = load_object(repository_root / "release.json")
    except (OSError, json.JSONDecodeError, ValueError) as error:
        errors.append(f"invalid release manifest: {error}")
    else:
        if release_manifest.get("schema") != "egohygiene.relay-release/v1":
            errors.append("release.json uses an unsupported schema")
        version = release_manifest.get("version")
        if not isinstance(version, str) or not SEMVER_TAG.fullmatch(version):
            errors.append(f"release.json version is not exact SemVer: {version}")
        if not isinstance(release_manifest.get("update_major_alias"), bool):
            errors.append("release.json update_major_alias must be boolean")

    entries = catalog.get("actions")
    if not isinstance(entries, list):
        return [*errors, "action catalog actions must be an array"]
    catalog_paths: set[str] = set()
    identifiers: set[str] = set()
    for index, entry in enumerate(entries):
        label = f"actions[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label} must be an object")
            continue
        identifier = entry.get("id")
        path = entry.get("path")
        if not isinstance(identifier, str) or not ACTION_ID.fullmatch(identifier):
            errors.append(f"{label}.id is invalid: {identifier}")
            continue
        if identifier in identifiers:
            errors.append(f"duplicate action id: {identifier}")
        identifiers.add(identifier)
        expected_path = f"actions/{identifier}"
        if path != expected_path:
            errors.append(f"{identifier} path must be {expected_path}: {path}")
            continue
        if path in catalog_paths:
            errors.append(f"duplicate action path: {path}")
        catalog_paths.add(path)
        expected_ref = f"egohygiene/relay/{path}@v1"
        if entry.get("consumer_ref") != expected_ref:
            errors.append(f"{identifier} consumer_ref must be {expected_ref}")
        validate_action_manifest(repository_root / path, errors)

    discovered = discovered_action_paths(repository_root)
    if catalog_paths != discovered:
        missing = sorted(discovered - catalog_paths)
        stale = sorted(catalog_paths - discovered)
        if missing:
            errors.append(f"actions missing from catalog: {', '.join(missing)}")
        if stale:
            errors.append(f"catalog paths without actions: {', '.join(stale)}")

    workflow_entries = catalog.get("workflows")
    if not isinstance(workflow_entries, list):
        errors.append("action catalog workflows must be an array")
        workflow_entries = []
    catalog_workflows: set[str] = set()
    workflow_identifiers: set[str] = set()
    for index, entry in enumerate(workflow_entries):
        label = f"workflows[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label} must be an object")
            continue
        identifier = entry.get("id")
        path = entry.get("path")
        if not isinstance(identifier, str) or not ACTION_ID.fullmatch(identifier):
            errors.append(f"{label}.id is invalid: {identifier}")
            continue
        if identifier in workflow_identifiers:
            errors.append(f"duplicate workflow id: {identifier}")
        workflow_identifiers.add(identifier)
        if not isinstance(path, str) or not path.startswith(".github/workflows/"):
            errors.append(f"{label}.path is invalid: {path}")
            continue
        catalog_workflows.add(path)
        expected_ref = f"egohygiene/relay/{path}@v1"
        if entry.get("consumer_ref") != expected_ref:
            errors.append(f"{identifier} workflow consumer_ref must be {expected_ref}")

    discovered_workflows = discovered_reusable_workflows(repository_root)
    if catalog_workflows != discovered_workflows:
        missing = sorted(discovered_workflows - catalog_workflows)
        stale = sorted(catalog_workflows - discovered_workflows)
        if missing:
            errors.append(f"reusable workflows missing from catalog: {', '.join(missing)}")
        if stale:
            errors.append(f"catalog paths without reusable workflows: {', '.join(stale)}")

    root_readme = (repository_root / "README.md").read_text(encoding="utf-8")
    for entry in entries:
        if isinstance(entry, dict) and entry.get("consumer_ref") not in root_readme:
            errors.append(f"README does not advertise {entry.get('consumer_ref')}")
    for entry in workflow_entries:
        if isinstance(entry, dict) and entry.get("consumer_ref") not in root_readme:
            errors.append(f"README does not advertise {entry.get('consumer_ref')}")
    validate_workflow_metadata(repository_root, errors)
    return errors


def main() -> int:
    """Validate the repository and print a compact result."""

    repository_root = Path(__file__).resolve().parents[1]
    errors = validate_catalog(repository_root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    action_count = len(discovered_action_paths(repository_root))
    workflow_count = len(discovered_reusable_workflows(repository_root))
    print(
        f"Validated {action_count} Relay actions and {workflow_count} reusable workflow "
        "against action-catalog.json"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
