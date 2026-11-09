#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Normalize bounded public release/deployment captures into an offline review."""

from __future__ import annotations

import argparse
from copy import deepcopy
import importlib.util
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import quote

import jsonschema
import yaml

_spec = importlib.util.spec_from_file_location(
    "relay_release_shared", Path(__file__).with_name("collect_repository_roadmap.py"))
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
_spec = importlib.util.spec_from_file_location(
    "relay_release_normalization", Path(__file__).with_name("collect_repository_adrs.py"))
normalization = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(normalization)

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "contracts/release-collector.v1.lock.json"
SCHEMA = "egohygiene.relay.release-collection-review/v1"
OUTPUT_NAME = "release-collection.review.json"
DOMAINS = ("roadmap", "decisions", "git", "issues", "pull_requests", "checks",
           "releases", "deployments", "history")
MESSAGES = {
    "INPUT": "Supply bounded canonical identities, full source revisions and explicit UTC observation times.",
    "PATH": "Use regular files outside the inspected repository; reject symlink ancestors and traversal.",
    "PIN": "Reacquire the exact locked owner sources and prepare the trusted offline runtime again.",
    "RUNTIME": "Prepare the pinned runtime and inspect the owning validators locally.",
    "VISIBILITY": "Supply only an explicitly public capture and allowlisted public deployment environments.",
    "PROVIDER": "Supply the closed public provider capture with honest inventory scope and complete pagination claims.",
    "SOURCE": "Bind the capture, collector and selected observations to their exact existing Git source revisions.",
    "RECEIPT": "Select a valid deployment receipt matching the explicit consumer revision, run, environment and conclusion.",
    "TARGET": "Recapture an explicit public release target; missing references remain unlinked and partial.",
    "HYGIENE": "Repair the candidate against the immutable Hygiene graph and vocabulary contract.",
}


def diagnostic(code: str) -> dict:
    return {"code": code, "owner": "relay", "remediation": MESSAGES[code]}


def valid_schema(value: dict, path: Path) -> bool:
    schema = base.load_json(base.read_file(path))
    return jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()).is_valid(value)


def text(value: str, *, filename: bool = False) -> str:
    # Provider strings are data; reject control characters and sensitive payloads
    # instead of letting them enter attributes, diagnostics or generated URLs.
    if (not isinstance(value, str) or not value or value != value.strip()
            or any(ord(character) < 32 or ord(character) == 127 for character in value)
            or base.SECRET.search(value)):
        base.fail("VISIBILITY")
    if filename and (value in {".", ".."} or "/" in value or "\\" in value):
        base.fail("PROVIDER")
    return value


def source_exists(root: Path, revision: str) -> None:
    if not isinstance(revision, str) or not base.SHA.fullmatch(revision):
        base.fail("SOURCE")
    actual = base.git(root, "rev-parse", "--verify", revision + "^{commit}").decode().strip()
    if actual != revision:
        base.fail("SOURCE")


def generator_binding(revision: str) -> dict:
    """Bind all executed Relay helpers and owner selections to one real commit."""
    generator_root = ROOT.parents[1]
    source_exists(generator_root, revision)
    paths = [Path(__file__).resolve(), Path(base.__file__).resolve(),
             Path(normalization.__file__).resolve(),
             Path(normalization.inputs.__file__).resolve(), LOCK_PATH,
             ROOT / "contracts/roadmap-collector-requirements.txt",
             ROOT / "schemas/release-provider-capture.v1.schema.json",
             ROOT / "schemas/release-collection-review.v1.schema.json",
             ROOT.parent / "repository-intelligence-deployment-provenance/schemas/deployment-receipt.schema.json"]
    digests = {}
    for path in paths:
        relative = path.relative_to(generator_root).as_posix()
        raw = base.read_file(path, base.MAX_OUTPUT)
        if base.git_blob(generator_root, revision, relative, base.MAX_OUTPUT) != raw:
            base.fail("SOURCE")
        digests[relative] = base.digest(raw)
    return digests


def inventory(value: dict, observed, maximum_age: int) -> tuple[dict, list[dict]]:
    state, records = value["status"], value["records"]
    captured = state in {"complete", "truncated", "filtered", "incomplete", "not_applicable"}
    instant = value["observed_at"]
    if captured:
        if instant is None:
            base.fail("PROVIDER")
        age = (observed - base.utc(instant)).total_seconds()
        if age < 0:
            base.fail("PROVIDER")
        freshness = "stale" if age > maximum_age else "current"
    elif instant is not None or records or value["pages_captured"] or value["pagination_complete"]:
        base.fail("PROVIDER")
    if state == "not_applicable":
        if records or value["pages_captured"] or value["pagination_complete"]:
            base.fail("PROVIDER")
        return {"collection": "not_applicable", "freshness": "not_applicable",
                "reason": "explicit_not_applicable", "observed_at": instant}, []
    if state in {"complete", "truncated", "filtered", "incomplete"}:
        if not value["pages_captured"] or (state == "complete" and not value["pagination_complete"]):
            base.fail("PROVIDER")
        if state == "truncated" and value["pagination_complete"]:
            base.fail("PROVIDER")
        return {"collection": ("observed" if records else "observed_empty") if state == "complete" else "partial",
                "freshness": freshness, "reason": "complete" if state == "complete" else state,
                "observed_at": instant}, records
    collection, reason = {
        "denied": ("unavailable", "access_denied"),
        "unavailable": ("unavailable", "provider_unavailable"),
        "failed": ("failed", "collection_failed"),
        "uncollected": ("uncollected", "not_requested"),
    }[state]
    return {"collection": collection, "freshness": "unknown", "reason": reason,
            "observed_at": None}, []


def receipts(paths: list[Path]) -> dict:
    if len(paths) > base.MAX_RECORDS:
        base.fail("INPUT")
    schema_path = ROOT.parent / "repository-intelligence-deployment-provenance/schemas/deployment-receipt.schema.json"
    result = {}
    for path in paths:
        raw = base.read_file(path)
        digest = base.digest(raw)
        value = base.load_json(raw)
        if digest in result or not valid_schema(value, schema_path):
            base.fail("RECEIPT")
        result[digest] = value
    return result


def validate_receipt(record: dict, value: dict, repository: str) -> dict:
    expected_conclusion = {"success": "success", "failure": "failure"}.get(record["status"])
    if (value["consumer"] != {"repository": repository, "revision": record["source_commit"]}
            or value["generator"]["repository"] != "egohygiene/relay"
            or value["workflow"] != {"run_id": record["run_id"], "run_attempt": record["run_attempt"]}
            or value["deployment"]["environment"] != record["environment"]
            or value["deployment"]["conclusion"] != expected_conclusion
            or value["deployment"]["recorded_at"] != record["recorded_at"]):
        base.fail("RECEIPT")
    # Do not publish the raw receipt: consumer paths, aliases, rollback URLs and
    # independently unverified hostnames stay outside this public graph.
    return {"sha256": record["receipt_sha256"],
            "generator_commit": value["generator"]["revision"],
            "bundle_digest": value["build_manifest"]["bundle_digest"],
            "site_digest": value["composition"]["site_digest"]}


def projection(args: argparse.Namespace, captured: dict | None, selected_receipts: dict) -> tuple[dict, list]:
    observed = base.utc(args.observed_at)
    claims = {domain: {"collection": "uncollected", "freshness": "unknown",
                       "reason": "not_requested", "observed_at": None} for domain in DOMAINS}
    records = {"releases": [], "deployments": []}
    for domain in records:
        if captured is None:
            claims[domain] = {"collection": "unavailable", "freshness": "unknown",
                              "reason": "provider_unavailable", "observed_at": None}
        else:
            claims[domain], records[domain] = inventory(captured[domain], observed, args.maximum_age_seconds)
    url = f"https://github.com/{args.repository}"
    source = {"id": "source:release-root", "kind": "git", "url": f"{url}/commit/{args.source_commit}",
              "repository": args.repository, "revision": args.source_commit,
              "observed_at": args.observed_at, "visibility": "public", "assertion": "authoritative", "freshness": "current"}
    root = {"id": f"ri:{args.repository}:repository:{args.repository}", "kind": "repository",
            "repository": args.repository, "key": args.repository, "title": args.repository,
            "canonical_url": url, "visibility": "public", "state": {"value": "unknown", "assertion": "unknown"},
            "freshness": "unknown", "provenance": [source["id"]], "attributes": {}, "extensions": {}}
    result = {"schema": "egohygiene.repository-intelligence/v1", "contract_version": "1.0.0-alpha.2",
              "projection_id": f"{args.repository}@{args.source_commit}", "repository": args.repository,
              "represented_commit": args.source_commit, "visibility": "public", "observed_at": args.observed_at,
              "generator": {"name": "egohygiene/relay:release-collector", "version": "0.1.0",
                            "contract": "egohygiene.repository-intelligence/v1"},
              "sources": [source], "entities": [root], "relationships": [], "events": [],
              "redactions": [], "extensions": {}, "collection_coverage": claims}
    release_ids, release_revisions = {}, {}
    tags, deployment_ids, used_receipts, commits = set(), set(), set(), {}
    diagnostics = []

    def add_source(domain, key, canonical, revision):
        claim = claims[domain]
        value = {**source, "id": f"source:{domain}-" + base.digest(key.encode())[:24], "kind": "release" if domain == "releases" else "deployment",
                 "url": canonical, "revision": revision, "observed_at": claim["observed_at"], "freshness": claim["freshness"]}
        result["sources"].append(value)
        return value

    def entity(kind, key, title, canonical, state, provenance, attributes, identity=None):
        identity = key if identity is None else identity
        return {**deepcopy(root), "id": f"ri:{args.repository}:{kind}:{identity}", "kind": kind, "key": key,
                "title": title, "canonical_url": canonical, "state": {"value": state, "assertion": "authoritative"},
                "freshness": provenance["freshness"], "provenance": [provenance["id"]], "attributes": attributes}

    def commit(revision, provenance):
        identifier = f"ri:{args.repository}:commit:{revision}"
        if revision not in commits:
            source_exists(args.repository_root, revision)
            value = entity("commit", revision, None, f"{url}/commit/{revision}", "observed", provenance, {"sha": revision})
            result["entities"].append(value)
            commits[revision] = value
        else:
            value = commits[revision]
            value["provenance"] = sorted(set(value["provenance"]) | {provenance["id"]})
            if provenance["freshness"] == "stale":
                value["freshness"] = "stale"
        return identifier

    def edge(kind, origin, target, provenance):
        result["relationships"].append({"id": "relationship:" + base.digest(f"{kind}:{origin}:{target}".encode())[:32],
            "type": kind, "source": origin, "target": target, "direction": "directed",
            "assertion": "authoritative", "freshness": provenance["freshness"],
            "provenance": [provenance["id"]], "extensions": {}})

    def event(kind, subject, occurred, provenance):
        result["events"].append({"id": "event:" + base.digest(f"{kind}:{subject}:{occurred}".encode())[:32],
            "type": kind, "subject": subject, "occurred_at": occurred, "recorded_at": provenance["observed_at"],
            "actor": None, "changes": [], "visibility": "public", "assertion": "authoritative",
            "freshness": provenance["freshness"], "provenance": [provenance["id"]], "extensions": {}})

    for record in records["releases"]:
        number, tag = record["id"], text(record["tag_name"])
        if number in release_ids or tag in tags:
            base.fail("PROVIDER")
        tags.add(tag)
        title = text(record["title"]) if record["title"] is not None else None
        if base.utc(record["published_at"]) > base.utc(claims["releases"]["observed_at"]):
            base.fail("PROVIDER")
        canonical = f"{url}/releases/tag/{quote(tag, safe='')}"
        provenance = add_source("releases", str(number), canonical, record["source_commit"])
        assets, names = [], set()
        for asset in record["assets"]:
            name = text(asset["name"], filename=True)
            if name in names:
                base.fail("PROVIDER")
            names.add(name)
            assets.append({**asset, "canonical_url": f"{url}/releases/download/{quote(tag, safe='')}/{quote(name, safe='')}"})
        attributes = {"tag_name": tag, "published_at": record["published_at"], "source_commit": record["source_commit"],
                      "provider_id": number, "draft": False, "prerelease": record["prerelease"],
                      "assets": sorted(assets, key=lambda asset: asset["name"]), "install_verification": "uncollected"}
        state = "retracted" if record["state"] == "retracted" else "prerelease" if record["prerelease"] else "published"
        value = entity("release", tag, title, canonical, state, provenance, attributes, identity=str(number))
        result["entities"].append(value)
        release_ids[number] = value["id"]
        release_revisions[number] = record["source_commit"]
        edge("releases", value["id"], commit(record["source_commit"], provenance), provenance)
        event("release.published", value["id"], record["published_at"], provenance)

    for record in records["deployments"]:
        key, environment = record["id"], text(record["environment"])
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", key) or key in deployment_ids:
            base.fail("PROVIDER")
        if environment not in args.public_environment:
            base.fail("VISIBILITY")
        deployment_ids.add(key)
        if base.utc(record["recorded_at"]) > base.utc(claims["deployments"]["observed_at"]):
            base.fail("PROVIDER")
        canonical = f"{url}/actions/runs/{record['run_id']}/attempts/{record['run_attempt']}"
        provenance = add_source("deployments", key, canonical, record["source_commit"])
        attributes = {"environment": environment, "status": record["status"], "source_commit": record["source_commit"],
                      "run_id": record["run_id"], "run_attempt": record["run_attempt"], "recorded_at": record["recorded_at"]}
        receipt_digest = record["receipt_sha256"]
        if receipt_digest is not None:
            if receipt_digest not in selected_receipts or receipt_digest in used_receipts:
                base.fail("RECEIPT")
            used_receipts.add(receipt_digest)
            attributes["receipt"] = validate_receipt(record, selected_receipts[receipt_digest], args.repository)
        value = entity("deployment", key, None, canonical, record["status"], provenance, attributes)
        result["entities"].append(value)
        edge("deploys", value["id"], commit(record["source_commit"], provenance), provenance)
        target = record["release_id"]
        if target is not None:
            if target in release_ids:
                if record["source_commit"] != release_revisions[target]:
                    base.fail("SOURCE")
                edge("deploys", value["id"], release_ids[target], provenance)
            else:
                # No placeholder target or sensitive provider identifier enters
                # diagnostics. An incomplete release inventory remains explicit.
                diagnostics.append(diagnostic("TARGET"))
                if claims["releases"]["collection"] in {"observed", "observed_empty"}:
                    base.fail("PROVIDER")
        if record["status"] in {"success", "failure", "inactive"}:
            event("deployment.completed", value["id"], record["recorded_at"], provenance)
    if used_receipts != set(selected_receipts):
        base.fail("RECEIPT")
    for name in ("sources", "entities", "relationships"):
        result[name].sort(key=lambda value: value["id"])
    result["events"].sort(key=lambda value: (value["occurred_at"], value["id"]))
    for domain, present in (("git", bool(commits)), ("history", bool(result["events"]))):
        if present:
            # Targeted commit identities and release/deployment lifecycle events
            # form a strict subset, never a complete Git or cross-domain history.
            selected = [claims[name] for name in ("releases", "deployments")
                        if records[name]]
            claims[domain] = {"collection": "partial", "reason": "filtered",
                              "freshness": "stale" if any(item["freshness"] == "stale" for item in selected) else "current",
                              "observed_at": max(item["observed_at"] for item in selected)}
    return result, diagnostics


def collect(args: argparse.Namespace) -> dict:
    if args.visibility != "public":
        base.fail("VISIBILITY")
    if (not base.REPOSITORY.fullmatch(args.repository) or not base.SHA.fullmatch(args.source_commit)
            or not base.SHA.fullmatch(args.generator_commit) or not 1 <= args.maximum_age_seconds <= 2678400):
        base.fail("INPUT")
    base.utc(args.observed_at)
    if len(args.public_environment) > 64 or len(set(args.public_environment)) != len(args.public_environment):
        base.fail("INPUT")
    for environment in args.public_environment:
        if len(environment) > 64 or not re.fullmatch(r"[A-Za-z0-9._ -]+", text(environment)):
            base.fail("VISIBILITY")
    lock, runtime_receipt = base.runtime_files(args.runtime, lock_path=LOCK_PATH)
    helpers = generator_binding(args.generator_commit)
    source_exists(args.repository_root, args.source_commit)
    captured, capture_digest = None, None
    if args.capture is not None:
        raw = base.read_file(args.capture)
        captured = base.load_json(raw)
        if not valid_schema(captured, ROOT / "schemas/release-provider-capture.v1.schema.json"):
            base.fail("PROVIDER")
        if captured["repository"] != args.repository or captured["represented_commit"] != args.source_commit:
            base.fail("SOURCE")
        capture_digest = base.digest(raw)
    selected_receipts = receipts(args.deployment_receipt)
    candidate, diagnostics = projection(args, captured, selected_receipts)
    snapshot, validation = normalization.normalize(args.runtime, candidate)
    if validation["hygiene"] == "invalid":
        status = "invalid"
        diagnostics.append(diagnostic("HYGIENE"))
    else:
        claims = [candidate["collection_coverage"][domain] for domain in ("releases", "deployments")]
        values = {claim["collection"] for claim in claims}
        if "partial" in values or diagnostics:
            status = "partial"
        elif values == {"not_applicable"}:
            status = "not_applicable"
        elif values == {"uncollected"}:
            status = "uncollected"
        elif values.intersection({"unavailable", "failed", "uncollected"}):
            status = "unavailable"
        elif any(claim["freshness"] == "stale" for claim in claims):
            status = "stale"
        else:
            status = "ready"
    return {"schema": SCHEMA, "status": status, "publication": "denied", "repository": args.repository,
            "represented_commit": args.source_commit, "generator_commit": args.generator_commit,
            "observed_at": args.observed_at,
            "inputs": {"capture_sha256": capture_digest, "receipt_sha256": sorted(selected_receipts),
                       "public_environments": sorted(args.public_environment), "maximum_age_seconds": args.maximum_age_seconds,
                       "inventory": {domain: {key: value for key, value in captured[domain].items() if key != "records"}
                                     for domain in ("releases", "deployments")} if captured else None},
            "runtime": {**runtime_receipt, "pins": lock, "relay_files_sha256": helpers},
            "validation": validation, "coverage": candidate["collection_coverage"], "diagnostics": diagnostics,
            "projection_candidate": candidate, "snapshot_candidate": snapshot,
            "candidate_digests": {"projection_sha256": base.digest(base.json_bytes(candidate)),
                                  "snapshot_sha256": base.digest(base.json_bytes(snapshot)) if snapshot else None}}


def write_result(path: Path, result: dict, repository_root: Path) -> None:
    path, consumer = base.safe_path(path), base.safe_path(repository_root)
    if path.is_relative_to(consumer) or path.name != OUTPUT_NAME or (path.exists() and not path.is_file()):
        base.fail("PATH")
    if not valid_schema(result, ROOT / "schemas/release-collection-review.v1.schema.json"):
        base.fail("INPUT")
    raw = base.json_bytes(result)
    if len(raw) > base.MAX_OUTPUT:
        base.fail("INPUT")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = result.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", allow_abbrev=False)
    for owner in ("hygiene", "egolint", "observatory"):
        prepare.add_argument("--" + owner, type=Path, required=True)
    prepare.add_argument("--cargo", type=Path, default=Path("cargo"))
    prepare.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("collect", allow_abbrev=False)
    for name in ("runtime", "repository-root", "output"):
        command.add_argument("--" + name, type=Path, required=True)
    for name in ("repository", "visibility", "source-commit", "generator-commit", "observed-at"):
        command.add_argument("--" + name, required=True)
    command.add_argument("--capture", type=Path)
    command.add_argument("--public-environment", action="append", default=[])
    command.add_argument("--deployment-receipt", action="append", type=Path, default=[])
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
        print("Release collection retained for review; publication denied")
        return 0 if result["status"] in {"ready", "not_applicable"} else 2
    except (base.CollectorError, OSError, ValueError, KeyError, TypeError, yaml.YAMLError, RecursionError):
        error = sys.exception()
        code = str(error) if isinstance(error, base.CollectorError) and str(error) in MESSAGES else "INPUT"
        if args.command == "collect":
            try:
                write_result(args.output, {"schema": SCHEMA, "status": "denied", "publication": "denied",
                                          "diagnostics": [diagnostic(code)]}, args.repository_root)
            except (base.CollectorError, OSError):
                pass
        print("Release collector: " + code, file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
