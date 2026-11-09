#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Map bounded captured GitHub work inventories into a denied offline review."""

from __future__ import annotations

import argparse
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

import jsonschema

_spec = importlib.util.spec_from_file_location(
    "relay_work_normalization", Path(__file__).with_name("collect_repository_adrs.py"))
adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adapter)
base = adapter.base

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "contracts/work-collector.v1.lock.json"
CAPTURE_PATH = ROOT / "schemas/work-provider-capture.v1.schema.json"
REVIEW_PATH = ROOT / "schemas/work-collection-review.v1.schema.json"
SCHEMA = "egohygiene.relay.work-collection-review/v1"
OUTPUT_NAME = "work-collection.review.json"
KINDS = {"issues": "issue", "pull_requests": "pull_request"}
MESSAGES = {
    **base.MESSAGES,
    "CAPTURE": "Supply the closed public Work capture with explicit per-domain scope, times and pagination.",
    "IDENTITY": "Bind the public capture and consumer checkout to the same canonical repository and full source commit.",
    "DUPLICATE": "Recapture one unambiguous provider record per native identity; keep pull requests separate from issues.",
    "CHRONOLOGY": "Preserve provider lifecycle timestamps and the original capture boundary; do not relabel older evidence current.",
    "INCOMPLETE": "Capture every authorized state and exhaust pagination before claiming a complete inventory.",
    "UNAVAILABLE": "Recapture the selected public inventory with authorized read access; unavailable is not empty.",
    "FAILED": "Repair the read-only provider capture and retain the original failure boundary.",
    "STALE": "Recapture public provider metadata at a new explicit observation boundary.",
    "LINK_UNAVAILABLE": "Supply public represented endpoints before projecting an explicit relationship; no placeholder was created.",
    "INTEGRATION": "Review native replay and consumer-owned build composition before production admission or publication.",
}


def diagnostic(code: str, owner: str = "relay") -> dict:
    return {"code": code, "owner": owner, "path": None, "line": None,
            "remediation": MESSAGES[code]}


def schema_valid(value: dict, path: Path) -> bool:
    schema = base.load_json(base.read_file(path))
    return jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()).is_valid(value)


def record_valid(record: dict, kind: str, captured, scope: str) -> None:
    """Validate only the capture seam; domain truth remains with its owners."""
    if record["kind"] != kind or record["visibility"] != "public":
        base.fail("CAPTURE")
    title = record["title"]
    if title is not None and (base.SECRET.search(title)
                              or any(ord(c) < 32 or ord(c) == 127 for c in title)):
        base.fail("VISIBILITY")
    state = record["state"]
    if ((scope == "open" and state != "open")
            or (scope == "closed" and state == "open")):
        base.fail("CAPTURE")
    created, updated = base.utc(record["created_at"]), base.utc(record["updated_at"])
    closed = base.utc(record["closed_at"]) if record["closed_at"] is not None else None
    if not created <= updated <= captured or (closed is not None and not created <= closed <= updated):
        base.fail("CHRONOLOGY")
    if (state == "open") != (closed is None):
        base.fail("CHRONOLOGY")
    if kind == "issue":
        if ((state == "open" and record["state_reason"] not in {None, "reopened"})
                or (state == "closed" and record["state_reason"] == "reopened")):
            base.fail("CAPTURE")
    else:
        merged = base.utc(record["merged_at"]) if record["merged_at"] is not None else None
        if (state == "merged") != (merged is not None):
            base.fail("CHRONOLOGY")
        if merged is not None and (closed is None or not created <= merged <= closed or record["draft"]):
            base.fail("CHRONOLOGY")


def inventory_claim(inventory: dict, kind: str, observed, maximum_age: int) -> dict:
    pages = inventory["pagination"]["pages_received"]
    outcome, records = inventory["outcome"], inventory["records"]
    if not pages:
        if records or inventory["captured_at"] is not None or inventory["pagination"] != {
                "pages_received": 0, "exhausted": False, "truncated": False}:
            base.fail("CAPTURE")
        if outcome == "not_requested":
            if inventory["scope"] != "all":
                base.fail("CAPTURE")
            return {"collection": "uncollected", "freshness": "unknown",
                    "reason": "not_requested", "observed_at": None}
        if outcome == "complete":
            base.fail("CAPTURE")
        failed = outcome == "collection_failed"
        return {"collection": "failed" if failed else "unavailable", "freshness": "unknown",
                "reason": "collection_failed" if failed else "access_denied" if outcome == "access_denied"
                else "provider_unavailable", "observed_at": None}
    if outcome == "not_requested" or inventory["captured_at"] is None or len(records) > pages * 100:
        base.fail("CAPTURE")
    captured = base.utc(inventory["captured_at"])
    age = (observed - captured).total_seconds()
    if age < 0:
        base.fail("CHRONOLOGY")
    freshness = "stale" if age > maximum_age else "current"
    for record in records:
        record_valid(record, kind, captured, inventory["scope"])
    pagination = inventory["pagination"]
    complete = (inventory["scope"] == "all" and outcome == "complete"
                and pagination["exhausted"] and not pagination["truncated"])
    reason = ("complete" if complete else "filtered" if inventory["scope"] != "all"
              else "truncated" if pagination["truncated"] else "incomplete")
    return {"collection": "observed" if records else "observed_empty", "freshness": freshness,
            "reason": reason, "observed_at": inventory["captured_at"]} if complete else {
                "collection": "partial", "freshness": freshness,
                "reason": reason, "observed_at": inventory["captured_at"]}


def entity_id(repository: str, kind: str, number: int) -> str:
    return f"ri:{repository}:{kind.replace('_', '-')}:{number}"


def project(args: argparse.Namespace, capture: dict, claims: dict) -> tuple[dict, list]:
    repository, revision = args.repository, args.source_commit
    url = f"https://github.com/{repository}"
    source = {"id": "source:work-context", "kind": "git", "url": f"{url}/tree/{revision}",
              "repository": repository, "revision": revision, "observed_at": args.observed_at,
              "visibility": "public", "assertion": "authoritative", "freshness": "current"}
    root = {"id": f"ri:{repository}:repository:{repository}", "kind": "repository",
            "repository": repository, "key": repository, "title": repository,
            "canonical_url": url, "visibility": "public",
            "state": {"value": "unknown", "assertion": "unknown"}, "freshness": "unknown",
            "provenance": [source["id"]], "attributes": {}, "extensions": {}}
    coverage = {domain: {"collection": "uncollected", "freshness": "unknown",
                         "reason": "not_requested", "observed_at": None} for domain in adapter.DOMAINS}
    coverage.update(claims)
    projection = {"schema": "egohygiene.repository-intelligence/v1", "contract_version": "1.0.0-alpha.2",
                  "projection_id": f"{repository}@{revision}", "repository": repository,
                  "represented_commit": revision, "visibility": "public", "observed_at": args.observed_at,
                  "generator": {"name": "egohygiene/relay:work-collector", "version": "0.1.0",
                                "contract": "egohygiene.repository-intelligence/v1"},
                  "sources": [source], "entities": [root], "relationships": [], "events": [],
                  "redactions": [], "extensions": {}, "collection_coverage": coverage}
    numbers, provider_ids, represented = set(), set(), {}
    for domain, kind in KINDS.items():
        inventory, claim = capture["inventories"][domain], claims[domain]
        if claim["observed_at"] is not None:
            projection["sources"].append({**source, "id": f"source:work-{domain.replace('_', '-')}",
                "kind": "github_issue" if kind == "issue" else "github_pull_request",
                "url": f"{url}/issues" if kind == "issue" else f"{url}/pulls",
                "observed_at": claim["observed_at"], "freshness": claim["freshness"]})
        for record in inventory["records"]:
            number = record["number"]
            identity = (kind, record["provider_id"])
            if number in numbers or identity in provider_ids:
                base.fail("DUPLICATE")
            numbers.add(number)
            provider_ids.add(identity)
            route = "issues" if kind == "issue" else "pull"
            canonical = f"{url}/{route}/{number}"
            source_id = f"source:work-{kind.replace('_', '-')}-{number}"
            projection["sources"].append({**source, "id": source_id,
                "kind": "github_issue" if kind == "issue" else "github_pull_request",
                "url": canonical, "observed_at": claim["observed_at"], "freshness": claim["freshness"]})
            attributes = {key: deepcopy(record[key]) for key in (
                "number", "provider_id", "state_reason", "draft", "created_at", "updated_at",
                "closed_at", "merged_at") if key in record}
            entity = {**root, "id": entity_id(repository, kind, number), "kind": kind,
                "key": str(number), "title": record["title"], "canonical_url": canonical,
                "state": {"value": record["state"], "assertion": "authoritative"},
                "freshness": claim["freshness"], "provenance": [source_id], "attributes": attributes}
            projection["entities"].append(entity)
            represented[(kind, number)] = entity
    links, missing = set(), False
    for relation in capture["relationships"]:
        source_key = (relation["source"]["kind"], relation["source"]["number"])
        target_key = (relation["target"]["kind"], relation["target"]["number"])
        identity = (relation["type"], source_key, target_key)
        if identity in links or source_key == target_key:
            base.fail("DUPLICATE")
        links.add(identity)
        if source_key not in represented or target_key not in represented:
            missing = True
            continue
        left, right = represented[source_key], represented[target_key]
        edge_digest = base.digest(base.json_bytes([relation["type"], left["id"], right["id"]]))
        projection["relationships"].append({"id": "relationship:work-" + edge_digest[:32],
            "type": relation["type"], "source": left["id"], "target": right["id"],
            "direction": "directed", "assertion": relation["assertion"],
            "freshness": "stale" if "stale" in {left["freshness"], right["freshness"]} else "current",
            "provenance": sorted(set(left["provenance"] + right["provenance"])), "extensions": {}})
    for key in ("sources", "entities", "relationships"):
        projection[key].sort(key=lambda value: value["id"])
    return projection, [diagnostic("LINK_UNAVAILABLE")] if missing else []


def collect(args: argparse.Namespace) -> dict:
    if args.visibility != "public":
        base.fail("VISIBILITY")
    if (not base.REPOSITORY.fullmatch(args.repository) or not base.SHA.fullmatch(args.source_commit)
            or not 1 <= args.maximum_age_seconds <= 2678400):
        base.fail("INPUT")
    observed = base.utc(args.observed_at)
    base.git(args.repository_root, "cat-file", "commit", args.source_commit, limit=base.MAX_SOURCE)
    raw = base.read_file(args.provider_evidence)
    capture = base.load_json(raw)
    # Visibility is checked before assembling identities, counts, links or diagnostics.
    if capture.get("visibility") != "public":
        base.fail("VISIBILITY")
    if not schema_valid(capture, CAPTURE_PATH):
        base.fail("CAPTURE")
    if capture["repository"] != args.repository or capture["source_commit"] != args.source_commit:
        base.fail("IDENTITY")
    lock, receipt = base.runtime_files(args.runtime, lock_path=LOCK_PATH)
    claims = {domain: inventory_claim(capture["inventories"][domain], kind, observed,
                                      args.maximum_age_seconds) for domain, kind in KINDS.items()}
    projection, diagnostics = project(args, capture, claims)
    snapshot, validation = adapter.normalize(args.runtime, projection)
    states = {claim["collection"] for claim in claims.values()}
    if validation["hygiene"] != "valid":
        status = "invalid"
        diagnostics.append(diagnostic("HYGIENE", "hygiene"))
    elif "partial" in states or diagnostics:
        status = "partial"
    elif "failed" in states:
        status = "failed"
    elif "unavailable" in states:
        status = "unavailable"
    elif "uncollected" in states:
        status = "uncollected"
    elif any(claim["freshness"] == "stale" for claim in claims.values()):
        status = "stale"
    else:
        status = "ready"
    for state, code in (("partial", "INCOMPLETE"), ("failed", "FAILED"), ("unavailable", "UNAVAILABLE")):
        if state in states:
            diagnostics.append(diagnostic(code))
    if any(claim["freshness"] == "stale" for claim in claims.values()):
        diagnostics.append(diagnostic("STALE"))
    diagnostics.append(diagnostic("INTEGRATION"))
    bounds = {domain: {key: deepcopy(value) for key, value in inventory.items() if key != "records"}
              for domain, inventory in capture["inventories"].items()}
    return {"schema": SCHEMA, "status": status, "publication": "denied", "repository": args.repository,
            "represented_commit": args.source_commit, "observed_at": args.observed_at,
            "inputs": {"provider_sha256": base.digest(raw),
                       "provider_schema_sha256": base.digest(base.read_file(CAPTURE_PATH)),
                       "maximum_age_seconds": args.maximum_age_seconds, "inventories": bounds},
            "runtime": {**receipt, "pins": lock, "collector_sha256": base.digest(Path(__file__).read_bytes()),
                        "shared_runtime_sha256": base.digest(Path(base.__file__).read_bytes()),
                        "normalizer_adapter_sha256": base.digest(Path(adapter.__file__).read_bytes())},
            "validation": validation, "coverage": projection["collection_coverage"], "diagnostics": diagnostics,
            "projection_candidate": projection, "snapshot_candidate": snapshot,
            "candidate_digests": {"projection_sha256": base.digest(base.json_bytes(projection)),
                                  "snapshot_sha256": base.digest(base.json_bytes(snapshot)) if snapshot else None}}


def write_result(path: Path, result: dict, repository_root: Path) -> None:
    path = base.safe_path(path)
    if (path.is_relative_to(base.safe_path(repository_root)) or path.name != OUTPUT_NAME
            or (path.exists() and not path.is_file())):
        base.fail("PATH")
    if not schema_valid(result, REVIEW_PATH):
        base.fail("INPUT")
    content = base.json_bytes(result)
    if len(content) > base.MAX_OUTPUT:
        base.fail("INPUT")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = result.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("prepare", allow_abbrev=False)
    for owner in ("hygiene", "egolint", "observatory"):
        setup.add_argument("--" + owner, type=Path, required=True)
    setup.add_argument("--cargo", type=Path, default=Path("cargo"))
    setup.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("collect", allow_abbrev=False)
    for name in ("runtime", "repository-root", "provider-evidence", "output"):
        command.add_argument("--" + name, type=Path, required=True)
    for name in ("repository", "visibility", "source-commit", "observed-at"):
        command.add_argument("--" + name, required=True)
    command.add_argument("--maximum-age-seconds", type=int, default=86400)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "prepare":
            base.prepare(args, lock_path=LOCK_PATH, reproducible=True)
            return 0
        result = collect(args)
        write_result(args.output, result, args.repository_root)
        print("Work collection retained for review; publication denied")
        return 0 if result["status"] == "ready" else 2
    except (base.CollectorError, OSError, ValueError, KeyError, TypeError, RecursionError):
        error = sys.exception()
        code = str(error) if isinstance(error, base.CollectorError) and str(error) in MESSAGES else "INPUT"
        if args.command == "collect":
            try:
                write_result(args.output, {"schema": SCHEMA, "status": "denied", "publication": "denied",
                                          "diagnostics": [diagnostic(code)]}, args.repository_root)
            except (base.CollectorError, OSError):
                pass
        print("Work collector: " + code, file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
