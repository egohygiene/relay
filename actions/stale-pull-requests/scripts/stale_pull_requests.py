#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT
"""Create and apply checksum-bound stale pull-request lifecycle plans."""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import html
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Any, Callable
from urllib.parse import quote, urlencode

PLAN_SCHEMA = "egohygiene.relay.stale-pull-request-plan/v1"
RESULT_SCHEMA = "egohygiene.relay.stale-pull-request-result/v1"
MARKER_PREFIX = "<!-- relay:stale-pull-requests:v1"
CLOSED_MARKER = "<!-- relay:stale-pull-requests:v1 closed -->"
MARKER_PATTERN = re.compile(
    r"(?:^|\n)<!-- relay:stale-pull-requests:v1 warning-days=([1-9][0-9]*) "
    r"close-enabled=(true|false) policy-sha256=([0-9a-f]{64}) "
    r"head-sha=([0-9a-f]{40}|none) -->\Z"
)
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MAXIMUM_ITEMS_LIMIT = 100
PROVIDER_SCAN_LIMIT = 1000
SUMMARY_ITEM_LIMIT = 100
DEFAULT_WARNING_MESSAGE = (
    "This item has been inactive and is now marked stale. New activity removes "
    "the stale state and restarts the inactivity window."
)
DEFAULT_CLOSE_MESSAGE = "Closing after the configured stale warning window."


class ContractError(ValueError):
    """Raised when input or live provider evidence is unsafe."""


def parse_timestamp(value: Any, context: str) -> datetime:
    """Parse a timezone-aware RFC 3339 timestamp."""

    if not isinstance(value, str) or not value:
        raise ContractError(f"{context} must be an RFC 3339 timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ContractError(f"{context} must be an RFC 3339 timestamp") from error
    if parsed.tzinfo is None:
        raise ContractError(f"{context} must include a timezone")
    return parsed.astimezone(timezone.utc)


def format_timestamp(value: datetime) -> str:
    """Serialize a timestamp with stable second precision."""

    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def current_time() -> datetime:
    """Return the current UTC time through one testable clock boundary."""

    return datetime.now(timezone.utc)


def stable_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest_json(value: Any) -> str:
    return hashlib.sha256(stable_json(value)).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_json(path: Path) -> Any:
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


def workspace_root() -> Path:
    raw = os.environ.get("GITHUB_WORKSPACE") or os.getcwd()
    try:
        root = Path(raw).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ContractError(f"repository workspace is unavailable: {raw}") from error
    if not root.is_dir():
        raise ContractError(f"repository workspace is not a directory: {raw}")
    return root


def validate_relative_path(
    value: str, context: str, *, must_exist: bool = False
) -> Path:
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or ".." in path.parts
        or any(part in {"", "."} for part in path.parts)
    ):
        raise ContractError(f"{context} must be a safe repository-relative path")
    root = workspace_root()
    candidate = root.joinpath(*path.parts)
    current = root
    for part in path.parts:
        current /= part
        if current.is_symlink():
            raise ContractError(f"{context} must not traverse a symbolic link")
    try:
        resolved = candidate.resolve(strict=must_exist)
        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError) as error:
        raise ContractError(
            f"{context} must resolve inside the repository workspace"
        ) from error
    if must_exist and (not resolved.is_file() or resolved.is_symlink()):
        raise ContractError(f"{context} must identify a regular non-symlink file")
    if not must_exist and resolved.exists() and (
        not resolved.is_file() or resolved.is_symlink()
    ):
        raise ContractError(f"{context} must identify a regular non-symlink file")
    return resolved


def parse_bool(value: str, context: str) -> bool:
    if value not in {"true", "false"}:
        raise ContractError(f"{context} must be true or false")
    return value == "true"


def parse_positive_integer(value: str, context: str, *, maximum: int | None = None) -> int:
    if not value.isdigit() or int(value) < 1:
        raise ContractError(f"{context} must be a positive integer")
    parsed = int(value)
    if maximum is not None and parsed > maximum:
        raise ContractError(f"{context} must not exceed {maximum}")
    return parsed


def parse_csv(value: str) -> list[str]:
    """Normalize a comma-separated set without inventing wildcard semantics."""

    entries = [entry.strip() for entry in value.split(",") if entry.strip()]
    return sorted(set(entries), key=lambda entry: (entry.casefold(), entry))


def validate_label(value: str, context: str, *, optional: bool = False) -> str:
    if optional and not value:
        return ""
    if not value or len(value) > 50 or any(character in value for character in "\r\n"):
        raise ContractError(f"{context} must be a non-empty GitHub label name")
    return value


def validate_message(value: str, context: str) -> str:
    if len(value.encode("utf-8")) > 10_000:
        raise ContractError(f"{context} must not exceed 10000 UTF-8 bytes")
    if MARKER_PREFIX in value:
        raise ContractError(f"{context} must not contain Relay's reserved marker")
    return value


def gh_api(method: str, endpoint: str, payload: dict[str, Any] | None = None) -> Any:
    """Call the GitHub API through the already-authorized GitHub CLI."""

    if not os.environ.get("GH_TOKEN"):
        raise ContractError("GH_TOKEN is required for GitHub API access")
    command = [
        "gh",
        "api",
        "--method",
        method,
        endpoint,
        "--header",
        "Accept: application/vnd.github+json",
        "--header",
        "X-GitHub-Api-Version: 2022-11-28",
    ]
    input_bytes: bytes | None = None
    if payload is not None:
        command.extend(["--input", "-"])
        input_bytes = stable_json(payload)
    try:
        completed = subprocess.run(
            command,
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as error:
        raise ContractError(f"unable to execute gh api: {error}") from error
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ContractError(f"gh api {method} {endpoint} failed: {detail}")
    if not completed.stdout.strip():
        return None
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise ContractError(f"gh api {method} {endpoint} returned invalid JSON") from error


def require_list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError(f"{context} must be an array")
    return value


def fetch_bounded_pull_requests(repository: str) -> list[Any]:
    encoded = quote(repository, safe="/")
    query = urlencode(
        {
            "state": "open",
            "sort": "updated",
            "direction": "asc",
            "per_page": 100,
        }
    )
    values: list[Any] = []
    for page in range(1, PROVIDER_SCAN_LIMIT // 100 + 1):
        page_values = require_list(
            gh_api("GET", f"repos/{encoded}/pulls?{query}&page={page}"),
            "open pull requests",
        )
        values.extend(page_values)
        if len(page_values) < 100:
            break
    if len(values) == PROVIDER_SCAN_LIMIT:
        probe = require_list(
            gh_api("GET", f"repos/{encoded}/pulls?{query}&page=11"),
            "pull-request scan-limit probe",
        )
        if probe:
            raise ContractError(
                f"open pull requests exceed the provider scan limit of {PROVIDER_SCAN_LIMIT}"
            )
    for value in values:
        if not isinstance(value, dict):
            raise ContractError("open pull requests contain a non-object value")
        value["_relay_kind"] = "pull_request"
    return values


def fetch_bounded_issues(repository: str) -> list[Any]:
    query = urlencode(
        {
            "q": f"repo:{repository} is:issue is:open",
            "sort": "updated",
            "order": "asc",
            "per_page": 100,
        }
    )
    values: list[Any] = []
    total: int | None = None
    for page in range(1, PROVIDER_SCAN_LIMIT // 100 + 1):
        response = gh_api("GET", f"search/issues?{query}&page={page}")
        if not isinstance(response, dict):
            raise ContractError("open issue search must return an object")
        if response.get("incomplete_results") is not False:
            raise ContractError("open issue search returned incomplete results")
        page_values = require_list(response.get("items"), "open issue search items")
        observed_total = response.get("total_count")
        if (
            isinstance(observed_total, bool)
            or not isinstance(observed_total, int)
            or observed_total < len(page_values)
        ):
            raise ContractError("open issue search returned an invalid total_count")
        if total is None:
            total = observed_total
            if total > PROVIDER_SCAN_LIMIT:
                raise ContractError(
                    f"open issues exceed the provider scan limit of {PROVIDER_SCAN_LIMIT}"
                )
        elif observed_total != total:
            raise ContractError("open issue count changed during the bounded scan")
        values.extend(page_values)
        if len(page_values) < 100:
            break
    for value in values:
        if not isinstance(value, dict):
            raise ContractError("open issue search contains a non-object value")
        value["_relay_kind"] = "issue"
    return values


def fetch_open_items_once(
    repository: str, process_issues: bool
) -> list[dict[str, Any]]:
    """Fetch one unique provider set within the explicit hard safety bound."""

    pulls = fetch_bounded_pull_requests(repository)
    issues: list[Any] = []
    if process_issues:
        issues = fetch_bounded_issues(repository)
    combined = pulls + issues
    if len(combined) > PROVIDER_SCAN_LIMIT:
        raise ContractError(
            f"combined open items exceed the provider scan limit of "
            f"{PROVIDER_SCAN_LIMIT}"
        )
    identities: set[tuple[str, int]] = set()
    for item in combined:
        kind = item.get("_relay_kind")
        number = item.get("number")
        if kind not in {"pull_request", "issue"} or (
            isinstance(number, bool) or not isinstance(number, int) or number < 1
        ):
            raise ContractError("open item scan contains an invalid identity")
        identity = (kind, number)
        if identity in identities:
            raise ContractError(
                f"open item scan returned duplicate {kind} identity #{number}"
            )
        identities.add(identity)
    combined.sort(
        key=lambda item: (
            str(item.get("updated_at", "")),
            int(item.get("number", 0)),
            str(item.get("_relay_kind", "")),
        )
    )
    return combined


def fetch_open_items(
    repository: str, process_issues: bool
) -> list[dict[str, Any]]:
    """Require two stable identity scans before evaluating provider state."""

    first = fetch_open_items_once(repository, process_issues)
    second = fetch_open_items_once(repository, process_issues)
    first_identities = {
        (str(item["_relay_kind"]), int(item["number"])) for item in first
    }
    second_identities = {
        (str(item["_relay_kind"]), int(item["number"])) for item in second
    }
    if first_identities != second_identities:
        raise ContractError("open item identities changed during the bounded scan")
    return second


def fetch_repository_labels(repository: str) -> list[str]:
    encoded = quote(repository, safe="/")
    values: list[Any] = []
    for page in range(1, PROVIDER_SCAN_LIMIT // 100 + 1):
        page_values = require_list(
            gh_api(
                "GET",
                f"repos/{encoded}/labels?per_page=100&page={page}",
            ),
            "repository labels",
        )
        values.extend(page_values)
        if len(page_values) < 100:
            break
    if len(values) == PROVIDER_SCAN_LIMIT:
        raise ContractError(
            f"repository labels reach the provider scan limit of {PROVIDER_SCAN_LIMIT}"
        )
    names: list[str] = []
    for value in values:
        if not isinstance(value, dict) or not isinstance(value.get("name"), str):
            raise ContractError("repository labels contain invalid data")
        names.append(value["name"])
    return names


def validate_managed_labels(repository: str, config: dict[str, Any]) -> None:
    available = fetch_repository_labels(repository)
    for context, label in (
        ("stale-label", config["stale_label"]),
        ("closed-label", config["closed_label"]),
    ):
        if label and not contains_casefold(available, label):
            raise ContractError(f"{context} {label!r} does not exist in {repository}")


def fetch_comments(repository: str, number: int) -> list[Any]:
    encoded = quote(repository, safe="/")
    values: list[Any] = []
    for page in range(1, PROVIDER_SCAN_LIMIT // 100 + 1):
        page_values = require_list(
            gh_api(
                "GET",
                f"repos/{encoded}/issues/{number}/comments?per_page=100&page={page}",
            ),
            f"comments for #{number}",
        )
        values.extend(page_values)
        if len(page_values) < 100:
            break
    if len(values) == PROVIDER_SCAN_LIMIT:
        probe = require_list(
            gh_api(
                "GET",
                f"repos/{encoded}/issues/{number}/comments?per_page=100&page=11",
            ),
            f"comment scan-limit probe for #{number}",
        )
        if probe:
            raise ContractError(
                f"comments for #{number} exceed the provider scan limit of "
                f"{PROVIDER_SCAN_LIMIT}"
            )
    return values


def fetch_requested_reviewers(
    repository: str, number: int
) -> tuple[list[str], list[str]]:
    encoded = quote(repository, safe="/")
    response = gh_api("GET", f"repos/{encoded}/pulls/{number}/requested_reviewers")
    if not isinstance(response, dict):
        raise ContractError(f"requested reviewers for #{number} must be an object")
    teams = require_list(response.get("teams", []), f"requested teams for #{number}")
    users = require_list(response.get("users", []), f"requested users for #{number}")
    slugs: list[str] = []
    for team in teams:
        if not isinstance(team, dict) or not isinstance(team.get("slug"), str):
            raise ContractError(f"requested teams for #{number} contain invalid data")
        slugs.append(team["slug"])
    logins: list[str] = []
    for user in users:
        if not isinstance(user, dict) or not isinstance(user.get("login"), str):
            raise ContractError(f"requested users for #{number} contain invalid data")
        logins.append(user["login"])
    return (
        sorted(set(slugs), key=lambda value: (value.casefold(), value)),
        sorted(set(logins), key=lambda value: (value.casefold(), value)),
    )


def label_names(item: dict[str, Any]) -> list[str]:
    values = require_list(item.get("labels", []), "item labels")
    names: list[str] = []
    for value in values:
        name = value.get("name") if isinstance(value, dict) else value
        if not isinstance(name, str) or not name:
            raise ContractError("item labels contain an invalid name")
        names.append(name)
    return sorted(set(names), key=lambda value: (value.casefold(), value))


def trusted_warning(comments: list[Any]) -> dict[str, Any] | None:
    """Return the newest Relay marker authored by GitHub Actions itself."""

    markers: list[dict[str, Any]] = []
    for raw in comments:
        if not isinstance(raw, dict):
            raise ContractError("issue comments contain a non-object value")
        body = raw.get("body")
        user = raw.get("user")
        if not isinstance(body, str) or not isinstance(user, dict):
            continue
        if body.count(MARKER_PREFIX) != 1:
            continue
        match = MARKER_PATTERN.search(body)
        login = user.get("login")
        user_type = user.get("type")
        if (
            match is None
            or user_type != "Bot"
            or login != "github-actions[bot]"
        ):
            continue
        created_at = parse_timestamp(raw.get("created_at"), "warning comment created_at")
        updated_at = parse_timestamp(raw.get("updated_at"), "warning comment updated_at")
        comment_id = raw.get("id")
        if isinstance(comment_id, bool) or not isinstance(comment_id, int) or comment_id < 1:
            raise ContractError("trusted warning comment has an invalid id")
        markers.append(
            {
                "comment_id": comment_id,
                "created_at": format_timestamp(created_at),
                "updated_at": format_timestamp(updated_at),
                "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                "promised_warning_days": int(match.group(1)),
                "close_enabled": match.group(2) == "true",
                "policy_sha256": match.group(3),
                "head_sha": None if match.group(4) == "none" else match.group(4),
            }
        )
    if not markers:
        return None
    return max(markers, key=lambda marker: marker["created_at"])


def normalize_item(
    item: dict[str, Any],
    comments: list[Any],
    requested_teams: list[str],
    requested_users: list[str],
) -> dict[str, Any]:
    number = item.get("number")
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise ContractError("item number must be a positive integer")
    state = item.get("state")
    if state != "open":
        raise ContractError(f"scanned item #{number} is not open")
    user = item.get("user")
    if not isinstance(user, dict):
        raise ContractError(f"item #{number} has no valid author")
    login = user.get("login")
    user_type = user.get("type")
    if not isinstance(login, str) or not login or not isinstance(user_type, str):
        raise ContractError(f"item #{number} has an invalid author")
    kind = item.get("_relay_kind")
    if kind not in {"pull_request", "issue"}:
        raise ContractError(f"item #{number} has an invalid kind")
    draft = item.get("draft", False) if kind == "pull_request" else False
    if not isinstance(draft, bool):
        raise ContractError(f"item #{number} has an invalid draft state")
    updated_at = format_timestamp(parse_timestamp(item.get("updated_at"), "updated_at"))
    head_sha: str | None = None
    if kind == "pull_request":
        head = item.get("head")
        head_sha = head.get("sha") if isinstance(head, dict) else None
        if not isinstance(head_sha, str) or GIT_SHA_PATTERN.fullmatch(head_sha) is None:
            raise ContractError(f"pull request #{number} has an invalid head SHA")
    assignees = require_list(item.get("assignees", []), "item assignees")
    assignee_logins: list[str] = []
    for assignee in assignees:
        if not isinstance(assignee, dict) or not isinstance(assignee.get("login"), str):
            raise ContractError(f"item #{number} has invalid assignees")
        assignee_logins.append(assignee["login"])
    warning = trusted_warning(comments)
    comment_ids = [
        comment.get("id")
        for comment in comments
        if isinstance(comment, dict)
        and isinstance(comment.get("id"), int)
        and not isinstance(comment.get("id"), bool)
    ]
    return {
        "number": number,
        "kind": kind,
        "state": state,
        "updated_at": updated_at,
        "head_sha": head_sha,
        "author": {"login": login, "type": user_type},
        "draft": draft,
        "labels": label_names(item),
        "assignees": sorted(
            set(assignee_logins), key=lambda value: (value.casefold(), value)
        ),
        "requested_review_users": requested_users,
        "requested_review_teams": requested_teams,
        "warning": warning,
        "latest_comment_id": max(comment_ids, default=None),
    }


def contains_casefold(values: list[str], candidate: str) -> bool:
    folded = {value.casefold() for value in values}
    return candidate.casefold() in folded


def exemption_reasons(snapshot: dict[str, Any], config: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if config["exempt_drafts"] and snapshot["draft"]:
        reasons.append("draft")
    login = snapshot["author"]["login"]
    related_users = [
        login,
        *snapshot["assignees"],
        *snapshot["requested_review_users"],
    ]
    if any(
        contains_casefold(config["exempt_users"], related)
        for related in related_users
    ):
        reasons.append("user")
    if config["exempt_bots"] and (
        snapshot["author"]["type"] == "Bot" or login.casefold().endswith("[bot]")
    ):
        reasons.append("bot")
    exempt_labels = {value.casefold() for value in config["exempt_labels"]}
    if any(label.casefold() in exempt_labels for label in snapshot["labels"]):
        reasons.append("label")
    exempt_teams = {value.casefold() for value in config["exempt_review_teams"]}
    if any(
        team.casefold() in exempt_teams for team in snapshot["requested_review_teams"]
    ):
        reasons.append("requested-review-team")
    return reasons


def managed_labels_present(snapshot: dict[str, Any], config: dict[str, Any]) -> list[str]:
    return [
        label
        for label in (config["stale_label"], config["closed_label"])
        if label and contains_casefold(snapshot["labels"], label)
    ]


def warning_matches_own_activity(snapshot: dict[str, Any]) -> bool:
    warning = snapshot["warning"]
    if (
        warning is None
        or snapshot["latest_comment_id"] != warning["comment_id"]
        or warning["updated_at"] != warning["created_at"]
        or warning["head_sha"] != snapshot["head_sha"]
    ):
        return False
    updated = parse_timestamp(snapshot["updated_at"], "snapshot.updated_at")
    created = parse_timestamp(warning["created_at"], "snapshot.warning.created_at")
    return updated == created


def policy_sha256(config: dict[str, Any]) -> str:
    return digest_json(
        {
            "close_enabled": config["close_enabled"],
            "stale_label": config["stale_label"],
        }
    )


def warning_body(
    message: str, config: dict[str, Any], head_sha: str | None
) -> str:
    custom = html.escape(message.strip())
    visible = (
        f"{custom}\n\n{DEFAULT_WARNING_MESSAGE}"
        if custom
        else DEFAULT_WARNING_MESSAGE
    )
    if config["close_enabled"]:
        visible += (
            f" If no new activity occurs, this item will be closed after "
            f"{config['warning_days']} day(s)."
        )
    return (
        f"{visible}\n\n"
        f"{MARKER_PREFIX} warning-days={config['warning_days']} "
        f"close-enabled={str(config['close_enabled']).lower()} "
        f"policy-sha256={policy_sha256(config)} "
        f"head-sha={head_sha or 'none'} -->"
    )


def decide(
    snapshot: dict[str, Any], config: dict[str, Any], evaluation_time: datetime
) -> dict[str, Any]:
    """Resolve one auditable state transition without mutating provider state."""

    managed = managed_labels_present(snapshot, config)
    exemptions = exemption_reasons(snapshot, config)
    decision: dict[str, Any] = {
        "number": snapshot["number"],
        "kind": snapshot["kind"],
        "action": "retain",
        "reason": "active",
        "exemptions": exemptions,
        "snapshot": snapshot,
    }
    if exemptions:
        decision["action"] = "reset" if managed else "exempt"
        decision["reason"] = "exempt"
        return decision

    if config["closed_label"] and contains_casefold(
        snapshot["labels"], config["closed_label"]
    ):
        decision["action"] = "reset"
        decision["reason"] = "reopened"
        return decision

    warning = snapshot["warning"]
    stale_present = contains_casefold(snapshot["labels"], config["stale_label"])
    if warning is not None and stale_present:
        if not warning_matches_own_activity(snapshot):
            decision["action"] = "reset"
            decision["reason"] = "activity-after-warning"
            return decision
        if warning["policy_sha256"] != policy_sha256(config):
            decision["action"] = "warn"
            decision["reason"] = "closure-policy-changed"
            decision["comment"] = warning_body(
                config["warning_message"], config, snapshot["head_sha"]
            )
            return decision
        required_days = max(
            config["warning_days"], warning["promised_warning_days"]
        )
        warning_age = evaluation_time - parse_timestamp(
            warning["created_at"], "warning.created_at"
        )
        if warning_age < timedelta(0):
            raise ContractError(
                f"warning timestamp for #{snapshot['number']} is in the future"
            )
        if warning_age >= timedelta(days=required_days):
            if config["close_enabled"] and warning["close_enabled"]:
                decision["action"] = "close"
                decision["reason"] = "warning-window-elapsed"
            else:
                decision["reason"] = "close-disabled"
        else:
            decision["reason"] = "warning-window-open"
        return decision

    updated = parse_timestamp(snapshot["updated_at"], "snapshot.updated_at")
    inactivity = evaluation_time - updated
    if inactivity < timedelta(0):
        raise ContractError(f"updated_at for #{snapshot['number']} is in the future")
    if stale_present and warning is None:
        decision["action"] = "warn"
        decision["reason"] = "untrusted-stale-label"
        decision["comment"] = warning_body(
            config["warning_message"], config, snapshot["head_sha"]
        )
    elif inactivity >= timedelta(days=config["inactivity_days"]):
        decision["action"] = "warn"
        decision["reason"] = "inactive"
        decision["comment"] = warning_body(
            config["warning_message"], config, snapshot["head_sha"]
        )
    elif managed:
        decision["action"] = "reset"
        decision["reason"] = "active-with-managed-label"
    return decision


def configuration_from_arguments(arguments: argparse.Namespace) -> dict[str, Any]:
    inactivity_days = parse_positive_integer(
        arguments.inactivity_days, "inactivity-days"
    )
    warning_days = parse_positive_integer(arguments.warning_days, "warning-days")
    maximum_items = parse_positive_integer(
        arguments.maximum_items,
        "maximum-items",
        maximum=MAXIMUM_ITEMS_LIMIT,
    )
    stale_label = validate_label(arguments.stale_label, "stale-label")
    closed_label = validate_label(
        arguments.closed_label, "closed-label", optional=True
    )
    if closed_label and stale_label.casefold() == closed_label.casefold():
        raise ContractError("stale-label and closed-label must differ")
    return {
        "inactivity_days": inactivity_days,
        "warning_days": warning_days,
        "stale_label": stale_label,
        "closed_label": closed_label,
        "exempt_labels": parse_csv(arguments.exempt_labels),
        "exempt_users": parse_csv(arguments.exempt_users),
        "exempt_review_teams": parse_csv(arguments.exempt_review_teams),
        "exempt_drafts": parse_bool(arguments.exempt_drafts, "exempt-drafts"),
        "exempt_bots": parse_bool(arguments.exempt_bots, "exempt-bots"),
        "process_issues": parse_bool(arguments.process_issues, "process-issues"),
        "close_enabled": parse_bool(arguments.close_enabled, "close-enabled"),
        "maximum_items": maximum_items,
        "warning_message": validate_message(
            arguments.warning_message, "warning-message"
        ),
        "close_message": validate_message(arguments.close_message, "close-message"),
    }


def public_configuration(config: dict[str, Any]) -> dict[str, Any]:
    """Remove comment bodies while binding their exact bytes into the plan."""

    result = copy.deepcopy(config)
    for key in ("warning_message", "close_message"):
        message = result.pop(key)
        result[f"{key}_sha256"] = hashlib.sha256(message.encode("utf-8")).hexdigest()
    return result


def public_decision(decision: dict[str, Any]) -> dict[str, Any]:
    """Remove a rendered provider comment while preserving its checksum."""

    result = copy.deepcopy(decision)
    if "comment" in result:
        comment = result.pop("comment")
        result["comment_sha256"] = hashlib.sha256(
            comment.encode("utf-8")
        ).hexdigest()
    return result


def decision_signature(decision: dict[str, Any]) -> dict[str, Any]:
    comment = decision.get("comment")
    return {
        "action": decision.get("action"),
        "reason": decision.get("reason"),
        "comment_sha256": (
            hashlib.sha256(comment.encode("utf-8")).hexdigest()
            if isinstance(comment, str)
            else decision.get("comment_sha256")
        ),
    }


def plan_counts(decisions: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "scanned": len(decisions),
        "candidate": sum(
            decision["action"] in {"warn", "close", "reset"}
            for decision in decisions
        ),
        "warning": sum(decision["action"] == "warn" for decision in decisions),
        "closure": sum(decision["action"] == "close" for decision in decisions),
        "reset": sum(decision["action"] == "reset" for decision in decisions),
        "exemption": sum(bool(decision["exemptions"]) for decision in decisions),
    }


def bind_plan(plan: dict[str, Any]) -> dict[str, Any]:
    bound = copy.deepcopy(plan)
    bound.pop("plan_sha256", None)
    bound["plan_sha256"] = digest_json(bound)
    return bound


def verify_plan(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError("plan must be an object")
    required = {
        "schema",
        "status",
        "repository",
        "evaluation_time",
        "configuration",
        "counts",
        "truncated",
        "decisions",
        "plan_sha256",
    }
    if set(value) != required:
        raise ContractError("plan has unexpected or missing top-level fields")
    if value["schema"] != PLAN_SCHEMA or value["status"] != "planned":
        raise ContractError("plan schema or status is unsupported")
    expected = value.get("plan_sha256")
    if not isinstance(expected, str) or SHA256_PATTERN.fullmatch(expected) is None:
        raise ContractError("plan_sha256 must be a lowercase SHA-256")
    unbound = copy.deepcopy(value)
    unbound.pop("plan_sha256")
    if digest_json(unbound) != expected:
        raise ContractError("plan checksum does not match its content")
    if (
        not isinstance(value["decisions"], list)
        or not isinstance(value["counts"], dict)
        or not isinstance(value["truncated"], bool)
    ):
        raise ContractError("plan decisions or counts are invalid")
    if plan_counts(value["decisions"]) != value["counts"]:
        raise ContractError("plan counts do not match its decisions")
    return value


def create_plan(arguments: argparse.Namespace) -> dict[str, Any]:
    repository = arguments.repository
    if REPOSITORY_PATTERN.fullmatch(repository) is None:
        raise ContractError("repository must use owner/name form")
    config = configuration_from_arguments(arguments)
    validate_managed_labels(repository, config)
    explicit_evaluation_time = (
        parse_timestamp(arguments.evaluation_time, "evaluation-time")
        if arguments.evaluation_time
        else None
    )
    if (
        explicit_evaluation_time is not None
        and explicit_evaluation_time > current_time()
    ):
        raise ContractError("evaluation-time must not be in the future")
    items = fetch_open_items(repository, config["process_issues"])
    snapshots: list[dict[str, Any]] = []
    for item in items:
        number = item.get("number")
        comments = fetch_comments(repository, number)
        requested_teams, requested_users = (
            fetch_requested_reviewers(repository, number)
            if item.get("_relay_kind") == "pull_request"
            and (config["exempt_review_teams"] or config["exempt_users"])
            else ([], [])
        )
        snapshots.append(
            normalize_item(item, comments, requested_teams, requested_users)
        )
    # Live plans capture one stable time only after provider evidence is read.
    # This prevents ordinary updates during pagination from appearing to be
    # future activity. Explicit historical replay remains strict.
    evaluation_time = (
        explicit_evaluation_time or current_time()
    ).replace(microsecond=0)
    decisions: list[dict[str, Any]] = []
    actionable_count = 0
    truncated = False
    for snapshot in snapshots:
        decision = decide(snapshot, config, evaluation_time)
        if decision["action"] in {"warn", "close", "reset"}:
            if actionable_count >= config["maximum_items"]:
                truncated = True
                break
            actionable_count += 1
        decisions.append(public_decision(decision))
    decisions.sort(key=lambda value: (value["number"], value["kind"]))
    plan = {
        "schema": PLAN_SCHEMA,
        "status": "planned",
        "repository": repository,
        "evaluation_time": format_timestamp(evaluation_time),
        "configuration": public_configuration(config),
        "counts": plan_counts(decisions),
        "truncated": truncated,
        "decisions": decisions,
    }
    return bind_plan(plan)


def live_snapshot(
    repository: str, decision: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    number = decision["number"]
    encoded = quote(repository, safe="/")
    teams, users = (
        fetch_requested_reviewers(repository, number)
        if decision["kind"] == "pull_request"
        and (config["exempt_review_teams"] or config["exempt_users"])
        else ([], [])
    )
    comments = fetch_comments(repository, number)
    # Read the complete item last so activity caused while reviewer and comment
    # evidence is collected invalidates the fingerprint. The pull endpoint is
    # required for PR-only callers because GET /issues/{number} needs Issues
    # permission even when that number identifies a pull request.
    endpoint = (
        f"repos/{encoded}/pulls/{number}"
        if decision["kind"] == "pull_request"
        else f"repos/{encoded}/issues/{number}"
    )
    item = gh_api("GET", endpoint)
    if not isinstance(item, dict):
        raise ContractError(f"live item #{number} must be an object")
    item["_relay_kind"] = decision["kind"]
    return normalize_item(item, comments, teams, users)


def assert_live_snapshot(expected: dict[str, Any], observed: dict[str, Any]) -> None:
    if expected != observed:
        raise ContractError(
            f"live provider state for #{expected.get('number')} changed after planning"
        )


def add_label(repository: str, number: int, label: str) -> None:
    encoded = quote(repository, safe="/")
    gh_api("POST", f"repos/{encoded}/issues/{number}/labels", {"labels": [label]})


def remove_label(repository: str, number: int, label: str) -> None:
    encoded = quote(repository, safe="/")
    gh_api(
        "DELETE",
        f"repos/{encoded}/issues/{number}/labels/{quote(label, safe='')}",
    )


def add_comment(repository: str, number: int, body: str) -> None:
    encoded = quote(repository, safe="/")
    gh_api("POST", f"repos/{encoded}/issues/{number}/comments", {"body": body})


def authorize_apply(repository: str) -> None:
    """Confine write authority to the target repository's default branch."""

    workflow_repository = os.environ.get("GITHUB_REPOSITORY")
    workflow_ref = os.environ.get("GITHUB_REF")
    if workflow_repository != repository:
        raise ContractError("apply repository must match GITHUB_REPOSITORY")
    encoded = quote(repository, safe="/")
    metadata = gh_api("GET", f"repos/{encoded}")
    if not isinstance(metadata, dict) or not isinstance(
        metadata.get("default_branch"), str
    ):
        raise ContractError("repository metadata has no default branch")
    expected_ref = f"refs/heads/{metadata['default_branch']}"
    if workflow_ref != expected_ref:
        raise ContractError(
            f"apply must run from the default branch ref {expected_ref!r}"
        )


def apply_decision(
    repository: str, decision: dict[str, Any], config: dict[str, Any]
) -> None:
    number = decision["number"]
    action = decision["action"]
    if action == "warn":
        if not contains_casefold(decision["snapshot"]["labels"], config["stale_label"]):
            add_label(repository, number, config["stale_label"])
        # The marker comment is deliberately the final mutation. GitHub timestamps
        # have second precision; any strictly later updated_at resets the lifecycle.
        add_comment(
            repository,
            number,
            warning_body(
                config["warning_message"], config, decision["snapshot"]["head_sha"]
            ),
        )
    elif action == "reset":
        for label in managed_labels_present(decision["snapshot"], config):
            remove_label(repository, number, label)
    elif action == "close":
        encoded = quote(repository, safe="/")
        # Closing is the first mutation, so a provider failure cannot leave a
        # misleading "closed" label or past-tense comment on an open item.
        gh_api("PATCH", f"repos/{encoded}/issues/{number}", {"state": "closed"})
        if config["closed_label"] and not contains_casefold(
            decision["snapshot"]["labels"], config["closed_label"]
        ):
            add_label(repository, number, config["closed_label"])
        message = html.escape(config["close_message"].strip()) or DEFAULT_CLOSE_MESSAGE
        add_comment(
            repository,
            number,
            message
            + "\n\nReopen this item to resume work; Relay clears its managed "
            "lifecycle labels on the next run.\n\n"
            + CLOSED_MARKER,
        )


def apply_plan(arguments: argparse.Namespace) -> dict[str, Any]:
    repository = arguments.repository
    if REPOSITORY_PATTERN.fullmatch(repository) is None:
        raise ContractError("repository must use owner/name form")
    expected_sha = arguments.expected_plan_sha256
    if SHA256_PATTERN.fullmatch(expected_sha or "") is None:
        raise ContractError("expected-plan-sha256 must be a lowercase SHA-256")
    plan = verify_plan(load_json(arguments.plan))
    if plan["plan_sha256"] != expected_sha:
        raise ContractError("expected-plan-sha256 does not match the verified plan")
    if plan["repository"] != repository:
        raise ContractError("plan repository does not match repository input")
    evaluation_time = parse_timestamp(
        plan["evaluation_time"], "plan.evaluation_time"
    )
    if evaluation_time > current_time():
        raise ContractError("plan evaluation_time must not be in the future")
    runtime_config = configuration_from_arguments(arguments)
    if public_configuration(runtime_config) != plan["configuration"]:
        raise ContractError("apply configuration does not match the reviewed plan")
    authorize_apply(repository)
    validate_managed_labels(repository, runtime_config)
    decisions = [
        decision
        for decision in plan["decisions"]
        if decision.get("action") in {"warn", "close", "reset"}
    ]
    preflighted: list[dict[str, Any]] = []
    for decision in decisions:
        if not isinstance(decision, dict) or not isinstance(decision.get("snapshot"), dict):
            raise ContractError("plan contains an invalid actionable decision")
        observed = live_snapshot(repository, decision, runtime_config)
        assert_live_snapshot(decision["snapshot"], observed)
        # Recompute the transition from the exact live snapshot. This catches a
        # structurally valid but semantically inconsistent reviewed plan.
        recomputed = decide(
            observed,
            runtime_config,
            evaluation_time,
        )
        if decision_signature(recomputed) != decision_signature(decision):
            raise ContractError(f"decision for #{decision['number']} is inconsistent")
        preflighted.append(decision)

    applied = {"warning": 0, "closure": 0, "reset": 0}
    for decision in preflighted:
        # Revalidate immediately before the first write for this item. The first
        # loop guarantees every planned mutation was also valid before any write.
        observed = live_snapshot(repository, decision, runtime_config)
        assert_live_snapshot(decision["snapshot"], observed)
        apply_decision(repository, decision, runtime_config)
        applied[{"warn": "warning", "close": "closure", "reset": "reset"}[decision["action"]]] += 1
    counts = {
        "scanned": plan["counts"]["scanned"],
        "candidate": len(decisions),
        "warning": applied["warning"],
        "closure": applied["closure"],
        "reset": applied["reset"],
        "exemption": plan["counts"]["exemption"],
    }
    return {
        "schema": RESULT_SCHEMA,
        "status": "applied",
        "repository": repository,
        "plan_sha256": plan["plan_sha256"],
        "truncated": plan["truncated"],
        "counts": counts,
        "applied": [
            {
                "number": decision["number"],
                "kind": decision["kind"],
                "action": decision["action"],
                "reason": decision["reason"],
            }
            for decision in decisions
        ],
    }


def write_summary(result: dict[str, Any], operation: str, output: Path) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    counts = result["counts"]
    lines = [
        "## Relay stale pull-request lifecycle",
        "",
        f"- Operation: `{operation}`",
        f"- Status: `{result['status']}`",
        f"- Repository: `{result['repository']}`",
        f"- Result: `{output.as_posix()}`",
        f"- Plan SHA-256: `{result['plan_sha256']}`",
        f"- Scanned: {counts['scanned']}",
        f"- Actionable candidates: {counts['candidate']}",
        f"- Warnings: {counts['warning']}",
        f"- Closures: {counts['closure']}",
        f"- Resets: {counts['reset']}",
        f"- Exemptions: {counts['exemption']}",
        f"- Additional actionable items omitted: {str(result['truncated']).lower()}",
        "",
    ]
    source = result.get("decisions", result.get("applied", []))
    represented = [
        item
        for item in source
        if isinstance(item, dict)
        and item.get("action") in {"warn", "close", "reset", "exempt"}
    ]
    if represented:
        lines.extend(["### Bounded decisions", ""])
        for item in represented[:SUMMARY_ITEM_LIMIT]:
            kind = item.get("kind", "item").replace("_", " ")
            lines.append(
                f"- {kind} #{item.get('number')} — `{item.get('action')}` "
                f"(`{item.get('reason', 'applied')}`)"
            )
        omitted = len(represented) - SUMMARY_ITEM_LIMIT
        if omitted > 0:
            lines.append(f"- … {omitted} additional bounded decisions omitted")
        lines.append("")
    try:
        with Path(summary_path).open("a", encoding="utf-8") as summary:
            summary.write("\n".join(lines))
    except OSError as error:
        raise ContractError(f"unable to write GITHUB_STEP_SUMMARY: {error}") from error


def add_configuration_arguments(target: argparse.ArgumentParser) -> None:
    target.add_argument("--inactivity-days", default="30")
    target.add_argument("--warning-days", default="7")
    target.add_argument("--stale-label", default="stale")
    target.add_argument("--closed-label", default="")
    target.add_argument(
        "--exempt-labels",
        default=(
            "do-not-stale,pinned,critical,security,dependencies,priority:p0,"
            "area:security"
        ),
    )
    target.add_argument("--exempt-users", default="")
    target.add_argument("--exempt-review-teams", default="")
    target.add_argument("--exempt-drafts", default="true")
    target.add_argument("--exempt-bots", default="true")
    target.add_argument("--process-issues", default="false")
    target.add_argument("--close-enabled", default="false")
    target.add_argument("--maximum-items", default="100")
    target.add_argument("--warning-message", default="")
    target.add_argument("--close-message", default="")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subparsers = result.add_subparsers(dest="operation", required=True)
    plan = subparsers.add_parser("plan")
    plan.add_argument("--repository", required=True)
    add_configuration_arguments(plan)
    plan.add_argument("--evaluation-time", default="")
    plan.add_argument("--output", required=True, type=Path)

    apply = subparsers.add_parser("apply")
    apply.add_argument("--repository", required=True)
    add_configuration_arguments(apply)
    apply.add_argument("--plan", required=True, type=Path)
    apply.add_argument("--expected-plan-sha256", required=True)
    apply.add_argument("--output", required=True, type=Path)
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        output = validate_relative_path(arguments.output.as_posix(), "output")
        if arguments.operation == "plan":
            result = create_plan(arguments)
        else:
            arguments.plan = validate_relative_path(
                arguments.plan.as_posix(), "plan", must_exist=True
            )
            if arguments.plan == output:
                raise ContractError("apply plan and output paths must differ")
            result = apply_plan(arguments)
        write_json(output, result)
        write_summary(result, arguments.operation, arguments.output)
    except ContractError as error:
        print(f"stale-pull-requests: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
