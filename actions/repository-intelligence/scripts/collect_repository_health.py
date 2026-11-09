#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Admit captured public check evidence through pinned Intelligence owners offline."""

from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import urlsplit

import jsonschema


def sibling(name: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, Path(__file__).with_name(name))
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


base = sibling("collect_repository_roadmap.py", "relay_health_runtime")
adr = sibling("collect_repository_adrs.py", "relay_health_normalization")
ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "contracts/health-collector.v1.lock.json"
SCHEMA = "egohygiene.relay.health-collection-review/v1"
OUTPUT_NAME = "health-collection.review.json"
PRODUCERS = ("osv", "megalinter", "scorecard")
CONCLUSIONS = {"success", "failure", "neutral", "cancelled", "skipped", "timed_out", "action_required", "unknown"}
MESSAGES = {
    **base.MESSAGES,
    "REPORT": "Recapture a supported normalized report with the exact represented repository and commit.",
    "MISSING": "Supply every requested producer capture; missing evidence is not a passing check.",
    "MISMATCH": "Regenerate the producer report at the represented revision; never relabel old evidence.",
    "FUTURE": "Use captures generated no later than the declared observation boundary.",
    "CHECKS": "Supply a bounded public same-repository GitHub check-runs capture with matching head revisions.",
    "TRUNCATED": "Recapture the complete declared inventory or preserve partial collection coverage.",
    "STALE": "Recapture expired producer evidence; retain its original generation and expiry times.",
    "INTEGRATION": "Review captured-input replay and consumer build integration before enabling publication.",
}


def diagnostic(code: str, producer: str | None = None) -> dict:
    return {"code": code, "owner": "relay", "producer": producer,
            "remediation": MESSAGES.get(code, MESSAGES["INPUT"])}


def public_url(value: object, repository: str, *, check: bool = False) -> str:
    """Only same-repository canonical GitHub routes; never signed/query URLs."""
    if not isinstance(value, str) or len(value) > 500:
        base.fail("CHECKS" if check else "REPORT")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or parsed.netloc != "github.com" or parsed.query
            or parsed.fragment or parsed.username or parsed.password):
        base.fail("CHECKS" if check else "REPORT")
    pattern = (rf"/{re.escape(repository)}/(?:runs/[1-9][0-9]*|actions/runs/[1-9][0-9]*(?:/job/[1-9][0-9]*)?)"
               if check else rf"/{re.escape(repository)}/actions/runs/[1-9][0-9]*")
    if not re.fullmatch(pattern, parsed.path):
        base.fail("CHECKS" if check else "REPORT")
    return value


def source(repository: str, revision: str, key: str, url: str,
           observed_at: str, freshness: str) -> dict:
    return {"id": "source:health-" + key, "kind": "check_provider", "url": url,
            "repository": repository, "revision": revision, "observed_at": observed_at,
            "visibility": "public", "assertion": "authoritative", "freshness": freshness}


def check_entity(args: argparse.Namespace, key: str, title: str, state: str,
                 evidence: dict, attributes: dict) -> dict:
    return {"id": f"ri:{args.repository}:check:{key}", "kind": "check", "repository": args.repository,
            "key": key, "title": title, "canonical_url": evidence["url"], "visibility": "public",
            "state": {"value": state, "assertion": "authoritative"}, "freshness": evidence["freshness"],
            "provenance": [evidence["id"]], "attributes": attributes, "extensions": {}}


def report_capture(args: argparse.Namespace, producer: str, path: Path,
                   validator: jsonschema.Draft202012Validator) -> tuple[list, list, dict]:
    raw = base.read_file(path)
    report = base.load_json(raw)
    if not validator.is_valid(report) or report["producer"] != producer:
        base.fail("REPORT")
    if report["repository"] != args.repository or report["commit"] != args.source_commit:
        base.fail("MISMATCH")
    generated = base.utc(report["generated_at"])
    expiry = base.utc(report["freshness"]["expires_at"])
    observed = base.utc(args.observed_at)
    if generated > observed or expiry <= generated:
        base.fail("FUTURE")
    freshness = "stale" if observed >= expiry else "current"
    run = report["provenance"]["run_id"]
    if not isinstance(run, str) or not re.fullmatch(r"[1-9][0-9]*", run):
        base.fail("REPORT")
    # A source link is derived from the bounded run identity. Arbitrary producer
    # messages, tool arrays, paths, detail/security links and provenance text do
    # not enter either the projection or retained input inventory.
    url = f"https://github.com/{args.repository}/actions/runs/{run}"
    evidence = source(args.repository, args.source_commit, producer, url,
                      report["generated_at"], freshness)
    execution = report["execution"]["state"]
    findings = report["findings"]
    conclusion = {"clear": "success", "attention": "neutral", "blocked": "failure", "unknown": "unknown"}
    records = [
        check_entity(args, f"report-{producer}-execution", f"{producer}: producer execution", execution, evidence,
                     {"name": f"{producer}: producer execution", "status": "completed", "conclusion": execution,
                      "producer": producer, "facet": "execution", "generated_at": report["generated_at"],
                      "expires_at": report["freshness"]["expires_at"]}),
        check_entity(args, f"report-{producer}-findings", f"{producer}: policy findings", findings["state"], evidence,
                     {"name": f"{producer}: policy findings", "status": "completed",
                      "conclusion": conclusion[findings["state"]], "producer": producer, "facet": "findings",
                      "total": findings["total"], "blocking": findings["blocking"], "advisory": findings["advisory"],
                      "generated_at": report["generated_at"], "expires_at": report["freshness"]["expires_at"]}),
    ]
    # Keep the two facets independent even when findings are unknown after a
    # failed execution. A valid summary is not proof that a native check ran.
    retained = {"producer": producer, "status": "admitted", "sha256": base.digest(raw),
                "generated_at": report["generated_at"], "expires_at": report["freshness"]["expires_at"],
                "freshness": freshness, "execution": execution, "findings": findings["state"]}
    return [evidence], records, retained


def provider_capture(args: argparse.Namespace) -> tuple[list, list, dict, list]:
    """Consume the documented GitHub REST check-runs response, never its logs."""
    status = args.check_runs_state
    retained = {"producer": "github-check-runs", "status": status, "sha256": None}
    if status != "observed":
        if args.check_runs is not None or args.check_runs_observed_at is not None:
            base.fail("CHECKS")
        return [], [], retained, []
    if args.check_runs is None or args.check_runs_observed_at is None:
        base.fail("CHECKS")
    captured = base.utc(args.check_runs_observed_at)
    age = (base.utc(args.observed_at) - captured).total_seconds()
    if age < 0:
        base.fail("FUTURE")
    raw = base.read_file(args.check_runs)
    value = base.load_json(raw)
    total = value.get("total_count")
    runs = value.get("check_runs")
    if (type(total) is not int or total < 0 or not isinstance(runs, list)
            or len(runs) > base.MAX_RECORDS or total < len(runs)):
        base.fail("CHECKS")
    freshness = "stale" if age > args.maximum_age_seconds else "current"
    diagnostics, sources, entities, identities = [], [], [], set()
    for run in runs:
        if not isinstance(run, dict):
            base.fail("CHECKS")
        identifier, name = run.get("id"), run.get("name")
        if (type(identifier) is not int or identifier < 1 or identifier in identities
                or not isinstance(name, str) or not 1 <= len(name) <= 200
                or any(ord(c) < 32 for c in name) or base.SECRET.search(name)):
            base.fail("CHECKS")
        identities.add(identifier)
        # Never relabel an old check's head_sha to satisfy current admission.
        if run.get("head_sha") != args.source_commit:
            diagnostics.append(diagnostic("MISMATCH", "github-check-runs"))
            continue
        state, conclusion = run.get("status"), run.get("conclusion")
        if state not in {"queued", "in_progress", "completed"}:
            base.fail("CHECKS")
        if state == "completed":
            if conclusion not in CONCLUSIONS:
                base.fail("CHECKS")
        elif conclusion is not None:
            base.fail("CHECKS")
        started, completed = run.get("started_at"), run.get("completed_at")
        if state == "completed" and completed is None:
            base.fail("CHECKS")
        for instant in (started, completed):
            if instant is not None and base.utc(instant) > captured:
                base.fail("FUTURE")
        if started is not None and completed is not None and base.utc(started) > base.utc(completed):
            base.fail("CHECKS")
        url = public_url(run.get("html_url"), args.repository, check=True)
        evidence = source(args.repository, args.source_commit, f"github-{identifier}", url,
                          args.check_runs_observed_at, freshness)
        entities.append(check_entity(args, f"github-check-{identifier}", name,
                                    conclusion if state == "completed" else state, evidence,
                                    {"name": name, "status": state, "conclusion": conclusion or "unknown",
                                     "provider": "github", "check_run_id": identifier,
                                     "started_at": started, "completed_at": completed}))
        sources.append(evidence)
    complete = total == len(runs) and not diagnostics
    if not complete:
        diagnostics.append(diagnostic("TRUNCATED", "github-check-runs"))
    retained.update(sha256=base.digest(raw), observed_at=args.check_runs_observed_at,
                    freshness=freshness, status="admitted" if complete else "partial")
    return sources, entities, retained, diagnostics


def project(args: argparse.Namespace, sources: list, checks: list, claim: dict) -> dict:
    url = f"https://github.com/{args.repository}"
    inventory = {"id": "source:health-inventory", "kind": "manual", "url": f"{url}/tree/{args.source_commit}",
                 "repository": args.repository, "revision": args.source_commit, "observed_at": args.observed_at,
                 "visibility": "public", "assertion": "authoritative", "freshness": "current"}
    root = {"id": f"ri:{args.repository}:repository:{args.repository}", "kind": "repository",
            "repository": args.repository, "key": args.repository, "title": args.repository,
            "canonical_url": url, "visibility": "public", "state": {"value": "unknown", "assertion": "unknown"},
            "freshness": "unknown", "provenance": [inventory["id"]], "attributes": {}, "extensions": {}}
    coverage = {domain: {"collection": "uncollected", "freshness": "unknown", "reason": "not_requested", "observed_at": None}
                for domain in adr.DOMAINS}
    coverage["checks"] = claim
    return {"schema": "egohygiene.repository-intelligence/v1", "contract_version": "1.0.0-alpha.2",
            "projection_id": f"{args.repository}@{args.source_commit}", "repository": args.repository,
            "visibility": "public", "represented_commit": args.source_commit, "observed_at": args.observed_at,
            "generator": {"name": "egohygiene/relay:health-collector", "version": "0.1.0", "contract": "egohygiene.repository-intelligence/v1"},
            "sources": sorted([inventory, *sources], key=lambda item: item["id"]),
            "entities": sorted([root, *checks], key=lambda item: item["id"]), "relationships": [], "events": [],
            "redactions": [], "extensions": {}, "collection_coverage": coverage}


def collect(args: argparse.Namespace) -> dict:
    if args.visibility != "public":
        base.fail("VISIBILITY")
    if not base.REPOSITORY.fullmatch(args.repository) or not base.SHA.fullmatch(args.source_commit):
        base.fail("INPUT")
    base.utc(args.observed_at)
    if not 1 <= args.maximum_age_seconds <= 2678400:
        base.fail("INPUT")
    # Verify source existence without reading consumer worktree configuration,
    # executing hooks, or binding public identity to a checkout directory name.
    base.git(args.repository_root, "cat-file", "commit", args.source_commit, limit=base.MAX_SOURCE)
    lock, receipt = base.runtime_files(args.runtime, lock_path=LOCK_PATH)
    summary_path = ROOT.parent / "normalize-repository-report/schemas/repository-report-summary.schema.json"
    raw_schema = base.read_file(summary_path)
    if base.digest(raw_schema) != lock["report_summary"]["schema_sha256"]:
        base.fail("PIN")
    validator = jsonschema.Draft202012Validator(base.load_json(raw_schema), format_checker=jsonschema.FormatChecker())
    reports = {}
    for selection in args.report:
        name, separator, path = selection.partition("=")
        if not separator or name not in PRODUCERS or name in reports or not path:
            base.fail("INPUT")
        reports[name] = Path(path)
    requested = sorted(set(args.expect_report))
    if len(requested) != len(args.expect_report) or set(reports) - set(requested):
        base.fail("INPUT")
    if args.inventory == "not-applicable" and (requested or args.check_runs_state != "not-requested"):
        base.fail("INPUT")
    diagnostics, sources, checks, retained = [], [], [], []
    for producer in requested:
        if producer not in reports:
            diagnostics.append(diagnostic("MISSING", producer))
            retained.append({"producer": producer, "status": "missing", "sha256": None})
            continue
        try:
            evidence, entities, record = report_capture(args, producer, reports[producer], validator)
            sources.extend(evidence)
            checks.extend(entities)
            retained.append(record)
            if record["freshness"] == "stale":
                diagnostics.append(diagnostic("STALE", producer))
        except (base.CollectorError, OSError, ValueError, KeyError, TypeError, RecursionError):
            error = sys.exception()
            code = str(error) if isinstance(error, base.CollectorError) and str(error) in MESSAGES else "REPORT"
            diagnostics.append(diagnostic(code, producer))
            retained.append({"producer": producer, "status": "rejected", "sha256": None})
    try:
        evidence, entities, record, findings = provider_capture(args)
        sources.extend(evidence)
        checks.extend(entities)
        retained.append(record)
        diagnostics.extend(findings)
    except (base.CollectorError, OSError, ValueError, KeyError, TypeError, RecursionError):
        error = sys.exception()
        code = str(error) if isinstance(error, base.CollectorError) and str(error) in MESSAGES else "CHECKS"
        diagnostics.append(diagnostic(code, "github-check-runs"))
        retained.append({"producer": "github-check-runs", "status": "rejected", "sha256": None})
    requested_any = bool(requested) or args.check_runs_state != "not-requested"
    incomplete = any(item["status"] in {"missing", "rejected", "partial", "unavailable", "failed"} for item in retained)
    freshness = "stale" if any(item.get("freshness") == "stale" for item in retained) else "current"
    if args.inventory == "not-applicable":
        claim = {"collection": "not_applicable", "freshness": "not_applicable",
                 "reason": "explicit_not_applicable", "observed_at": args.observed_at}
    elif not requested_any:
        claim = {"collection": "uncollected", "freshness": "unknown", "reason": "not_requested", "observed_at": None}
    elif checks or (not incomplete and args.inventory == "complete"):
        partial = incomplete or args.inventory != "complete"
        claim = {"collection": "partial" if partial else "observed" if checks else "observed_empty",
                 "freshness": freshness, "reason": "incomplete" if incomplete else "filtered" if partial else "complete",
                 "observed_at": args.observed_at}
    else:
        failed = any(item["status"] in {"failed", "rejected"} for item in retained)
        claim = {"collection": "failed" if failed else "unavailable", "freshness": "unknown",
                 "reason": "collection_failed" if failed else "provider_unavailable", "observed_at": None}
    projection = project(args, sources, checks, claim)
    snapshot, validation = adr.normalize(args.runtime, projection)
    if validation["hygiene"] != "valid":
        diagnostics.append(diagnostic("HYGIENE"))
    diagnostics.append(diagnostic("INTEGRATION"))
    status = "invalid" if snapshot is None else "partial" if claim["collection"] == "partial" else "ready" if claim["collection"] in {"observed", "observed_empty"} else claim["collection"]
    return {"schema": SCHEMA, "status": status, "publication": "denied", "repository": args.repository,
            "represented_commit": args.source_commit, "observed_at": args.observed_at,
            "inputs": {"inventory": args.inventory, "requested_reports": requested,
                       "maximum_age_seconds": args.maximum_age_seconds, "captures": retained},
            "runtime": {**receipt, "pins": lock, "collector_sha256": base.digest(Path(__file__).read_bytes()),
                        "shared_runtime_sha256": base.digest(Path(base.__file__).read_bytes()),
                        "normalization_sha256": base.digest(Path(adr.__file__).read_bytes())},
            "validation": validation, "coverage": projection["collection_coverage"], "diagnostics": diagnostics,
            "projection_candidate": projection, "snapshot_candidate": snapshot,
            "candidate_digests": {"projection_sha256": base.digest(base.json_bytes(projection)),
                                  "snapshot_sha256": base.digest(base.json_bytes(snapshot)) if snapshot is not None else None}}


def write_result(path: Path, result: dict, repository_root: Path) -> None:
    path, consumer = base.safe_path(path), base.safe_path(repository_root)
    if path.is_relative_to(consumer) or path.name != OUTPUT_NAME or (path.exists() and not path.is_file()):
        base.fail("PATH")
    schema = base.load_json(base.read_file(ROOT / "schemas/health-collection-review.v1.schema.json"))
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
    command.add_argument("--expect-report", action="append", choices=PRODUCERS, default=[])
    command.add_argument("--report", action="append", default=[], metavar="PRODUCER=PATH")
    command.add_argument("--inventory", choices=("partial", "complete", "not-applicable"), default="partial",
                         help="Complete requires an owner-reviewed declaration of the entire check producer inventory.")
    command.add_argument("--check-runs", type=Path)
    command.add_argument("--check-runs-state", choices=("not-requested", "observed", "unavailable", "failed"), default="not-requested")
    command.add_argument("--check-runs-observed-at")
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
        print("Health collection retained for review; publication denied")
        return 0 if result["status"] in {"ready", "not_applicable"} else 2
    except (base.CollectorError, OSError, ValueError, KeyError, TypeError, RecursionError):
        error = sys.exception()
        code = str(error) if isinstance(error, base.CollectorError) and str(error) in MESSAGES else "INPUT"
        if args.command == "collect":
            try:
                write_result(args.output, {"schema": SCHEMA, "status": "denied", "publication": "denied",
                                          "diagnostics": [diagnostic(code)]}, args.repository_root)
            except (base.CollectorError, OSError):
                pass
        print("Health collector: " + code, file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
