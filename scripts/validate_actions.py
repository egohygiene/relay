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
WORKFLOW_CATALOG_SCHEMA = "egohygiene.relay-workflow-catalog/v1"
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


def discovered_workflow_paths(repository_root: Path) -> set[str]:
    """Return every internal and reusable workflow path."""

    workflow_root = repository_root / ".github/workflows"
    return {
        path.relative_to(repository_root).as_posix()
        for path in (*workflow_root.glob("*.yml"), *workflow_root.glob("*.yaml"))
    }


def workflow_job_blocks(text: str) -> dict[str, str]:
    """Extract top-level job blocks without accepting YAML aliases or merges."""

    lines = text.splitlines()
    jobs: dict[str, list[str]] = {}
    current: str | None = None
    in_jobs = False
    for line in lines:
        if line == "jobs:":
            in_jobs = True
            continue
        if not in_jobs:
            continue
        if line and not line.startswith(" "):
            break
        match = re.fullmatch(r"  ([A-Za-z0-9_-]+):", line)
        if match:
            current = match.group(1)
            jobs[current] = [line]
        elif current is not None:
            jobs[current].append(line)
    return {name: "\n".join(lines) for name, lines in jobs.items()}


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
        if re.search(r"^permissions:\s*write-all\s*$", text, re.MULTILINE):
            errors.append(f"workflow grants write-all permissions: {workflow}")
        if re.search(r"^\s*pull_request_target:\s*$", text, re.MULTILINE):
            errors.append(f"workflow uses forbidden pull_request_target: {workflow}")
        top_level = text.split("\njobs:\n", maxsplit=1)[0]
        if not re.search(
            r"^permissions:\s*\n\s{2}contents:\s*read\s*$",
            top_level,
            re.MULTILINE,
        ):
            errors.append(f"workflow default permissions are not contents: read: {workflow}")
        for job_name, job in workflow_job_blocks(text).items():
            if "runs-on:" in job and "timeout-minutes:" not in job:
                errors.append(f"workflow job lacks a timeout: {workflow}#{job_name}")
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


def validate_workflow_catalog(repository_root: Path, errors: list[str]) -> None:
    """Validate the complete owner, security, and caller contract inventory."""

    path = repository_root / "workflow-catalog.json"
    try:
        catalog = load_object(path)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        errors.append(f"invalid workflow catalog: {error}")
        return

    if (
        catalog.get("schema") != WORKFLOW_CATALOG_SCHEMA
        or catalog.get("schema_version") != 1
    ):
        errors.append("workflow catalog uses an unsupported schema")
    if catalog.get("owner") != "egohygiene/relay":
        errors.append("workflow catalog owner must be egohygiene/relay")
    expected_release_model = {
        "unit": "repository",
        "immutable": "vMAJOR.MINOR.PATCH",
        "moving_alias": "vMAJOR",
        "recommended_consumer_pin": "full-commit-sha",
    }
    if catalog.get("release_model") != expected_release_model:
        errors.append("workflow catalog release model is incomplete or unsupported")
    expected_security = {
        "default_permissions": {"contents": "read"},
        "write_permissions": "job-scoped-and-purpose-bound",
        "remote_dependencies": "full-commit-sha",
        "reusable_local_dependencies": "exact-called-relay-revision",
        "forbidden_triggers": ["pull_request_target"],
    }
    if catalog.get("security_policy") != expected_security:
        errors.append("workflow catalog security policy is incomplete or unsupported")

    entries = catalog.get("workflows")
    if not isinstance(entries, list):
        errors.append("workflow catalog workflows must be an array")
        return
    paths: set[str] = set()
    identifiers: set[str] = set()
    for index, entry in enumerate(entries):
        label = f"workflow-catalog.workflows[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label} must be an object")
            continue
        identifier = entry.get("id")
        workflow_path = entry.get("path")
        if not isinstance(identifier, str) or not ACTION_ID.fullmatch(identifier):
            errors.append(f"{label}.id is invalid: {identifier}")
        elif identifier in identifiers:
            errors.append(f"duplicate workflow catalog id: {identifier}")
        else:
            identifiers.add(identifier)
        if not isinstance(workflow_path, str) or not workflow_path.startswith(
            ".github/workflows/"
        ):
            errors.append(f"{label}.path is invalid: {workflow_path}")
            continue
        if workflow_path in paths:
            errors.append(f"duplicate workflow catalog path: {workflow_path}")
        paths.add(workflow_path)
        source_path = repository_root / workflow_path
        if not source_path.is_file():
            errors.append(f"cataloged workflow does not exist: {workflow_path}")
            continue
        source = source_path.read_text(encoding="utf-8")
        if entry.get("owner") != "egohygiene/relay":
            errors.append(f"{label}.owner must be egohygiene/relay")
        if not isinstance(entry.get("purpose"), str) or not entry["purpose"].strip():
            errors.append(f"{label}.purpose must be non-empty")
        if entry.get("status") not in {"experimental", "beta", "stable", "deprecated"}:
            errors.append(f"{label}.status is invalid: {entry.get('status')}")
        permissions = entry.get("permissions")
        observed_permissions: dict[str, str] = {}
        for scope, level in re.findall(
            r"^\s{2,}([a-z-]+):\s*(read|write)\s*$", source, re.MULTILINE
        ):
            if level == "write" or scope not in observed_permissions:
                observed_permissions[scope] = level
        if permissions != observed_permissions:
            errors.append(
                f"catalog permissions do not match maximum authority in {workflow_path}"
            )
        failure = entry.get("failure_semantics")
        if not isinstance(failure, dict) or set(failure) != {
            "mode",
            "partial_success",
            "retry",
            "description",
        }:
            errors.append(f"{label}.failure_semantics is incomplete")
        elif (
            failure.get("mode") not in {"fail-closed", "resume-verified-release"}
            or failure.get("partial_success") is not False
            or failure.get("retry") not in {"fresh-run", "matching-commit-only"}
            or not isinstance(failure.get("description"), str)
            or not failure["description"].strip()
        ):
            errors.append(f"{label}.failure_semantics is invalid")
        audience = entry.get("audience")
        consumer_ref = entry.get("consumer_ref")
        expected_ref = f"egohygiene/relay/{workflow_path}@v1"
        if audience == "reusable":
            if "workflow_call:" not in source:
                errors.append(f"reusable catalog entry is not callable: {workflow_path}")
            if consumer_ref != expected_ref:
                errors.append(f"reusable consumer_ref must be {expected_ref}")
        elif audience == "internal":
            if consumer_ref is not None:
                errors.append(f"internal workflow must not publish a consumer_ref: {workflow_path}")
        else:
            errors.append(f"{label}.audience is invalid: {audience}")

        triggers = entry.get("triggers")
        if not isinstance(triggers, list) or not triggers:
            errors.append(f"{label}.triggers must be a non-empty array")
        else:
            for trigger in triggers:
                if not isinstance(trigger, str) or f"  {trigger}:" not in source:
                    errors.append(f"catalog trigger is absent from {workflow_path}: {trigger}")
        timeout = entry.get("timeout_minutes")
        if not isinstance(timeout, int) or f"timeout-minutes: {timeout}" not in source:
            errors.append(f"catalog timeout does not match {workflow_path}: {timeout}")
        concurrency = entry.get("concurrency")
        if not isinstance(concurrency, dict):
            errors.append(f"{label}.concurrency must be an object")
        else:
            group = concurrency.get("group")
            cancel = str(concurrency.get("cancel_in_progress")).lower()
            if not isinstance(group, str) or group not in source:
                errors.append(f"catalog concurrency group does not match {workflow_path}")
            if f"cancel-in-progress: {cancel}" not in source:
                errors.append(f"catalog cancellation policy does not match {workflow_path}")
        for field in ("inputs", "outputs"):
            parameters = entry.get(field)
            if not isinstance(parameters, list):
                errors.append(f"{label}.{field} must be an array")
                continue
            names: set[str] = set()
            for parameter in parameters:
                name = parameter.get("name") if isinstance(parameter, dict) else None
                if not isinstance(name, str) or not ACTION_ID.fullmatch(name):
                    errors.append(f"{label}.{field} contains an invalid parameter")
                elif name in names:
                    errors.append(f"{label}.{field} contains duplicate parameter {name}")
                else:
                    names.add(name)
                    if (
                        parameter.get("type") not in {"boolean", "number", "string"}
                        or not isinstance(parameter.get("required"), bool)
                        or not isinstance(parameter.get("description"), str)
                        or not parameter["description"].strip()
                    ):
                        errors.append(f"{label}.{field} parameter {name} is incomplete")
                    if (
                        field == "inputs"
                        and parameter.get("required") is False
                        and "default" not in parameter
                    ):
                        errors.append(f"optional input lacks a default: {workflow_path}#{name}")
                    if f"      {name}:" not in source:
                        errors.append(
                            f"catalog parameter is absent from {workflow_path}: {name}"
                        )

    discovered = discovered_workflow_paths(repository_root)
    if paths != discovered:
        missing = sorted(discovered - paths)
        stale = sorted(paths - discovered)
        if missing:
            errors.append(f"workflows missing from workflow catalog: {', '.join(missing)}")
        if stale:
            errors.append(f"workflow catalog paths do not exist: {', '.join(stale)}")

    example_root = repository_root / "examples/workflows"
    required_example = example_root / "repository-intelligence.yml"
    if not required_example.is_file():
        errors.append("repository-intelligence adoption example is missing")
    for example in (*example_root.glob("*.yml"), *example_root.glob("*.yaml")):
        for reference in REMOTE_USES.findall(example.read_text(encoding="utf-8")):
            version = reference.rsplit("@", maxsplit=1)[-1] if "@" in reference else ""
            if not FULL_SHA.fullmatch(version):
                errors.append(f"adoption example is not pinned to a full SHA: {example}")


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
    validate_workflow_catalog(repository_root, errors)
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
    reusable_count = len(discovered_reusable_workflows(repository_root))
    workflow_count = len(discovered_workflow_paths(repository_root))
    print(
        f"Validated {action_count} Relay actions, {workflow_count} workflows, and "
        f"{reusable_count} reusable workflow against the Relay catalogs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
