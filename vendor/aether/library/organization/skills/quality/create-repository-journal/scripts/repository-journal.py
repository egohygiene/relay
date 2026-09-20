#!/usr/bin/env python3
"""Render a deterministic, evidence-labelled repository journal."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


CONTRACT_ID = "repository-journal"
CONTRACT_VERSION = "1.0.0"
ROOT = Path(__file__).resolve().parents[6]
SPEC_PATH = ROOT / "library/organization/specs/quality/repository-journal.spec.md"
SECTIONS = (
    ("Merged work and releases", ("merged_work", "releases")),
    ("Open work and stale work", ("open_work", "stale_work")),
    ("CI, dependency, and security signals", ("ci", "dependency_security")),
    ("Risks, blockers, and unknowns", ("risks_blockers",)),
    ("Proposed follow-up actions", ("follow_ups",)),
)


def _digest() -> str:
    return hashlib.sha256(SPEC_PATH.read_text(encoding="utf-8").replace("\r\n", "\n").encode()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {"schema_version", "repository", "interval", "evidence"}
    if not isinstance(data, dict) or set(data) - {"schema_version", "repository", "interval", "evidence", "repository_sections"} or not required <= set(data):
        raise ValueError("input must satisfy aether.repository-journal-input/v1")
    if data["schema_version"] != "aether.repository-journal-input/v1":
        raise ValueError("unsupported journal input schema version")
    if not isinstance(data["repository"], str) or data["repository"].count("/") != 1:
        raise ValueError("repository must be owner/repository")
    if not isinstance(data["interval"], dict) or set(data["interval"]) != {"start", "end"}:
        raise ValueError("interval requires start and end")
    if not all(isinstance(data["interval"][key], str) and data["interval"][key].endswith("Z") for key in ("start", "end")):
        raise ValueError("interval timestamps must be UTC RFC 3339 strings")
    if not isinstance(data["evidence"], dict) or any(not isinstance(v, list) or not all(isinstance(item, str) for item in v) for v in data["evidence"].values()):
        raise ValueError("evidence values must be lists of strings")
    return data


def _lines(evidence: dict[str, list[str]], keys: tuple[str, ...]) -> list[str]:
    lines: list[str] = []
    for key in keys:
        label = key.replace("_", " ")
        if key not in evidence:
            lines.append(f"- {label}: not available")
        elif not evidence[key]:
            lines.append(f"- {label}: observed: none")
        else:
            lines.extend(f"- {label}: observed: {item}" for item in evidence[key])
    return lines


def render(data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    evidence = data["evidence"]
    digest = _digest()
    lines = [
        "# Repository Journal", "", "## Provenance and reporting interval",
        f"- repository: {data['repository']}", f"- interval: {data['interval']['start']} to {data['interval']['end']}",
        f"- contract: {CONTRACT_ID}@{CONTRACT_VERSION}", f"- contract digest: sha256-utf8-lf:{digest}",
        "", "## Executive summary",
        "- This report contains only caller-supplied evidence for the stated interval.",
        "- Follow-up actions are proposals and require separate authorization.", "",
    ]
    for heading, keys in SECTIONS:
        lines.extend((f"## {heading}", *_lines(evidence, keys), ""))
    for name, items in sorted(data.get("repository_sections", {}).items()):
        lines.extend((f"## Repository section: {name}", *(f"- observed: {item}" for item in items), ""))
    machine = {"schema_version": "aether.repository-journal/v1", "contract_id": CONTRACT_ID, "contract_version": CONTRACT_VERSION, "contract_digest": {"algorithm": "sha256-utf8-lf", "value": digest}, "repository": data["repository"], "interval": data["interval"], "evidence": evidence, "repository_sections": data.get("repository_sections", {})}
    return "\n".join(lines).rstrip() + "\n", machine


def main() -> int:
    parser = argparse.ArgumentParser()
    command = parser.add_subparsers(dest="command", required=True)
    render_parser = command.add_parser("render")
    render_parser.add_argument("--input", type=Path, required=True)
    render_parser.add_argument("--output", type=Path, required=True)
    render_parser.add_argument("--json-output", type=Path, required=True)
    args = parser.parse_args()
    try:
        markdown, machine = render(_load(args.input))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    args.output.write_text(markdown, encoding="utf-8")
    args.json_output.write_text(json.dumps(machine, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
