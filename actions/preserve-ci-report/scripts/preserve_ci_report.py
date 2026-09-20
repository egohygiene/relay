# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT
"""Bind one bounded CI report directory to immutable workflow-run evidence."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import stat

PRODUCER = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA256 = re.compile(r"^[0-9a-f]{40}$")
OUTCOMES = {"success", "failure", "cancelled", "skipped"}
METADATA_NAMES = {"relay-report-manifest.json", "SHA256SUMS"}


def positive_integer(value: str, label: str, maximum: int) -> int:
    """Parse a bounded positive decimal integer."""

    if not re.fullmatch(r"[1-9][0-9]*", value):
        raise ValueError(f"{label} must be a positive decimal integer")
    parsed = int(value)
    if parsed > maximum:
        raise ValueError(f"{label} must not exceed {maximum}")
    return parsed


def sha256(path: Path) -> str:
    """Return the SHA-256 digest of one regular file."""

    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def scan_report(directory: Path, maximum_files: int, maximum_bytes: int) -> list[dict[str, object]]:
    """Return a deterministic bounded inventory without following links."""

    files: list[dict[str, object]] = []
    total_bytes = 0
    for path in sorted(directory.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(directory).as_posix()
        if path.is_symlink():
            raise ValueError(f"report evidence must not contain symbolic links: {relative}")
        mode = path.stat(follow_symlinks=False).st_mode
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode):
            raise ValueError(f"report evidence must contain only regular files: {relative}")
        if relative in METADATA_NAMES:
            continue
        size = path.stat(follow_symlinks=False).st_size
        total_bytes += size
        if len(files) + 1 > maximum_files:
            raise ValueError(f"report evidence exceeds the {maximum_files}-file limit")
        if total_bytes > maximum_bytes:
            raise ValueError(f"report evidence exceeds the {maximum_bytes}-byte limit")
        files.append({"path": relative, "sha256": sha256(path), "size_bytes": size})
    return files


def prepare(arguments: argparse.Namespace) -> dict[str, str]:
    """Validate inputs, create the manifest, and return action outputs."""

    if not PRODUCER.fullmatch(arguments.producer):
        raise ValueError("producer must be a stable lowercase kebab-case identifier")
    if arguments.outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of: {', '.join(sorted(OUTCOMES))}")
    if not REPOSITORY.fullmatch(arguments.repository):
        raise ValueError("repository must use owner/name form")
    if not SHA256.fullmatch(arguments.represented_revision):
        raise ValueError("represented-revision must be a full lowercase Git SHA")

    run_id = positive_integer(arguments.run_id, "run-id", 10**20)
    run_attempt = positive_integer(arguments.run_attempt, "run-attempt", 10**6)
    retention_days = positive_integer(arguments.retention_days, "retention-days", 90)
    maximum_files = positive_integer(arguments.maximum_files, "maximum-files", 10_000)
    maximum_bytes = positive_integer(arguments.maximum_bytes, "maximum-bytes", 1024**3)

    workspace = Path.cwd().resolve()
    relative_directory = Path(".reports") / arguments.producer
    directory = workspace / relative_directory
    directory.mkdir(parents=True, exist_ok=True)
    if directory.is_symlink() or directory.resolve() != directory:
        raise ValueError("report directory must be a real path inside the workspace")

    for metadata_name in METADATA_NAMES:
        (directory / metadata_name).unlink(missing_ok=True)
    files = scan_report(directory, maximum_files, maximum_bytes)
    if arguments.outcome == "success" and not files:
        raise ValueError("a successful check must preserve at least one producer report file")

    if arguments.outcome == "success":
        completeness = "complete"
    elif files:
        completeness = "partial"
    else:
        completeness = "unavailable"

    manifest = {
        "$schema": "https://egohygiene.github.io/relay/contracts/ci-report-manifest/v1/schema.json",
        "schema": "egohygiene.relay.ci-report-manifest/v1",
        "producer": arguments.producer,
        "repository": arguments.repository,
        "represented_revision": arguments.represented_revision,
        "run": {"id": run_id, "attempt": run_attempt},
        "outcome": arguments.outcome,
        "completeness": completeness,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "retention_days": retention_days,
        "limits": {"maximum_files": maximum_files, "maximum_bytes": maximum_bytes},
        "files": files,
    }
    manifest_path = directory / "relay-report-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest_digest = sha256(manifest_path)

    checksum_lines = [f"{item['sha256']}  {item['path']}" for item in files]
    checksum_lines.append(f"{manifest_digest}  relay-report-manifest.json")
    (directory / "SHA256SUMS").write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8"
    )

    artifact_name = (
        f"relay-report-{arguments.producer}-{run_id}-{run_attempt}"
    )
    outputs = {
        "artifact-name": artifact_name,
        "completeness": completeness,
        "manifest-path": (relative_directory / manifest_path.name).as_posix(),
        "manifest-sha256": manifest_digest,
        "report-directory": relative_directory.as_posix(),
    }
    if arguments.github_output:
        with Path(arguments.github_output).open("a", encoding="utf-8") as destination:
            for key, value in outputs.items():
                destination.write(f"{key}={value}\n")
    return outputs


def parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    value = argparse.ArgumentParser()
    value.add_argument("--producer", required=True)
    value.add_argument("--outcome", required=True)
    value.add_argument("--repository", required=True)
    value.add_argument("--represented-revision", required=True)
    value.add_argument("--run-id", required=True)
    value.add_argument("--run-attempt", required=True)
    value.add_argument("--retention-days", required=True)
    value.add_argument("--maximum-files", required=True)
    value.add_argument("--maximum-bytes", required=True)
    value.add_argument("--github-output")
    return value


def main() -> int:
    """Prepare one report bundle or fail closed with a concise error."""

    try:
        prepare(parser().parse_args())
    except (OSError, ValueError) as error:
        print(f"preserve-ci-report: {error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
