#!/usr/bin/env python3
"""Plan and safely apply governed repository label automation."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote

LOCK_SCHEMA = "egohygiene.relay.organization-labels-lock/v1"
CONFIG_SCHEMA = "egohygiene.relay.repository-labels/v1"
SYNC_PLAN_SCHEMA = "egohygiene.relay.label-sync-plan/v1"
PR_PLAN_SCHEMA = "egohygiene.relay.pull-request-label-plan/v1"
PATH_PROFILE_SCHEMA = "egohygiene.relay.path-label-profile/v1"
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA = re.compile(r"^[0-9a-f]{40}$")
COLOR = re.compile(r"^[0-9a-f]{6}$")
FIRST_CONTRIBUTOR = {"FIRST_TIME_CONTRIBUTOR", "FIRST_TIMER"}
WELCOME_MARKER = "<!-- relay:first-contribution:v1 -->"
MAINTAINER_MARKER = "<!-- relay:maintainer-edits:v1 -->"


class ContractError(ValueError):
    """Raised when governed input is invalid or unsafe."""


def load_json(path: Path) -> Any:
    """Load JSON while rejecting duplicate object keys."""

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ContractError(f"{path}: duplicate key {key!r}")
            result[key] = value
        return result

    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"{path}: {error}") from error


def write_json(path: Path, value: Any) -> None:
    """Write stable UTF-8 JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def digest_json(value: Any) -> str:
    return digest_bytes(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    )


def require_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{context} must be an object")
    return value


def require_keys(value: dict[str, Any], keys: set[str], context: str) -> None:
    if set(value) != keys:
        raise ContractError(
            f"{context} keys must be {sorted(keys)}, got {sorted(value)}"
        )


def validate_repository(repository: str) -> None:
    if REPOSITORY.fullmatch(repository) is None:
        raise ContractError(f"repository must use owner/name form: {repository!r}")


def validate_contract(
    lock_path: Path, catalog_path: Path, assignments_path: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Verify the exact canonical contract bytes and compatible versions."""

    lock = require_object(load_json(lock_path), "lock")
    require_keys(
        lock,
        {"schema", "repository", "revision", "catalog", "assignments"},
        "lock",
    )
    if lock["schema"] != LOCK_SCHEMA or lock["repository"] != "egohygiene/.github":
        raise ContractError("lock owner or schema is invalid")
    if not isinstance(lock["revision"], str) or SHA.fullmatch(lock["revision"]) is None:
        raise ContractError("lock revision must be a full Git SHA")
    for key, path in (("catalog", catalog_path), ("assignments", assignments_path)):
        entry = require_object(lock[key], f"lock.{key}")
        require_keys(entry, {"path", "sha256"}, f"lock.{key}")
        if digest_file(path) != entry["sha256"]:
            raise ContractError(f"{key} bytes do not match the immutable lock")

    catalog = require_object(load_json(catalog_path), "catalog")
    assignments = require_object(load_json(assignments_path), "assignments")
    if catalog.get("owner") != "egohygiene/.github" or catalog.get("schema_version") != 1:
        raise ContractError("catalog owner or schema version is incompatible")
    if assignments.get("schema_version") != 1:
        raise ContractError("assignment schema version is incompatible")
    if assignments.get("catalog_version") != catalog.get("catalog_version"):
        raise ContractError("assignment and catalog versions disagree")
    return lock, catalog, assignments


def validate_label(label: Any, context: str) -> dict[str, str]:
    value = require_object(label, context)
    required = {"name", "description", "color"}
    if "category" in value:
        required.add("category")
    require_keys(value, required, context)
    for key in ("name", "description", "color"):
        if not isinstance(value[key], str) or not value[key]:
            raise ContractError(f"{context}.{key} must be a non-empty string")
    if COLOR.fullmatch(value["color"]) is None:
        raise ContractError(f"{context}.color must be six lowercase hexadecimal digits")
    return {key: value[key] for key in ("name", "description", "color")}


def desired_labels(
    repository: str, catalog: dict[str, Any], assignments: dict[str, Any]
) -> list[dict[str, str]]:
    """Resolve universal, overlay, and repository-local labels without precedence."""

    validate_repository(repository)
    entries = assignments.get("repositories")
    if not isinstance(entries, list):
        raise ContractError("assignments.repositories must be an array")
    matches = [entry for entry in entries if entry.get("repository") == repository]
    if len(matches) != 1:
        raise ContractError(
            f"repository {repository!r} must have exactly one canonical assignment"
        )
    assignment = require_object(matches[0], "repository assignment")
    if assignment.get("include_universal") is not True:
        raise ContractError("canonical assignment cannot disable universal labels")
    selected = assignment.get("overlays")
    if not isinstance(selected, list) or any(not isinstance(item, str) for item in selected):
        raise ContractError("repository overlays must be an array of strings")

    overlay_map: dict[str, list[Any]] = {}
    for index, overlay in enumerate(catalog.get("overlays", [])):
        value = require_object(overlay, f"catalog.overlays[{index}]")
        overlay_id = value.get("id")
        if not isinstance(overlay_id, str) or overlay_id in overlay_map:
            raise ContractError("catalog overlay identifiers must be unique strings")
        labels = value.get("labels")
        if not isinstance(labels, list):
            raise ContractError(f"overlay {overlay_id!r} labels must be an array")
        overlay_map[overlay_id] = labels
    unknown = set(selected) - set(overlay_map)
    if unknown:
        raise ContractError(f"assignment selects unknown overlays: {sorted(unknown)}")

    raw: list[Any] = list(catalog.get("universal", []))
    for overlay_id in selected:
        raw.extend(overlay_map[overlay_id])
    additional = assignment.get("additional_labels")
    if not isinstance(additional, list):
        raise ContractError("assignment.additional_labels must be an array")
    raw.extend(additional)

    resolved: dict[str, dict[str, str]] = {}
    for index, label in enumerate(raw):
        normalized = validate_label(label, f"resolved label[{index}]")
        if normalized["name"] in resolved:
            raise ContractError(f"canonical labels collide on {normalized['name']!r}")
        resolved[normalized["name"]] = normalized
    return [resolved[name] for name in sorted(resolved)]


def normalize_observed_labels(value: Any) -> list[dict[str, str]]:
    """Normalize GitHub label API arrays and fixture objects."""

    if isinstance(value, dict):
        value = value.get("labels")
    if not isinstance(value, list):
        raise ContractError("observed labels must be an array")
    result: list[dict[str, str]] = []
    names: set[str] = set()
    for index, item in enumerate(value):
        label = require_object(item, f"observed[{index}]")
        name = label.get("name")
        color = label.get("color")
        description = label.get("description")
        if not isinstance(name, str) or not name or name in names:
            raise ContractError("observed label names must be unique non-empty strings")
        if not isinstance(color, str) or COLOR.fullmatch(color.lower()) is None:
            raise ContractError(f"observed label {name!r} has invalid color")
        if description is None:
            description = ""
        if not isinstance(description, str):
            raise ContractError(f"observed label {name!r} has invalid description")
        names.add(name)
        result.append({"name": name, "color": color.lower(), "description": description})
    return sorted(result, key=lambda item: item["name"])


def empty_config() -> dict[str, Any]:
    return {
        "schema": CONFIG_SCHEMA,
        "sync": {"retire_labels": []},
        "pull_requests": {
            "path_labels": {
                "enabled": False,
                "preset": "none",
                "missing_label": "error",
                "rules": [],
            },
            "size_labels": {"enabled": False, "thresholds": []},
            "welcome": {"enabled": False, "message": ""},
            "maintainer_edits": {
                "required_for_forks": False,
                "behavior": "warn",
            },
        },
    }


def load_config(path: Path, *, absent_is_disabled: bool) -> tuple[dict[str, Any], bool]:
    if not path.exists():
        if absent_is_disabled:
            return empty_config(), False
        return empty_config(), False
    config = require_object(load_json(path), "configuration")
    require_keys(config, {"schema", "sync", "pull_requests"}, "configuration")
    if config["schema"] != CONFIG_SCHEMA:
        raise ContractError("unsupported repository label configuration schema")
    sync = require_object(config["sync"], "configuration.sync")
    require_keys(sync, {"retire_labels"}, "configuration.sync")
    if not isinstance(sync["retire_labels"], list) or any(
        not isinstance(item, str) or not item for item in sync["retire_labels"]
    ):
        raise ContractError("sync.retire_labels must be an array of label names")
    if len(sync["retire_labels"]) != len(set(sync["retire_labels"])):
        raise ContractError("sync.retire_labels must not contain duplicates")

    pr = require_object(config["pull_requests"], "configuration.pull_requests")
    require_keys(
        pr,
        {"path_labels", "size_labels", "welcome", "maintainer_edits"},
        "configuration.pull_requests",
    )
    path_labels = require_object(pr["path_labels"], "path_labels")
    require_keys(
        path_labels,
        {"enabled", "preset", "missing_label", "rules"},
        "path_labels",
    )
    if not isinstance(path_labels["enabled"], bool) or path_labels["missing_label"] not in {
        "error",
        "warn",
    }:
        raise ContractError("path_labels enablement or missing-label behavior is invalid")
    if path_labels["preset"] not in {"none", "organization-v1"}:
        raise ContractError("path_labels.preset is unsupported")
    if not isinstance(path_labels["rules"], list):
        raise ContractError("path_labels.rules must be an array")
    rule_labels: set[str] = set()
    for index, rule in enumerate(path_labels["rules"]):
        value = require_object(rule, f"path_labels.rules[{index}]")
        require_keys(value, {"label", "paths"}, f"path_labels.rules[{index}]")
        if not isinstance(value["label"], str) or not value["label"]:
            raise ContractError("path rule label must be non-empty")
        if value["label"] in rule_labels:
            raise ContractError(f"path label {value['label']!r} is configured twice")
        rule_labels.add(value["label"])
        if not isinstance(value["paths"], list) or not value["paths"] or any(
            not isinstance(pattern, str)
            or not pattern
            or pattern.startswith(("/", "!"))
            or ".." in PurePosixPath(pattern).parts
            for pattern in value["paths"]
        ):
            raise ContractError("path rules require safe repository-relative glob patterns")

    size = require_object(pr["size_labels"], "size_labels")
    require_keys(size, {"enabled", "thresholds"}, "size_labels")
    if not isinstance(size["enabled"], bool) or not isinstance(size["thresholds"], list):
        raise ContractError("size_labels configuration is invalid")
    maximums: list[int] = []
    size_names: set[str] = set()
    catch_all = 0
    for index, threshold in enumerate(size["thresholds"]):
        value = require_object(threshold, f"size_labels.thresholds[{index}]")
        require_keys(value, {"label", "max_changes"}, f"size_labels.thresholds[{index}]")
        label = value["label"]
        maximum = value["max_changes"]
        if not isinstance(label, str) or not label or label in size_names:
            raise ContractError("size threshold labels must be unique non-empty strings")
        size_names.add(label)
        if maximum is None:
            catch_all += 1
            if index != len(size["thresholds"]) - 1:
                raise ContractError("the unbounded size threshold must be last")
        elif isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 0:
            raise ContractError("max_changes must be a non-negative integer or null")
        else:
            maximums.append(maximum)
    if maximums != sorted(maximums) or len(maximums) != len(set(maximums)):
        raise ContractError("bounded size thresholds must increase strictly")
    if size["enabled"] and (not size["thresholds"] or catch_all != 1):
        raise ContractError("enabled size labels require one final unbounded threshold")

    welcome = require_object(pr["welcome"], "welcome")
    require_keys(welcome, {"enabled", "message"}, "welcome")
    if not isinstance(welcome["enabled"], bool) or not isinstance(welcome["message"], str):
        raise ContractError("welcome configuration is invalid")
    if welcome["enabled"] and not welcome["message"].strip():
        raise ContractError("enabled welcome message cannot be empty")

    edits = require_object(pr["maintainer_edits"], "maintainer_edits")
    require_keys(edits, {"required_for_forks", "behavior"}, "maintainer_edits")
    if not isinstance(edits["required_for_forks"], bool) or edits["behavior"] not in {
        "error",
        "warn",
    }:
        raise ContractError("maintainer_edits configuration is invalid")
    return config, True


def load_path_profile(path: Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Load Relay-owned shared mappings without defining label semantics."""

    profile = require_object(load_json(path), "path label profile")
    require_keys(profile, {"schema", "profile", "rules"}, "path label profile")
    if (
        profile["schema"] != PATH_PROFILE_SCHEMA
        or profile["profile"] != "organization-v1"
        or not isinstance(profile["rules"], list)
    ):
        raise ContractError("shared path label profile is incompatible")
    rules: list[dict[str, Any]] = []
    names: set[str] = set()
    for index, item in enumerate(profile["rules"]):
        rule = require_object(item, f"path label profile rule[{index}]")
        require_keys(rule, {"label", "paths"}, f"path label profile rule[{index}]")
        if (
            not isinstance(rule["label"], str)
            or not rule["label"]
            or rule["label"] in names
            or not isinstance(rule["paths"], list)
            or not rule["paths"]
            or any(
                not isinstance(pattern, str)
                or not pattern
                or pattern.startswith(("/", "!"))
                or ".." in PurePosixPath(pattern).parts
                for pattern in rule["paths"]
            )
        ):
            raise ContractError("shared path label rules are invalid")
        names.add(rule["label"])
        rules.append(rule)
    return rules, {
        "profile": profile["profile"],
        "sha256": digest_file(path),
    }


def contract_evidence(
    lock: dict[str, Any], catalog: dict[str, Any]
) -> dict[str, Any]:
    return {
        "repository": lock["repository"],
        "revision": lock["revision"],
        "catalog_version": catalog["catalog_version"],
        "catalog_sha256": lock["catalog"]["sha256"],
        "assignments_sha256": lock["assignments"]["sha256"],
    }


def finalize_plan(plan: dict[str, Any]) -> dict[str, Any]:
    result = dict(plan)
    result["plan_sha256"] = digest_json(plan)
    return result


def verify_plan(plan: dict[str, Any], expected_schema: str) -> None:
    digest = plan.get("plan_sha256")
    if plan.get("schema") != expected_schema or not isinstance(digest, str):
        raise ContractError("plan schema or checksum is missing")
    unsigned = dict(plan)
    del unsigned["plan_sha256"]
    if digest_json(unsigned) != digest:
        raise ContractError("plan checksum does not match its content")


def plan_sync(arguments: argparse.Namespace) -> dict[str, Any]:
    lock, catalog, assignments = validate_contract(
        arguments.lock, arguments.catalog, arguments.assignments
    )
    config, present = load_config(arguments.config, absent_is_disabled=True)
    desired = desired_labels(arguments.repository, catalog, assignments)
    observed = normalize_observed_labels(load_json(arguments.observed_labels))
    desired_map = {label["name"]: label for label in desired}
    observed_map = {label["name"]: label for label in observed}

    create = [desired_map[name] for name in sorted(set(desired_map) - set(observed_map))]
    update = [
        desired_map[name]
        for name in sorted(set(desired_map) & set(observed_map))
        if desired_map[name]["color"] != observed_map[name]["color"]
        or desired_map[name]["description"] != observed_map[name]["description"]
    ]
    retire = config["sync"]["retire_labels"] if present else []
    illegal = sorted(set(retire) & set(desired_map))
    unknown = sorted(set(retire) - set(observed_map))
    if illegal:
        raise ContractError(f"cannot retire desired canonical labels: {illegal}")
    if unknown:
        raise ContractError(f"retirement labels are not present: {unknown}")
    delete = [observed_map[name] for name in sorted(retire)]
    return finalize_plan(
        {
            "schema": SYNC_PLAN_SCHEMA,
            "repository": arguments.repository,
            "contract": contract_evidence(lock, catalog),
            "configuration_present": present,
            "observed_labels_sha256": digest_json(observed),
            "removal_policy": catalog["defaults"]["removal_policy"],
            "operations": {"create": create, "update": update, "delete": delete},
            "summary": {
                "create": len(create),
                "update": len(update),
                "delete": len(delete),
                "unchanged": len(desired) - len(create) - len(update),
            },
        }
    )


def path_matches(path: str, pattern: str) -> bool:
    normalized = PurePosixPath(path).as_posix()
    return fnmatch.fnmatchcase(normalized, pattern) or (
        pattern.startswith("**/") and fnmatch.fnmatchcase(normalized, pattern[3:])
    )


def normalize_changed_files(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ContractError("changed files must be an array")
    result = []
    for index, item in enumerate(value):
        entry = require_object(item, f"changed_files[{index}]")
        filename = entry.get("filename")
        additions = entry.get("additions", 0)
        deletions = entry.get("deletions", 0)
        if (
            not isinstance(filename, str)
            or filename.startswith("/")
            or ".." in PurePosixPath(filename).parts
        ):
            raise ContractError("changed filenames must be safe repository-relative paths")
        if any(
            isinstance(number, bool) or not isinstance(number, int) or number < 0
            for number in (additions, deletions)
        ):
            raise ContractError(
                "changed-file additions and deletions must be non-negative integers"
            )
        result.append({"filename": filename, "additions": additions, "deletions": deletions})
    return sorted(result, key=lambda item: item["filename"])


def plan_pull_request(arguments: argparse.Namespace) -> dict[str, Any]:
    lock, catalog, assignments = validate_contract(
        arguments.lock, arguments.catalog, arguments.assignments
    )
    config, present = load_config(arguments.config, absent_is_disabled=True)
    event = require_object(load_json(arguments.event), "event")
    pull = require_object(event.get("pull_request"), "event.pull_request")
    repository = event.get("repository", {}).get("full_name")
    if repository != arguments.repository:
        raise ContractError("event repository does not match the requested repository")
    number = pull.get("number") or event.get("number")
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise ContractError("pull request number is invalid")
    head = pull.get("head", {}).get("sha")
    base = pull.get("base", {}).get("sha")
    if (
        not isinstance(head, str)
        or SHA.fullmatch(head) is None
        or not isinstance(base, str)
        or SHA.fullmatch(base) is None
    ):
        raise ContractError("pull request head and base must be full Git SHAs")

    desired = desired_labels(arguments.repository, catalog, assignments)
    canonical_names = {label["name"] for label in desired}
    available = normalize_observed_labels(load_json(arguments.available_labels))
    available_names = {label["name"] for label in available}
    changed = normalize_changed_files(load_json(arguments.changed_files))
    comments = load_json(arguments.comments)
    if not isinstance(comments, list):
        raise ContractError("comments must be an array")
    comment_bodies = [item.get("body", "") for item in comments if isinstance(item, dict)]
    current_labels = normalize_observed_labels(pull.get("labels", []))
    current_names = {label["name"] for label in current_labels}

    warnings: list[str] = []
    violations: list[str] = []
    managed: set[str] = set()
    selected: set[str] = set()
    pr_config = config["pull_requests"]
    path_config = pr_config["path_labels"]
    path_rules: list[dict[str, Any]] = []
    path_profile = {"profile": "none", "sha256": ""}
    if path_config["preset"] == "organization-v1":
        path_rules, path_profile = load_path_profile(arguments.path_defaults)
    merged_rules = {rule["label"]: rule for rule in path_rules}
    merged_rules.update({rule["label"]: rule for rule in path_config["rules"]})
    if path_config["enabled"]:
        for rule in merged_rules.values():
            label = rule["label"]
            managed.add(label)
            if any(
                path_matches(item["filename"], pattern)
                for item in changed
                for pattern in rule["paths"]
            ):
                selected.add(label)

    size_config = pr_config["size_labels"]
    changes = sum(item["additions"] + item["deletions"] for item in changed)
    if size_config["enabled"]:
        managed.update(item["label"] for item in size_config["thresholds"])
        for threshold in size_config["thresholds"]:
            if threshold["max_changes"] is None or changes <= threshold["max_changes"]:
                selected.add(threshold["label"])
                break

    for label in sorted(managed):
        if label not in canonical_names:
            raise ContractError(
                f"configured PR label is not in the canonical projection: {label!r}"
            )
        if label not in available_names:
            message = f"configured PR label does not exist in the repository: {label}"
            if path_config["missing_label"] == "error":
                violations.append(message)
            else:
                warnings.append(message)
                selected.discard(label)

    comments_to_add: list[dict[str, str]] = []
    author = pull.get("user", {})
    author_login = author.get("login", "")
    author_type = author.get("type", "")
    association = pull.get("author_association", "")
    is_bot = author_type == "Bot" or (
        isinstance(author_login, str) and author_login.endswith("[bot]")
    )
    welcome = pr_config["welcome"]
    if (
        present
        and welcome["enabled"]
        and association in FIRST_CONTRIBUTOR
        and not is_bot
        and not any(WELCOME_MARKER in body for body in comment_bodies)
    ):
        comments_to_add.append(
            {"marker": WELCOME_MARKER, "body": f"{WELCOME_MARKER}\n{welcome['message'].strip()}"}
        )

    head_repository = pull.get("head", {}).get("repo", {}).get("full_name")
    is_fork = isinstance(head_repository, str) and head_repository != arguments.repository
    edits = pr_config["maintainer_edits"]
    if is_fork and edits["required_for_forks"] and pull.get("maintainer_can_modify") is not True:
        message = "maintainer edits must be enabled for fork pull requests"
        if edits["behavior"] == "error":
            violations.append(message)
        else:
            warnings.append(message)
        if not any(MAINTAINER_MARKER in body for body in comment_bodies):
            comments_to_add.append(
                {
                    "marker": MAINTAINER_MARKER,
                    "body": (
                        f"{MAINTAINER_MARKER}\nPlease enable **Allow edits and access "
                        "to secrets by "
                        "maintainers** for this pull request. No secrets are exposed by Relay; the "
                        "setting allows maintainers to help update the contribution when needed."
                    ),
                }
            )

    add = sorted(selected - current_names)
    remove = sorted((managed & current_names) - selected)
    return finalize_plan(
        {
            "schema": PR_PLAN_SCHEMA,
            "repository": arguments.repository,
            "pull_request": number,
            "source": {
                "run_id": arguments.run_id,
                "event": "pull_request",
                "base_sha": base,
                "head_sha": head,
                "fork": is_fork,
            },
            "contract": contract_evidence(lock, catalog),
            "configuration_present": present,
            "path_label_profile": path_profile,
            "changed_files_sha256": digest_json(changed),
            "changed_lines": changes,
            "operations": {
                "add_labels": add,
                "remove_labels": remove,
                "comments": comments_to_add,
            },
            "managed_labels": sorted(managed),
            "warnings": warnings,
            "violations": violations,
            "blocking": bool(violations),
            "status": "ready" if present else "not-configured",
        }
    )


def gh_api(
    method: str,
    endpoint: str,
    payload: Any | None = None,
    *,
    paginate: bool = False,
) -> Any:
    if not os.environ.get("GH_TOKEN"):
        raise ContractError("GH_TOKEN is required for apply operations")
    command = ["gh", "api", "--method", method, endpoint]
    if paginate:
        command.extend(["--paginate", "--slurp"])
    input_text = None
    if payload is not None:
        command.extend(["--input", "-"])
        input_text = json.dumps(payload, ensure_ascii=False)
    completed = subprocess.run(
        command,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise ContractError(
            f"GitHub API {method} {endpoint} failed: {completed.stderr.strip()}"
        )
    if not completed.stdout.strip():
        return None
    result = json.loads(completed.stdout)
    if paginate:
        if not isinstance(result, list):
            raise ContractError("paginated GitHub API response must be an array")
        return [item for page in result for item in page]
    return result


def apply_sync(arguments: argparse.Namespace) -> dict[str, Any]:
    plan = require_object(load_json(arguments.plan), "plan")
    verify_plan(plan, SYNC_PLAN_SCHEMA)
    if plan["repository"] != arguments.repository:
        raise ContractError("plan repository does not match apply target")
    deletes = plan["operations"]["delete"]
    if deletes and not arguments.allow_deletions:
        raise ContractError("plan contains deletions but deletion authority was not granted")
    repository = arguments.repository
    for label in plan["operations"]["create"]:
        gh_api("POST", f"repos/{repository}/labels", label)
    for label in plan["operations"]["update"]:
        gh_api(
            "PATCH",
            f"repos/{repository}/labels/{quote(label['name'], safe='')}",
            {
                "new_name": label["name"],
                "color": label["color"],
                "description": label["description"],
            },
        )
    for label in deletes:
        gh_api("DELETE", f"repos/{repository}/labels/{quote(label['name'], safe='')}")
    return {
        "schema": "egohygiene.relay.label-sync-apply-evidence/v1",
        "repository": repository,
        "plan_sha256": plan["plan_sha256"],
        "applied": plan["summary"],
        "deletions_authorized": arguments.allow_deletions,
    }


def apply_pull_request(arguments: argparse.Namespace) -> dict[str, Any]:
    plan = require_object(load_json(arguments.plan), "plan")
    verify_plan(plan, PR_PLAN_SCHEMA)
    if plan["repository"] != arguments.repository:
        raise ContractError("plan repository does not match apply target")
    if str(plan["source"]["run_id"]) != str(arguments.expected_run_id):
        raise ContractError("plan was not produced by the triggering workflow run")
    repository = arguments.repository
    number = plan["pull_request"]
    pull = require_object(gh_api("GET", f"repos/{repository}/pulls/{number}"), "live pull request")
    if (
        pull.get("head", {}).get("sha") != plan["source"]["head_sha"]
        or pull.get("base", {}).get("sha") != plan["source"]["base_sha"]
    ):
        raise ContractError("pull request moved after planning; run a fresh plan")
    for label in plan["operations"]["add_labels"]:
        gh_api("POST", f"repos/{repository}/issues/{number}/labels", {"labels": [label]})
    for label in plan["operations"]["remove_labels"]:
        gh_api("DELETE", f"repos/{repository}/issues/{number}/labels/{quote(label, safe='')}")
    live_comments = gh_api(
        "GET",
        f"repos/{repository}/issues/{number}/comments?per_page=100",
        paginate=True,
    )
    bodies = [item.get("body", "") for item in live_comments if isinstance(item, dict)]
    comments_added = 0
    for comment in plan["operations"]["comments"]:
        if not any(comment["marker"] in body for body in bodies):
            gh_api(
                "POST",
                f"repos/{repository}/issues/{number}/comments",
                {"body": comment["body"]},
            )
            comments_added += 1
    return {
        "schema": "egohygiene.relay.pull-request-label-apply-evidence/v1",
        "repository": repository,
        "pull_request": number,
        "plan_sha256": plan["plan_sha256"],
        "labels_added": len(plan["operations"]["add_labels"]),
        "labels_removed": len(plan["operations"]["remove_labels"]),
        "comments_added": comments_added,
        "blocking": plan["blocking"],
        "violations": plan["violations"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)
    for name in ("sync-plan", "pr-plan"):
        command = subparsers.add_parser(name)
        command.add_argument("--repository", required=True)
        command.add_argument("--lock", required=True, type=Path)
        command.add_argument("--catalog", required=True, type=Path)
        command.add_argument("--assignments", required=True, type=Path)
        command.add_argument("--config", required=True, type=Path)
        command.add_argument("--output", required=True, type=Path)
    sync = subparsers.choices["sync-plan"]
    sync.add_argument("--observed-labels", required=True, type=Path)
    pull = subparsers.choices["pr-plan"]
    pull.add_argument("--event", required=True, type=Path)
    pull.add_argument("--changed-files", required=True, type=Path)
    pull.add_argument("--available-labels", required=True, type=Path)
    pull.add_argument("--comments", required=True, type=Path)
    pull.add_argument("--path-defaults", required=True, type=Path)
    pull.add_argument("--run-id", required=True)

    sync_apply = subparsers.add_parser("sync-apply")
    sync_apply.add_argument("--repository", required=True)
    sync_apply.add_argument("--plan", required=True, type=Path)
    sync_apply.add_argument("--allow-deletions", action="store_true")
    sync_apply.add_argument("--output", required=True, type=Path)
    pr_apply = subparsers.add_parser("pr-apply")
    pr_apply.add_argument("--repository", required=True)
    pr_apply.add_argument("--plan", required=True, type=Path)
    pr_apply.add_argument("--expected-run-id", required=True)
    pr_apply.add_argument("--output", required=True, type=Path)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    try:
        validate_repository(arguments.repository)
        if arguments.operation == "sync-plan":
            result = plan_sync(arguments)
        elif arguments.operation == "pr-plan":
            result = plan_pull_request(arguments)
        elif arguments.operation == "sync-apply":
            result = apply_sync(arguments)
        else:
            result = apply_pull_request(arguments)
        write_json(arguments.output, result)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except ContractError as error:
        print(f"repository label automation refused: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
