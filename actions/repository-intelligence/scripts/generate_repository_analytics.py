# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import calendar
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

ANALYTICS_SCHEMA = "egohygiene.repository-analytics/v1"
ANALYTICS_SCHEMA_VERSION = 1
DEFAULT_EXCLUDED_PATHS = [
    ".git",
    ".staging",
    ".cache",
    ".venv",
    ".tox",
    ".mypy_cache",
    ".ruff_cache",
    ".reports",
    "docs/generated",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    "site",
    "target",
]
RELATIVE_SINCE = re.compile(
    r"^(?P<count>[1-9][0-9]*)\s+(?P<unit>day|week|month|year)s?\s+ago$",
    re.IGNORECASE,
)
BRACED_RENAME = re.compile(r"\{[^{}]* => (?P<destination>[^{}]*)\}")

JsonObject = dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a deterministic, public-safe repository analytics summary."
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--since", default="1 year ago")
    parser.add_argument(
        "--excluded-paths",
        default=",".join(DEFAULT_EXCLUDED_PATHS),
        help="Comma-separated paths excluded from public repository analytics.",
    )
    return parser.parse_args()


def run_git(repo_root: Path, arguments: Sequence[str]) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *arguments],
        check=True,
        capture_output=True,
    )
    return completed.stdout


def normalize_excluded_paths(raw_paths: str) -> list[str]:
    excluded: list[str] = []
    for raw_path in raw_paths.split(","):
        candidate = raw_path.strip().strip("/")
        if candidate and candidate not in excluded:
            excluded.append(candidate)
    return excluded


def is_excluded_path(relative_path: str, excluded_paths: Iterable[str]) -> bool:
    parts = Path(relative_path).parts

    for excluded_path in excluded_paths:
        if "/" not in excluded_path and excluded_path in parts:
            return True
        if relative_path == excluded_path or relative_path.startswith(f"{excluded_path}/"):
            return True

    return False


def normalize_git_path(path: str) -> str:
    normalized = path

    while match := BRACED_RENAME.search(normalized):
        normalized = (
            normalized[: match.start()] + match.group("destination") + normalized[match.end() :]
        )

    if " => " in normalized:
        normalized = normalized.rsplit(" => ", maxsplit=1)[-1]

    return normalized


def parse_timestamp(raw_value: str) -> datetime:
    normalized = raw_value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def subtract_months(anchor: datetime, months: int) -> datetime:
    target_index = anchor.year * 12 + anchor.month - 1 - months
    target_year, target_month_index = divmod(target_index, 12)
    target_month = target_month_index + 1
    target_day = min(anchor.day, calendar.monthrange(target_year, target_month)[1])
    return anchor.replace(year=target_year, month=target_month, day=target_day)


def resolve_since(raw_since: str, anchor: datetime) -> datetime:
    candidate = raw_since.strip()
    match = RELATIVE_SINCE.fullmatch(candidate)

    if match:
        count = int(match.group("count"))
        unit = match.group("unit").lower()
        if unit == "day":
            return anchor - timedelta(days=count)
        if unit == "week":
            return anchor - timedelta(weeks=count)
        if unit == "month":
            return subtract_months(anchor, count)
        return subtract_months(anchor, count * 12)

    try:
        return parse_timestamp(candidate)
    except ValueError as error:
        raise ValueError(
            "since must be an ISO-8601 timestamp/date or '<count> days|weeks|months|years ago'"
        ) from error


def iso_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def top_level_area(relative_path: str) -> str:
    parts = Path(relative_path).parts
    return parts[0] if len(parts) > 1 else "(root)"


def extension_name(relative_path: str) -> str:
    suffix = Path(relative_path).suffix.casefold()
    return suffix if suffix else "[no extension]"


def list_tracked_paths(repo_root: Path, revision: str) -> list[str]:
    output = run_git(repo_root, ["ls-tree", "-r", "-z", "--name-only", revision])
    return [
        raw_path.decode("utf-8", errors="surrogateescape")
        for raw_path in output.split(b"\0")
        if raw_path
    ]


def collect_commits(
    repo_root: Path,
    revision: str,
    since: datetime,
) -> tuple[list[JsonObject], int]:
    output = run_git(
        repo_root,
        [
            "log",
            revision,
            f"--since={iso_timestamp(since)}",
            "--use-mailmap",
            "--format=%H%x1f%aI%x1f%P%x1f%aN%x1f%aE%x1e",
        ],
    ).decode("utf-8", errors="replace")
    commits: list[JsonObject] = []
    identities: set[tuple[str, str]] = set()

    for raw_record in output.split("\x1e"):
        record = raw_record.strip("\r\n")
        if not record:
            continue
        commit, authored_at, parents, author_name, author_email = record.split("\x1f", maxsplit=4)
        identities.add((author_name.strip().casefold(), author_email.strip().casefold()))
        commits.append(
            {
                "commit": commit,
                "authored_at": parse_timestamp(authored_at),
                "is_merge": len(parents.split()) > 1,
            }
        )

    return commits, len(identities)


def weekly_activity(commits: list[JsonObject]) -> list[JsonObject]:
    if not commits:
        return []

    counts: dict[datetime, Counter[str]] = defaultdict(Counter)
    for commit in commits:
        authored_at = commit["authored_at"]
        week = (authored_at - timedelta(days=authored_at.weekday())).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        counts[week]["commits"] += 1
        counts[week]["merges"] += int(commit["is_merge"])

    first_week = min(counts)
    last_week = max(counts)
    result: list[JsonObject] = []
    week = first_week
    while week <= last_week:
        result.append(
            {
                "week": week.date().isoformat(),
                "commits": counts[week]["commits"],
                "merges": counts[week]["merges"],
            }
        )
        week += timedelta(weeks=1)

    return result


def collect_changes(
    repo_root: Path,
    revision: str,
    since: datetime,
    excluded_paths: Iterable[str],
) -> tuple[dict[str, Counter[str]], int]:
    output = run_git(
        repo_root,
        [
            "log",
            revision,
            f"--since={iso_timestamp(since)}",
            "--format=",
            "--numstat",
            "-z",
            "--no-renames",
        ],
    )
    file_changes: dict[str, Counter[str]] = defaultdict(Counter)
    excluded_records = 0

    for raw_record in output.split(b"\0"):
        record = raw_record.lstrip(b"\r\n")
        if not record:
            continue
        fields = record.split(b"\t", maxsplit=2)
        if len(fields) != 3:
            continue
        raw_insertions, raw_deletions, raw_path = fields
        path = normalize_git_path(raw_path.decode("utf-8", errors="surrogateescape"))
        if is_excluded_path(path, excluded_paths):
            excluded_records += 1
            continue

        stats = file_changes[path]
        stats["commit_touches"] += 1
        if raw_insertions == b"-" or raw_deletions == b"-":
            stats["binary_changes"] += 1
        else:
            stats["insertions"] += int(raw_insertions)
            stats["deletions"] += int(raw_deletions)

    return file_changes, excluded_records


def area_file_counts(paths: Iterable[str]) -> list[JsonObject]:
    counts = Counter(top_level_area(path) for path in paths)
    return [
        {"name": name, "file_count": count}
        for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def extension_file_counts(paths: Iterable[str]) -> list[JsonObject]:
    counts = Counter(extension_name(path) for path in paths)
    return [
        {"name": name, "file_count": count}
        for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def change_metrics(stats: Counter[str]) -> JsonObject:
    return {
        "commit_touches": stats["commit_touches"],
        "insertions": stats["insertions"],
        "deletions": stats["deletions"],
        "binary_changes": stats["binary_changes"],
    }


def aggregate_change_areas(file_changes: dict[str, Counter[str]]) -> list[JsonObject]:
    areas: dict[str, Counter[str]] = defaultdict(Counter)
    for path, stats in file_changes.items():
        areas[top_level_area(path)].update(stats)

    return [
        {"name": name, **change_metrics(stats)}
        for name, stats in sorted(
            areas.items(),
            key=lambda item: (-item[1]["commit_touches"], item[0]),
        )
    ]


def hotspot_changes(file_changes: dict[str, Counter[str]], limit: int = 20) -> list[JsonObject]:
    ranked = sorted(
        file_changes.items(),
        key=lambda item: (-item[1]["commit_touches"], item[0]),
    )[:limit]
    return [{"path": path, **change_metrics(stats)} for path, stats in ranked]


def resolve_source(repo_root: Path, ref: str) -> tuple[str, datetime]:
    revision = (
        run_git(repo_root, ["rev-parse", "--verify", f"{ref}^{{commit}}"]).decode("utf-8").strip()
    )
    committed_at = (
        run_git(repo_root, ["show", "--no-patch", "--format=%cI", revision]).decode("utf-8").strip()
    )
    return revision, parse_timestamp(committed_at)


def generate_summary(
    repo_root: Path,
    ref: str,
    since_value: str,
    excluded_paths: list[str],
) -> JsonObject:
    revision, committed_at = resolve_source(repo_root, ref)
    since = resolve_since(since_value, committed_at)
    tracked_paths = list_tracked_paths(repo_root, revision)
    included_paths = [path for path in tracked_paths if not is_excluded_path(path, excluded_paths)]
    commits, contributor_count = collect_commits(repo_root, revision, since)
    file_changes, excluded_change_records = collect_changes(
        repo_root,
        revision,
        since,
        excluded_paths,
    )
    authored_dates = [commit["authored_at"] for commit in commits]
    insertions = sum(stats["insertions"] for stats in file_changes.values())
    deletions = sum(stats["deletions"] for stats in file_changes.values())

    return {
        "schema": ANALYTICS_SCHEMA,
        "schema_version": ANALYTICS_SCHEMA_VERSION,
        "source": {
            "revision": revision,
            "ref": ref,
            "committed_at": iso_timestamp(committed_at),
        },
        "scope": {
            "since": since_value,
            "resolved_since": iso_timestamp(since),
        },
        "privacy": {
            "public_safe": True,
            "contributor_identities_included": False,
            "commit_messages_included": False,
        },
        "repository": {
            "tracked_files": len(included_paths),
            "areas": area_file_counts(included_paths),
            "extensions": extension_file_counts(included_paths),
        },
        "activity": {
            "commits": len(commits),
            "merges": sum(int(commit["is_merge"]) for commit in commits),
            "contributors": contributor_count,
            "first_commit_at": iso_timestamp(min(authored_dates)) if authored_dates else None,
            "last_commit_at": iso_timestamp(max(authored_dates)) if authored_dates else None,
            "weekly": weekly_activity(commits),
        },
        "changes": {
            "files_changed": len(file_changes),
            "insertions": insertions,
            "deletions": deletions,
            "net_lines": insertions - deletions,
            "areas": aggregate_change_areas(file_changes),
            "hotspots": hotspot_changes(file_changes),
        },
        "filters": {
            "excluded_paths": excluded_paths,
            "excluded_tracked_files": len(tracked_paths) - len(included_paths),
            "excluded_change_records": excluded_change_records,
        },
    }


def atomic_write_json(path: Path, payload: JsonObject) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            json.dump(payload, handle, indent=2, sort_keys=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    output = Path(args.output).resolve()
    if not repo_root.is_dir():
        raise SystemExit(f"Repository root is not a directory: {repo_root}")
    try:
        output.relative_to(repo_root)
    except ValueError as error:
        raise SystemExit(f"Output must be inside the repository: {output}") from error

    try:
        summary = generate_summary(
            repo_root=repo_root,
            ref=args.ref,
            since_value=args.since,
            excluded_paths=normalize_excluded_paths(args.excluded_paths),
        )
    except (subprocess.CalledProcessError, ValueError) as error:
        raise SystemExit(f"Could not generate repository analytics: {error}") from error

    atomic_write_json(output, summary)


if __name__ == "__main__":
    main()
