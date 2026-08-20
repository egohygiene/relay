# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Validate one visibility-aware Repository Intelligence static subtree."""

from __future__ import annotations

import argparse
from datetime import datetime
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any
from urllib.parse import quote, unquote, urlsplit

BUNDLE_FILES = {
    "explorer.js",
    "index.html",
    "provenance.json",
    "styles.css",
    "summary.json",
}
ALLOWED_LOCAL_FRAGMENTS = {
    "main-content",
    "tree-icon-directory",
    "tree-icon-file",
    "tree-icon-submodule",
    "tree-icon-symlink",
}
PROVENANCE_SCHEMA = "egohygiene.relay.repository-intelligence-provenance/v1"
DASHBOARD_SCHEMA = "egohygiene.repository-intelligence-dashboard/v3"
FULL_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
REPOSITORY_PATTERN = re.compile(
    r"^(?!\.{1,2}/)(?![^/]+/\.{1,2}$)[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
)
EMAIL_PATTERN = re.compile(r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
WINDOWS_PATH_PATTERN = re.compile(r"(?i)\b[A-Z]:\\(?:Users|runner|workspace|tmp)\\")
RUNNER_PATH_PATTERN = re.compile(
    r"(?:^|[\s\"'(<>=:])/(?:home/runner|Users/[^/]+|runner|workspace|private|tmp)/"
)
SECRET_PATTERNS = (
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:bearer|token|password|secret)\s*[:=]\s*[^\s<]+"),
)
FORBIDDEN_PUBLIC_KEYS = {
    "actor",
    "author_email",
    "author_name",
    "body",
    "commit_message",
    "filesystem_path",
    "issue_body",
    "password",
    "private_metadata",
    "runner",
    "secret",
    "session",
    "token",
}
EXPECTED_CONTRACTS = {
    "dashboard": (DASHBOARD_SCHEMA, 1),
    "analytics": ("egohygiene.repository-analytics/v1", 1),
    "repository_tree": ("egohygiene.repository-tree/v1", 1),
    "repository_report": ("egohygiene.repository-report-summary/v1", 1),
}
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
DASHBOARD_KEYS = {
    "schema",
    "schema_version",
    "generated_at",
    "repository",
    "states",
    "producers",
    "analytics",
    "anatomy",
    "vitality",
}
PROVENANCE_KEYS = {
    "schema",
    "schema_version",
    "generator",
    "consumer",
    "contracts",
    "generated_at",
    "timestamp_source",
    "projection",
}


class BundleValidationError(ValueError):
    """Raised when generated output is unsafe or internally inconsistent."""


class ReferenceCollector(HTMLParser):
    """Collect local and external href/src values from one HTML document."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[tuple[str, str]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        for key, value in attrs:
            if key in {"href", "src"} and value is not None:
                self.references.append((tag, value))


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
    """Parse the action's final validation interface."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--repository-visibility", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--generator-version", required=True)
    parser.add_argument("--generator-source-ref", default="")
    parser.add_argument("--generator-source-commit", default="")
    parser.add_argument("--generator-immutable", required=True)
    return parser.parse_args()


def require_object(value: Any, label: str) -> dict[str, Any]:
    """Return one JSON object or raise a stable validation error."""

    if not isinstance(value, dict):
        raise BundleValidationError(f"{label} must be an object")
    return value


def canonical_output_root(repository_root: Path, output_root: Path) -> tuple[Path, Path]:
    """Resolve the bundle without following a path outside the consumer repository."""

    root = repository_root.resolve(strict=True)
    lexical = output_root if output_root.is_absolute() else root / output_root
    try:
        relative = lexical.relative_to(root)
    except ValueError as error:
        raise BundleValidationError("output root must remain inside the repository") from error
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise BundleValidationError("output root must not contain symbolic-link components")
    output = lexical.resolve(strict=True)
    try:
        output.relative_to(root)
    except ValueError as error:
        raise BundleValidationError("output root must remain inside the repository") from error
    if output == root:
        raise BundleValidationError("output root must not be the repository root")
    if output.name != "intelligence":
        raise BundleValidationError("output root must end with the intelligence subtree")
    return root, output


def collect_bundle_files(output_root: Path) -> set[str]:
    """Return a flat bundle allowlist and reject symlinks or nested output."""

    discovered: set[str] = set()
    for path in output_root.iterdir():
        if path.is_symlink():
            raise BundleValidationError(f"generated bundle contains a symbolic link: {path.name}")
        if not path.is_file():
            raise BundleValidationError(f"generated bundle contains a nested path: {path.name}")
        discovered.add(path.name)
    if discovered != BUNDLE_FILES:
        missing = sorted(BUNDLE_FILES - discovered)
        unexpected = sorted(discovered - BUNDLE_FILES)
        details = []
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected {', '.join(unexpected)}")
        raise BundleValidationError("generated bundle file set is invalid: " + "; ".join(details))
    return discovered


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    """Load one strict JSON object."""

    def reject_nonstandard_number(value: str) -> None:
        raise ValueError(f"non-standard JSON number: {value}")

    try:
        document = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=reject_nonstandard_number,
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        raise BundleValidationError(f"{label} must contain valid UTF-8 JSON") from error
    return require_object(document, label)


def require_exact_keys(document: dict[str, Any], expected: set[str], label: str) -> None:
    """Require one generated object to match its closed contract shape."""

    actual = set(document)
    if actual != expected:
        missing = ", ".join(sorted(expected - actual)) or "none"
        unexpected = ", ".join(sorted(actual - expected)) or "none"
        raise BundleValidationError(
            f"{label} has invalid members; missing: {missing}; unexpected: {unexpected}"
        )


def validate_rfc3339(value: Any, label: str) -> None:
    """Require an offset-aware RFC 3339-compatible timestamp."""

    if not isinstance(value, str):
        raise BundleValidationError(f"{label} must be an RFC 3339 string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise BundleValidationError(f"{label} must be an RFC 3339 string") from error
    if parsed.tzinfo is None:
        raise BundleValidationError(f"{label} must include a timezone")


def validate_status(value: Any, label: str, allowed_states: set[str]) -> dict[str, Any]:
    """Validate one generated state/message pair."""

    status = require_object(value, label)
    require_exact_keys(status, {"state", "message"}, label)
    if status["state"] not in allowed_states or not isinstance(status["message"], str):
        raise BundleValidationError(f"{label} must contain string state and message values")
    return status


def require_integer(
    value: Any,
    label: str,
    *,
    minimum: int | None = None,
    allow_none: bool = False,
) -> int | None:
    """Validate one JSON integer without accepting booleans."""

    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise BundleValidationError(f"{label} must be an integer")
    if minimum is not None and value < minimum:
        raise BundleValidationError(f"{label} must be at least {minimum}")
    return value


def validate_analytics_rows(
    value: Any,
    *,
    label: str,
    identity: str,
    metrics: tuple[str, ...],
) -> None:
    """Validate one closed analytics row collection."""

    if not isinstance(value, list):
        raise BundleValidationError(f"{label} must be an array")
    identities: set[str] = set()
    for index, row_value in enumerate(value):
        row = require_object(row_value, f"{label}[{index}]")
        require_exact_keys(row, {identity, *metrics}, f"{label}[{index}]")
        identity_value = row[identity]
        if not isinstance(identity_value, str) or not identity_value:
            raise BundleValidationError(f"{label}[{index}].{identity} must be non-empty")
        if identity == "path" and (
            identity_value.startswith("/")
            or "\\" in identity_value
            or any(part in {"", ".", ".."} for part in identity_value.split("/"))
        ):
            raise BundleValidationError(f"{label}[{index}].path is not repository-relative")
        if identity == "week":
            try:
                datetime.strptime(identity_value, "%Y-%m-%d")
            except ValueError as error:
                raise BundleValidationError(f"{label}[{index}].week is invalid") from error
        if identity_value in identities:
            raise BundleValidationError(f"{label} identities must be unique")
        identities.add(identity_value)
        for metric in metrics:
            require_integer(row[metric], f"{label}[{index}].{metric}", minimum=0)


def validate_analytics_summary(value: Any, source_commit: str) -> None:
    """Validate the complete public analytics projection."""

    summary = require_object(value, "summary.analytics.summary")
    require_exact_keys(
        summary,
        {"source", "scope", "repository", "activity", "changes", "filters"},
        "summary.analytics.summary",
    )
    source = require_object(summary["source"], "summary.analytics.summary.source")
    require_exact_keys(source, {"revision", "ref", "committed_at"}, "analytics.source")
    if source["revision"] != source_commit or not isinstance(source["ref"], str) or not source["ref"]:
        raise BundleValidationError("analytics source does not match the dashboard")
    validate_rfc3339(source["committed_at"], "analytics.source.committed_at")
    scope = require_object(summary["scope"], "analytics.scope")
    require_exact_keys(scope, {"since", "resolved_since"}, "analytics.scope")
    if not isinstance(scope["since"], str) or not scope["since"]:
        raise BundleValidationError("analytics.scope.since must be non-empty")
    validate_rfc3339(scope["resolved_since"], "analytics.scope.resolved_since")
    repository = require_object(summary["repository"], "analytics.repository")
    require_exact_keys(repository, {"tracked_files", "areas"}, "analytics.repository")
    tracked_files = require_integer(
        repository["tracked_files"], "analytics.repository.tracked_files", minimum=0
    )
    validate_analytics_rows(
        repository["areas"],
        label="analytics.repository.areas",
        identity="name",
        metrics=("file_count",),
    )
    if sum(row["file_count"] for row in repository["areas"]) != tracked_files:
        raise BundleValidationError("analytics repository area counts are inconsistent")
    activity = require_object(summary["activity"], "analytics.activity")
    require_exact_keys(
        activity,
        {"commits", "merges", "contributors", "first_commit_at", "last_commit_at", "weekly"},
        "analytics.activity",
    )
    for key in ("commits", "merges", "contributors"):
        require_integer(activity[key], f"analytics.activity.{key}", minimum=0)
    if activity["merges"] > activity["commits"]:
        raise BundleValidationError("analytics merges exceed commits")
    for key in ("first_commit_at", "last_commit_at"):
        if activity[key] is not None:
            validate_rfc3339(activity[key], f"analytics.activity.{key}")
    validate_analytics_rows(
        activity["weekly"],
        label="analytics.activity.weekly",
        identity="week",
        metrics=("commits", "merges"),
    )
    changes = require_object(summary["changes"], "analytics.changes")
    require_exact_keys(
        changes,
        {"files_changed", "insertions", "deletions", "net_lines", "areas", "hotspots"},
        "analytics.changes",
    )
    for key in ("files_changed", "insertions", "deletions"):
        require_integer(changes[key], f"analytics.changes.{key}", minimum=0)
    require_integer(changes["net_lines"], "analytics.changes.net_lines")
    change_metrics = ("commit_touches", "insertions", "deletions", "binary_changes")
    validate_analytics_rows(
        changes["areas"],
        label="analytics.changes.areas",
        identity="name",
        metrics=change_metrics,
    )
    validate_analytics_rows(
        changes["hotspots"],
        label="analytics.changes.hotspots",
        identity="path",
        metrics=change_metrics,
    )
    filters = require_object(summary["filters"], "analytics.filters")
    require_exact_keys(
        filters,
        {"excluded_tracked_files", "excluded_change_records"},
        "analytics.filters",
    )
    for key in filters:
        require_integer(filters[key], f"analytics.filters.{key}", minimum=0)


def validate_tree_node(value: Any, *, parent: str | None, depth: int) -> tuple[int, dict[str, int], int]:
    """Validate one bounded anatomy node and return visible counts."""

    if depth > 20:
        raise BundleValidationError("repository anatomy exceeds depth 20")
    node = require_object(value, "anatomy tree node")
    node_type = node.get("type")
    if node_type not in {"directory", "file", "symlink", "submodule"}:
        raise BundleValidationError("anatomy tree node type is invalid")
    required = {"name", "path", "type"}
    if node_type == "directory":
        required |= {"children", "descendants"}
        allowed = required | {"truncated"}
    else:
        allowed = required
    if not required.issubset(node) or not set(node).issubset(allowed):
        raise BundleValidationError("anatomy tree node members are invalid")
    name = node["name"]
    path = node["path"]
    if not isinstance(name, str) or not name or not isinstance(path, str):
        raise BundleValidationError("anatomy tree node name and path must be strings")
    expected_path = "." if parent is None else (name if parent == "." else f"{parent}/{name}")
    if path != expected_path:
        raise BundleValidationError("anatomy tree node path does not match its hierarchy")
    counts = {"directories": 0, "files": 0, "symlinks": 0, "submodules": 0}
    if node_type != "directory":
        counts[f"{node_type}s"] += 1
        return 1, counts, depth
    if not isinstance(node["children"], list):
        raise BundleValidationError("anatomy directory children must be an array")
    node_count = 1
    deepest = depth
    child_names: set[str] = set()
    for child in node["children"]:
        child_count, child_counts, child_depth = validate_tree_node(
            child,
            parent=path,
            depth=depth + 1,
        )
        child_name = child["name"]
        if child_name in child_names:
            raise BundleValidationError("anatomy sibling names must be unique")
        child_names.add(child_name)
        node_count += child_count
        deepest = max(deepest, child_depth)
        if child["type"] == "directory":
            counts["directories"] += 1
        for key in counts:
            counts[key] += child_counts[key]
    descendants = require_object(node["descendants"], "anatomy descendants")
    require_exact_keys(descendants, set(counts), "anatomy descendants")
    if descendants != counts:
        raise BundleValidationError("anatomy descendant counts are inconsistent")
    if node.get("truncated") not in {None, True}:
        raise BundleValidationError("anatomy truncated marker is invalid")
    return node_count, counts, deepest


def validate_anatomy_summary(value: Any, source_commit: str) -> None:
    """Validate the commit-scoped repository anatomy projection."""

    summary = require_object(value, "summary.anatomy.summary")
    require_exact_keys(
        summary,
        {"source", "counts", "node_count", "max_depth", "tree"},
        "summary.anatomy.summary",
    )
    source = require_object(summary["source"], "anatomy.source")
    require_exact_keys(source, {"revision", "ref", "committed_at"}, "anatomy.source")
    if source["revision"] != source_commit or not isinstance(source["ref"], str) or not source["ref"]:
        raise BundleValidationError("anatomy source does not match the dashboard")
    validate_rfc3339(source["committed_at"], "anatomy.source.committed_at")
    node_count, counts, max_depth = validate_tree_node(summary["tree"], parent=None, depth=0)
    declared_counts = require_object(summary["counts"], "anatomy.counts")
    require_exact_keys(declared_counts, set(counts), "anatomy.counts")
    if declared_counts != counts:
        raise BundleValidationError("anatomy counts are inconsistent")
    if summary["node_count"] != node_count or summary["max_depth"] != max_depth:
        raise BundleValidationError("anatomy size metadata is inconsistent")


def validate_metric_count_map(
    value: Any,
    *,
    label: str,
    allowed_keys: set[str],
) -> None:
    """Validate a bounded generated metric map."""

    metrics = require_object(value, label)
    if not set(metrics).issubset(allowed_keys):
        raise BundleValidationError(f"{label} contains unsupported metrics")
    for key, count in metrics.items():
        require_integer(count, f"{label}.{key}", minimum=0)


def validate_producer_metrics(name: str, value: Any) -> None:
    """Validate one producer's closed, public metric projection."""

    metrics = require_object(value, f"summary.producers.{name}.metrics")
    if not metrics:
        return
    if name == "osv":
        require_exact_keys(
            metrics,
            {"vulnerabilities", "affected_packages", "ecosystems", "threshold", "severity"},
            "summary.producers.osv.metrics",
        )
        for key in ("vulnerabilities", "affected_packages", "ecosystems"):
            require_integer(metrics[key], f"summary.producers.osv.metrics.{key}", minimum=0, allow_none=True)
        if metrics["threshold"] not in {None, "low", "medium", "high", "critical", "none"}:
            raise BundleValidationError("OSV threshold metric is invalid")
        validate_metric_count_map(
            metrics["severity"],
            label="summary.producers.osv.metrics.severity",
            allowed_keys=PUBLIC_SEVERITIES,
        )
        return
    if name == "megalinter":
        require_exact_keys(
            metrics,
            {"profile", "tools", "diagnostics"},
            "summary.producers.megalinter.metrics",
        )
        if metrics["profile"] not in {None, "all", "holistic", "changed-files"}:
            raise BundleValidationError("MegaLinter profile metric is invalid")
        validate_metric_count_map(
            metrics["tools"],
            label="summary.producers.megalinter.metrics.tools",
            allowed_keys={
                "active",
                "passed",
                "with_findings",
                "execution_errors",
                "runner_failed",
                "blocking",
                "advisory",
            },
        )
        validate_metric_count_map(
            metrics["diagnostics"],
            label="summary.producers.megalinter.metrics.diagnostics",
            allowed_keys={"errors", "warnings"},
        )
        return
    require_exact_keys(
        metrics,
        {
            "aggregate_score",
            "aggregate_source",
            "api_status",
            "checks_total",
            "checks_needing_attention",
            "weakest_checks",
        },
        "summary.producers.scorecard.metrics",
    )
    aggregate_score = metrics["aggregate_score"]
    if aggregate_score is not None and (
        isinstance(aggregate_score, bool)
        or not isinstance(aggregate_score, (int, float))
        or not 0 <= aggregate_score <= 10
    ):
        raise BundleValidationError("Scorecard aggregate score is invalid")
    if metrics["aggregate_source"] not in {None, "api", "official-api", "unavailable"}:
        raise BundleValidationError("Scorecard aggregate source is invalid")
    if metrics["api_status"] not in {None, "matched", "unavailable", "invalid", "stale"}:
        raise BundleValidationError("Scorecard API status is invalid")
    for key in ("checks_total", "checks_needing_attention"):
        require_integer(metrics[key], f"summary.producers.scorecard.metrics.{key}", minimum=0, allow_none=True)
    if not isinstance(metrics["weakest_checks"], list):
        raise BundleValidationError("Scorecard weakest checks must be an array")
    for index, item_value in enumerate(metrics["weakest_checks"]):
        item = require_object(item_value, f"scorecard.weakest_checks[{index}]")
        require_exact_keys(item, {"name", "score"}, f"scorecard.weakest_checks[{index}]")
        if item["name"] not in SCORECARD_CHECK_NAMES:
            raise BundleValidationError("Scorecard check name is unsupported")
        score = item["score"]
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 10:
            raise BundleValidationError("Scorecard check score is invalid")


def validate_dashboard_shape(
    summary: dict[str, Any],
    *,
    repository_name: str,
    source_commit: str,
) -> None:
    """Validate the complete closed dashboard projection shape."""

    require_exact_keys(summary, DASHBOARD_KEYS, "summary.json")
    validate_rfc3339(summary["generated_at"], "summary.generated_at")
    repository = require_object(summary["repository"], "summary.repository")
    require_exact_keys(
        repository,
        {"name", "default_branch", "source_commit"},
        "summary.repository",
    )
    if not all(isinstance(repository[key], str) and repository[key] for key in repository):
        raise BundleValidationError("summary.repository values must be non-empty strings")
    if repository["name"] != repository_name or repository["source_commit"] != source_commit:
        raise BundleValidationError("summary.repository does not match the consumer source")

    allowed_states = {
        "availability": {"available", "unavailable", "invalid"},
        "execution": {"success", "failure", "cancelled", "unknown"},
        "findings": {"clear", "attention", "blocked", "unknown"},
        "freshness": {"fresh", "stale", "unknown"},
    }
    states = require_object(summary["states"], "summary.states")
    require_exact_keys(states, set(allowed_states), "summary.states")
    for dimension, allowed in allowed_states.items():
        counts = require_object(states[dimension], f"summary.states.{dimension}")
        require_exact_keys(counts, allowed, f"summary.states.{dimension}")
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in counts.values()):
            raise BundleValidationError(f"summary.states.{dimension} must contain counts")
        if sum(counts.values()) != 3:
            raise BundleValidationError(f"summary.states.{dimension} must count three producers")

    producers = require_object(summary["producers"], "summary.producers")
    require_exact_keys(producers, {"osv", "megalinter", "scorecard"}, "summary.producers")
    producer_keys = {
        "producer",
        "name",
        "availability",
        "generated_at",
        "commit",
        "execution",
        "findings",
        "freshness",
        "links",
        "metrics",
    }
    for name in ("osv", "megalinter", "scorecard"):
        producer = require_object(producers[name], f"summary.producers.{name}")
        require_exact_keys(producer, producer_keys, f"summary.producers.{name}")
        if producer["producer"] != name or producer["availability"] not in allowed_states["availability"]:
            raise BundleValidationError(f"summary.producers.{name} identity is invalid")
        expected_name = {
            "osv": "Dependency risk",
            "megalinter": "Code quality",
            "scorecard": "Supply-chain posture",
        }[name]
        if producer["name"] != expected_name:
            raise BundleValidationError(f"summary.producers.{name} display name is invalid")
        availability = producer["availability"]
        if availability == "available":
            validate_rfc3339(
                producer["generated_at"],
                f"summary.producers.{name}.generated_at",
            )
            if producer["commit"] != source_commit:
                raise BundleValidationError(
                    f"summary.producers.{name} does not match the dashboard source commit"
                )
        elif producer["generated_at"] is not None or producer["commit"] is not None:
            raise BundleValidationError(
                f"summary.producers.{name} unavailable metadata must be null"
            )
        execution = validate_status(
            producer["execution"],
            f"summary.producers.{name}.execution",
            allowed_states["execution"],
        )
        findings = require_object(producer["findings"], f"summary.producers.{name}.findings")
        require_exact_keys(
            findings,
            {"state", "total", "blocking", "advisory", "by_severity"},
            f"summary.producers.{name}.findings",
        )
        if findings["state"] not in allowed_states["findings"]:
            raise BundleValidationError(f"summary.producers.{name} findings state is invalid")
        unknown_findings = findings["state"] == "unknown"
        finding_counts = [
            require_integer(
                findings[key],
                f"summary.producers.{name}.findings.{key}",
                minimum=0,
                allow_none=unknown_findings,
            )
            for key in ("total", "blocking", "advisory")
        ]
        if unknown_findings and any(value is not None for value in finding_counts):
            raise BundleValidationError(f"summary.producers.{name} unknown findings need null counts")
        if not unknown_findings and finding_counts[1] + finding_counts[2] != finding_counts[0]:
            raise BundleValidationError(f"summary.producers.{name} finding counts are inconsistent")
        validate_metric_count_map(
            findings["by_severity"],
            label=f"summary.producers.{name}.findings.by_severity",
            allowed_keys=PUBLIC_SEVERITIES,
        )
        freshness = require_object(producer["freshness"], f"summary.producers.{name}.freshness")
        require_exact_keys(
            freshness,
            {
                "state",
                "message",
                "expires_at",
                "stale_after_days",
                "elapsed_percent",
                "remaining_days",
            },
            f"summary.producers.{name}.freshness",
        )
        if freshness["state"] not in allowed_states["freshness"] or not isinstance(
            freshness["message"], str
        ):
            raise BundleValidationError(f"summary.producers.{name} freshness is invalid")
        if availability == "available":
            if freshness["state"] not in {"fresh", "stale"}:
                raise BundleValidationError(f"summary.producers.{name} freshness is unknown")
            validate_rfc3339(
                freshness["expires_at"],
                f"summary.producers.{name}.freshness.expires_at",
            )
            require_integer(
                freshness["stale_after_days"],
                f"summary.producers.{name}.freshness.stale_after_days",
                minimum=1,
            )
            elapsed = require_integer(
                freshness["elapsed_percent"],
                f"summary.producers.{name}.freshness.elapsed_percent",
                minimum=0,
            )
            if elapsed > 100:
                raise BundleValidationError(f"summary.producers.{name} freshness exceeds 100%")
            require_integer(
                freshness["remaining_days"],
                f"summary.producers.{name}.freshness.remaining_days",
            )
        elif any(
            freshness[key] is not None
            for key in ("expires_at", "stale_after_days", "elapsed_percent", "remaining_days")
        ) or freshness["state"] != "unknown":
            raise BundleValidationError(f"summary.producers.{name} absent freshness is invalid")
        links = require_object(producer["links"], f"summary.producers.{name}.links")
        if not set(links).issubset({"detail", "workflow", "security", "source"}) or not all(
            isinstance(value, str) for value in links.values()
        ):
            raise BundleValidationError(f"summary.producers.{name} links are invalid")
        validate_producer_metrics(name, producer["metrics"])
        if availability != "available" and (links or producer["metrics"]):
            raise BundleValidationError(f"summary.producers.{name} absent projection is not empty")
        if availability == "available" and not producer["metrics"]:
            raise BundleValidationError(f"summary.producers.{name} available metrics are empty")
        if availability == "unavailable" and (
            execution["state"] != "unknown"
            or findings["state"] != "unknown"
            or freshness["state"] != "unknown"
        ):
            raise BundleValidationError(f"summary.producers.{name} unavailable states are inconsistent")
        if availability == "invalid" and (
            execution["state"] != "failure"
            or findings["state"] != "unknown"
            or freshness["state"] != "unknown"
        ):
            raise BundleValidationError(f"summary.producers.{name} invalid states are inconsistent")
        if execution["state"] not in allowed_states["execution"]:
            raise BundleValidationError(f"summary.producers.{name} execution is invalid")

    observed_states = {
        "availability": [producer["availability"] for producer in producers.values()],
        "execution": [producer["execution"]["state"] for producer in producers.values()],
        "findings": [producer["findings"]["state"] for producer in producers.values()],
        "freshness": [producer["freshness"]["state"] for producer in producers.values()],
    }
    for dimension, observed in observed_states.items():
        expected_counts = {
            state: observed.count(state) for state in sorted(allowed_states[dimension])
        }
        if states[dimension] != expected_counts:
            raise BundleValidationError(f"summary.states.{dimension} is inconsistent")

    for projection_name in ("analytics", "anatomy"):
        projection = require_object(summary[projection_name], f"summary.{projection_name}")
        require_exact_keys(
            projection,
            {"availability", "message", "summary"},
            f"summary.{projection_name}",
        )
        if projection["availability"] not in allowed_states["availability"]:
            raise BundleValidationError(f"summary.{projection_name} availability is invalid")
        if not isinstance(projection["message"], str):
            raise BundleValidationError(f"summary.{projection_name} message must be a string")
        expected_summary_type = dict if projection["availability"] == "available" else type(None)
        if not isinstance(projection["summary"], expected_summary_type):
            raise BundleValidationError(f"summary.{projection_name} payload is inconsistent")
        if projection["availability"] == "available":
            if projection_name == "analytics":
                validate_analytics_summary(projection["summary"], source_commit)
            else:
                validate_anatomy_summary(projection["summary"], source_commit)

    vitality = require_object(summary["vitality"], "summary.vitality")
    required_vitality = {
        "execution",
        "repository",
        "default_branch",
        "source_commit",
        "metrics",
    }
    if frozenset(vitality) not in {
        frozenset(required_vitality),
        frozenset(required_vitality | {"latest_commit"}),
    }:
        raise BundleValidationError("summary.vitality has invalid members")
    vitality_execution = validate_status(
        vitality["execution"],
        "summary.vitality.execution",
        {"success", "failure"},
    )
    if (
        vitality["repository"] != repository_name
        or vitality["default_branch"] != repository["default_branch"]
        or vitality["source_commit"] != source_commit
    ):
        raise BundleValidationError("summary.vitality does not match the dashboard source")
    vitality_metrics = require_object(vitality["metrics"], "summary.vitality.metrics")
    if vitality_execution["state"] == "failure":
        if vitality_metrics or "latest_commit" in vitality:
            raise BundleValidationError("failed vitality must not contain collected metrics")
    else:
        expected_metrics = {
            "commits_30_days",
            "contributors_90_days",
            "tracked_files",
            "workflows",
            "composite_actions",
            "test_artifacts",
            "history_complete",
        }
        require_exact_keys(vitality_metrics, expected_metrics, "summary.vitality.metrics")
        for key in expected_metrics - {"history_complete"}:
            require_integer(vitality_metrics[key], f"summary.vitality.metrics.{key}", minimum=0)
        if not isinstance(vitality_metrics["history_complete"], bool):
            raise BundleValidationError("summary.vitality.metrics.history_complete must be boolean")
        latest = require_object(vitality.get("latest_commit"), "summary.vitality.latest_commit")
        require_exact_keys(latest, {"short_sha", "committed_at"}, "summary.vitality.latest_commit")
        if latest["short_sha"] != source_commit[:12]:
            raise BundleValidationError("summary.vitality latest commit is inconsistent")
        validate_rfc3339(latest["committed_at"], "summary.vitality.latest_commit.committed_at")


def exact_commit_from_ref(source_ref: str) -> str | None:
    """Return a commit only when the requested direct or workflow ref is immutable."""

    match = re.search(r"(?:^|@)([0-9a-f]{40})$", source_ref)
    return match.group(1) if match else None


def validate_json_contracts(
    output_root: Path,
    *,
    repository: str,
    repository_visibility: str,
    source_commit: str,
    generator_version: str,
    generator_source_ref: str,
    generator_source_commit: str,
    generator_immutable: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate dashboard and provenance structure, versions, and source alignment."""

    summary = load_json_object(output_root / "summary.json", "summary.json")
    provenance = load_json_object(output_root / "provenance.json", "provenance.json")
    validate_dashboard_shape(
        summary,
        repository_name=repository,
        source_commit=source_commit,
    )
    if summary.get("schema") != DASHBOARD_SCHEMA or summary.get("schema_version") != 1:
        raise BundleValidationError("summary.json uses an unsupported dashboard contract")
    summary_repository = require_object(summary.get("repository"), "summary.repository")
    if summary_repository.get("name") != repository:
        raise BundleValidationError("summary repository does not match the consumer")
    if summary_repository.get("source_commit") != source_commit:
        raise BundleValidationError("summary source commit does not match the consumer")

    require_exact_keys(provenance, PROVENANCE_KEYS, "provenance.json")
    if provenance.get("schema") != PROVENANCE_SCHEMA or provenance.get("schema_version") != 1:
        raise BundleValidationError("provenance.json uses an unsupported contract")
    generator = require_object(provenance.get("generator"), "provenance.generator")
    consumer = require_object(provenance.get("consumer"), "provenance.consumer")
    contracts = require_object(provenance.get("contracts"), "provenance.contracts")
    projection = require_object(provenance.get("projection"), "provenance.projection")
    require_exact_keys(
        generator,
        {"name", "version", "repository", "source_ref", "source_commit", "immutable"},
        "provenance.generator",
    )
    require_exact_keys(
        consumer,
        {"repository", "source_commit", "visibility"},
        "provenance.consumer",
    )
    require_exact_keys(
        projection,
        {"route", "classification", "deployment_authority"},
        "provenance.projection",
    )
    if generator.get("name") != "egohygiene/relay/actions/repository-intelligence":
        raise BundleValidationError("provenance generator name is invalid")
    if generator.get("repository") != "egohygiene/relay":
        raise BundleValidationError("provenance generator repository is invalid")
    if generator.get("version") != generator_version:
        raise BundleValidationError("provenance generator version does not match Relay")
    if generator.get("source_ref") != generator_source_ref:
        raise BundleValidationError("provenance Relay source ref is inconsistent")
    expected_generator_commit: str | None = generator_source_commit or None
    if generator.get("source_commit") != expected_generator_commit:
        raise BundleValidationError("provenance Relay source commit is inconsistent")
    exact_ref_commit = exact_commit_from_ref(generator_source_ref)
    if exact_ref_commit is not None and exact_ref_commit != generator_source_commit:
        raise BundleValidationError("immutable Relay source ref does not match its commit")
    if generator_immutable is not bool(exact_ref_commit):
        raise BundleValidationError("expected Relay immutable state is inconsistent")
    if generator.get("immutable") is not generator_immutable:
        raise BundleValidationError("provenance immutable state is inconsistent")
    if repository_visibility not in CONSUMER_VISIBILITIES:
        raise BundleValidationError("consumer repository visibility is invalid")
    if consumer != {
        "repository": repository,
        "source_commit": source_commit,
        "visibility": repository_visibility,
    }:
        raise BundleValidationError("provenance consumer source is inconsistent")
    validate_rfc3339(provenance.get("generated_at"), "provenance.generated_at")
    if provenance.get("generated_at") != summary.get("generated_at"):
        raise BundleValidationError("provenance timestamp does not match the dashboard")
    if provenance.get("timestamp_source") not in {
        "consumer-source-commit",
        "explicit-input",
    }:
        raise BundleValidationError("provenance timestamp source is invalid")
    expected_classification = (
        "public-safe" if repository_visibility == "public" else "internal-only"
    )
    if projection != {
        "route": "/intelligence/",
        "classification": expected_classification,
        "deployment_authority": "consumer",
    }:
        raise BundleValidationError("provenance projection contract is invalid")
    if set(contracts) != set(EXPECTED_CONTRACTS):
        raise BundleValidationError("provenance contract inventory is incomplete")
    for name, (schema, version) in EXPECTED_CONTRACTS.items():
        if contracts.get(name) != {"schema": schema, "schema_version": version}:
            raise BundleValidationError(f"provenance contract entry is invalid: {name}")
    return summary, provenance


def validate_github_reference(path: str, repository: str, source_commit: str) -> None:
    """Require a reviewed same-consumer route pinned to the represented commit."""

    escaped_repository = re.escape(repository)
    if re.fullmatch(
        rf"/{escaped_repository}/(?:actions/runs/[0-9]+|security/code-scanning)",
        path,
    ):
        return
    if path == f"/{repository}/commit/{source_commit}":
        return
    source_match = re.fullmatch(
        rf"/{escaped_repository}/(blob|tree)/({re.escape(source_commit)})(?:/(.+))?",
        path,
    )
    if source_match is None:
        raise BundleValidationError("GitHub reference is outside the consumer contract")
    kind, _, encoded_path = source_match.groups()
    if encoded_path is None:
        if kind == "tree":
            return
        raise BundleValidationError("GitHub blob reference has no repository path")
    decoded_path = unquote(encoded_path)
    if quote(decoded_path, safe="/") != encoded_path or "\\" in decoded_path:
        raise BundleValidationError("GitHub source path is not canonically encoded")
    if any(part in {"", ".", ".."} for part in decoded_path.split("/")):
        raise BundleValidationError("GitHub source path contains traversal")


def validate_https_reference(value: str, repository: str, source_commit: str) -> None:
    """Reject credential-bearing or sensitive external links."""

    if "\\" in value or any(character.isspace() for character in value):
        raise BundleValidationError("external reference is not a valid public URL")
    try:
        parsed = urlsplit(value)
        parsed.port
    except ValueError as error:
        raise BundleValidationError("external reference is not a valid public URL") from error
    if parsed.scheme != "https" or not parsed.hostname:
        raise BundleValidationError("external reference must use HTTPS")
    if parsed.port not in {None, 443}:
        raise BundleValidationError("external reference uses a nonstandard HTTPS port")
    if parsed.hostname.casefold() not in {"github.com", "scorecard.dev"}:
        raise BundleValidationError("external reference uses an unsupported public origin")
    if parsed.username is not None or parsed.password is not None or parsed.fragment:
        raise BundleValidationError("external reference contains credentials or a fragment")
    decoded = decode_percent_layers(value)
    if decoded is None:
        raise BundleValidationError("external reference uses excessive percent encoding")
    if EMAIL_PATTERN.search(decoded):
        raise BundleValidationError("external reference contains an encoded identity")
    if RUNNER_PATH_PATTERN.search(decoded) or WINDOWS_PATH_PATTERN.search(decoded):
        raise BundleValidationError("external reference contains a local filesystem path")
    if any(pattern.search(decoded) for pattern in SECRET_PATTERNS):
        raise BundleValidationError("external reference contains secret-like data")
    hostname = parsed.hostname.casefold()
    if hostname == "github.com":
        if parsed.query:
            raise BundleValidationError("GitHub reference contains an unsupported query")
        validate_github_reference(parsed.path, repository, source_commit)
        return
    if parsed.query:
        allowed_scorecard_query = (
            hostname == "scorecard.dev"
            and parsed.path == "/viewer/"
            and parsed.query == f"uri=github.com/{repository}"
        )
        if not allowed_scorecard_query:
            raise BundleValidationError("external reference contains an unsupported query")
        return
    raise BundleValidationError("Scorecard reference must use the repository viewer contract")


def resolve_local_reference(
    output_root: Path,
    value: str,
    repository: str,
    source_commit: str,
) -> Path | None:
    """Resolve a relative bundle reference as if the site were served at /intelligence/."""

    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        validate_https_reference(value, repository, source_commit)
        return None
    if parsed.query:
        raise BundleValidationError("local bundle references may not contain queries")
    if parsed.fragment:
        if parsed.path or parsed.fragment not in ALLOWED_LOCAL_FRAGMENTS:
            raise BundleValidationError("local bundle references contain an unsupported fragment")
        return None
    decoded = unquote(parsed.path)
    if decoded.startswith("/") or "\\" in decoded:
        raise BundleValidationError("local bundle references must be relative to /intelligence/")
    relative = PurePosixPath(decoded)
    if ".." in relative.parts:
        raise BundleValidationError("local bundle reference contains traversal")
    if any(part in {"", ".", ".."} for part in relative.parts):
        if decoded.startswith("./"):
            relative = PurePosixPath(decoded[2:])
        else:
            raise BundleValidationError("local bundle reference is not canonical")
    if any(part in {"", ".", ".."} for part in relative.parts):
        raise BundleValidationError("local bundle reference contains traversal")
    destination = output_root.joinpath(*relative.parts)
    if not destination.is_file() or destination.is_symlink():
        raise BundleValidationError(f"local bundle reference is broken: {value}")
    return destination


def validate_html_references(
    output_root: Path,
    repository: str,
    source_commit: str,
) -> None:
    """Validate every HTML href/src and the required framework-free assets."""

    html_text = (output_root / "index.html").read_text(encoding="utf-8")
    collector = ReferenceCollector()
    collector.feed(html_text)
    destinations = {
        destination.name
        for _, value in collector.references
        if (
            destination := resolve_local_reference(
                output_root,
                value,
                repository,
                source_commit,
            )
        )
        is not None
    }
    required = {"explorer.js", "provenance.json", "styles.css", "summary.json"}
    if not required.issubset(destinations):
        missing = ", ".join(sorted(required - destinations))
        raise BundleValidationError(f"index.html does not reference required bundle files: {missing}")


def validate_canonical_assets(output_root: Path) -> None:
    """Require generated client assets to match Relay's sole canonical sources."""

    assets_root = Path(__file__).resolve().parents[1] / "assets"
    expected = {
        "explorer.js": assets_root / "explorer.js",
        "styles.css": assets_root / "dashboard.css",
    }
    for output_name, source in expected.items():
        try:
            source_bytes = source.read_bytes()
            output_bytes = (output_root / output_name).read_bytes()
        except OSError as error:
            raise BundleValidationError("canonical Relay client assets are unavailable") from error
        if output_bytes != source_bytes:
            raise BundleValidationError(f"{output_name} does not match the canonical Relay asset")


def iter_json_items(value: Any, path: str = "$") -> list[tuple[str, str | None, Any]]:
    """Return stable JSON paths, member names, and scalar values for privacy checks."""

    items: list[tuple[str, str | None, Any]] = []
    if isinstance(value, dict):
        for key in sorted(value):
            child_path = f"{path}.{key}"
            items.append((child_path, key, value[key]))
            items.extend(iter_json_items(value[key], child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            items.extend(iter_json_items(child, f"{path}[{index}]"))
    return items


def validate_privacy(
    output_root: Path,
    repository_root: Path,
    documents: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    """Reject identities, secrets, raw private fields, and runner-local paths."""

    for document in documents:
        for path, key, value in iter_json_items(document):
            if key is not None and key.casefold() in FORBIDDEN_PUBLIC_KEYS:
                raise BundleValidationError(f"public JSON contains a private field: {path}")
            if key is not None and (
                EMAIL_PATTERN.search(key)
                or RUNNER_PATH_PATTERN.search(key)
                or WINDOWS_PATH_PATTERN.search(key)
                or any(pattern.search(key) for pattern in SECRET_PATTERNS)
            ):
                raise BundleValidationError(f"public JSON contains a private member name: {path}")
            if not isinstance(value, str):
                continue
            if EMAIL_PATTERN.search(value):
                raise BundleValidationError(f"public JSON contains an email address: {path}")
            if RUNNER_PATH_PATTERN.search(value) or WINDOWS_PATH_PATTERN.search(value):
                raise BundleValidationError(f"public JSON contains a local filesystem path: {path}")
            if any(pattern.search(value) for pattern in SECRET_PATTERNS):
                raise BundleValidationError(f"public JSON contains a secret-like value: {path}")
    repository_path = str(repository_root)
    for name in sorted(BUNDLE_FILES):
        text = (output_root / name).read_text(encoding="utf-8")
        decoded_text = decode_percent_layers(text)
        if decoded_text is None:
            raise BundleValidationError(
                f"generated projection uses excessive percent encoding in {name}"
            )
        if repository_path and repository_path in text:
            raise BundleValidationError(f"generated projection exposes the consumer workspace in {name}")
        if ".cache/repository-intelligence/activity" in text:
            raise BundleValidationError(f"generated projection exposes private diagnostics in {name}")
        if EMAIL_PATTERN.search(text) or EMAIL_PATTERN.search(decoded_text):
            raise BundleValidationError(f"generated projection contains an email address in {name}")
        if (
            RUNNER_PATH_PATTERN.search(text)
            or WINDOWS_PATH_PATTERN.search(text)
            or RUNNER_PATH_PATTERN.search(decoded_text)
            or WINDOWS_PATH_PATTERN.search(decoded_text)
        ):
            raise BundleValidationError(f"generated projection contains a local filesystem path in {name}")
        if any(
            pattern.search(text) or pattern.search(decoded_text)
            for pattern in SECRET_PATTERNS
        ):
            raise BundleValidationError(f"generated projection contains a secret-like value in {name}")


def validate_intelligence_route(
    output_root: Path,
    repository: str,
    source_commit: str,
) -> None:
    """Verify the route contract has an entry point and only relative local assets."""

    if not (output_root / "index.html").is_file():
        raise BundleValidationError("/intelligence/ has no index.html entry point")
    validate_html_references(output_root, repository, source_commit)


def validate_bundle(
    *,
    repository_root: Path,
    output_root: Path,
    repository: str,
    repository_visibility: str,
    source_commit: str,
    generator_version: str,
    generator_source_ref: str,
    generator_source_commit: str,
    generator_immutable: bool,
) -> None:
    """Validate the complete generated subtree."""

    root, output = canonical_output_root(repository_root, output_root)
    if not REPOSITORY_PATTERN.fullmatch(repository):
        raise BundleValidationError("consumer repository must use owner/name form")
    if not FULL_SHA_PATTERN.fullmatch(source_commit):
        raise BundleValidationError("consumer source commit must be a full lowercase SHA")
    if generator_source_commit and not FULL_SHA_PATTERN.fullmatch(generator_source_commit):
        raise BundleValidationError("Relay source commit must be empty or a full lowercase SHA")
    collect_bundle_files(output)
    documents = validate_json_contracts(
        output,
        repository=repository,
        repository_visibility=repository_visibility,
        source_commit=source_commit,
        generator_version=generator_version,
        generator_source_ref=generator_source_ref,
        generator_source_commit=generator_source_commit,
        generator_immutable=generator_immutable,
    )
    validate_intelligence_route(output, repository, source_commit)
    validate_canonical_assets(output)
    validate_privacy(output, root, documents)


def main() -> int:
    """Validate one generated public subtree without mutating it."""

    arguments = parse_arguments()
    if arguments.generator_immutable not in {"true", "false"}:
        raise SystemExit("--generator-immutable must be true or false")
    try:
        validate_bundle(
            repository_root=arguments.repository_root,
            output_root=arguments.output_root,
            repository=arguments.repository,
            repository_visibility=arguments.repository_visibility,
            source_commit=arguments.source_commit,
            generator_version=arguments.generator_version,
            generator_source_ref=arguments.generator_source_ref,
            generator_source_commit=arguments.generator_source_commit,
            generator_immutable=arguments.generator_immutable == "true",
        )
    except BundleValidationError as error:
        raise SystemExit(f"Repository Intelligence bundle is invalid: {error}") from error
    print(f"Validated Repository Intelligence subtree: {arguments.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
