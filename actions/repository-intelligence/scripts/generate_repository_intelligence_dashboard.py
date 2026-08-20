# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Generate a deterministic static dashboard from normalized report summaries."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import html
import json
from math import ceil, isfinite, pi
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any
from urllib.parse import quote, unquote, urlsplit

DASHBOARD_SCHEMA = "egohygiene.repository-intelligence-dashboard/v3"
REPORT_SCHEMA = "egohygiene.repository-report-summary/v1"
ANALYTICS_SCHEMA = "egohygiene.repository-analytics/v1"
TREE_SCHEMA = "egohygiene.repository-tree/v1"
PROVENANCE_SCHEMA = "egohygiene.relay.repository-intelligence-provenance/v1"
PROVENANCE_SCHEMA_VERSION = 1
GENERATOR_NAME = "egohygiene/relay/actions/repository-intelligence"
GENERATOR_REPOSITORY = "egohygiene/relay"
CONSUMER_VISIBILITIES = {"public", "private", "internal", "unknown"}
PUBLIC_SEVERITIES = {"unknown", "low", "medium", "high", "critical", "warning"}
SCORECARD_CHECK_NAMES = {
    "Binary-Artifacts",
    "Branch-Protection",
    "CI-Tests",
    "CII-Best-Practices",
    "Code-Review",
    "Contributors",
    "Dangerous-Workflow",
    "Dependency-Update-Tool",
    "Fuzzing",
    "License",
    "Maintained",
    "Packaging",
    "Pinned-Dependencies",
    "SAST",
    "SBOM",
    "Security-Policy",
    "Signed-Releases",
    "Token-Permissions",
    "Vulnerabilities",
    "Webhooks",
}
TREE_NODE_TYPES = {"directory", "file", "symlink", "submodule"}
MAX_TREE_DEPTH = 20
MAX_TREE_NODES = 20_000
PRODUCERS = ("osv", "megalinter", "scorecard")
PRODUCER_NAMES = {
    "osv": "Dependency risk",
    "megalinter": "Code quality",
    "scorecard": "Supply-chain posture",
}
EXECUTION_STATES = {"success", "failure", "cancelled", "unknown"}
FINDING_STATES = {"clear", "attention", "blocked", "unknown"}
AVAILABILITY_STATES = {"available", "unavailable", "invalid"}
FRESHNESS_STATES = {"fresh", "stale", "unknown"}
FULL_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
EMAIL_PATTERN = re.compile(
    r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)
REPOSITORY_PATTERN = re.compile(
    r"^(?!\.{1,2}/)(?![^/]+/\.{1,2}$)[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
)


class DashboardInputError(ValueError):
    """Raised when a dashboard or producer input violates its contract."""


def decode_percent_layers(value: str, max_rounds: int = 8) -> str | None:
    """Decode bounded percent-encoding layers or reject ambiguous deep encoding."""

    decoded = value
    for _ in range(max_rounds):
        next_value = unquote(decoded)
        if next_value == decoded:
            return decoded
        decoded = next_value
    return None if unquote(decoded) != decoded else decoded


def parse_arguments() -> argparse.Namespace:
    """Parse the standalone builder interface used by the composite action."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--reports-root", required=True)
    parser.add_argument("--analytics-summary", default="")
    parser.add_argument("--repository-tree", default="")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--default-branch", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--timestamp-source", required=True)
    parser.add_argument("--generator-version", required=True)
    parser.add_argument("--generator-repository", required=True)
    parser.add_argument("--generator-ref", default="")
    parser.add_argument("--generator-commit", default="")
    parser.add_argument("--generator-immutable", required=True)
    parser.add_argument("--consumer-visibility", required=True)
    parser.add_argument("--stylesheet-source", required=True)
    parser.add_argument("--script-source", required=True)
    return parser.parse_args()


def parse_timestamp(value: str, label: str) -> datetime:
    """Parse an aware RFC 3339 timestamp and normalize it to UTC."""

    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise DashboardInputError(f"{label} must be RFC 3339") from error
    if parsed.tzinfo is None:
        raise DashboardInputError(f"{label} must include a timezone")
    return parsed.astimezone(UTC).replace(microsecond=0)


def format_timestamp(value: datetime) -> str:
    """Render an aware datetime as stable UTC RFC 3339."""

    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_integer(value: Any, *, allow_none: bool = False) -> int | None:
    """Return a non-negative integer without accepting booleans."""

    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise DashboardInputError("finding counts must be non-negative integers or null")
    return value


def metric_integer(value: Any) -> int | None:
    """Return a display-safe non-negative metric integer or unknown."""

    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def metric_string(value: Any) -> str | None:
    """Return a display-safe metric string or unknown."""

    return value if isinstance(value, str) and value else None


def metric_score(value: Any) -> int | float | None:
    """Return a finite score in the OpenSSF Scorecard range or unknown."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if isfinite(value) and 0 <= value <= 10 else None


def scorecard_weakest_checks(value: Any) -> list[dict[str, Any]]:
    """Project a bounded list of display-safe Scorecard check summaries."""

    if not isinstance(value, list):
        return []
    checks = []
    for candidate in value[:5]:
        if not isinstance(candidate, dict):
            continue
        name = metric_string(candidate.get("name"))
        score = metric_score(candidate.get("score"))
        if name in SCORECARD_CHECK_NAMES and score is not None:
            checks.append({"name": name, "score": score})
    return checks


def canonical_github_reference(
    path: str,
    repository: str,
    source_commit: str | None,
) -> bool:
    """Accept only source-pinned consumer links and reviewed GitHub route shapes."""

    escaped_repository = re.escape(repository)
    if re.fullmatch(
        rf"/{escaped_repository}/(?:actions/runs/[0-9]+|security/code-scanning)",
        path,
    ):
        return True
    if source_commit is None or not FULL_SHA_PATTERN.fullmatch(source_commit):
        return False
    if path == f"/{repository}/commit/{source_commit}":
        return True
    source_match = re.fullmatch(
        rf"/{escaped_repository}/(blob|tree)/({re.escape(source_commit)})(?:/(.+))?",
        path,
    )
    if source_match is None:
        return False
    kind, _, encoded_path = source_match.groups()
    if encoded_path is None:
        return kind == "tree"
    decoded_path = unquote(encoded_path)
    if quote(decoded_path, safe="/") != encoded_path or "\\" in decoded_path:
        return False
    return all(part not in {"", ".", ".."} for part in decoded_path.split("/"))


def safe_url(
    value: Any,
    repository: str | None = None,
    source_commit: str | None = None,
) -> str:
    """Keep only credential-free HTTPS or canonical repository-relative links."""

    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or any(character.isspace() for character in value)
    ):
        return ""
    try:
        parsed = urlsplit(value)
        parsed.port
    except ValueError:
        return ""
    decoded_value = decode_percent_layers(value)
    if decoded_value is None or EMAIL_PATTERN.search(decoded_value) or re.search(
        r"(?i)(?:github_pat_|gh[pousr]_|(?:token|password|secret)\s*[:=])",
        decoded_value or "",
    ):
        return ""
    if value.startswith("./"):
        encoded_path = parsed.path[2:]
        decoded_path = unquote(encoded_path)
        if (
            parsed.scheme
            or parsed.netloc
            or parsed.query
            or parsed.fragment
            or not encoded_path
            or quote(decoded_path, safe="/") != encoded_path
            or "\\" in decoded_path
            or any(part in {"", ".", ".."} for part in decoded_path.split("/"))
        ):
            return ""
        return value
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.port not in {None, 443}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        return ""
    if parsed.hostname.casefold() not in {"github.com", "scorecard.dev"}:
        return ""
    hostname = parsed.hostname.casefold()
    if hostname == "github.com":
        if repository is None or parsed.query:
            return ""
        return value if canonical_github_reference(parsed.path, repository, source_commit) else ""
    if (
        hostname == "scorecard.dev"
        and parsed.path == "/viewer/"
        and repository is not None
        and parsed.query == f"uri=github.com/{repository}"
    ):
        return value
    return ""


def public_execution_message(producer: str, state: str) -> str:
    """Describe producer execution without copying untrusted diagnostic text."""

    descriptions = {
        "success": f"{PRODUCER_NAMES[producer]} evidence was normalized successfully.",
        "failure": f"{PRODUCER_NAMES[producer]} evidence reported an execution failure.",
        "cancelled": f"{PRODUCER_NAMES[producer]} evidence reported a cancelled execution.",
        "unknown": f"{PRODUCER_NAMES[producer]} execution could not be determined.",
    }
    return descriptions[state]


def unknown_status(state: str, message: str) -> dict[str, str]:
    """Build one compact status object."""

    return {"state": state, "message": message}


def unavailable_projection(producer: str) -> dict[str, Any]:
    """Represent absent producer evidence without guessing consumer configuration."""

    return {
        "producer": producer,
        "name": PRODUCER_NAMES[producer],
        "availability": "unavailable",
        "generated_at": None,
        "commit": None,
        "execution": unknown_status(
            "unknown",
            "No compatible summary was supplied. This producer may be unconfigured, "
            "not applicable, or awaiting its first snapshot.",
        ),
        "findings": {
            "state": "unknown",
            "total": None,
            "blocking": None,
            "advisory": None,
            "by_severity": {},
        },
        "freshness": {
            **unknown_status("unknown", "Freshness cannot be determined."),
            "expires_at": None,
            "stale_after_days": None,
            "elapsed_percent": None,
            "remaining_days": None,
        },
        "links": {},
        "metrics": {},
    }


def invalid_projection(producer: str, message: str) -> dict[str, Any]:
    """Represent malformed or incompatible producer data as an execution failure."""

    projection = unavailable_projection(producer)
    projection["availability"] = "invalid"
    projection["execution"] = unknown_status("failure", message)
    return projection


def require_object(document: dict[str, Any], key: str) -> dict[str, Any]:
    """Read a required object from a report document."""

    value = document.get(key)
    if not isinstance(value, dict):
        raise DashboardInputError(f"{key} must be an object")
    return value


def producer_metrics(producer: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Select the compact, public metrics rendered by one producer card."""

    if producer == "osv":
        scan = payload.get("scan", {})
        discovery = payload.get("discovery", {})
        severity = scan.get("severity", {}) if isinstance(scan, dict) else {}
        return {
            "vulnerabilities": metric_integer(scan.get("vulnerabilities"))
            if isinstance(scan, dict)
            else None,
            "affected_packages": metric_integer(scan.get("affected_packages"))
            if isinstance(scan, dict)
            else None,
            "ecosystems": metric_integer(discovery.get("ecosystem_count"))
            if isinstance(discovery, dict)
            else None,
            "threshold": payload.get("severity_threshold")
            if payload.get("severity_threshold") in {"low", "medium", "high", "critical", "none"}
            else None,
            "severity": {
                str(key): count
                for key, value in sorted(severity.items())
                if key in PUBLIC_SEVERITIES
                and (count := metric_integer(value)) is not None
            }
            if isinstance(severity, dict)
            else {},
        }
    if producer == "megalinter":
        tools = payload.get("tools", {})
        diagnostics = payload.get("diagnostics", {})
        return {
            "profile": payload.get("profile")
            if payload.get("profile") in {"all", "holistic", "changed-files"}
            else None,
            "tools": {
                str(key): count
                for key, value in sorted(tools.items())
                if key
                in {
                    "active",
                    "passed",
                    "with_findings",
                    "execution_errors",
                    "runner_failed",
                    "blocking",
                    "advisory",
                }
                and (count := metric_integer(value)) is not None
            }
            if isinstance(tools, dict)
            else {},
            "diagnostics": {
                str(key): count
                for key, value in sorted(diagnostics.items())
                if key in {"errors", "warnings"}
                and (count := metric_integer(value)) is not None
            }
            if isinstance(diagnostics, dict)
            else {},
        }
    return {
        "aggregate_score": metric_score(payload.get("aggregate_score")),
        "aggregate_source": payload.get("aggregate_source")
        if payload.get("aggregate_source") in {"api", "official-api", "unavailable"}
        else None,
        "api_status": payload.get("api_status")
        if payload.get("api_status") in {"matched", "unavailable", "invalid", "stale"}
        else None,
        "checks_total": metric_integer(payload.get("checks_total")),
        "checks_needing_attention": metric_integer(payload.get("checks_needing_attention")),
        "weakest_checks": scorecard_weakest_checks(payload.get("weakest_checks")),
    }


def validate_report(
    document: dict[str, Any],
    producer: str,
    repository: str,
    source_commit: str,
    as_of: datetime,
) -> dict[str, Any]:
    """Validate and project one normalized producer summary."""

    if document.get("schema") != REPORT_SCHEMA or document.get("schema_version") != 1:
        raise DashboardInputError("Summary uses an incompatible schema.")
    if document.get("producer") != producer:
        raise DashboardInputError("Summary producer does not match its report directory.")
    if document.get("repository") != repository:
        raise DashboardInputError("Summary repository does not match this dashboard.")
    commit = document.get("commit")
    if not isinstance(commit, str) or not FULL_SHA_PATTERN.fullmatch(commit):
        raise DashboardInputError("Summary commit must be a full lowercase SHA.")
    if commit != source_commit:
        raise DashboardInputError("Summary does not represent the dashboard source commit.")
    generated_at_raw = document.get("generated_at")
    if not isinstance(generated_at_raw, str):
        raise DashboardInputError("generated_at must be an RFC 3339 string.")
    generated_at = parse_timestamp(generated_at_raw, "generated_at")

    execution = require_object(document, "execution")
    execution_state = execution.get("state")
    if execution_state not in EXECUTION_STATES or not isinstance(execution.get("message"), str):
        raise DashboardInputError("execution contains an unsupported state or message.")

    report_findings = require_object(document, "findings")
    finding_state = report_findings.get("state")
    if finding_state not in FINDING_STATES:
        raise DashboardInputError("findings contains an unsupported state.")
    allow_none = finding_state == "unknown"
    total = safe_integer(report_findings.get("total"), allow_none=allow_none)
    blocking = safe_integer(report_findings.get("blocking"), allow_none=allow_none)
    advisory = safe_integer(report_findings.get("advisory"), allow_none=allow_none)
    if total is not None and blocking is not None and advisory is not None:
        if blocking + advisory != total:
            raise DashboardInputError("blocking and advisory counts must sum to total.")
    by_severity = report_findings.get("by_severity")
    if not isinstance(by_severity, dict):
        raise DashboardInputError("findings.by_severity must be an object.")
    normalized_severity = {
        str(key): safe_integer(value)
        for key, value in sorted(by_severity.items())
        if key in PUBLIC_SEVERITIES
    }

    report_freshness = require_object(document, "freshness")
    expires_at_raw = report_freshness.get("expires_at")
    if not isinstance(expires_at_raw, str):
        raise DashboardInputError("freshness.expires_at must be an RFC 3339 string.")
    expires_at = parse_timestamp(expires_at_raw, "freshness.expires_at")
    stale_after_days = report_freshness.get("stale_after_days")
    if (
        isinstance(stale_after_days, bool)
        or not isinstance(stale_after_days, int)
        or stale_after_days < 1
    ):
        raise DashboardInputError("freshness.stale_after_days must be a positive integer.")
    if expires_at <= generated_at:
        raise DashboardInputError("freshness.expires_at must be after generated_at.")
    freshness_state = "stale" if as_of >= expires_at else "fresh"
    freshness_message = (
        f"Expired at {format_timestamp(expires_at)}."
        if freshness_state == "stale"
        else f"Valid through {format_timestamp(expires_at)}."
    )
    elapsed_seconds = max(0.0, (as_of - generated_at).total_seconds())
    freshness_window_seconds = (expires_at - generated_at).total_seconds()
    elapsed_percent = round(min(1.0, elapsed_seconds / freshness_window_seconds) * 100)
    remaining_days = ceil((expires_at - as_of).total_seconds() / 86400)

    provenance = require_object(document, "provenance")
    if not all(isinstance(provenance.get(key), str) for key in ("event", "workflow")):
        raise DashboardInputError("provenance event and workflow must be strings.")
    run_id = provenance.get("run_id")
    run_attempt = provenance.get("run_attempt")
    if run_id is not None and not isinstance(run_id, str):
        raise DashboardInputError("provenance.run_id must be a string or null.")
    if run_attempt is not None and (
        isinstance(run_attempt, bool) or not isinstance(run_attempt, int) or run_attempt < 1
    ):
        raise DashboardInputError("provenance.run_attempt must be a positive integer or null.")

    report_links = require_object(document, "links")
    link_keys = ("detail", "workflow", "security", "source")
    if not all(isinstance(report_links.get(key), str) for key in link_keys):
        raise DashboardInputError(
            "links must declare detail, workflow, security, and source strings."
        )
    links = {
        key: safe_url(report_links.get(key), repository, source_commit)
        for key in link_keys
    }
    payload = require_object(document, producer)
    return {
        "producer": producer,
        "name": PRODUCER_NAMES[producer],
        "availability": "available",
        "generated_at": format_timestamp(generated_at),
        "commit": commit,
        "execution": {
            "state": execution_state,
            "message": public_execution_message(producer, execution_state),
        },
        "findings": {
            "state": finding_state,
            "total": total,
            "blocking": blocking,
            "advisory": advisory,
            "by_severity": normalized_severity,
        },
        "freshness": {
            "state": freshness_state,
            "message": freshness_message,
            "expires_at": format_timestamp(expires_at),
            "stale_after_days": stale_after_days,
            "elapsed_percent": elapsed_percent,
            "remaining_days": remaining_days,
        },
        "links": {key: value for key, value in links.items() if value},
        "metrics": producer_metrics(producer, payload),
    }


def load_report(
    reports_root: Path,
    producer: str,
    repository: str,
    source_commit: str,
    as_of: datetime,
) -> dict[str, Any]:
    """Load one producer summary with explicit unavailable and invalid fallbacks."""

    path = reports_root / producer / "summary.json"
    if (reports_root / producer).is_symlink() or path.is_symlink():
        return invalid_projection(producer, "Summary path must not use symbolic links.")
    if not path.is_file() or path.stat().st_size == 0:
        return unavailable_projection(producer)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, RecursionError):
        return invalid_projection(producer, "Summary is malformed JSON.")
    if not isinstance(document, dict):
        return invalid_projection(producer, "Summary must contain a JSON object.")
    try:
        return validate_report(document, producer, repository, source_commit, as_of)
    except DashboardInputError as error:
        return invalid_projection(producer, str(error))


def analytics_projection(availability: str, message: str) -> dict[str, Any]:
    """Build an explicit analytics availability wrapper."""

    return {"availability": availability, "message": message, "summary": None}


def analytics_integer(value: Any, label: str) -> int:
    """Validate one non-negative analytics integer."""

    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise DashboardInputError(f"{label} must be a non-negative integer.")
    return value


def analytics_signed_integer(value: Any, label: str) -> int:
    """Validate one analytics integer that may be negative."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise DashboardInputError(f"{label} must be an integer.")
    return value


def analytics_rows(
    value: Any,
    *,
    label: str,
    identity_key: str,
    metric_keys: tuple[str, ...],
    limit: int,
) -> list[dict[str, Any]]:
    """Validate and bound one public analytics row collection."""

    if not isinstance(value, list):
        raise DashboardInputError(f"{label} must be an array.")
    rows: list[dict[str, Any]] = []
    for index, candidate in enumerate(value[:limit]):
        if not isinstance(candidate, dict):
            raise DashboardInputError(f"{label}[{index}] must be an object.")
        identity = candidate.get(identity_key)
        if not isinstance(identity, str) or not identity:
            raise DashboardInputError(f"{label}[{index}].{identity_key} must be non-empty.")
        if identity_key == "path":
            parts = identity.split("/")
            if identity.startswith("/") or "\\" in identity or any(
                part in {"", ".", ".."} for part in parts
            ):
                raise DashboardInputError(f"{label}[{index}].path must be repository-relative.")
        if identity_key == "week":
            try:
                datetime.strptime(identity, "%Y-%m-%d")
            except ValueError as error:
                raise DashboardInputError(
                    f"{label}[{index}].week must use YYYY-MM-DD."
                ) from error
        row: dict[str, Any] = {identity_key: identity}
        for metric_key in metric_keys:
            row[metric_key] = analytics_integer(
                candidate.get(metric_key),
                f"{label}[{index}].{metric_key}",
            )
        rows.append(row)
    if len({row[identity_key] for row in rows}) != len(rows):
        raise DashboardInputError(f"{label} identities must be unique.")
    return rows


def validate_analytics(document: dict[str, Any], source_commit: str) -> dict[str, Any]:
    """Project the versioned public analytics contract used by the charts."""

    if document.get("schema") != ANALYTICS_SCHEMA or document.get("schema_version") != 1:
        raise DashboardInputError("Analytics uses an incompatible schema.")
    source = require_object(document, "source")
    if source.get("revision") != source_commit:
        raise DashboardInputError("Analytics does not represent the dashboard source commit.")
    source_ref = source.get("ref")
    source_committed_at = source.get("committed_at")
    if not isinstance(source_ref, str) or not source_ref:
        raise DashboardInputError("Analytics source.ref must be non-empty.")
    if not isinstance(source_committed_at, str):
        raise DashboardInputError("Analytics source.committed_at must be RFC 3339.")
    committed_at = format_timestamp(
        parse_timestamp(source_committed_at, "analytics source.committed_at")
    )

    privacy = require_object(document, "privacy")
    if privacy != {
        "public_safe": True,
        "contributor_identities_included": False,
        "commit_messages_included": False,
    }:
        raise DashboardInputError("Analytics privacy declaration is not public-safe.")

    scope = require_object(document, "scope")
    since = scope.get("since")
    resolved_since = scope.get("resolved_since")
    if not isinstance(since, str) or not since or not isinstance(resolved_since, str):
        raise DashboardInputError("Analytics scope must declare since and resolved_since.")

    repository = require_object(document, "repository")
    activity = require_object(document, "activity")
    changes = require_object(document, "changes")
    filters = require_object(document, "filters")
    weekly = analytics_rows(
        activity.get("weekly"),
        label="analytics.activity.weekly",
        identity_key="week",
        metric_keys=("commits", "merges"),
        limit=260,
    )
    if any(row["merges"] > row["commits"] for row in weekly):
        raise DashboardInputError("Weekly merge counts cannot exceed commit counts.")
    if weekly != sorted(weekly, key=lambda row: row["week"]):
        raise DashboardInputError("Weekly analytics must be ordered by week.")

    repository_areas = analytics_rows(
        repository.get("areas"),
        label="analytics.repository.areas",
        identity_key="name",
        metric_keys=("file_count",),
        limit=100,
    )
    change_areas = analytics_rows(
        changes.get("areas"),
        label="analytics.changes.areas",
        identity_key="name",
        metric_keys=("commit_touches", "insertions", "deletions", "binary_changes"),
        limit=100,
    )
    hotspots = analytics_rows(
        changes.get("hotspots"),
        label="analytics.changes.hotspots",
        identity_key="path",
        metric_keys=("commit_touches", "insertions", "deletions", "binary_changes"),
        limit=20,
    )
    first_commit_at = activity.get("first_commit_at")
    last_commit_at = activity.get("last_commit_at")
    for value, label in (
        (first_commit_at, "analytics.activity.first_commit_at"),
        (last_commit_at, "analytics.activity.last_commit_at"),
    ):
        if value is not None and not isinstance(value, str):
            raise DashboardInputError(f"{label} must be an RFC 3339 string or null.")
        if isinstance(value, str):
            parse_timestamp(value, label)

    tracked_files = analytics_integer(
        repository.get("tracked_files"), "analytics.repository.tracked_files"
    )
    if sum(row["file_count"] for row in repository_areas) != tracked_files:
        raise DashboardInputError("Repository area file counts must sum to tracked_files.")
    activity_commits = analytics_integer(activity.get("commits"), "analytics.activity.commits")
    activity_merges = analytics_integer(activity.get("merges"), "analytics.activity.merges")
    if activity_merges > activity_commits:
        raise DashboardInputError("Analytics merge count cannot exceed commit count.")

    return {
        "source": {
            "revision": source_commit,
            "ref": source_ref,
            "committed_at": committed_at,
        },
        "scope": {
            "since": since,
            "resolved_since": format_timestamp(
                parse_timestamp(resolved_since, "analytics scope.resolved_since")
            ),
        },
        "repository": {
            "tracked_files": tracked_files,
            "areas": repository_areas,
        },
        "activity": {
            "commits": activity_commits,
            "merges": activity_merges,
            "contributors": analytics_integer(
                activity.get("contributors"), "analytics.activity.contributors"
            ),
            "first_commit_at": first_commit_at,
            "last_commit_at": last_commit_at,
            "weekly": weekly,
        },
        "changes": {
            "files_changed": analytics_integer(
                changes.get("files_changed"), "analytics.changes.files_changed"
            ),
            "insertions": analytics_integer(
                changes.get("insertions"), "analytics.changes.insertions"
            ),
            "deletions": analytics_integer(changes.get("deletions"), "analytics.changes.deletions"),
            "net_lines": analytics_signed_integer(
                changes.get("net_lines"), "analytics.changes.net_lines"
            ),
            "areas": change_areas,
            "hotspots": hotspots,
        },
        "filters": {
            "excluded_tracked_files": analytics_integer(
                filters.get("excluded_tracked_files"),
                "analytics.filters.excluded_tracked_files",
            ),
            "excluded_change_records": analytics_integer(
                filters.get("excluded_change_records"),
                "analytics.filters.excluded_change_records",
            ),
        },
    }


def load_analytics(path: Path | None, source_commit: str) -> dict[str, Any]:
    """Load the public analytics summary with honest missing and invalid states."""

    if path is None or not path.is_file() or path.stat().st_size == 0:
        return analytics_projection(
            "unavailable",
            "No commit-scoped repository analytics summary is available.",
        )
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, RecursionError):
        return analytics_projection("invalid", "Repository analytics is malformed JSON.")
    if not isinstance(document, dict):
        return analytics_projection("invalid", "Repository analytics must be an object.")
    try:
        summary = validate_analytics(document, source_commit)
    except DashboardInputError as error:
        return analytics_projection("invalid", str(error))
    return {
        "availability": "available",
        "message": "Commit-scoped repository analytics is available.",
        "summary": summary,
    }


def anatomy_projection(availability: str, message: str) -> dict[str, Any]:
    """Build an explicit repository-anatomy availability wrapper."""

    return {"availability": availability, "message": message, "summary": None}


def tree_count(value: Any, label: str) -> int:
    """Validate one non-negative repository-tree count."""

    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise DashboardInputError(f"{label} must be a non-negative integer.")
    return value


def validate_tree_path(value: Any, *, label: str, root: bool = False) -> str:
    """Validate one canonical repository-relative POSIX path."""

    if not isinstance(value, str) or not value:
        raise DashboardInputError(f"{label} must be non-empty.")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise DashboardInputError(f"{label} must contain valid UTF-8 text.") from error
    if root:
        if value != ".":
            raise DashboardInputError("The repository-tree root path must be '.'.")
        return value
    parts = value.split("/")
    if value.startswith("/") or "\\" in value or any(part in {"", ".", ".."} for part in parts):
        raise DashboardInputError(f"{label} must be a canonical repository-relative path.")
    return value


def validate_tree_node(
    candidate: Any,
    *,
    parent_path: str | None,
    depth: int,
    budget: list[int],
) -> tuple[dict[str, Any], dict[str, int], int]:
    """Validate and sanitize one bounded repository-tree node recursively."""

    if not isinstance(candidate, dict):
        raise DashboardInputError("Repository-tree nodes must be objects.")
    if depth > MAX_TREE_DEPTH:
        raise DashboardInputError(f"Repository tree exceeds depth {MAX_TREE_DEPTH}.")
    budget[0] += 1
    if budget[0] > MAX_TREE_NODES:
        raise DashboardInputError(f"Repository tree exceeds {MAX_TREE_NODES} nodes.")

    name = candidate.get("name")
    node_type = candidate.get("type")
    if not isinstance(name, str) or not name or "/" in name or "\\" in name:
        raise DashboardInputError("Repository-tree node names must be non-empty path segments.")
    try:
        name.encode("utf-8")
    except UnicodeEncodeError as error:
        raise DashboardInputError("Repository-tree node names must be valid UTF-8 text.") from error
    if name in {".", ".."}:
        raise DashboardInputError("Repository-tree node names may not be dot segments.")
    if node_type not in TREE_NODE_TYPES:
        raise DashboardInputError("Repository-tree nodes contain an unsupported type.")

    is_root = parent_path is None
    path = validate_tree_path(
        candidate.get("path"), label="repository-tree node path", root=is_root
    )
    if not is_root:
        expected_path = name if parent_path == "." else f"{parent_path}/{name}"
        if path != expected_path:
            raise DashboardInputError("Repository-tree child paths must match their hierarchy.")

    if node_type != "directory":
        if any(key in candidate for key in ("children", "descendants", "truncated")):
            raise DashboardInputError(
                "Repository-tree leaf nodes may not contain directory fields."
            )
        counts = {
            "directories": 0,
            "files": int(node_type == "file"),
            "symlinks": int(node_type == "symlink"),
            "submodules": int(node_type == "submodule"),
        }
        return {"name": name, "path": path, "type": node_type}, counts, depth

    children = candidate.get("children")
    descendants = candidate.get("descendants")
    if not isinstance(children, list) or not isinstance(descendants, dict):
        raise DashboardInputError("Repository-tree directories require children and descendants.")
    if candidate.get("truncated") not in (None, True):
        raise DashboardInputError("Repository-tree truncated may only be true when present.")

    sanitized_children: list[dict[str, Any]] = []
    calculated = {"directories": 0, "files": 0, "symlinks": 0, "submodules": 0}
    deepest = depth
    child_names: set[str] = set()
    for child in children:
        sanitized, child_counts, child_depth = validate_tree_node(
            child,
            parent_path=path,
            depth=depth + 1,
            budget=budget,
        )
        if sanitized["name"] in child_names:
            raise DashboardInputError("Repository-tree sibling names must be unique.")
        child_names.add(sanitized["name"])
        sanitized_children.append(sanitized)
        if sanitized["type"] == "directory":
            calculated["directories"] += 1
        for key, value in child_counts.items():
            calculated[key] += value
        deepest = max(deepest, child_depth)

    declared = {
        key: tree_count(descendants.get(key), f"repository-tree descendants.{key}")
        for key in ("directories", "files", "symlinks", "submodules")
    }
    if declared != calculated:
        raise DashboardInputError("Repository-tree descendant counts do not match visible nodes.")
    sanitized_directory: dict[str, Any] = {
        "name": name,
        "path": path,
        "type": node_type,
        "children": sanitized_children,
        "descendants": declared,
    }
    if candidate.get("truncated") is True:
        sanitized_directory["truncated"] = True
    return sanitized_directory, calculated, deepest


def validate_repository_tree(document: dict[str, Any], source_commit: str) -> dict[str, Any]:
    """Project the commit-scoped public repository tree used by the explorer."""

    if document.get("schema") != TREE_SCHEMA or document.get("schema_version") != 1:
        raise DashboardInputError("Repository tree uses an incompatible schema.")
    source = require_object(document, "source")
    if source.get("revision") != source_commit:
        raise DashboardInputError("Repository tree does not represent the dashboard source commit.")
    source_ref = source.get("ref")
    source_committed_at = source.get("committed_at")
    if not isinstance(source_ref, str) or not source_ref:
        raise DashboardInputError("Repository-tree source.ref must be non-empty.")
    if not isinstance(source_committed_at, str):
        raise DashboardInputError("Repository-tree source.committed_at must be RFC 3339.")
    committed_at = format_timestamp(
        parse_timestamp(source_committed_at, "repository-tree source.committed_at")
    )
    budget = [0]
    tree, counts, max_depth = validate_tree_node(
        document.get("tree"),
        parent_path=None,
        depth=0,
        budget=budget,
    )
    if tree["type"] != "directory":
        raise DashboardInputError("Repository-tree root must be a directory.")
    return {
        "source": {
            "revision": source_commit,
            "ref": source_ref,
            "committed_at": committed_at,
        },
        "counts": counts,
        "node_count": budget[0],
        "max_depth": max_depth,
        "tree": tree,
    }


def load_repository_tree(path: Path | None, source_commit: str) -> dict[str, Any]:
    """Load repository anatomy with honest missing and invalid states."""

    if path is None or not path.is_file() or path.stat().st_size == 0:
        return anatomy_projection(
            "unavailable",
            "No commit-scoped repository tree is available.",
        )
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, RecursionError):
        return anatomy_projection("invalid", "Repository tree is malformed JSON.")
    if not isinstance(document, dict):
        return anatomy_projection("invalid", "Repository tree must be an object.")
    try:
        summary = validate_repository_tree(document, source_commit)
    except DashboardInputError as error:
        return anatomy_projection("invalid", str(error))
    return {
        "availability": "available",
        "message": "Commit-scoped repository anatomy is available.",
        "summary": summary,
    }


def run_git(repository_root: Path, *arguments: str) -> str:
    """Run a read-only Git query and return normalized stdout."""

    result = subprocess.run(
        ["git", "-C", str(repository_root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def is_test_artifact(path: str) -> bool:
    """Identify tracked test code and fixtures across common ecosystems."""

    parts = path.casefold().split("/")
    name = parts[-1]
    test_directories = {"test", "tests", "spec", "specs", "__tests__"}
    if any(part in test_directories for part in parts[:-1]):
        return True
    if name.startswith(("test_", "spec_")):
        return True
    return any(
        marker in name
        for marker in (
            "_test.",
            "_spec.",
            ".test.",
            ".spec.",
        )
    ) or name.endswith((".bats", "test.java", "tests.java"))


def collect_vitality(
    repository_root: Path,
    repository: str,
    default_branch: str,
    source_commit: str,
    as_of: datetime,
) -> dict[str, Any]:
    """Collect deterministic repository counts without exposing contributor identities."""

    try:
        resolved_commit = run_git(repository_root, "rev-parse", source_commit)
        if not FULL_SHA_PATTERN.fullmatch(resolved_commit):
            raise DashboardInputError("Git did not resolve a full source commit.")
        committed_at = run_git(
            repository_root, "show", "--no-patch", "--format=%cI", resolved_commit
        )
        since_30_days = format_timestamp(as_of - timedelta(days=30))
        since_90_days = format_timestamp(as_of - timedelta(days=90))
        until = format_timestamp(as_of)
        commits_30_days = int(
            run_git(
                repository_root,
                "rev-list",
                "--count",
                f"--since={since_30_days}",
                f"--until={until}",
                resolved_commit,
            )
            or "0"
        )
        contributor_emails = run_git(
            repository_root,
            "log",
            f"--since={since_90_days}",
            f"--until={until}",
            "--format=%ae",
            resolved_commit,
        ).splitlines()
        contributors_90_days = len(
            {email.strip().casefold() for email in contributor_emails if email.strip()}
        )
        tracked_paths = [
            line
            for line in run_git(
                repository_root, "ls-tree", "-r", "--name-only", resolved_commit
            ).splitlines()
            if line
        ]
        tracked_files = len(tracked_paths)
        history_complete = (
            run_git(repository_root, "rev-parse", "--is-shallow-repository") == "false"
        )
        workflow_count = sum(
            path.startswith(".github/workflows/")
            and path.rsplit("/", maxsplit=1)[-1].endswith((".yaml", ".yml"))
            for path in tracked_paths
        )
        action_count = sum(
            path.startswith(".github/actions/")
            and path.endswith("/action.yml")
            and path.count("/") == 3
            for path in tracked_paths
        )
        test_artifact_count = sum(is_test_artifact(path) for path in tracked_paths)
    except (DashboardInputError, OSError, subprocess.CalledProcessError, ValueError):
        return {
            "execution": {
                "state": "failure",
                "message": "Repository vitality could not be collected from this checkout.",
            },
            "repository": repository,
            "default_branch": default_branch,
            "source_commit": source_commit,
            "metrics": {},
        }
    return {
        "execution": {
            "state": "success",
            "message": "Repository vitality was collected from the local checkout.",
        },
        "repository": repository,
        "default_branch": default_branch,
        "source_commit": resolved_commit,
        "latest_commit": {
            "short_sha": resolved_commit[:12],
            "committed_at": format_timestamp(parse_timestamp(committed_at, "commit timestamp")),
        },
        "metrics": {
            "commits_30_days": commits_30_days,
            "contributors_90_days": contributors_90_days,
            "tracked_files": tracked_files,
            "workflows": workflow_count,
            "composite_actions": action_count,
            "test_artifacts": test_artifact_count,
            "history_complete": history_complete,
        },
    }


def count_states(producers: dict[str, dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Aggregate independent state dimensions without inventing a global score."""

    counts = {
        "availability": {state: 0 for state in sorted(AVAILABILITY_STATES)},
        "execution": {state: 0 for state in sorted(EXECUTION_STATES)},
        "findings": {state: 0 for state in sorted(FINDING_STATES)},
        "freshness": {state: 0 for state in sorted(FRESHNESS_STATES)},
    }
    for projection in producers.values():
        counts["availability"][projection["availability"]] += 1
        counts["execution"][projection["execution"]["state"]] += 1
        counts["findings"][projection["findings"]["state"]] += 1
        counts["freshness"][projection["freshness"]["state"]] += 1
    return counts


def build_dashboard(
    *,
    repository_root: Path,
    reports_root: Path,
    repository: str,
    default_branch: str,
    source_commit: str,
    as_of: datetime,
    analytics_summary: Path | None = None,
    repository_tree: Path | None = None,
) -> dict[str, Any]:
    """Build the complete public dashboard model."""

    if not FULL_SHA_PATTERN.fullmatch(source_commit):
        raise DashboardInputError("source-commit must be a full lowercase SHA")
    if not REPOSITORY_PATTERN.fullmatch(repository) or not default_branch:
        raise DashboardInputError(
            "repository must use owner/name form and default-branch must be non-empty"
        )
    producers = {
        producer: load_report(
            reports_root,
            producer,
            repository,
            source_commit,
            as_of,
        )
        for producer in PRODUCERS
    }
    vitality = collect_vitality(repository_root, repository, default_branch, source_commit, as_of)
    return {
        "schema": DASHBOARD_SCHEMA,
        "schema_version": 1,
        "generated_at": format_timestamp(as_of),
        "repository": {
            "name": repository,
            "default_branch": default_branch,
            "source_commit": source_commit,
        },
        "states": count_states(producers),
        "producers": producers,
        "analytics": load_analytics(analytics_summary, source_commit),
        "anatomy": load_repository_tree(repository_tree, source_commit),
        "vitality": vitality,
    }


def build_bundle_provenance(
    *,
    repository: str,
    source_commit: str,
    generated_at: datetime,
    timestamp_source: str,
    generator_version: str,
    generator_repository: str,
    generator_ref: str,
    generator_commit: str,
    generator_immutable: bool,
    consumer_visibility: str,
) -> dict[str, Any]:
    """Build deterministic Relay and consumer provenance outside dashboard v3."""

    if timestamp_source not in {"consumer-source-commit", "explicit-input"}:
        raise DashboardInputError("timestamp-source is unsupported")
    if generator_repository != GENERATOR_REPOSITORY:
        raise DashboardInputError("generator-repository must identify egohygiene/relay")
    if not re.fullmatch(
        r"[1-9][0-9]*\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)",
        generator_version,
    ):
        raise DashboardInputError("generator-version must use MAJOR.MINOR.PATCH")
    if generator_commit and not FULL_SHA_PATTERN.fullmatch(generator_commit):
        raise DashboardInputError("generator-commit must be empty or a full lowercase SHA")
    exact_ref_match = re.search(r"(?:^|@)([0-9a-f]{40})$", generator_ref)
    exact_ref_commit = exact_ref_match.group(1) if exact_ref_match else None
    if exact_ref_commit is not None and exact_ref_commit != generator_commit:
        raise DashboardInputError("immutable generator-ref must match generator-commit")
    if not isinstance(generator_immutable, bool) or generator_immutable is not bool(
        exact_ref_commit
    ):
        raise DashboardInputError("generator immutable state does not match generator-ref")
    if consumer_visibility not in CONSUMER_VISIBILITIES:
        raise DashboardInputError("consumer-visibility is unsupported")
    classification = "public-safe" if consumer_visibility == "public" else "internal-only"
    return {
        "schema": PROVENANCE_SCHEMA,
        "schema_version": PROVENANCE_SCHEMA_VERSION,
        "generator": {
            "name": GENERATOR_NAME,
            "version": generator_version,
            "repository": generator_repository,
            "source_ref": generator_ref,
            "source_commit": generator_commit or None,
            "immutable": generator_immutable,
        },
        "consumer": {
            "repository": repository,
            "source_commit": source_commit,
            "visibility": consumer_visibility,
        },
        "contracts": {
            "dashboard": {"schema": DASHBOARD_SCHEMA, "schema_version": 1},
            "analytics": {"schema": ANALYTICS_SCHEMA, "schema_version": 1},
            "repository_tree": {"schema": TREE_SCHEMA, "schema_version": 1},
            "repository_report": {"schema": REPORT_SCHEMA, "schema_version": 1},
        },
        "generated_at": format_timestamp(generated_at),
        "timestamp_source": timestamp_source,
        "projection": {
            "route": "/intelligence/",
            "classification": classification,
            "deployment_authority": "consumer",
        },
    }


def escaped(value: Any) -> str:
    """Escape a scalar for safe HTML text or attribute output."""

    return html.escape(str(value), quote=True)


def display_count(value: Any) -> str:
    """Render an optional count without turning missing data into zero."""

    return "—" if value is None else str(value)


def badge(label: str, state: str) -> str:
    """Render a textual state badge whose meaning is not color-only."""

    return f'<span class="badge state-{escaped(state)}">{escaped(label)}: {escaped(state)}</span>'


def metric_rows(producer: str, projection: dict[str, Any]) -> list[tuple[str, str]]:
    """Return card-specific metric labels and values."""

    metrics = projection["metrics"]
    if producer == "osv":
        severity = metrics.get("severity", {})
        severe: int | None = 0
        if isinstance(severity, dict):
            critical = metric_integer(severity.get("critical", 0))
            high = metric_integer(severity.get("high", 0))
            severe = critical + high if critical is not None and high is not None else None
        return [
            ("Affected packages", display_count(metrics.get("affected_packages"))),
            ("High or critical", str(severe)),
            ("Ecosystems", display_count(metrics.get("ecosystems"))),
            ("Policy threshold", display_count(metrics.get("threshold"))),
        ]
    if producer == "megalinter":
        tools = metrics.get("tools", {})
        diagnostics = metrics.get("diagnostics", {})
        errors = metric_integer(diagnostics.get("errors"))
        warnings = metric_integer(diagnostics.get("warnings"))
        diagnostic_total = (
            errors + warnings if errors is not None and warnings is not None else None
        )
        return [
            ("Active tools", display_count(tools.get("active"))),
            ("Passing tools", display_count(tools.get("passed"))),
            ("Blocking tools", display_count(tools.get("blocking"))),
            ("Diagnostics", display_count(diagnostic_total)),
        ]
    return [
        ("Aggregate source", display_count(metrics.get("aggregate_source"))),
        ("Checks evaluated", display_count(metrics.get("checks_total"))),
        ("Checks needing attention", display_count(metrics.get("checks_needing_attention"))),
        ("API status", display_count(metrics.get("api_status"))),
    ]


def headline_metric(producer: str, projection: dict[str, Any]) -> str:
    """Return the primary card metric with honest missing-data language."""

    if projection["availability"] != "available":
        return "Data unavailable"
    metrics = projection["metrics"]
    if producer == "osv":
        count = metrics.get("vulnerabilities")
        return f"{display_count(count)} vulnerabilities"
    if producer == "megalinter":
        tools = metrics.get("tools", {})
        passed = display_count(tools.get("passed"))
        active = display_count(tools.get("active"))
        return f"{passed} / {active} tools passing"
    score = metrics.get("aggregate_score")
    return "Aggregate pending" if score is None else f"{score:g} / 10"


def render_links(links: dict[str, str]) -> str:
    """Render allowlisted public links for one producer."""

    labels = {
        "detail": "View details",
        "workflow": "Workflow run",
        "security": "Security findings",
        "source": "Source commit",
    }
    rendered = [
        f'<a href="{escaped(url)}">{labels[key]}</a>'
        for key, url in links.items()
        if key in labels and url
    ]
    return "".join(f"<span>{link}</span>" for link in rendered) or (
        "<span>No public links available.</span>"
    )


def render_producer_card(producer: str, projection: dict[str, Any]) -> str:
    """Render one accessible producer card."""

    rows = "".join(
        f"<div><dt>{escaped(label)}</dt><dd>{escaped(value)}</dd></div>"
        for label, value in metric_rows(producer, projection)
    )
    return f"""<article class="producer-card" aria-labelledby="{producer}-title">
  <p class="card-kicker">{escaped(producer)}</p>
  <h3 id="{producer}-title">{escaped(projection["name"])}</h3>
  <div class="badge-row">
    {badge("Availability", projection["availability"])}
    {badge("Execution", projection["execution"]["state"])}
    {badge("Findings", projection["findings"]["state"])}
    {badge("Freshness", projection["freshness"]["state"])}
  </div>
  <p class="headline-metric">{escaped(headline_metric(producer, projection))}</p>
  <p class="card-message">{escaped(projection["execution"]["message"])}</p>
  <dl class="metric-list">{rows}</dl>
  <div class="link-row">{render_links(projection["links"])}</div>
</article>"""


def compact_number(value: int) -> str:
    """Render a compact, deterministic integer label."""

    if abs(value) < 1_000:
        return str(value)
    for divisor, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if abs(value) >= divisor:
            scaled = value / divisor
            precision = 0 if abs(scaled) >= 10 else 1
            return f"{scaled:.{precision}f}{suffix}".replace(".0", "")
    return str(value)


def render_data_table(
    caption: str,
    headers: tuple[str, ...],
    rows: list[tuple[Any, ...]],
) -> str:
    """Render a compact table fallback for a visual chart."""

    header_cells = "".join(f'<th scope="col">{escaped(header)}</th>' for header in headers)
    body_rows = "".join(
        "<tr>"
        + "".join(
            f'<th scope="row">{escaped(value)}</th>' if index == 0 else f"<td>{escaped(value)}</td>"
            for index, value in enumerate(row)
        )
        + "</tr>"
        for row in rows
    )
    return f"""<details class="data-table">
  <summary>View data table</summary>
  <div class="table-scroll">
    <table>
      <caption class="sr-only">{escaped(caption)}</caption>
      <thead><tr>{header_cells}</tr></thead>
      <tbody>{body_rows}</tbody>
    </table>
  </div>
</details>"""


def chart_card(
    *,
    identifier: str,
    kicker: str,
    title: str,
    description: str,
    visualization: str,
    table: str,
    wide: bool = False,
) -> str:
    """Wrap one chart and its table fallback in the shared visual system."""

    wide_class = " chart-card-wide" if wide else ""
    return f"""<article class="chart-card{wide_class}" aria-labelledby="{identifier}-heading">
  <div class="chart-card-heading">
    <div>
      <p class="card-kicker">{escaped(kicker)}</p>
      <h3 id="{identifier}-heading">{escaped(title)}</h3>
    </div>
    <p>{escaped(description)}</p>
  </div>
  {visualization}
  {table}
</article>"""


def render_activity_chart(summary: dict[str, Any]) -> str:
    """Render weekly commits and merges as an ordered line chart."""

    weekly = summary["activity"]["weekly"]
    if not weekly:
        return chart_card(
            identifier="activity-chart",
            kicker="Ordered trend",
            title="Weekly activity",
            description="No commits fall inside the represented activity window.",
            visualization='<div class="chart-empty">No activity points available.</div>',
            table="",
            wide=True,
        )
    width = 820
    height = 320
    left = 52
    right = 24
    top = 28
    bottom = 54
    plot_width = width - left - right
    plot_height = height - top - bottom
    maximum = max([1, *(row["commits"] for row in weekly)])

    def coordinates(metric: str) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        for index, row in enumerate(weekly):
            x = left + (
                plot_width / 2 if len(weekly) == 1 else plot_width * index / (len(weekly) - 1)
            )
            y = top + plot_height * (1 - row[metric] / maximum)
            points.append((x, y))
        return points

    commit_points = coordinates("commits")
    merge_points = coordinates("merges")
    grid = []
    for index in range(5):
        y = top + plot_height * index / 4
        value = round(maximum * (1 - index / 4))
        grid.append(
            f'<line class="chart-grid-line" x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" />'
            f'<text class="chart-axis-label" x="{left - 10}" y="{y + 4:.1f}" text-anchor="end">{value}</text>'
        )
    label_count = min(6, len(weekly))
    label_indexes = (
        {0}
        if label_count == 1
        else {round(index * (len(weekly) - 1) / (label_count - 1)) for index in range(label_count)}
    )
    x_labels = []
    for index in sorted(label_indexes):
        date = datetime.fromisoformat(weekly[index]["week"])
        label = f"{date.strftime('%b')} {date.day}"
        x_labels.append(
            f'<text class="chart-axis-label" x="{commit_points[index][0]:.1f}" y="{height - 20}" text-anchor="middle">{escaped(label)}</text>'
        )

    def polyline(points: list[tuple[float, float]], css_class: str) -> str:
        serialized = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        markers = "".join(
            f'<circle class="{css_class}-point" cx="{x:.1f}" cy="{y:.1f}" r="4" />'
            for x, y in points
        )
        return f'<polyline class="{css_class}" points="{serialized}" />{markers}'

    visualization = f"""<figure class="chart-figure">
  <svg class="chart-svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="activity-svg-title activity-svg-desc">
    <title id="activity-svg-title">Weekly repository commits and merges</title>
    <desc id="activity-svg-desc">An ordered line chart containing every weekly point in the public analytics window.</desc>
    {"".join(grid)}
    {polyline(commit_points, "chart-line-commits")}
    {polyline(merge_points, "chart-line-merges")}
    {"".join(x_labels)}
  </svg>
  <figcaption class="chart-legend">
    <span><i class="legend-line commits"></i>Commits</span>
    <span><i class="legend-line merges"></i>Merges</span>
  </figcaption>
</figure>"""
    table = render_data_table(
        "Weekly repository activity",
        ("Week", "Commits", "Merges"),
        [(row["week"], row["commits"], row["merges"]) for row in weekly],
    )
    return chart_card(
        identifier="activity-chart",
        kicker="Ordered trend",
        title="Weekly activity",
        description=(
            f"{summary['activity']['commits']} commits and "
            f"{summary['activity']['merges']} merges since {summary['scope']['resolved_since'][:10]}."
        ),
        visualization=visualization,
        table=table,
        wide=True,
    )


def repository_composition(summary: dict[str, Any]) -> list[dict[str, Any]]:
    """Bound repository composition to five named slices plus Other."""

    areas = summary["repository"]["areas"]
    top = areas[:5]
    remainder = max(
        0,
        summary["repository"]["tracked_files"] - sum(row["file_count"] for row in top),
    )
    return [*top, *([{"name": "Other", "file_count": remainder}] if remainder else [])]


def render_composition_chart(summary: dict[str, Any]) -> str:
    """Render repository file composition as a bounded donut chart."""

    composition = repository_composition(summary)
    total = sum(row["file_count"] for row in composition)
    radius = 82
    circumference = 2 * pi * radius
    offset = 0.0
    segments = []
    legend = []
    for index, row in enumerate(composition):
        fraction = row["file_count"] / total if total else 0
        length = circumference * fraction
        segments.append(
            f'<circle class="donut-slice slice-{index}" cx="140" cy="140" r="{radius}" '
            f'stroke-dasharray="{length:.3f} {circumference - length:.3f}" '
            f'stroke-dashoffset="{-offset:.3f}" />'
        )
        percentage = fraction * 100
        legend.append(
            f'<li><i class="legend-swatch slice-{index}"></i><span>{escaped(row["name"])}</span>'
            f"<strong>{row['file_count']} · {percentage:.1f}%</strong></li>"
        )
        offset += length
    visualization = f"""<figure class="chart-figure donut-figure">
  <svg class="donut-chart" viewBox="0 0 280 280" role="img" aria-labelledby="composition-svg-title composition-svg-desc">
    <title id="composition-svg-title">Repository file composition</title>
    <desc id="composition-svg-desc">A donut chart showing the five largest repository areas and an Other slice.</desc>
    <circle class="donut-track" cx="140" cy="140" r="{radius}" />
    <g transform="rotate(-90 140 140)">{"".join(segments)}</g>
    <text class="donut-total" x="140" y="132" text-anchor="middle">{compact_number(total)}</text>
    <text class="donut-label" x="140" y="158" text-anchor="middle">source files</text>
  </svg>
  <figcaption><ul class="composition-legend">{"".join(legend)}</ul></figcaption>
</figure>"""
    table = render_data_table(
        "Repository composition by area",
        ("Area", "Files", "Share"),
        [
            (
                row["name"],
                row["file_count"],
                f"{(row['file_count'] / total * 100 if total else 0):.1f}%",
            )
            for row in composition
        ],
    )
    return chart_card(
        identifier="composition-chart",
        kicker="Part to whole",
        title="Repository composition",
        description="Generated reports, caches, build outputs, and vendored dependencies are excluded.",
        visualization=visualization,
        table=table,
    )


def render_hotspot_chart(summary: dict[str, Any]) -> str:
    """Render repository-area change concentration as horizontal bars."""

    rows = summary["changes"]["areas"][:8]
    maximum = max([1, *(row["commit_touches"] for row in rows)])
    width = 820
    row_height = 48
    height = 46 + row_height * len(rows)
    label_width = 165
    bar_width = 535
    bars = []
    for index, row in enumerate(rows):
        y = 28 + index * row_height
        rendered_width = bar_width * row["commit_touches"] / maximum
        display_name = row["name"] if len(row["name"]) <= 20 else row["name"][:18] + "…"
        bars.append(
            f'<text class="bar-label" x="0" y="{y + 17}">{escaped(display_name)}</text>'
            f'<rect class="bar-track" x="{label_width}" y="{y}" width="{bar_width}" height="22" rx="7" />'
            f'<rect class="bar-value" x="{label_width}" y="{y}" width="{rendered_width:.1f}" height="22" rx="7" />'
            f'<text class="bar-count" x="{label_width + bar_width + 18}" y="{y + 17}">{row["commit_touches"]}</text>'
        )
    visualization = f"""<figure class="chart-figure">
  <svg class="chart-svg hotspot-chart" viewBox="0 0 {width} {height}" role="img" aria-labelledby="hotspot-svg-title hotspot-svg-desc">
    <title id="hotspot-svg-title">Repository change hotspots</title>
    <desc id="hotspot-svg-desc">A horizontal bar chart ranking repository areas by commit touches.</desc>
    {"".join(bars)}
  </svg>
  <figcaption class="chart-note">Commit touches count how many commits changed files in each repository area.</figcaption>
</figure>"""
    table = render_data_table(
        "Repository change hotspots",
        ("Area", "Commit touches", "Insertions", "Deletions", "Binary changes"),
        [
            (
                row["name"],
                row["commit_touches"],
                row["insertions"],
                row["deletions"],
                row["binary_changes"],
            )
            for row in rows
        ],
    )
    return chart_card(
        identifier="hotspot-chart",
        kicker="Ranked comparison",
        title="Change hotspots",
        description=(
            f"{summary['changes']['files_changed']} source files changed; "
            f"{summary['filters']['excluded_change_records']} generated change records were filtered."
        ),
        visualization=visualization,
        table=table,
        wide=True,
    )


def render_findings_chart(producers: dict[str, dict[str, Any]]) -> str:
    """Render blocking and advisory findings without turning unknown into zero."""

    known_totals = [
        projection["findings"]["total"]
        for projection in producers.values()
        if projection["findings"]["total"] is not None
    ]
    maximum = max([1, *known_totals])
    width = 720
    label_width = 130
    bar_width = 420
    rows = []
    table_rows = []
    for index, producer in enumerate(PRODUCERS):
        projection = producers[producer]
        findings = projection["findings"]
        y = 34 + index * 58
        total = findings["total"]
        table_rows.append(
            (
                producer.upper(),
                projection["availability"],
                display_count(total),
                display_count(findings["blocking"]),
                display_count(findings["advisory"]),
            )
        )
        rows.append(f'<text class="bar-label" x="0" y="{y + 17}">{producer.upper()}</text>')
        if total is None:
            rows.append(
                f'<rect class="finding-unknown" x="{label_width}" y="{y}" width="{bar_width}" height="22" rx="7" />'
                f'<text class="bar-count" x="{label_width + bar_width + 18}" y="{y + 17}">unknown</text>'
            )
            continue
        blocking = findings["blocking"] or 0
        advisory = findings["advisory"] or 0
        blocking_width = bar_width * blocking / maximum
        advisory_width = bar_width * advisory / maximum
        rows.append(
            f'<rect class="bar-track" x="{label_width}" y="{y}" width="{bar_width}" height="22" rx="7" />'
            f'<rect class="finding-blocking" x="{label_width}" y="{y}" width="{blocking_width:.1f}" height="22" rx="7" />'
            f'<rect class="finding-advisory" x="{label_width + blocking_width:.1f}" y="{y}" width="{advisory_width:.1f}" height="22" rx="7" />'
            f'<text class="bar-count" x="{label_width + bar_width + 18}" y="{y + 17}">{total}</text>'
        )
    visualization = f"""<figure class="chart-figure">
  <svg class="chart-svg findings-chart" viewBox="0 0 {width} 220" role="img" aria-labelledby="findings-svg-title findings-svg-desc">
    <title id="findings-svg-title">Scanner findings by producer</title>
    <desc id="findings-svg-desc">Horizontal bars distinguish blocking, advisory, clear, and unknown evidence.</desc>
    {"".join(rows)}
  </svg>
  <figcaption class="chart-legend">
    <span><i class="legend-box blocking"></i>Blocking</span>
    <span><i class="legend-box advisory"></i>Advisory</span>
    <span><i class="legend-box unknown"></i>Unknown</span>
  </figcaption>
</figure>"""
    return chart_card(
        identifier="findings-chart",
        kicker="Evidence distribution",
        title="Scanner findings",
        description="Unavailable evidence remains visibly unknown rather than becoming a misleading zero.",
        visualization=visualization,
        table=render_data_table(
            "Scanner findings by producer",
            ("Producer", "Availability", "Total", "Blocking", "Advisory"),
            table_rows,
        ),
    )


def freshness_label(freshness: dict[str, Any]) -> str:
    """Describe one producer freshness window in human units."""

    remaining = freshness.get("remaining_days")
    if remaining is None:
        return "No freshness evidence"
    if remaining > 1:
        return f"{remaining} days until stale"
    if remaining == 1:
        return "1 day until stale"
    if remaining == 0:
        return "Freshness boundary reached"
    if remaining == -1:
        return "1 day stale"
    return f"{abs(remaining)} days stale"


def render_freshness_panel(producers: dict[str, dict[str, Any]]) -> str:
    """Render evidence clocks as accessible progress meters."""

    rows = []
    table_rows = []
    for producer in PRODUCERS:
        freshness = producers[producer]["freshness"]
        percent = freshness.get("elapsed_percent")
        label = freshness_label(freshness)
        meter = (
            f'<progress value="{percent}" max="100" aria-label="{escaped(producer.upper())} freshness window: {escaped(label)}">{percent}%</progress>'
            if percent is not None
            else '<div class="unknown-meter" aria-hidden="true"></div>'
        )
        rows.append(
            f"""<div class="freshness-row">
  <div><strong>{producer.upper()}</strong>{badge("Freshness", freshness["state"])}</div>
  {meter}
  <p>{escaped(label)}</p>
</div>"""
        )
        table_rows.append(
            (
                producer.upper(),
                freshness["state"],
                display_count(freshness.get("expires_at")),
                label,
            )
        )
    return chart_card(
        identifier="freshness-chart",
        kicker="Evidence clocks",
        title="Report freshness",
        description="Meters show elapsed evidence windows, not a synthetic health score.",
        visualization=f'<div class="freshness-list">{"".join(rows)}</div>',
        table=render_data_table(
            "Report freshness by producer",
            ("Producer", "State", "Expires at", "Window"),
            table_rows,
        ),
    )


def render_analytics_section(dashboard: dict[str, Any]) -> str:
    """Render repository statistics and scanner evidence visualizations."""

    analytics = dashboard["analytics"]
    summary = analytics.get("summary")
    if analytics["availability"] == "available" and isinstance(summary, dict):
        repository_charts = (
            render_activity_chart(summary)
            + render_composition_chart(summary)
            + render_hotspot_chart(summary)
        )
    else:
        repository_charts = f"""<article class="chart-card chart-card-wide chart-empty-card">
  <p class="card-kicker">Repository analytics</p>
  <h3>Statistical snapshots unavailable</h3>
  <p>{escaped(analytics["message"])}</p>
</article>"""
    return f"""<section class="section" aria-labelledby="analytics-heading">
  <div class="section-heading">
    <div>
      <p class="eyebrow">Statistical snapshots</p>
      <h2 id="analytics-heading">Repository analytics</h2>
    </div>
    <p>{escaped(analytics["message"])} Generated and vendored noise is excluded before visualization.</p>
  </div>
  <div class="analytics-grid">{repository_charts}</div>
  <div class="evidence-grid">
    {render_findings_chart(dashboard["producers"])}
    {render_freshness_panel(dashboard["producers"])}
  </div>
</section>"""


def repository_source_url(
    repository: str,
    source_commit: str,
    path: str,
    node_type: str,
) -> str:
    """Build a source-pinned GitHub URL without accepting arbitrary origins."""

    parts = repository.split("/")
    if len(parts) != 2 or not all(re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in parts):
        return ""
    owner, name = (quote(part, safe="") for part in parts)
    kind = "tree" if node_type in {"directory", "submodule"} else "blob"
    base = f"https://github.com/{owner}/{name}/{kind}/{source_commit}"
    return base if path == "." else f"{base}/{quote(path, safe='/')}"


def tree_icon(node_type: str) -> str:
    """Render one consistent icon from the page-local repository icon sprite."""

    return (
        '<svg class="tree-icon" aria-hidden="true" width="18" height="18">'
        f'<use href="#tree-icon-{escaped(node_type)}"></use></svg>'
    )


def tree_icon_sprite() -> str:
    """Define the repository icon set once without an external dependency."""

    return """<svg class="tree-icon-sprite" aria-hidden="true">
  <symbol id="tree-icon-directory" viewBox="0 0 24 24"><path d="M3 6.5a2 2 0 0 1 2-2h5l2 2H19a2 2 0 0 1 2 2v8.75a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 17.25Z" /></symbol>
  <symbol id="tree-icon-file" viewBox="0 0 24 24"><path d="M6 3.5h7l5 5v12H6Z" /><path d="M13 3.5v5h5" /></symbol>
  <symbol id="tree-icon-symlink" viewBox="0 0 24 24"><path d="M9.5 14.5 14.5 9.5" /><path d="M7.25 16.75 5.5 18.5a3.54 3.54 0 0 1-5-5l3-3a3.54 3.54 0 0 1 5 0" transform="translate(3 -1)" /><path d="m13.5 6.5 2-2a3.54 3.54 0 0 1 5 5l-3 3a3.54 3.54 0 0 1-5 0" /></symbol>
  <symbol id="tree-icon-submodule" viewBox="0 0 24 24"><path d="m12 2 9 5-9 5-9-5Z" /><path d="m3 12 9 5 9-5" /><path d="m3 17 9 5 9-5" /></symbol>
</svg>"""


def render_tree_node(
    node: dict[str, Any],
    *,
    repository: str,
    source_commit: str,
    depth: int,
) -> str:
    """Render one progressively enhanced, source-linked anatomy node."""

    node_type = node["type"]
    source_url = repository_source_url(repository, source_commit, node["path"], node_type)
    source_link = (
        f'<a class="tree-source-link" href="{escaped(source_url)}">View at source commit</a>'
        if source_url
        else ""
    )
    common = (
        f'class="tree-node tree-node-{escaped(node_type)}" '
        f'data-search="{escaped(node["path"].casefold())}" '
        f'data-kind="{escaped(node_type)}"'
    )
    if node_type != "directory":
        name = (
            f'<a class="tree-entry-link" href="{escaped(source_url)}">{escaped(node["name"])}</a>'
            if source_url
            else f'<span class="tree-entry-name">{escaped(node["name"])}</span>'
        )
        return f"""<li {common}>
  <div class="tree-leaf-row">{tree_icon(node_type)}{name}<span class="tree-type">{escaped(node_type)}</span></div>
</li>"""

    counts = node["descendants"]
    entry_count = sum(counts.values())
    children = "".join(
        render_tree_node(
            child,
            repository=repository,
            source_commit=source_commit,
            depth=depth + 1,
        )
        for child in node["children"]
    )
    truncated = (
        '<p class="tree-truncated">Additional depth was intentionally truncated.</p>'
        if node.get("truncated")
        else ""
    )
    open_attribute = " open" if depth == 0 else ""
    return f"""<li {common}>
  <details data-tree-directory{open_attribute}>
    <summary>{tree_icon(node_type)}<span class="tree-entry-name">{escaped(node["name"])}</span><span class="tree-count">{entry_count} descendants</span></summary>
    <div class="tree-directory-body">
      {source_link}
      {truncated}
      <ul class="tree-children">{children}</ul>
    </div>
  </details>
</li>"""


def render_anatomy_section(dashboard: dict[str, Any]) -> str:
    """Render the searchable repository anatomy explorer."""

    anatomy = dashboard["anatomy"]
    summary = anatomy.get("summary")
    heading = """<div class="section-heading">
    <div>
      <p class="eyebrow">Repository anatomy</p>
      <h2 id="anatomy-heading">Explore the source tree</h2>
    </div>
    <p>Search and expand a public-safe tree pinned to the exact dashboard commit.</p>
  </div>"""
    if anatomy["availability"] != "available" or not isinstance(summary, dict):
        return f"""<section class="section" aria-labelledby="anatomy-heading">
  {heading}
  <article class="chart-card chart-empty-card">
    <p class="card-kicker">Tree contract</p>
    <h3>Repository anatomy unavailable</h3>
    <p>{escaped(anatomy["message"])}</p>
  </article>
</section>"""

    tree = summary["tree"]
    counts = summary["counts"]
    source_url = repository_source_url(
        dashboard["repository"]["name"],
        dashboard["repository"]["source_commit"],
        ".",
        "directory",
    )
    root_link = (
        f'<a href="{escaped(source_url)}">Open complete tree at source commit</a>'
        if source_url
        else ""
    )
    children = "".join(
        render_tree_node(
            child,
            repository=dashboard["repository"]["name"],
            source_commit=dashboard["repository"]["source_commit"],
            depth=0,
        )
        for child in tree["children"]
    )
    visible_entries = max(0, summary["node_count"] - 1)
    return f"""<section class="section" aria-labelledby="anatomy-heading">
  {heading}
  <article class="anatomy-card" data-repository-explorer>
    <div class="anatomy-overview">
      <div>
        <p class="card-kicker">{escaped(tree["name"])}</p>
        <p class="anatomy-total">{visible_entries} visible entries</p>
        <p class="anatomy-meta">{counts["directories"]} directories · {counts["files"]} files · {counts["symlinks"]} symlinks · {counts["submodules"]} submodules · depth {summary["max_depth"]}</p>
      </div>
      <p>{root_link}</p>
    </div>
    <div class="tree-toolbar">
      <div class="tree-search-field">
        <label for="repository-tree-search">Search paths</label>
        <input id="repository-tree-search" type="search" placeholder="Filter files and directories…" autocomplete="off" spellcheck="false" data-tree-search />
      </div>
      <div class="tree-actions" aria-label="Tree controls">
        <button type="button" data-tree-expand>Expand all</button>
        <button type="button" data-tree-collapse>Collapse all</button>
      </div>
    </div>
    <p class="tree-result-status" data-tree-status aria-live="polite">Showing all {visible_entries} entries.</p>
    <div class="tree-viewport">
      {tree_icon_sprite()}
      <ul class="repository-tree" data-tree-root>{children}</ul>
      <p class="tree-empty" data-tree-empty hidden>No paths match this search.</p>
    </div>
    <noscript><p class="tree-noscript">Search controls require JavaScript; the complete collapsible tree remains available.</p></noscript>
  </article>
</section>"""


def render_html(dashboard: dict[str, Any]) -> str:
    """Render the complete framework-free dashboard document."""

    repository = dashboard["repository"]
    states = dashboard["states"]
    producer_cards = "\n".join(
        render_producer_card(producer, dashboard["producers"][producer]) for producer in PRODUCERS
    )
    vitality = dashboard["vitality"]
    vitality_metrics = vitality.get("metrics", {})
    vitality_items = [
        ("Commits", vitality_metrics.get("commits_30_days"), "in the last 30 days"),
        ("Contributors", vitality_metrics.get("contributors_90_days"), "in the last 90 days"),
        ("Tracked files", vitality_metrics.get("tracked_files"), "at the represented commit"),
        ("Workflows", vitality_metrics.get("workflows"), "GitHub Actions workflows"),
        ("Actions", vitality_metrics.get("composite_actions"), "local composite actions"),
        (
            "Test artifacts",
            vitality_metrics.get("test_artifacts"),
            "tracked test files and fixtures",
        ),
        (
            "History",
            "complete" if vitality_metrics.get("history_complete") else "shallow",
            "checkout depth",
        ),
        ("Default branch", repository["default_branch"], "repository target"),
    ]
    vitality_cards = "".join(
        f"""<article class="vitality-card">
  <p class="card-kicker">{escaped(label)}</p>
  <p class="vitality-value">{escaped(display_count(value))}</p>
  <p class="vitality-label">{escaped(description)}</p>
</article>"""
        for label, value, description in vitality_items
    )
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="color-scheme" content="dark" />
    <meta name="description" content="Repository intelligence for {escaped(repository["name"])}." />
    <title>Repository intelligence · {escaped(repository["name"])}</title>
    <link rel="stylesheet" href="./styles.css" />
  </head>
  <body>
    <a class="skip-link" href="#main-content">Skip to dashboard</a>
    <header class="hero">
      <div class="shell">
        <p class="eyebrow">{escaped(repository["name"])}</p>
        <h1 class="gradient-text">Repository intelligence</h1>
        <p class="lede">A transparent view of dependency risk, code quality, supply-chain posture, and repository vitality. Scanner execution and findings remain separate.</p>
        <div class="meta-row">
          <span class="meta-chip">Branch: {escaped(repository["default_branch"])}</span>
          <span class="meta-chip">Commit: {escaped(repository["source_commit"][:12])}</span>
          <span class="meta-chip">As of: {escaped(dashboard["generated_at"])}</span>
        </div>
      </div>
    </header>
    <main id="main-content" class="shell">
      <section class="section" aria-labelledby="state-heading">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Independent dimensions</p>
            <h2 id="state-heading">Current state</h2>
          </div>
          <p>No synthetic health score. These counts preserve what ran, what it found, and whether its evidence is current.</p>
        </div>
        <div class="status-grid">
          <article class="panel">
            <p class="panel-label">Execution</p>
            <p class="panel-value">{states["execution"]["success"]} successful · {states["execution"]["failure"]} failed · {states["execution"]["cancelled"]} cancelled · {states["execution"]["unknown"]} unknown</p>
          </article>
          <article class="panel">
            <p class="panel-label">Findings</p>
            <p class="panel-value">{states["findings"]["clear"]} clear · {states["findings"]["attention"]} attention · {states["findings"]["blocked"]} blocked · {states["findings"]["unknown"]} unknown</p>
          </article>
          <article class="panel">
            <p class="panel-label">Freshness</p>
            <p class="panel-value">{states["freshness"]["fresh"]} fresh · {states["freshness"]["stale"]} stale · {states["freshness"]["unknown"]} unknown</p>
          </article>
        </div>
      </section>
      {render_analytics_section(dashboard)}
      {render_anatomy_section(dashboard)}
      <section class="section" aria-labelledby="producer-heading">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Authoritative producers</p>
            <h2 id="producer-heading">Security and quality signals</h2>
          </div>
          <p>Each card links back to its canonical source rather than duplicating raw reports.</p>
        </div>
        <div class="producer-grid">{producer_cards}</div>
      </section>
      <section class="section" aria-labelledby="vitality-heading">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Local collector</p>
            <h2 id="vitality-heading">Repository vitality</h2>
          </div>
          <p>{escaped(vitality["execution"]["message"])}</p>
        </div>
        <div class="vitality-grid">{vitality_cards}</div>
      </section>
      <aside class="panel provenance" aria-label="Dashboard provenance">
        <div>
          <p class="card-kicker">Provenance</p>
          <p><code>{escaped(repository["source_commit"])}</code></p>
        </div>
        <p><a href="./summary.json">View public JSON</a> · <a href="./provenance.json">View provenance</a></p>
      </aside>
    </main>
    <script src="./explorer.js" defer></script>
  </body>
</html>
"""


def atomic_write_text(path: Path, content: str) -> None:
    """Write one dashboard asset atomically."""

    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def validate_paths(repository_root: Path, *paths: Path) -> None:
    """Keep all reads and writes inside the checked-out repository."""

    for path in paths:
        try:
            path.relative_to(repository_root)
        except ValueError as error:
            raise DashboardInputError(f"Path must remain inside the repository: {path}") from error


def write_dashboard_bundle(
    output_root: Path,
    dashboard: dict[str, Any],
    stylesheet_source: Path,
    script_source: Path,
    provenance: dict[str, Any] | None = None,
) -> None:
    """Write the public JSON, HTML, and stylesheet as one static bundle."""

    atomic_write_text(
        output_root / "summary.json",
        json.dumps(dashboard, allow_nan=False, indent=2, sort_keys=True) + "\n",
    )
    atomic_write_text(output_root / "index.html", render_html(dashboard))
    atomic_write_text(output_root / "styles.css", stylesheet_source.read_text(encoding="utf-8"))
    atomic_write_text(output_root / "explorer.js", script_source.read_text(encoding="utf-8"))
    if provenance is not None:
        atomic_write_text(
            output_root / "provenance.json",
            json.dumps(provenance, allow_nan=False, indent=2, sort_keys=True) + "\n",
        )


def main() -> int:
    """Build and write the deterministic dashboard bundle."""

    args = parse_arguments()
    repository_root = Path(args.repository_root).resolve()
    reports_root = Path(args.reports_root).resolve()
    analytics_summary = Path(args.analytics_summary).resolve() if args.analytics_summary else None
    repository_tree = Path(args.repository_tree).resolve() if args.repository_tree else None
    output_root = Path(args.output_root).resolve()
    stylesheet_source = Path(args.stylesheet_source).resolve()
    script_source = Path(args.script_source).resolve()
    if not repository_root.is_dir():
        raise SystemExit(f"Repository root is not a directory: {repository_root}")
    validate_paths(
        repository_root,
        reports_root,
        output_root,
        *([analytics_summary] if analytics_summary is not None else []),
        *([repository_tree] if repository_tree is not None else []),
    )
    if not stylesheet_source.is_file():
        raise SystemExit(f"Stylesheet source is unavailable: {stylesheet_source}")
    if not script_source.is_file():
        raise SystemExit(f"Explorer script source is unavailable: {script_source}")
    if args.generator_immutable not in {"true", "false"}:
        raise SystemExit("generator-immutable must be true or false")
    as_of = parse_timestamp(args.as_of, "as-of")
    dashboard = build_dashboard(
        repository_root=repository_root,
        reports_root=reports_root,
        repository=args.repository,
        default_branch=args.default_branch,
        source_commit=args.source_commit,
        as_of=as_of,
        analytics_summary=analytics_summary,
        repository_tree=repository_tree,
    )
    provenance = build_bundle_provenance(
        repository=args.repository,
        source_commit=args.source_commit,
        generated_at=as_of,
        timestamp_source=args.timestamp_source,
        generator_version=args.generator_version,
        generator_repository=args.generator_repository,
        generator_ref=args.generator_ref,
        generator_commit=args.generator_commit,
        generator_immutable=args.generator_immutable == "true",
        consumer_visibility=args.consumer_visibility,
    )
    write_dashboard_bundle(
        output_root,
        dashboard,
        stylesheet_source,
        script_source,
        provenance,
    )
    print(
        f"Generated repository intelligence dashboard at {output_root} "
        f"for {args.repository}@{args.source_commit[:12]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
