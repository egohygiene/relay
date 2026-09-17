# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Normalize bounded artifact-size evidence into one Relay budget report."""

from __future__ import annotations

import argparse
from collections.abc import Iterable
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any


REPORT_SCHEMA = "egohygiene.relay.artifact-budget-report/v1"
REPORT_SCHEMA_ID = (
    "https://egohygiene.github.io/relay/contracts/"
    "artifact-budget-report/v1/schema.json"
)
VALID_ADAPTERS = {"filesystem", "size-limit-json"}
VALID_ARTIFACT_KINDS = {
    "archive",
    "container-image-archive",
    "directory",
    "file",
    "javascript-bundle",
    "native-binary",
    "other",
    "static-site",
}
VALID_MODES = {"advisory", "blocking"}
STATUS_PRECEDENCE = {
    "pass": 0,
    "warn": 1,
    "missing-baseline": 2,
    "unsupported": 3,
    "fail": 4,
}
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SUBJECT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
MAX_SIZE_LIMIT_NAME = 200
MAX_SIZE_LIMIT_JSON_BYTES = 8_388_608
MAX_EXACT_JSON_INTEGER = 9_007_199_254_740_991


class ContractError(ValueError):
    """Raised when caller input cannot satisfy the public action contract."""


def parse_non_negative_integer(value: str, name: str) -> int:
    """Parse a non-negative integer input."""

    if not re.fullmatch(r"0|[1-9][0-9]*", value):
        raise ContractError(f"{name} must be a non-negative whole number")
    parsed = int(value)
    if parsed > MAX_EXACT_JSON_INTEGER:
        raise ContractError(f"{name} exceeds the supported integer range")
    return parsed


def parse_positive_integer(value: str, name: str) -> int:
    """Parse a positive integer input."""

    parsed = parse_non_negative_integer(value, name)
    if parsed == 0:
        raise ContractError(f"{name} must be greater than zero")
    return parsed


def parse_optional_integer(value: str, name: str) -> int | None:
    """Parse an optional non-negative integer input."""

    if not value:
        return None
    return parse_non_negative_integer(value, name)


def parse_optional_number(value: str, name: str) -> float | None:
    """Parse an optional finite non-negative number input."""

    if not value:
        return None
    try:
        parsed = float(value)
    except ValueError as error:
        raise ContractError(f"{name} must be a non-negative number") from error
    if not math.isfinite(parsed) or parsed < 0:
        raise ContractError(f"{name} must be a finite non-negative number")
    return parsed


def parse_warning_threshold(value: str) -> float:
    """Parse the percentage at which a passing budget becomes a warning."""

    parsed = parse_optional_number(value, "warning-threshold-percent")
    if parsed is None or parsed <= 0 or parsed >= 100:
        raise ContractError(
            "warning-threshold-percent must be greater than zero and less than 100"
        )
    return parsed


def validate_revision(value: str, name: str, required: bool) -> str | None:
    """Validate one optional or required immutable Git revision."""

    if not value:
        if required:
            raise ContractError(f"{name} is required")
        return None
    if not FULL_SHA.fullmatch(value):
        raise ContractError(f"{name} must be a full lowercase 40-character Git SHA")
    return value


def workspace_root() -> Path:
    """Return the resolved GitHub workspace or current working directory."""

    configured = os.environ.get("GITHUB_WORKSPACE", "")
    root = Path(configured) if configured else Path.cwd()
    return root.resolve(strict=True)


def validate_relative_path(value: str, name: str, root: Path) -> Path:
    """Resolve a repository-relative path without accepting symlink components."""

    if not value or "\x00" in value:
        raise ContractError(f"{name} must be a non-empty repository-relative path")
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ContractError(f"{name} must remain within GITHUB_WORKSPACE")
    current = root
    for part in candidate.parts:
        if part in {"", "."}:
            continue
        current = current / part
        if current.is_symlink():
            raise ContractError(f"{name} must not contain symbolic links")
    resolved = (root / candidate).resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ContractError(f"{name} must remain within GITHUB_WORKSPACE") from error
    return resolved


def display_path(path: Path, root: Path) -> str:
    """Return a stable workspace-relative display path."""

    relative = path.relative_to(root).as_posix()
    return relative or "."


def ensure_output_is_outside_sources(output: Path, sources: Iterable[Path]) -> None:
    """Reject an output nested within a measured file or directory."""

    for source in sources:
        if output == source:
            raise ContractError("output must not replace a measured source")
        if source.is_dir():
            try:
                output.relative_to(source)
            except ValueError:
                continue
            raise ContractError("output must not be nested inside a measured directory")


def scan_filesystem(
    path: Path,
    artifact_kind: str,
    maximum_files: int,
    scan_maximum_bytes: int,
) -> dict[str, int | str]:
    """Measure a regular file or directory under explicit resource ceilings."""

    if not path.exists():
        raise ContractError(f"artifact path does not exist: {path}")
    mode = path.lstat().st_mode
    if stat.S_ISLNK(mode):
        raise ContractError("artifact path must not be a symbolic link")

    directory_kinds = {"directory", "static-site"}
    file_kinds = {
        "archive",
        "container-image-archive",
        "file",
        "native-binary",
    }
    if artifact_kind in directory_kinds and not path.is_dir():
        raise ContractError(f"artifact-kind {artifact_kind} requires a directory")
    if artifact_kind in file_kinds and not path.is_file():
        raise ContractError(f"artifact-kind {artifact_kind} requires a regular file")

    if path.is_file():
        size = path.stat().st_size
        if size > scan_maximum_bytes:
            raise ContractError("artifact exceeds scan-maximum-bytes")
        return {"kind": "file", "file_count": 1, "total_bytes": size}
    if not path.is_dir():
        raise ContractError("artifact path must be a regular file or directory")

    entry_count = 0
    file_count = 0
    total_bytes = 0
    for candidate in path.rglob("*"):
        entry_count += 1
        if entry_count > maximum_files:
            raise ContractError("artifact exceeds maximum-files")
        candidate_mode = candidate.lstat().st_mode
        if stat.S_ISLNK(candidate_mode):
            raise ContractError("artifact directory must not contain symbolic links")
        if stat.S_ISDIR(candidate_mode):
            continue
        if not stat.S_ISREG(candidate_mode):
            raise ContractError("artifact directory must contain only regular files")
        file_count += 1
        total_bytes += candidate.stat().st_size
        if total_bytes > scan_maximum_bytes:
            raise ContractError("artifact exceeds scan-maximum-bytes")
    return {"kind": "directory", "file_count": file_count, "total_bytes": total_bytes}


def load_size_limit(
    path: Path,
    maximum_items: int,
    scan_maximum_bytes: int,
) -> list[dict[str, Any]]:
    """Load and validate Size Limit's documented ``--json`` array."""

    if not path.is_file():
        raise ContractError("size-limit-json input must be a regular JSON file")
    size = path.stat().st_size
    if size > MAX_SIZE_LIMIT_JSON_BYTES:
        raise ContractError("size-limit-json input exceeds the 8 MiB parser safety ceiling")
    if size > scan_maximum_bytes:
        raise ContractError("size-limit-json input exceeds scan-maximum-bytes")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise ContractError(f"size-limit-json input is invalid: {error}") from error
    if isinstance(value, dict) and isinstance(value.get("error"), str):
        raise ContractError("Size Limit reported an execution error instead of results")
    if not isinstance(value, list) or not value:
        raise ContractError("size-limit-json input must be a non-empty JSON array")
    if len(value) > maximum_items:
        raise ContractError("size-limit-json input exceeds maximum-items")

    normalized: list[dict[str, Any]] = []
    names: set[str] = set()
    allowed = {"name", "passed", "size", "sizeLimit", "running", "loading"}
    for index, item in enumerate(value):
        label = f"size-limit-json[{index}]"
        if not isinstance(item, dict) or not set(item).issubset(allowed):
            raise ContractError(f"{label} has an unsupported shape")
        name = item.get("name")
        if (
            not isinstance(name, str)
            or not name.strip()
            or len(name) > MAX_SIZE_LIMIT_NAME
            or any(ord(character) < 32 for character in name)
        ):
            raise ContractError(f"{label}.name is invalid")
        if name in names:
            raise ContractError(f"size-limit-json contains duplicate name: {name}")
        names.add(name)
        parsed: dict[str, Any] = {"name": name}
        for field in ("size", "sizeLimit"):
            field_value = item.get(field)
            if field_value is not None:
                if (
                    isinstance(field_value, bool)
                    or not isinstance(field_value, int)
                    or field_value < 0
                    or field_value > MAX_EXACT_JSON_INTEGER
                ):
                    raise ContractError(
                        f"{label}.{field} must be a supported non-negative integer"
                    )
                parsed[field] = field_value
        passed = item.get("passed")
        if passed is not None:
            if not isinstance(passed, bool):
                raise ContractError(f"{label}.passed must be boolean")
            parsed["passed"] = passed
        for field in ("running", "loading"):
            field_value = item.get(field)
            if field_value is not None:
                if (
                    isinstance(field_value, bool)
                    or not isinstance(field_value, (int, float))
                    or not math.isfinite(float(field_value))
                    or field_value < 0
                ):
                    raise ContractError(f"{label}.{field} must be non-negative and finite")
                parsed[field] = float(field_value)
        normalized.append(parsed)
    return sorted(normalized, key=lambda item: item["name"])


def percentage_delta(current: int, baseline: int) -> float | None:
    """Return a deterministic percentage delta or ``None`` for zero baselines."""

    if baseline == 0:
        return 0.0 if current == 0 else None
    return round(((current - baseline) / baseline) * 100, 6)


def threshold_warning(value: float, maximum: float, warning_percent: float) -> bool:
    """Return whether a non-failing value reached the configured warning band."""

    if maximum <= 0:
        return False
    return value >= maximum * (warning_percent / 100)


def evaluate_measurement(
    identifier: str,
    current_bytes: int | None,
    baseline_bytes: int | None,
    baseline_expected: bool,
    source_budget_bytes: int | None,
    source_passed: bool | None,
    source_loading_seconds: float | None,
    source_running_seconds: float | None,
    budget: dict[str, int | float | None],
) -> dict[str, Any]:
    """Evaluate one measurement against absolute and regression budgets."""

    reasons: list[str] = []
    states: list[str] = ["pass"]
    delta_bytes = None
    delta_percent = None
    if current_bytes is None:
        states.append("unsupported")
        reasons.append("deterministic-byte-measurement-unavailable")
    elif baseline_bytes is not None:
        delta_bytes = current_bytes - baseline_bytes
        delta_percent = percentage_delta(current_bytes, baseline_bytes)
    elif baseline_expected:
        states.append("missing-baseline")
        reasons.append("baseline-entry-missing")

    requires_baseline = any(
        budget[key] is not None
        for key in ("maximum_increase_bytes", "maximum_increase_percent")
    )
    if current_bytes is not None and baseline_bytes is None and requires_baseline:
        states.append("missing-baseline")
        if "baseline-entry-missing" not in reasons:
            reasons.append("regression-budget-requires-baseline")

    maximum_bytes = budget["maximum_bytes"]
    maximum_increase_bytes = budget["maximum_increase_bytes"]
    maximum_increase_percent = budget["maximum_increase_percent"]
    warning_percent = float(budget["warning_threshold_percent"])

    absolute_limits = [
        ("configured-maximum-bytes", maximum_bytes),
        ("size-limit-maximum-bytes", source_budget_bytes),
    ]
    if current_bytes is not None:
        for reason, maximum in absolute_limits:
            if maximum is None:
                continue
            if current_bytes > maximum:
                states.append("fail")
                reasons.append(reason)
            elif threshold_warning(current_bytes, maximum, warning_percent):
                states.append("warn")
                reasons.append(f"approaching-{reason}")

    if delta_bytes is not None and maximum_increase_bytes is not None:
        if delta_bytes > maximum_increase_bytes:
            states.append("fail")
            reasons.append("maximum-increase-bytes-exceeded")
        elif threshold_warning(delta_bytes, maximum_increase_bytes, warning_percent):
            states.append("warn")
            reasons.append("approaching-maximum-increase-bytes")

    if maximum_increase_percent is not None and baseline_bytes is not None:
        if delta_percent is None:
            states.append("unsupported")
            reasons.append("percentage-regression-undefined-for-zero-baseline")
        elif delta_percent > maximum_increase_percent:
            states.append("fail")
            reasons.append("maximum-increase-percent-exceeded")
        elif threshold_warning(delta_percent, maximum_increase_percent, warning_percent):
            states.append("warn")
            reasons.append("approaching-maximum-increase-percent")

    if source_passed is False:
        states.append("fail")
        reasons.append("size-limit-reported-failure")

    state = max(states, key=lambda value: STATUS_PRECEDENCE[value])
    return {
        "id": identifier,
        "metric": "bytes",
        "current_bytes": current_bytes,
        "baseline_bytes": baseline_bytes,
        "delta_bytes": delta_bytes,
        "delta_percent": delta_percent,
        "source": {
            "size_limit_bytes": source_budget_bytes,
            "passed": source_passed,
            "loading_seconds": source_loading_seconds,
            "running_seconds": source_running_seconds,
        },
        "state": state,
        "reasons": sorted(set(reasons)),
    }


def summarize(measurements: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    """Summarize measurement states and totals without hiding incomplete evidence."""

    counts = {state: 0 for state in STATUS_PRECEDENCE}
    for measurement in measurements:
        counts[measurement["state"]] += 1
    state = max(
        (measurement["state"] for measurement in measurements),
        key=lambda value: STATUS_PRECEDENCE[value],
    )
    current_values = [measurement["current_bytes"] for measurement in measurements]
    baseline_values = [measurement["baseline_bytes"] for measurement in measurements]
    current_total = (
        sum(current_values) if all(value is not None for value in current_values) else None
    )
    baseline_total = (
        sum(baseline_values)
        if all(value is not None for value in baseline_values)
        else None
    )
    total_delta = (
        current_total - baseline_total
        if current_total is not None and baseline_total is not None
        else None
    )
    total_delta_percent = (
        percentage_delta(current_total, baseline_total)
        if current_total is not None and baseline_total is not None
        else None
    )
    return {
        "state": state,
        "counts": counts,
        "measurement_count": len(measurements),
        "current_total_bytes": current_total,
        "baseline_total_bytes": baseline_total,
        "delta_total_bytes": total_delta,
        "delta_total_percent": total_delta_percent,
        "blocking_failure": mode == "blocking"
        and state in {"fail", "missing-baseline", "unsupported"},
    }


def filesystem_report(
    current_path: Path,
    baseline_path: Path | None,
    artifact_kind: str,
    subject: str,
    maximum_files: int,
    scan_maximum_bytes: int,
    budget: dict[str, int | float | None],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Create measurements and coverage for a materialized filesystem artifact."""

    current = scan_filesystem(
        current_path, artifact_kind, maximum_files, scan_maximum_bytes
    )
    baseline = (
        scan_filesystem(baseline_path, artifact_kind, maximum_files, scan_maximum_bytes)
        if baseline_path is not None
        else None
    )
    measurement = evaluate_measurement(
        subject,
        int(current["total_bytes"]),
        int(baseline["total_bytes"]) if baseline else None,
        baseline_path is not None,
        None,
        None,
        None,
        None,
        budget,
    )
    coverage = {
        "current": {"state": "complete", **current},
        "baseline": (
            {"state": "complete", **baseline}
            if baseline
            else {"state": "not-provided", "kind": None, "file_count": 0, "total_bytes": None}
        ),
    }
    return [measurement], coverage


def size_limit_report(
    current_path: Path,
    baseline_path: Path | None,
    maximum_items: int,
    scan_maximum_bytes: int,
    budget: dict[str, int | float | None],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Normalize Size Limit JSON without executing project code or installing Node."""

    current = load_size_limit(current_path, maximum_items, scan_maximum_bytes)
    baseline = (
        load_size_limit(baseline_path, maximum_items, scan_maximum_bytes)
        if baseline_path
        else []
    )
    baseline_by_name = {item["name"]: item for item in baseline}
    measurements: list[dict[str, Any]] = []
    for item in current:
        baseline_item = baseline_by_name.get(item["name"])
        measurements.append(
            evaluate_measurement(
                item["name"],
                item.get("size"),
                baseline_item.get("size") if baseline_item else None,
                baseline_path is not None,
                item.get("sizeLimit"),
                item.get("passed"),
                item.get("loading"),
                item.get("running"),
                budget,
            )
        )
    def complete_total(items: list[dict[str, Any]]) -> int | None:
        values = [item.get("size") for item in items]
        if not values or any(value is None for value in values):
            return None
        total = sum(values)
        if total > MAX_EXACT_JSON_INTEGER:
            raise ContractError("Size Limit aggregate exceeds the supported integer range")
        return total

    current_total = complete_total(current)
    baseline_total = complete_total(baseline)
    coverage = {
        "current": {
            "state": "complete",
            "kind": "size-limit-json",
            "file_count": len(current),
            "total_bytes": current_total,
        },
        "baseline": (
            {
                "state": "complete",
                "kind": "size-limit-json",
                "file_count": len(baseline),
                "total_bytes": baseline_total,
            }
            if baseline_path
            else {"state": "not-provided", "kind": None, "file_count": 0, "total_bytes": None}
        ),
    }
    return measurements, coverage


def canonical_json(value: dict[str, Any]) -> bytes:
    """Return stable UTF-8 report bytes."""

    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_report(path: Path, report: dict[str, Any]) -> str:
    """Write the deterministic report and return its SHA-256 digest."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json(report)
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def write_github_output(path: str, report: dict[str, Any], digest: str) -> None:
    """Write bounded scalar outputs when running as a composite action."""

    if not path:
        return
    summary = report["summary"]
    values = {
        "status": summary["state"],
        "report-sha256": digest,
        "measurement-count": summary["measurement_count"],
        "current-total-bytes": summary["current_total_bytes"]
        if summary["current_total_bytes"] is not None
        else "",
        "delta-total-bytes": summary["delta_total_bytes"]
        if summary["delta_total_bytes"] is not None
        else "",
    }
    with Path(path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def markdown_escape(value: str) -> str:
    """Escape one bounded value for a GitHub Markdown table."""

    return value.replace("|", "\\|")


def write_step_summary(report: dict[str, Any]) -> None:
    """Append a compact artifact-budget summary when GitHub provides a target."""

    target = os.environ.get("GITHUB_STEP_SUMMARY", "")
    if not target:
        return
    summary = report["summary"]
    lines = [
        "## Relay artifact budget",
        "",
        f"Overall state: **{summary['state']}**",
        "",
        "| Measurement | Current bytes | Baseline bytes | Delta bytes | State |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for measurement in report["measurements"]:
        lines.append(
            "| {identifier} | {current} | {baseline} | {delta} | {state} |".format(
                identifier=markdown_escape(measurement["id"]),
                current=measurement["current_bytes"]
                if measurement["current_bytes"] is not None
                else "unavailable",
                baseline=measurement["baseline_bytes"]
                if measurement["baseline_bytes"] is not None
                else "unavailable",
                delta=measurement["delta_bytes"]
                if measurement["delta_bytes"] is not None
                else "unavailable",
                state=measurement["state"],
            )
        )
    with Path(target).open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def build_report(arguments: argparse.Namespace) -> tuple[dict[str, Any], Path]:
    """Validate CLI arguments and build the complete public report."""

    if arguments.adapter not in VALID_ADAPTERS:
        raise ContractError(f"unsupported adapter: {arguments.adapter}")
    if arguments.artifact_kind not in VALID_ARTIFACT_KINDS:
        raise ContractError(f"unsupported artifact-kind: {arguments.artifact_kind}")
    if arguments.mode not in VALID_MODES:
        raise ContractError(f"unsupported mode: {arguments.mode}")
    if not SUBJECT_ID.fullmatch(arguments.subject):
        raise ContractError(
            "subject must be a bounded identifier using letters, numbers, dot, underscore, or hyphen"
        )
    if arguments.adapter == "size-limit-json" and arguments.artifact_kind != "javascript-bundle":
        raise ContractError("size-limit-json requires artifact-kind javascript-bundle")

    root = workspace_root()
    current_path = validate_relative_path(arguments.current_path, "current-path", root)
    baseline_path = (
        validate_relative_path(arguments.baseline_path, "baseline-path", root)
        if arguments.baseline_path
        else None
    )
    output = validate_relative_path(arguments.output, "output", root)
    sources = [current_path, *([baseline_path] if baseline_path else [])]
    ensure_output_is_outside_sources(output, sources)

    current_revision = validate_revision(
        arguments.current_revision, "current-revision", required=True
    )
    baseline_revision = validate_revision(
        arguments.baseline_revision,
        "baseline-revision",
        required=baseline_path is not None,
    )
    if baseline_revision and baseline_path is None:
        raise ContractError("baseline-revision requires baseline-path")

    maximum_files = parse_positive_integer(arguments.maximum_files, "maximum-files")
    maximum_items = parse_positive_integer(arguments.maximum_items, "maximum-items")
    scan_maximum_bytes = parse_positive_integer(
        arguments.scan_maximum_bytes, "scan-maximum-bytes"
    )
    budget: dict[str, int | float | None] = {
        "maximum_bytes": parse_optional_integer(
            arguments.maximum_bytes, "maximum-bytes"
        ),
        "maximum_increase_bytes": parse_optional_integer(
            arguments.maximum_increase_bytes, "maximum-increase-bytes"
        ),
        "maximum_increase_percent": parse_optional_number(
            arguments.maximum_increase_percent, "maximum-increase-percent"
        ),
        "warning_threshold_percent": parse_warning_threshold(
            arguments.warning_threshold_percent
        ),
    }

    if arguments.adapter == "filesystem":
        measurements, coverage = filesystem_report(
            current_path,
            baseline_path,
            arguments.artifact_kind,
            arguments.subject,
            maximum_files,
            scan_maximum_bytes,
            budget,
        )
    else:
        measurements, coverage = size_limit_report(
            current_path,
            baseline_path,
            maximum_items,
            scan_maximum_bytes,
            budget,
        )
    summary = summarize(measurements, arguments.mode)
    report = {
        "$schema": REPORT_SCHEMA_ID,
        "schema": REPORT_SCHEMA,
        "contract_version": 1,
        "subject": {
            "id": arguments.subject,
            "adapter": arguments.adapter,
            "artifact_kind": arguments.artifact_kind,
        },
        "mode": arguments.mode,
        "revisions": {
            "current": current_revision,
            "baseline": baseline_revision,
        },
        "sources": {
            "current": display_path(current_path, root),
            "baseline": display_path(baseline_path, root) if baseline_path else None,
        },
        "budget": budget,
        "limits": {
            "maximum_files": maximum_files,
            "maximum_items": maximum_items,
            "scan_maximum_bytes": scan_maximum_bytes,
        },
        "coverage": coverage,
        "measurements": measurements,
        "summary": summary,
    }
    return report, output


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line parser used by local and action execution."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--artifact-kind", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--current-path", required=True)
    parser.add_argument("--baseline-path", default="")
    parser.add_argument("--current-revision", required=True)
    parser.add_argument("--baseline-revision", default="")
    parser.add_argument("--mode", default="advisory")
    parser.add_argument("--maximum-bytes", default="")
    parser.add_argument("--maximum-increase-bytes", default="")
    parser.add_argument("--maximum-increase-percent", default="")
    parser.add_argument("--warning-threshold-percent", default="90")
    parser.add_argument("--maximum-files", default="10000")
    parser.add_argument("--maximum-items", default="100")
    parser.add_argument("--scan-maximum-bytes", default="1073741824")
    parser.add_argument("--output", required=True)
    parser.add_argument("--github-output", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run artifact-budget normalization and return the enforcement exit code."""

    arguments = create_parser().parse_args(argv)
    try:
        report, output = build_report(arguments)
        digest = write_report(output, report)
        write_github_output(arguments.github_output, report, digest)
        write_step_summary(report)
    except (ContractError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(
        f"Artifact budget {report['summary']['state']}: "
        f"{report['summary']['measurement_count']} measurement(s); "
        f"report sha256 {digest}"
    )
    return 1 if report["summary"]["blocking_failure"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
