# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Bounded source discovery only; diagram languages remain format-owned."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re

import validate_repository_architecture_contract as contract


SCHEMA = "relay.repository-architecture-diagram-evidence/v1"
DISCOVERY = "relay.diagram-source-discovery/v1"
MAX_SOURCES = 256
MAX_FILE_BYTES = 1024 * 1024
MAX_EVIDENCE_BYTES = 1024 * 1024
FORMATS = ("mermaid", "plantuml", "excalidraw")
SUFFIXES = {
    ".mmd": "mermaid", ".mermaid": "mermaid",
    ".puml": "plantuml", ".plantuml": "plantuml", ".pu": "plantuml",
    ".excalidraw": "excalidraw", ".excalidraw.json": "excalidraw",
}
FENCE = re.compile(rb"^ {0,3}(`{3,}|~{3,})([^\r\n]*)(?:\r\n|\r|\n)?$")
REASONS = {
    "overlapping-roots", "missing-root", "unsafe-input", "bound-exceeded",
    "invalid-markdown-encoding", "snapshot-unavailable",
}


class DiscoveryError(ValueError):
    """Fixed, source-free discovery reason and optional safe relative path."""

    def __init__(self, reason: str, path: str | None = None):
        self.reason = reason
        self.path = path
        super().__init__(reason)


def canonical(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode()


def capabilities() -> list[dict]:
    # The reviewed profile contains no immutable format-validator runtime.
    # A binary found on PATH cannot establish that missing trust boundary.
    return [{"format": name, "status": "unavailable", "validator": None,
             "reason": "no-reviewed-validator-in-profile"} for name in FORMATS]


def base(request: dict, snapshot_sha256: str | None) -> dict:
    adoption = request["adoption"]["diagram-sources"]
    return {
        "schema_version": SCHEMA, "discovery_contract": DISCOVERY,
        "profile": request["profile"],
        "repository": {key: value for key, value in request["repository"].items() if key != "root"},
        "snapshot_sha256": snapshot_sha256, "adoption": adoption,
        "roots": sorted(request["inputs"]["diagram_roots"]),
        "inventory_status": "complete" if adoption in {"present", "legacy"} else adoption,
        "validation_status": "not-applicable" if adoption == "not-applicable" else "unavailable",
        "capabilities": capabilities(), "sources": [], "diagnostics": [],
        "bounds": {"maximum_sources": MAX_SOURCES, "maximum_source_file_bytes": MAX_FILE_BYTES,
                   "maximum_evidence_bytes": MAX_EVIDENCE_BYTES, "examined_files": 0,
                   "examined_bytes": 0, "ignored_files": 0, "observed_sources": 0,
                   "retained_sources": 0, "truncated": False},
    }


def unavailable(request: dict, snapshot_sha256: str | None = None) -> dict:
    """Explicit source-discovery failure without copying exception prose."""
    value = base(request, snapshot_sha256)
    if value["adoption"] in {"present", "legacy"}:
        value["inventory_status"] = "rejected"
        value["diagnostics"] = [{"code": "snapshot-unavailable", "path": None}]
    return value


def validate(value: dict, request: dict) -> None:
    """Check Relay's closed metadata and cross-field invariants without plugins."""
    errors = []
    expected = base(request, value.get("snapshot_sha256"))
    if not contract.exact_keys(value, set(expected), "diagram evidence", errors):
        raise ValueError("Invalid closed diagram evidence")
    for field in ("schema_version", "discovery_contract", "profile", "repository", "adoption",
                  "roots", "validation_status", "capabilities"):
        if value[field] != expected[field]:
            errors.append(field)
    snapshot = value["snapshot_sha256"]
    if snapshot is not None and (not isinstance(snapshot, str) or not contract.SHA256.fullmatch(snapshot)):
        errors.append("snapshot")
    status = value["inventory_status"]
    allowed = {"complete", "rejected"} if value["adoption"] in {"present", "legacy"} else {value["adoption"]}
    if not isinstance(status, str) or status not in allowed:
        errors.append("inventory status")
    if status == "complete" and snapshot is None:
        errors.append("missing snapshot identity")
    bounds = value["bounds"]
    if not contract.exact_keys(bounds, set(expected["bounds"]), "diagram bounds", errors):
        raise ValueError("Invalid closed diagram evidence")
    for field in ("maximum_sources", "maximum_source_file_bytes", "maximum_evidence_bytes"):
        if type(bounds[field]) is not int or bounds[field] != expected["bounds"][field]:
            errors.append(field)
    for field in ("examined_files", "examined_bytes", "ignored_files", "observed_sources", "retained_sources"):
        if type(bounds[field]) is not int or bounds[field] < 0:
            errors.append(field)
    if type(bounds["truncated"]) is not bool:
        errors.append("truncation")
    if errors:
        raise ValueError("Invalid closed diagram evidence")
    if (bounds["examined_files"] + bounds["ignored_files"] > request["bounds"]["maximum_scanned_files"]
            or bounds["examined_bytes"] > request["bounds"]["maximum_scanned_bytes"]
            or bounds["observed_sources"] > MAX_SOURCES + 1
            or bounds["retained_sources"] > MAX_SOURCES):
        errors.append("bounds")
    sources = value["sources"]
    source_keys = {"path", "format", "origin", "start_line", "end_line", "bytes", "sha256", "validation_status", "validator"}
    identities = []
    if not isinstance(sources, list) or len(sources) > MAX_SOURCES:
        raise ValueError("Invalid closed diagram evidence")
    for source in sources:
        if not contract.exact_keys(source, source_keys, "diagram source", errors):
            continue
        path = source["path"]
        if (not contract.relative_path(path) or source["format"] not in FORMATS
                or source["validation_status"] != "unavailable" or source["validator"] is not None
                or type(source["bytes"]) is not int or not 0 <= source["bytes"] <= MAX_FILE_BYTES
                or not isinstance(source["sha256"], str) or not contract.SHA256.fullmatch(source["sha256"])):
            errors.append("source metadata")
            continue
        if not any(path == root or path.startswith(root + "/") for root in value["roots"]):
            errors.append("source outside declared roots")
        if source["origin"] == "file":
            if source["start_line"] is not None or source["end_line"] is not None or standalone_format(path) != source["format"]:
                errors.append("file location")
        elif source["origin"] == "markdown-fence":
            if (PurePosixPath(path).suffix.lower() not in {".md", ".markdown"}
                    or source["format"] == "excalidraw"
                    or type(source["start_line"]) is not int or type(source["end_line"]) is not int
                    or not 1 <= source["start_line"] <= source["end_line"]):
                errors.append("fence location")
        else:
            errors.append("origin")
        identities.append((path, source["start_line"] or 0))
    if errors:
        raise ValueError("Invalid closed diagram evidence")
    if identities != sorted(set(identities)):
        errors.append("duplicate or unordered sources")
    diagnostics = value["diagnostics"]
    if not isinstance(diagnostics, list) or len(diagnostics) > 1:
        raise ValueError("Invalid closed diagram evidence")
    for diagnostic in diagnostics:
        if not contract.exact_keys(diagnostic, {"code", "path"}, "diagram diagnostic", errors):
            continue
        if (not isinstance(diagnostic["code"], str) or diagnostic["code"] not in REASONS
                or diagnostic["path"] is not None and not contract.relative_path(diagnostic["path"])):
            errors.append("diagnostic")
    if (bounds["retained_sources"] != len(sources) or bounds["observed_sources"] < len(sources)
            or status == "rejected" and (sources or not diagnostics)
            or status != "rejected" and (diagnostics or bounds["truncated"])
            or status == "complete" and bounds["observed_sources"] != len(sources)
            or status in {"unknown", "not-applicable"} and any(bounds[key] for key in ("examined_files", "examined_bytes", "ignored_files", "observed_sources", "retained_sources"))
            or bounds["truncated"] != any(item.get("code") == "bound-exceeded" for item in diagnostics)
            or len(canonical(value)) > MAX_EVIDENCE_BYTES):
        errors.append("evidence consistency")
    if errors:
        raise ValueError("Invalid closed diagram evidence")


def standalone_format(path: str) -> str | None:
    name = path.lower()
    return next((kind for suffix, kind in SUFFIXES.items() if name.endswith(suffix)), None)


def fenced_sources(data: bytes):
    """Recognize bounded fence lines; never parse or evaluate diagram grammar."""
    try:
        data.decode("utf-8")
    except UnicodeError:
        raise DiscoveryError("invalid-markdown-encoding") from None
    active = None
    payload = bytearray()
    lines = data.splitlines(keepends=True)
    for number, line in enumerate(lines, 1):
        fence = FENCE.fullmatch(line)
        if active is None:
            if fence is None:
                continue
            marker, info = fence.groups()
            # Backticks in an opening backtick info string do not open a fence.
            if marker.startswith(b"`") and b"`" in info:
                continue
            words = info.strip().lower().split()
            kind = {b"mermaid": "mermaid", b"plantuml": "plantuml", b"puml": "plantuml"}.get(words[0] if words else b"")
            active = (marker[:1], len(marker), number, kind)
            payload.clear()
        elif fence and fence[1][:1] == active[0] and len(fence[1]) >= active[1] and not fence[2].strip():
            if active[3] is not None:
                yield active[3], active[2], number, bytes(payload)
            active = None
        elif active[3] is not None:
            payload.extend(line)
    # An unclosed Markdown fence extends to EOF; this says nothing about the
    # validity of its contained diagram. Preserve that exact bounded byte range.
    if active is not None and active[3] is not None:
        yield active[3], active[2], len(lines), bytes(payload)


def collect(workspace: Path, files: list[str], request: dict, snapshot_sha256: str,
            read_file) -> dict:
    """Inventory only the already bounded regular-file snapshot, never walk Git."""
    value = base(request, snapshot_sha256)
    if value["adoption"] not in {"present", "legacy"}:
        return value
    bounds = value["bounds"]
    roots = value["roots"]
    current = None
    try:
        if (not roots or len(roots) > 16 or len(files) != len(set(files))
                or len(files) > request["bounds"]["maximum_scanned_files"]):
            raise DiscoveryError("unsafe-input")
        if any(not contract.relative_path(path) or ".git" in PurePosixPath(path).parts
               or path.split("/")[0] == ".reports" for path in [*roots, *files]):
            raise DiscoveryError("unsafe-input")
        for index, root in enumerate(roots):
            if any(other == root or other.startswith(root + "/") or root.startswith(other + "/")
                   for other in roots[:index]):
                raise DiscoveryError("overlapping-roots", root)
            if not any(path == root or path.startswith(root + "/") for path in files):
                raise DiscoveryError("missing-root", root)
        selected = sorted(path for path in files if any(path == root or path.startswith(root + "/") for root in roots))
        for current in selected:
            kind = standalone_format(current)
            markdown = PurePosixPath(current).suffix.lower() in {".md", ".markdown"}
            if kind is None and not markdown:
                bounds["ignored_files"] += 1
                continue
            bounds["examined_files"] += 1
            # read_file rejects links/special files and reads at most the cap.
            data = read_file(workspace / current, MAX_FILE_BYTES)
            bounds["examined_bytes"] += len(data)
            if bounds["examined_bytes"] > request["bounds"]["maximum_scanned_bytes"]:
                raise DiscoveryError("bound-exceeded", current)
            records = ([(kind, None, None, data)] if kind is not None else fenced_sources(data))
            for kind, start, end, source in records:
                bounds["observed_sources"] += 1
                if bounds["observed_sources"] > MAX_SOURCES:
                    raise DiscoveryError("bound-exceeded", current)
                value["sources"].append({
                    "path": current, "format": kind,
                    "origin": "file" if start is None else "markdown-fence",
                    "start_line": start, "end_line": end,
                    "bytes": len(source), "sha256": hashlib.sha256(source).hexdigest(),
                    "validation_status": "unavailable", "validator": None,
                })
        bounds["retained_sources"] = len(value["sources"])
        if len(canonical(value)) > MAX_EVIDENCE_BYTES:
            raise DiscoveryError("bound-exceeded")
    except (DiscoveryError, OSError, ValueError) as error:
        reason = error.reason if isinstance(error, DiscoveryError) else "bound-exceeded" if str(error) == "BOUND" else "unsafe-input"
        location = error.path if isinstance(error, DiscoveryError) and error.path else current
        value["inventory_status"] = "rejected"
        value["diagnostics"] = [{"code": reason, "path": location}]
        value["sources"] = []
        bounds["retained_sources"] = 0
        bounds["truncated"] = reason == "bound-exceeded"
    return value
