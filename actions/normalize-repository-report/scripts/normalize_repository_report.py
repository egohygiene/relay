# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Normalize scanner-native outputs into repository-intelligence summaries."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Any
from urllib.parse import unquote, urlsplit

SCHEMA_NAME = "egohygiene.repository-report-summary/v1"
SEVERITY_ORDER = ("unknown", "low", "medium", "high", "critical")
SCORE_PATTERN = re.compile(r"^score is (?P<score>-?\d+):", re.IGNORECASE)
REPOSITORY_PATTERN = re.compile(
    r"^(?!\.{1,2}/)(?![^/]+/\.{1,2}$)[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
)


class ReportInputError(ValueError):
    """Raised when a producer input exists but is not usable."""


class PathValidationError(ValueError):
    """Raised when an action path can reach outside the checked-out workspace."""


def parse_arguments() -> argparse.Namespace:
    """Parse command-line options shared by the composite action and tests."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--producer", choices=("osv", "megalinter", "scorecard"), required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--generated-at")
    parser.add_argument("--event", default="")
    parser.add_argument("--workflow", default="")
    parser.add_argument("--run-id")
    parser.add_argument("--run-attempt", type=int)
    parser.add_argument("--server-url", default="https://github.com")
    parser.add_argument("--stale-after-days", type=int, default=8)
    parser.add_argument("--detail-url")
    parser.add_argument("--policy-input")
    parser.add_argument("--scorecard-api-input")
    return parser.parse_args()


def resolve_workspace_path(
    workspace: Path, raw_path: str | None, label: str, *, required: bool = True
) -> Path | None:
    """Resolve one repository-relative path without permitting a workspace escape."""

    if raw_path is None or raw_path == "":
        if required:
            raise PathValidationError(f"{label} must be a non-empty repository-relative path")
        return None
    if not isinstance(raw_path, str):
        raise PathValidationError(f"{label} must be a repository-relative path string")

    candidate = Path(raw_path)
    if candidate.is_absolute() or candidate == Path(".") or ".." in candidate.parts:
        raise PathValidationError(
            f"{label} must be a non-empty repository-relative path without '..' components"
        )

    try:
        resolved = (workspace / candidate).resolve(strict=False)
        resolved.relative_to(workspace)
    except (OSError, RuntimeError, ValueError) as error:
        raise PathValidationError(
            f"{label} resolves outside the repository workspace: {raw_path}"
        ) from error
    return resolved


def resolve_workspace_paths(args: argparse.Namespace) -> dict[str, Path | None]:
    """Validate every read/write path against the canonical workspace boundary."""

    raw_workspace = getattr(args, "workspace", None)
    if not isinstance(raw_workspace, str) or not raw_workspace:
        raise PathValidationError("workspace must be a non-empty path")
    try:
        workspace = Path(raw_workspace).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise PathValidationError(f"workspace is unavailable: {raw_workspace}") from error
    if not workspace.is_dir():
        raise PathValidationError(f"workspace is not a directory: {raw_workspace}")

    return {
        "workspace": workspace,
        "input": resolve_workspace_path(workspace, getattr(args, "input", None), "input"),
        "output": resolve_workspace_path(workspace, getattr(args, "output", None), "output"),
        "policy_input": resolve_workspace_path(
            workspace,
            getattr(args, "policy_input", None),
            "policy-input",
            required=False,
        ),
        "scorecard_api_input": resolve_workspace_path(
            workspace,
            getattr(args, "scorecard_api_input", None),
            "scorecard-api-input",
            required=False,
        ),
    }


def reject_nonstandard_json_number(value: str) -> None:
    """Reject NaN and infinity tokens accepted by Python but forbidden by JSON."""

    raise ReportInputError(f"non-standard JSON number is not allowed: {value}")


def ensure_finite_json(value: Any, label: str) -> None:
    """Reject numeric overflow that parsed to infinity anywhere in producer input."""

    if isinstance(value, float) and not math.isfinite(value):
        raise ReportInputError(f"{label} contains a non-finite number")
    if isinstance(value, dict):
        for child in value.values():
            ensure_finite_json(child, label)
    elif isinstance(value, list):
        for child in value:
            ensure_finite_json(child, label)


def nonnegative_integer(value: Any, label: str) -> int:
    """Validate a JSON integer used as a count or return code."""

    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ReportInputError(f"{label} must be a non-negative integer")
    return value


def bounded_number(value: Any, label: str, *, minimum: float, maximum: float) -> float:
    """Validate a finite JSON number against an inclusive producer range."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ReportInputError(f"{label} must be a number from {minimum:g} through {maximum:g}")
    number = float(value)
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ReportInputError(f"{label} must be a number from {minimum:g} through {maximum:g}")
    return number


def load_object(path: Path, label: str) -> dict[str, Any]:
    """Load one required JSON object with a useful contract error."""

    if not path.is_file() or path.stat().st_size == 0:
        raise FileNotFoundError(f"{label} is unavailable")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=reject_nonstandard_json_number,
        )
    except ReportInputError:
        raise
    except OSError as error:
        raise ReportInputError(f"{label} is unreadable") from error
    except (json.JSONDecodeError, RecursionError) as error:
        raise ReportInputError(f"{label} is malformed JSON") from error
    if not isinstance(value, dict):
        raise ReportInputError(f"{label} must contain a JSON object")
    ensure_finite_json(value, label)
    return value


def parse_timestamp(value: str | None) -> datetime:
    """Return an aware UTC datetime from RFC 3339 input or the current clock."""

    if not value:
        return datetime.now(UTC).replace(microsecond=0)
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ReportInputError(f"generated-at is not RFC 3339: {value}") from error
    if parsed.tzinfo is None:
        raise ReportInputError("generated-at must include a timezone")
    return parsed.astimezone(UTC).replace(microsecond=0)


def format_timestamp(value: datetime) -> str:
    """Render one datetime as a stable UTC RFC 3339 value."""

    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_public_https_url(value: str, label: str, *, origin_only: bool = False) -> str:
    """Validate a credential-free public HTTPS URL without queries or fragments."""

    if "\\" in value or any(character.isspace() for character in value):
        raise ReportInputError(
            f"{label} must be a credential-free HTTPS URL without a query or fragment"
        )
    try:
        parsed = urlsplit(value)
        parsed.port
    except ValueError as error:
        raise ReportInputError(f"{label} must be a valid HTTPS URL") from error
    if re.search(
        r"(?i)(?:github_pat_|gh[pousr]_|(?:token|password|secret)\s*[:=])",
        unquote(value),
    ):
        raise ReportInputError(f"{label} must not contain secret-like data")
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.port not in {None, 443}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ReportInputError(
            f"{label} must be a credential-free HTTPS URL without a query or fragment"
        )
    if origin_only and parsed.path not in {"", "/"}:
        raise ReportInputError(f"{label} must identify an HTTPS origin")
    return value.rstrip("/")


def unknown_findings() -> dict[str, Any]:
    """Return the non-green fallback used for unavailable producer data."""

    return {
        "state": "unknown",
        "total": None,
        "blocking": None,
        "advisory": None,
        "by_severity": {},
    }


def findings(total: int, blocking: int, by_severity: dict[str, int]) -> dict[str, Any]:
    """Build a finding state while keeping policy-blocking separate from advisory data."""

    validated_total = nonnegative_integer(total, "findings total")
    validated_blocking = nonnegative_integer(blocking, "blocking findings")
    if validated_blocking > validated_total:
        raise ReportInputError("blocking findings cannot exceed total findings")
    validated_severity = {
        name: nonnegative_integer(count, f"{name} severity count")
        for name, count in by_severity.items()
    }
    advisory = validated_total - validated_blocking
    if validated_blocking:
        state = "blocked"
    elif validated_total:
        state = "attention"
    else:
        state = "clear"
    return {
        "state": state,
        "total": validated_total,
        "blocking": validated_blocking,
        "advisory": advisory,
        "by_severity": validated_severity,
    }


def default_links(
    *,
    producer: str,
    repository: str,
    commit: str,
    server_url: str,
    run_id: str | None,
    detail_url: str | None,
) -> dict[str, str]:
    """Construct stable source links without artifact URLs or private run data."""

    repository_url = f"{server_url.rstrip('/')}/{repository}"
    if detail_url:
        detail = detail_url
    elif producer == "scorecard":
        detail = f"https://scorecard.dev/viewer/?uri=github.com/{repository}"
    else:
        detail = f"{repository_url}/tree/{commit}/.reports/{producer}"
    workflow = f"{repository_url}/actions/runs/{run_id}" if run_id else ""
    return {
        "detail": detail,
        "workflow": workflow,
        "security": f"{repository_url}/security/code-scanning",
        "source": f"{repository_url}/commit/{commit}",
    }


def common_summary(
    *,
    producer: str,
    repository: str,
    commit: str,
    generated_at: datetime,
    stale_after_days: int,
    event: str,
    workflow: str,
    run_id: str | None,
    run_attempt: int | None,
    server_url: str,
    detail_url: str | None,
) -> dict[str, Any]:
    """Create the common, versioned portion of a producer summary."""

    if not REPOSITORY_PATTERN.fullmatch(repository):
        raise ReportInputError("repository must use owner/name form")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ReportInputError("commit must be a full, lowercase 40-character SHA")
    if (
        isinstance(stale_after_days, bool)
        or not isinstance(stale_after_days, int)
        or stale_after_days < 1
    ):
        raise ReportInputError("stale-after-days must be at least one")
    if run_attempt is not None and (
        isinstance(run_attempt, bool) or not isinstance(run_attempt, int) or run_attempt < 1
    ):
        raise ReportInputError("run-attempt must be a positive integer")
    try:
        expires_at = generated_at + timedelta(days=stale_after_days)
    except OverflowError as error:
        raise ReportInputError("stale-after-days produces an out-of-range expiry") from error
    validated_server_url = validate_public_https_url(
        server_url,
        "server-url",
        origin_only=True,
    )
    validated_detail_url = (
        validate_public_https_url(detail_url, "detail-url") if detail_url else None
    )
    return {
        "schema": SCHEMA_NAME,
        "schema_version": 1,
        "producer": producer,
        "repository": repository,
        "commit": commit,
        "generated_at": format_timestamp(generated_at),
        "freshness": {
            "expires_at": format_timestamp(expires_at),
            "stale_after_days": stale_after_days,
        },
        "execution": {"state": "unknown", "message": "Producer input was not evaluated."},
        "findings": unknown_findings(),
        "provenance": {
            "event": event,
            "workflow": workflow,
            "run_id": run_id,
            "run_attempt": run_attempt,
        },
        "links": default_links(
            producer=producer,
            repository=repository,
            commit=commit,
            server_url=validated_server_url,
            run_id=run_id,
            detail_url=validated_detail_url,
        ),
    }


def normalize_osv(document: dict[str, Any], summary: dict[str, Any]) -> None:
    """Add the common envelope around an OSV workflow summary."""

    source = document.get("osv") if document.get("producer") == "osv" else document
    if not isinstance(source, dict):
        raise ReportInputError("OSV summary has no producer payload")
    scan = source.get("scan")
    threshold = source.get("severity_threshold")
    if not isinstance(scan, dict) or threshold not in (*SEVERITY_ORDER[1:], "none"):
        raise ReportInputError("OSV summary is missing scan data or a valid severity threshold")
    severity = scan.get("severity")
    if not isinstance(severity, dict):
        raise ReportInputError("OSV summary is missing severity counts")
    counts = {
        name: nonnegative_integer(severity.get(name, 0), f"OSV {name} severity count")
        for name in SEVERITY_ORDER
    }
    total = sum(counts.values())
    if "total" in severity:
        reported_total = nonnegative_integer(severity["total"], "OSV total severity count")
        if reported_total != total:
            raise ReportInputError("OSV total severity count does not match severity buckets")
    for field in ("affected_packages", "vulnerabilities"):
        if field in scan:
            nonnegative_integer(scan[field], f"OSV scan.{field}")
    if "scan_duration_seconds" in source:
        duration = source["scan_duration_seconds"]
        if (
            isinstance(duration, bool)
            or not isinstance(duration, (int, float))
            or not math.isfinite(float(duration))
            or duration < 0
        ):
            raise ReportInputError("OSV scan_duration_seconds must be a non-negative number")
    if threshold == "none":
        blocking = 0
    else:
        threshold_index = SEVERITY_ORDER.index(str(threshold))
        blocking = sum(counts[name] for name in SEVERITY_ORDER[threshold_index:])

    excluded = {
        "schema",
        "schema_version",
        "producer",
        "repository",
        "commit",
        "generated_at",
        "freshness",
        "execution",
        "findings",
        "provenance",
        "links",
        "osv",
    }
    summary["execution"] = {
        "state": "success",
        "message": "Canonical OSV JSON and SARIF outputs were validated.",
    }
    summary["findings"] = findings(total, blocking, counts)
    summary["osv"] = {key: value for key, value in source.items() if key not in excluded}


def normalize_megalinter(
    document: dict[str, Any], policy: dict[str, Any], summary: dict[str, Any]
) -> None:
    """Summarize MegaLinter tool outcomes against the canonical policy matrix."""

    active_linters = document.get("active_linters")
    tools = policy.get("tools")
    if not isinstance(active_linters, list) or not isinstance(tools, list):
        raise ReportInputError("MegaLinter report or tool matrix is missing its tool list")
    enforcement_by_id = {
        str(tool.get("id")): str(tool.get("enforcement", "advisory"))
        for tool in tools
        if isinstance(tool, dict) and tool.get("id")
    }

    passed = 0
    finding_tools: list[dict[str, Any]] = []
    execution_errors: list[dict[str, Any]] = []
    diagnostic_errors = 0
    diagnostic_warnings = 0
    for linter in active_linters:
        if not isinstance(linter, dict):
            raise ReportInputError("MegaLinter active_linters must contain JSON objects")
        identifier = str(linter.get("name", "unknown"))
        status = str(linter.get("status", "unknown")).lower()
        raw_error_count = linter.get("total_number_errors")
        if raw_error_count is None:
            raw_error_count = linter.get("number_errors", 0)
        error_count = nonnegative_integer(
            raw_error_count,
            f"MegaLinter {identifier} error count",
        )
        warning_count = nonnegative_integer(
            linter.get("total_number_warnings", 0),
            f"MegaLinter {identifier} warning count",
        )
        diagnostic_errors += error_count
        diagnostic_warnings += warning_count
        enforcement = enforcement_by_id.get(identifier, "advisory")
        compact = {
            "id": identifier,
            "status": status,
            "enforcement": enforcement,
            "errors": error_count,
            "warnings": warning_count,
        }
        if status == "success" and error_count == 0 and warning_count == 0:
            passed += 1
        elif status == "error" and error_count == 0 and warning_count == 0:
            execution_errors.append(compact)
        else:
            finding_tools.append(compact)

    blocking = sum(tool["enforcement"] == "blocking" for tool in finding_tools)
    root_failed = str(document.get("status", "unknown")).lower() not in {"success", "warning"}
    root_failed = root_failed or document.get("return_code") not in {None, 0}
    execution_failed = bool(execution_errors) or root_failed
    if execution_errors:
        execution_message = f"{len(execution_errors)} tool execution(s) did not produce findings."
    elif root_failed:
        execution_message = "MegaLinter returned a failing runner status."
    else:
        execution_message = "MegaLinter produced a valid per-tool report."
    summary["execution"] = {
        "state": "failure" if execution_failed else "success",
        "message": execution_message,
    }
    summary["findings"] = findings(len(finding_tools), blocking, {})
    summary["megalinter"] = {
        "profile": "holistic" if document.get("validate_all_code_base") else "changed-files",
        "status": str(document.get("status", "unknown")),
        "return_code": document.get("return_code"),
        "tools": {
            "active": len(active_linters),
            "passed": passed,
            "with_findings": len(finding_tools),
            "execution_errors": len(execution_errors),
            "runner_failed": root_failed,
            "blocking": blocking,
            "advisory": len(finding_tools) - blocking,
        },
        "diagnostics": {"errors": diagnostic_errors, "warnings": diagnostic_warnings},
        "finding_tools": sorted(finding_tools, key=lambda item: item["id"]),
        "execution_error_tools": sorted(execution_errors, key=lambda item: item["id"]),
    }


def risk_from_rule(rule: dict[str, Any]) -> str:
    """Translate SARIF's numeric security severity into a compact risk label."""

    properties = rule.get("properties")
    if not isinstance(properties, dict):
        return "unknown"
    raw_severity = properties.get("security-severity")
    if raw_severity is None:
        return "unknown"
    try:
        severity = float(raw_severity)
    except (TypeError, ValueError):
        return "unknown"
    if not math.isfinite(severity) or not 0 <= severity <= 10:
        return "unknown"
    if severity >= 9:
        return "critical"
    if severity >= 7:
        return "high"
    if severity >= 4:
        return "medium"
    if severity > 0:
        return "low"
    return "unknown"


def scorecard_sarif_checks(document: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    """Extract unique check scores from Scorecard SARIF alert messages."""

    if document.get("version") != "2.1.0" or not isinstance(document.get("runs"), list):
        raise ReportInputError("Scorecard input is not SARIF 2.1.0")
    rules_by_id: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    total_rules = 0
    for run in document["runs"]:
        if not isinstance(run, dict):
            raise ReportInputError("Scorecard SARIF runs must contain JSON objects")
        tool = run.get("tool")
        if not isinstance(tool, dict) or not isinstance(tool.get("driver"), dict):
            raise ReportInputError("Scorecard SARIF run is missing tool.driver")
        driver = tool["driver"]
        rules = driver.get("rules", [])
        if not isinstance(rules, list):
            raise ReportInputError("Scorecard SARIF driver.rules must be an array")
        total_rules += len(rules)
        for rule in rules:
            if not isinstance(rule, dict):
                raise ReportInputError("Scorecard SARIF rules must contain JSON objects")
            if rule.get("id"):
                rules_by_id[str(rule["id"])] = rule
        run_results = run.get("results", [])
        if not isinstance(run_results, list):
            raise ReportInputError("Scorecard SARIF results must be an array")
        if any(not isinstance(result, dict) for result in run_results):
            raise ReportInputError("Scorecard SARIF results must contain JSON objects")
        results.extend(run_results)

    checks: dict[str, dict[str, Any]] = {}
    for result in results:
        identifier = str(result.get("ruleId", ""))
        message = result.get("message", {})
        text = str(message.get("text", "")) if isinstance(message, dict) else ""
        match = SCORE_PATTERN.match(text)
        if not identifier or not match:
            continue
        score = int(match.group("score"))
        if not 0 <= score <= 10:
            raise ReportInputError("Scorecard SARIF check scores must be from 0 through 10")
        rule = rules_by_id.get(identifier, {})
        name = str(rule.get("name") or identifier)
        candidate = {
            "id": identifier,
            "name": name,
            "score": score,
            "risk": risk_from_rule(rule),
            "url": str(rule.get("helpUri", "")),
        }
        existing = checks.get(identifier)
        if existing is None or score < existing["score"]:
            checks[identifier] = candidate
    return sorted(checks.values(), key=lambda item: (item["score"], item["name"])), total_rules


def matched_scorecard_api(
    api_document: dict[str, Any] | None, repository: str, commit: str
) -> tuple[str, dict[str, Any] | None]:
    """Accept public API data only when it names this repository and scanned commit."""

    if api_document is None:
        return "unavailable", None
    repo = api_document.get("repo")
    if not isinstance(repo, dict):
        return "invalid", None
    expected_name = f"github.com/{repository}".lower()
    if str(repo.get("name", "")).lower() != expected_name:
        return "invalid", None
    if repo.get("commit") != commit:
        return "stale", None
    checks = api_document.get("checks")
    if not isinstance(checks, list):
        return "invalid", None
    try:
        bounded_number(
            api_document.get("score"),
            "Scorecard API aggregate score",
            minimum=0,
            maximum=10,
        )
        for index, check in enumerate(checks):
            if not isinstance(check, dict):
                raise ReportInputError("Scorecard API checks must contain JSON objects")
            bounded_number(
                check.get("score"),
                f"Scorecard API check {index} score",
                minimum=0,
                maximum=10,
            )
    except ReportInputError:
        return "invalid", None
    return "matched", api_document


def normalize_scorecard(
    document: dict[str, Any],
    api_document: dict[str, Any] | None,
    summary: dict[str, Any],
) -> None:
    """Combine canonical SARIF with commit-matched public aggregate data."""

    sarif_checks, sarif_rule_count = scorecard_sarif_checks(document)
    api_status, matched_api = matched_scorecard_api(
        api_document, summary["repository"], summary["commit"]
    )
    aggregate_score: float | None = None
    checks = sarif_checks
    checks_total = sarif_rule_count
    source = "sarif"
    if matched_api is not None:
        aggregate_score = bounded_number(
            matched_api["score"],
            "Scorecard API aggregate score",
            minimum=0,
            maximum=10,
        )
        api_checks = []
        for check in matched_api["checks"]:
            score_number = bounded_number(
                check["score"],
                "Scorecard API check score",
                minimum=0,
                maximum=10,
            )
            if score_number == 10:
                continue
            score = int(score_number)
            documentation = check.get("documentation", {})
            api_checks.append(
                {
                    "id": str(check.get("name", "unknown")),
                    "name": str(check.get("name", "unknown")),
                    "score": score,
                    "risk": next(
                        (
                            item["risk"]
                            for item in sarif_checks
                            if item["name"] == str(check.get("name", ""))
                        ),
                        "unknown",
                    ),
                    "reason": str(check.get("reason", "")),
                    "url": (
                        str(documentation.get("url", "")) if isinstance(documentation, dict) else ""
                    ),
                }
            )
        checks = sorted(api_checks, key=lambda item: (item["score"], item["name"]))
        checks_total = len(matched_api["checks"])
        source = "api"

    by_severity = {name: 0 for name in SEVERITY_ORDER}
    for check in checks:
        risk = str(check.get("risk", "unknown"))
        by_severity[risk if risk in by_severity else "unknown"] += 1
    summary["execution"] = {
        "state": "success",
        "message": "OpenSSF Scorecard produced valid SARIF output.",
    }
    summary["findings"] = findings(len(checks), 0, by_severity)
    summary["scorecard"] = {
        "aggregate_score": aggregate_score,
        "aggregate_source": "official-api" if aggregate_score is not None else "unavailable",
        "api_status": api_status,
        "check_source": source,
        "checks_total": checks_total,
        "checks_needing_attention": len(checks),
        "weakest_checks": checks[:10],
    }


def normalize(args: argparse.Namespace) -> dict[str, Any]:
    """Normalize one producer, retaining an explicit fallback for bad input."""

    generated_at = parse_timestamp(args.generated_at)
    summary = common_summary(
        producer=args.producer,
        repository=args.repository,
        commit=args.commit,
        generated_at=generated_at,
        stale_after_days=args.stale_after_days,
        event=args.event,
        workflow=args.workflow,
        run_id=args.run_id,
        run_attempt=args.run_attempt,
        server_url=args.server_url,
        detail_url=args.detail_url,
    )
    try:
        document = load_object(Path(args.input), f"{args.producer} input")
        if args.producer == "osv":
            normalize_osv(document, summary)
        elif args.producer == "megalinter":
            if not args.policy_input:
                raise ReportInputError("MegaLinter normalization requires --policy-input")
            policy = load_object(Path(args.policy_input), "MegaLinter policy input")
            normalize_megalinter(document, policy, summary)
        else:
            api_document = None
            if args.scorecard_api_input:
                try:
                    api_document = load_object(
                        Path(args.scorecard_api_input), "Scorecard API input"
                    )
                except (FileNotFoundError, ReportInputError):
                    api_document = None
            normalize_scorecard(document, api_document, summary)
    except FileNotFoundError:
        summary["execution"] = {
            "state": "unknown",
            "message": "Producer input is unavailable.",
        }
        summary[args.producer] = {"status": "unavailable"}
    except (ReportInputError, TypeError, AttributeError, KeyError, OverflowError):
        summary["execution"] = {
            "state": "failure",
            "message": "Producer input is invalid.",
        }
        summary["findings"] = unknown_findings()
        summary[args.producer] = {"status": "invalid"}
    return summary


def atomic_write_summary(output: Path, summary: dict[str, Any]) -> None:
    """Write one standard-JSON summary without following a predictable temp path."""

    ensure_finite_json(summary, "normalized summary")
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=output.parent,
        prefix=f".{output.name}.",
    )
    temporary_output = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(summary, handle, allow_nan=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary_output.replace(output)
    except BaseException:
        temporary_output.unlink(missing_ok=True)
        raise


def main() -> int:
    """Normalize and atomically write one stable JSON summary."""

    args = parse_arguments()
    try:
        paths = resolve_workspace_paths(args)
    except PathValidationError as error:
        raise SystemExit(f"Unsafe repository report path: {error}") from error
    args.input = str(paths["input"])
    args.output = str(paths["output"])
    args.policy_input = str(paths["policy_input"]) if paths["policy_input"] else None
    args.scorecard_api_input = (
        str(paths["scorecard_api_input"]) if paths["scorecard_api_input"] else None
    )
    summary = normalize(args)
    output = Path(args.output)
    atomic_write_summary(output, summary)
    print(
        f"Normalized {args.producer} report: execution={summary['execution']['state']} "
        f"findings={summary['findings']['state']} output={output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
