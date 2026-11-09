#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Collect bounded immutable Git history through the existing Intelligence contracts."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import UTC, datetime
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import tomllib
import unicodedata

import jsonschema
import yaml

_spec = importlib.util.spec_from_file_location(
    "relay_journey_native", Path(__file__).with_name("collect_repository_adrs.py"))
native = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(native)
base = native.base

ROOT = Path(__file__).resolve().parents[1]
# Reuse the reviewed alpha.2 runtime; this collector does not repin any owner.
LOCK_PATH = native.LOCK_PATH
SCHEMA = "egohygiene.relay.journey-collection-review/v1"
OUTPUT_NAME = "journey-collection.review.json"
MAX_TOTAL = 2 * base.MAX_JSON
MESSAGES = {
    **base.MESSAGES,
    "HISTORY": "Acquire the declared immutable history boundary without shallow or truncated ancestry for complete Git coverage.",
    "CLOCK": "Review commit timestamps against the explicit observation boundary; future or malformed dates are withheld.",
    "SCOPE": "Git commit events are partial history; provider lifecycle events, semantic links and parent topology are not collected.",
    "NATIVE": "Inspect the pinned EgoLint trailer diagnostics locally; source prose is not included in public evidence.",
    "INTEGRATION": "Review the captured projection and consumer-owned build handoff before publication.",
}


def diagnostic(code: str, owner: str = "relay", *, commit: str | None = None,
               line: int | None = None) -> dict:
    return {"code": code, "owner": owner, "commit": commit, "line": line,
            "remediation": MESSAGES.get(code, MESSAGES["NATIVE"])}


def public_subject(message: str, revision: str, enabled: bool) -> str:
    """Retain no body, authors, URLs, filesystem paths or credential-shaped text."""
    fallback = "Commit " + revision[:12]
    if not enabled:
        return fallback
    value = message.split("\n", 1)[0]
    value = "".join(c for c in value if unicodedata.category(c)[0] != "C")
    if base.SECRET.search(value):
        return fallback
    value = re.sub(r"(?i)(?:https?://|www\.)\S+", "[link omitted]", value)
    # Subject disclosure is caller opt-in. Keep names of referenced repositories
    # and arbitrary filesystem paths out of even that bounded presentation.
    value = re.sub(r"(?<!\w)(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.#-]+", "[reference omitted]", value)
    value = " ".join(value.split())[:240]
    return value or fallback


def inventory(args: argparse.Namespace) -> tuple[list[dict], dict, dict[str, bytes]]:
    """Read exact commit objects; never read checkout content or evaluate filters."""
    output = base.git(args.repository_root, "rev-list", "--topo-order",
                      "--max-count=" + str(args.maximum_commits + 1), args.source_commit,
                      "--", limit=65536).decode("ascii")
    revisions = output.splitlines()
    if (not revisions or revisions[0] != args.source_commit
            or any(not base.SHA.fullmatch(sha) for sha in revisions)
            or len(set(revisions)) != len(revisions)):
        base.fail("INPUT")
    truncated = len(revisions) > args.maximum_commits
    revisions = revisions[:args.maximum_commits]
    shallow = base.git(args.repository_root, "rev-parse", "--is-shallow-repository").strip()
    if shallow not in {b"true", b"false"}:
        base.fail("INPUT")
    records, objects, total = [], {}, 0
    lower = base.utc(args.since) if args.since else None
    upper = base.utc(args.until) if args.until else base.utc(args.observed_at)
    if lower and lower > upper:
        base.fail("INPUT")
    omitted_dates = False
    for sha in revisions:
        size = int(base.git(args.repository_root, "cat-file", "-s", sha))
        if size > base.MAX_SOURCE or total + size > MAX_TOTAL:
            base.fail("INPUT")
        raw = base.git(args.repository_root, "cat-file", "commit", sha, limit=base.MAX_SOURCE)
        total += len(raw)
        objects[sha] = raw
        header, separator, body = raw.partition(b"\n\n")
        if not separator or b"\0" in raw:
            base.fail("INPUT")
        # Only structural parents and a UTC commit instant are inspected. Author,
        # committer identities, signatures, tree paths and full prose stay local.
        parents = [line[7:].decode("ascii") for line in header.splitlines() if line.startswith(b"parent ")]
        if any(not base.SHA.fullmatch(parent) for parent in parents):
            base.fail("INPUT")
        dates = [line for line in header.splitlines() if line.startswith(b"committer ")]
        if len(dates) != 1:
            base.fail("INPUT")
        match = re.search(rb" (-?[0-9]{1,12}) [+-][0-9]{4}$", dates[0])
        try:
            instant = datetime.fromtimestamp(int(match[1]), UTC) if match else None
            occurred_at = instant.strftime("%Y-%m-%dT%H:%M:%SZ") if instant else None
            if occurred_at:
                base.utc(occurred_at)
        except (ValueError, OverflowError, OSError):
            occurred_at = None
        if not occurred_at or instant > base.utc(args.collected_at):
            omitted_dates = True
            continue
        if (lower and instant < lower) or instant > upper:
            continue
        # Native EgoLint deliberately validates the original message privately;
        # only an explicitly requested safe first line can enter a projection.
        message = body.decode("utf-8")
        records.append({"sha": sha, "occurred_at": occurred_at,
                        "title": public_subject(message, sha, args.public_subjects)})
    return records, {"shallow": shallow == b"true", "truncated": truncated,
                     "time_filtered": bool(args.since or args.until),
                     "withheld_timestamps": omitted_dates}, objects


def source_validate(args: argparse.Namespace, objects: dict[str, bytes]) -> dict:
    """Run the owner's trailer syntax check in a fresh, bounded, offline Git corpus."""
    catalog = tomllib.loads(base.read_file(
        args.runtime / "egolint/.config/rules/repository-intelligence.v1.toml").decode())
    pins = deepcopy(catalog["upstream-contracts"])
    for index, pin in enumerate(pins):
        if pin["id"] == "egohygiene.repository-intelligence/v1":
            pins[index] = next(p for p in catalog["compatible-upstream-contracts"]
                               if p["version"] == "1.0.0-alpha.2")
    policy = (f'schema-version = 1\nid = "egolint.repository-intelligence-validation/v1"\n'
              f'repository = "{args.repository}"\n'
              '[profile]\nid = "relay-journey-review"\nenforcement = "blocking"\n'
              'enabled-rules = ["EGO-INTEL-TRAILER-001"]\n')
    for pin in pins:
        policy += "\n[[contracts]]\n" + "".join(f"{k} = {json.dumps(v)}\n" for k, v in pin.items())
    policy += ('\n[adrs]\nstate = "unknown"\npolicy-reference = "uncollected/policy-reference.json"\n'
               'decision-directory = "uncollected/decisions"\nindex = "uncollected/index.md"\n'
               '[roadmap]\nstate = "unknown"\npath = "ROADMAP.md"\n'
               f'[commit-history]\nstate = "present"\nmaximum-commits = {args.maximum_commits}\n')
    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory)
        (workspace / "template").mkdir()
        base.git(workspace, "init", "--quiet", "--template", str(workspace / "template"))
        boundaries = []
        for sha, raw in sorted(objects.items()):
            actual = base.git(workspace, "hash-object", "-t", "commit", "-w", "--stdin", data=raw).decode().strip()
            if actual != sha:
                base.fail("INPUT")
            header = raw.partition(b"\n\n")[0]
            parents = [line[7:].decode("ascii") for line in header.splitlines() if line.startswith(b"parent ")]
            if any(parent not in objects for parent in parents):
                boundaries.append(sha)
        if boundaries:
            (workspace / ".git/shallow").write_text("\n".join(boundaries) + "\n")
        (workspace / ".relay-journey-validation.toml").write_text(policy)
        base.run([str(args.runtime / "egolint-bin"), "--workspace", str(workspace), "validate",
                  "--repository-intelligence", ".relay-journey-validation.toml",
                  "--represented-commit", args.source_commit],
                 cwd=workspace, allowed=(0, 1, 2, 3), timeout=60)
        report = base.load_json(base.read_file(workspace / ".reports/egolint/repository-intelligence.json"))
    schema = base.load_json(base.read_file(args.runtime / "egolint/schemas/repository-intelligence-report.schema.json"))
    if (not jsonschema.Draft202012Validator(schema).is_valid(report)
            or report["repository"] != args.repository
            or report["represented_commit"]["revision"] != args.source_commit
            or report["catalog_version"] != catalog["catalog-version"] or report["contracts"] != pins):
        base.fail("RUNTIME")
    return report


def project(args: argparse.Namespace, records: list[dict], scope: dict) -> dict:
    url = f"https://github.com/{args.repository}"
    source = {"id": "source:git-inventory", "kind": "git", "url": f"{url}/tree/{args.source_commit}",
              "repository": args.repository, "revision": args.source_commit,
              "observed_at": args.collected_at, "visibility": "public",
              "assertion": "authoritative", "freshness": args.freshness}
    root = {"id": f"ri:{args.repository}:repository:{args.repository}", "kind": "repository",
            "repository": args.repository, "key": args.repository, "title": args.repository,
            "canonical_url": url, "visibility": "public",
            "state": {"value": "unknown", "assertion": "unknown"}, "freshness": "unknown",
            "provenance": [source["id"]], "attributes": {}, "extensions": {}}
    coverage = {domain: {"collection": "uncollected", "freshness": "unknown",
                         "reason": "not_requested", "observed_at": None} for domain in native.DOMAINS}
    partial = any(scope.values())
    reason = ("truncated" if scope["truncated"] else "filtered" if scope["time_filtered"]
              else "incomplete" if partial else "complete")
    coverage["git"] = {"collection": "partial" if partial else "observed" if records else "observed_empty",
                       "freshness": args.freshness, "reason": reason, "observed_at": args.collected_at}
    # A complete Git ancestry never establishes cross-domain semantic history.
    coverage["history"] = {"collection": "partial", "freshness": args.freshness,
                           "reason": "incomplete", "observed_at": args.collected_at}
    projection = {"schema": "egohygiene.repository-intelligence/v1", "contract_version": "1.0.0-alpha.2",
                  "projection_id": f"{args.repository}@{args.source_commit}", "repository": args.repository,
                  "represented_commit": args.source_commit, "visibility": "public", "observed_at": args.observed_at,
                  "generator": {"name": "egohygiene/relay:journey-collector", "version": "0.1.0",
                                "contract": "egohygiene.repository-intelligence/v1"},
                  "sources": [source], "entities": [root], "relationships": [], "events": [],
                  "redactions": [], "extensions": {}, "collection_coverage": coverage}
    for record in records:
        sha = record["sha"]
        identity = f"ri:{args.repository}:commit:{sha}"
        source_id = "source:commit-" + sha
        canonical_url = f"{url}/commit/{sha}"
        projection["sources"].append({**source, "id": source_id, "url": canonical_url,
                                       "revision": sha, "freshness": "not_applicable"})
        projection["entities"].append({**root, "id": identity, "kind": "commit", "key": sha,
            "title": record["title"], "canonical_url": canonical_url,
            "state": {"value": "recorded", "assertion": "authoritative"}, "freshness": "not_applicable",
            "provenance": [source_id], "attributes": {"sha": sha}})
        projection["events"].append({"id": "event:commit-" + sha, "type": "commit.created", "subject": identity,
            "occurred_at": record["occurred_at"], "recorded_at": args.collected_at,
            "actor": None, "changes": [], "visibility": "public", "assertion": "authoritative",
            "freshness": "not_applicable", "provenance": [source_id], "extensions": {}})
    for key in ("sources", "entities"):
        projection[key].sort(key=lambda value: value["id"])
    projection["events"].sort(key=lambda value: (value["occurred_at"], value["id"]))
    return projection


def collect(args: argparse.Namespace) -> dict:
    args = argparse.Namespace(**vars(args))
    if args.visibility != "public":
        base.fail("VISIBILITY")
    if (not base.REPOSITORY.fullmatch(args.repository) or not base.SHA.fullmatch(args.source_commit)
            or not 1 <= args.maximum_commits <= base.MAX_RECORDS
            or not 1 <= args.maximum_age_seconds <= 2678400):
        base.fail("INPUT")
    args.collected_at = args.collected_at or args.observed_at
    age = (base.utc(args.observed_at) - base.utc(args.collected_at)).total_seconds()
    if age < 0 or (args.until and base.utc(args.until) > base.utc(args.observed_at)):
        base.fail("INPUT")
    args.freshness = "stale" if age > args.maximum_age_seconds else "current"
    lock, receipt = base.runtime_files(args.runtime, lock_path=LOCK_PATH)
    records, scope, objects = inventory(args)
    report = source_validate(args, objects)
    projection = project(args, records, scope)
    snapshot, validation = native.normalize(args.runtime, projection)
    diagnostics = [diagnostic("SCOPE"), diagnostic("INTEGRATION")]
    if any(scope.values()):
        diagnostics.append(diagnostic("HISTORY"))
    if scope["withheld_timestamps"]:
        diagnostics.append(diagnostic("CLOCK"))
    for finding in report["diagnostics"][:base.MAX_RECORDS]:
        location = finding.get("location") or {}
        # Native messages contain original source text. Preserve only owner code
        # and a validated commit/line location, never the message or raw path.
        location_commit = location.get("path", "")
        commit = location_commit.removeprefix("commit:")
        diagnostics.append(diagnostic(finding["rule_id"], "egolint",
                                      commit=commit if commit in objects else None,
                                      line=location.get("line")))
    status = "partial" if any(scope.values()) else "ready"
    if report["status"] == "invalid" or validation["hygiene"] == "invalid":
        status = "invalid"
    if validation["hygiene"] == "invalid":
        diagnostics.append(diagnostic("HYGIENE", "hygiene"))
    return {"schema": SCHEMA, "status": status, "publication": "denied", "repository": args.repository,
            "represented_commit": args.source_commit, "observed_at": args.observed_at,
            "inputs": {"collected_at": args.collected_at, "maximum_age_seconds": args.maximum_age_seconds,
                       "maximum_commits": args.maximum_commits, "since": args.since, "until": args.until,
                       "public_subjects": args.public_subjects,
                       "commits": [{"revision": sha, "sha256": base.digest(raw)} for sha, raw in sorted(objects.items())]},
            "scope": {**scope, "provider_events": "uncollected", "parent_topology": "unavailable",
                      "declared_reference_resolution": "unavailable"},
            "runtime": {**receipt, "pins": lock, "collector_sha256": base.digest(Path(__file__).read_bytes()),
                        "shared_runtime_sha256": base.digest(Path(base.__file__).read_bytes()),
                        "normalizer_adapter_sha256": base.digest(Path(native.__file__).read_bytes())},
            "validation": {**validation, "egolint": report["status"],
                           "diagnostics_truncated": len(report["diagnostics"]) > base.MAX_RECORDS},
            "coverage": projection["collection_coverage"], "diagnostics": diagnostics,
            "projection_candidate": projection, "snapshot_candidate": snapshot,
            "candidate_digests": {"projection_sha256": base.digest(base.json_bytes(projection)),
                                  "snapshot_sha256": base.digest(base.json_bytes(snapshot)) if snapshot else None}}


def write_result(path: Path, result: dict, repository_root: Path) -> None:
    path, consumer = base.safe_path(path), base.safe_path(repository_root)
    if path.is_relative_to(consumer) or path.name != OUTPUT_NAME or (path.exists() and not path.is_file()):
        base.fail("PATH")
    schema = base.load_json(base.read_file(ROOT / "schemas/journey-collection-review.v1.schema.json"))
    if not jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).is_valid(result):
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
    for name in ("runtime", "repository-root", "output"):
        command.add_argument("--" + name, type=Path, required=True)
    for name in ("repository", "visibility", "source-commit", "observed-at"):
        command.add_argument("--" + name, required=True)
    command.add_argument("--collected-at")
    command.add_argument("--maximum-age-seconds", type=int, default=86400)
    command.add_argument("--maximum-commits", type=int, default=base.MAX_RECORDS)
    command.add_argument("--since", help="Inclusive UTC lower bound; the resulting Git inventory remains partial.")
    command.add_argument("--until", help="Inclusive UTC upper bound; the resulting Git inventory remains partial.")
    command.add_argument("--public-subjects", action="store_true",
                         help="Explicitly disclose bounded sanitized first-line subjects from the public corpus.")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "prepare":
            base.prepare(args, lock_path=LOCK_PATH, reproducible=True)
            return 0
        result = collect(args)
        write_result(args.output, result, args.repository_root)
        print("Journey Git collection retained for review; publication denied")
        return 0 if result["status"] == "ready" else 2
    except (base.CollectorError, OSError, ValueError, KeyError, TypeError, UnicodeError,
            yaml.YAMLError, RecursionError):
        error = sys.exception()
        code = str(error) if isinstance(error, base.CollectorError) and str(error) in MESSAGES else "INPUT"
        if args.command == "collect":
            try:
                write_result(args.output, {"schema": SCHEMA, "status": "denied", "publication": "denied",
                                          "diagnostics": [diagnostic(code)]}, args.repository_root)
            except (base.CollectorError, OSError):
                pass
        print("Journey collector: " + code, file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
