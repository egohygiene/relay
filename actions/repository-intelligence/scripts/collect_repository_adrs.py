#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Collect canonical ADRs from immutable Git objects into an offline review envelope."""

from __future__ import annotations

import argparse
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
import tomllib

import jsonschema
import yaml

_spec = importlib.util.spec_from_file_location(
    "relay_collection_runtime", Path(__file__).with_name("collect_repository_roadmap.py"))
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "contracts/adr-collector.v1.lock.json"
SCHEMA = "egohygiene.relay.adr-collection-review/v1"
OUTPUT_NAME = "adr-collection.review.json"
MAX_TOTAL = 2 * base.MAX_JSON
DOMAINS = ("roadmap", "decisions", "git", "issues", "pull_requests", "checks",
           "releases", "deployments", "history")
ADR_SCHEMA = "egohygiene.architecture-decision/v1"
MESSAGES = {
    **base.MESSAGES,
    "EXTRACTION": "Preserve legacy records and complete owner-reviewed ADR migration before claiming full coverage.",
    "UNAVAILABLE": "Supply the canonical index and decision directory at the represented revision.",
    "EXTENSION": "Review a supported owner mapping before projecting local extension payloads.",
    "INTEGRATION": "Complete Relay #115 build integration and consumer review before publication.",
}


def diagnostic(code: str, owner: str = "relay", path: str | None = None,
               line: int | None = None) -> dict:
    return {"code": code, "owner": owner, "path": path, "line": line,
            "remediation": MESSAGES.get(code, "Run the pinned EgoLint validator and repair its source finding.")}


def relative(value: str) -> str:
    if (not isinstance(value, str) or len(value) > 240
            or not re.fullmatch(r"[A-Za-z0-9._/-]+", value)
            or value.startswith("/") or value.endswith("/")
            or any(p in {"", ".", "..", ".git", ".reports"} for p in value.split("/"))):
        base.fail("PATH")
    return value


def inventory(args: argparse.Namespace) -> tuple[dict[str, bytes], bool]:
    """Read only bounded regular Git blobs; never follow checkout links or filters."""
    paths = [relative(args.decision_directory), relative(args.index), relative(args.policy_reference)]
    if not args.index.endswith(".md") or not args.policy_reference.endswith(".json"):
        base.fail("PATH")
    raw = base.git(args.repository_root, "ls-tree", "-r", "-z", "--full-tree",
                   args.source_commit, "--", *paths, limit=base.MAX_JSON)
    entries = raw.split(b"\0")[:-1]
    if len(entries) > base.MAX_RECORDS:
        base.fail("INPUT")
    files = {}
    total = 0
    directory_present = False
    for entry in entries:
        header, name = entry.split(b"\t", 1)
        mode, kind, blob = header.decode("ascii").split()
        path = relative(name.decode("utf-8"))
        if mode not in {"100644", "100755"} or kind != "blob":
            base.fail("PATH")
        under_directory = path.startswith(args.decision_directory + "/")
        directory_present |= under_directory
        if not under_directory and path not in paths[1:]:
            base.fail("PATH")
        if path not in paths[1:] and not path.endswith(".md"):
            continue
        size = int(base.git(args.repository_root, "cat-file", "-s", blob))
        if size > base.MAX_SOURCE or total + size > MAX_TOTAL:
            base.fail("INPUT")
        content = base.git(args.repository_root, "cat-file", "blob", blob, limit=base.MAX_SOURCE)
        total += len(content)
        files[path] = content
    return files, directory_present


def front_matter(text: str) -> dict | None:
    if not text.startswith("---\n"):
        return None
    match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", text, re.DOTALL)
    if not match:
        base.fail("EXTRACTION")
    source = match[1]

    class Loader(yaml.SafeLoader):
        yaml_implicit_resolvers = {
            key: [(tag, regex) for tag, regex in values if tag != "tag:yaml.org,2002:timestamp"]
            for key, values in yaml.SafeLoader.yaml_implicit_resolvers.items()
        }

    def mapping(loader, node):
        return base.unique_pairs([(loader.construct_object(k, deep=True),
                                   loader.construct_object(v, deep=True)) for k, v in node.value])

    Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    for count, token in enumerate(yaml.scan(source)):
        if count > 8192 or isinstance(token, (yaml.tokens.AnchorToken, yaml.tokens.AliasToken, yaml.tokens.TagToken)):
            base.fail("EXTRACTION")
    result = yaml.load(source, Loader=Loader)
    if not isinstance(result, dict):
        base.fail("EXTRACTION")
    return result


def extract(files: dict[str, bytes], args: argparse.Namespace, runtime: Path) -> tuple[list, list, bool]:
    schema = base.load_json(base.read_file(runtime / "hygiene_adr/schemas/architecture-decision.v1.schema.json"))
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    records, diagnostics, seen = [], [], set()
    partial = args.adoption == "legacy"
    for path, content in sorted(files.items()):
        text = content.decode("utf-8").replace("\r\n", "\n")
        if base.SECRET.search(text):
            base.fail("VISIBILITY")
        if not path.startswith(args.decision_directory + "/") or not path.endswith(".md"):
            continue
        name = PurePosixPath(path).name
        if name == "ADR-TEMPLATE.md" or path == args.index:
            continue
        metadata = front_matter(text)
        candidate = name.startswith("ADR-") or (metadata and metadata.get("schema") == ADR_SCHEMA)
        if not candidate:
            # Preserve unsupported indexed legacy prefixes as uncertainty, not nodes.
            if name not in {"README.md", "POLICY.md", "MIGRATION.md", "VALIDATION.md", "RATIFICATION.md"}:
                partial = True
                diagnostics.append(diagnostic("EXTRACTION"))
            continue
        if metadata is not None and metadata.get("visibility") != "public":
            base.fail("VISIBILITY")
        if metadata is None or not validator.is_valid(metadata):
            partial = True
            diagnostics.append(diagnostic("EXTRACTION"))
            continue
        if metadata["id"] in seen:
            # Withhold every ambiguous identity rather than selecting a winner.
            records = [r for r in records if r["metadata"]["id"] != metadata["id"]]
            partial = True
            diagnostics.append(diagnostic("EXTRACTION"))
            continue
        seen.add(metadata["id"])
        if metadata.get("extensions"):
            partial = True
            diagnostics.append(diagnostic("EXTENSION"))
        records.append({"path": path, "metadata": metadata})
    return records, diagnostics, partial


def source_validate(args: argparse.Namespace, files: dict, commit: bytes, available: bool) -> dict:
    runtime = args.runtime
    catalog = tomllib.loads(base.read_file(runtime / "egolint/.config/rules/repository-intelligence.v1.toml").decode())
    rules = [r["id"] for r in catalog["rules"] if not (
        r["id"].startswith("EGO-INTEL-ROADMAP-") or r["id"] == "EGO-INTEL-TRAILER-001")]
    policy = f'schema-version = 1\nid = "egolint.repository-intelligence-validation/v1"\nrepository = "{args.repository}"\n'
    policy += '[profile]\nid = "relay-adr-review"\nenforcement = "blocking"\nenabled-rules = ' + json.dumps(rules) + "\n"
    pins = deepcopy(catalog["upstream-contracts"])
    for i, pin in enumerate(pins):
        if pin["id"] == "egohygiene.repository-intelligence/v1":
            pins[i] = next(p for p in catalog["compatible-upstream-contracts"] if p["version"] == "1.0.0-alpha.2")
    for pin in pins:
        policy += "\n[[contracts]]\n" + "".join(f"{k} = {json.dumps(v)}\n" for k, v in pin.items())
    state = "not-applicable" if args.adoption == "not-applicable" else "present" if available else "unknown"
    policy += (f'\n[adrs]\nstate = "{state}"\npolicy-reference = "{args.policy_reference}"\n'
               f'decision-directory = "{args.decision_directory}"\nindex = "{args.index}"\n'
               '[roadmap]\nstate = "unknown"\npath = "ROADMAP.md"\n'
               '[commit-history]\nstate = "unknown"\nmaximum-commits = 1\n')
    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory)
        (workspace / "template").mkdir()
        base.git(workspace, "init", "--quiet", "--template", str(workspace / "template"))
        actual = base.git(workspace, "hash-object", "-t", "commit", "-w", "--stdin", data=commit).decode().strip()
        if actual != args.source_commit:
            base.fail("INPUT")
        (workspace / ".git/shallow").write_text(args.source_commit + "\n")
        for path, content in files.items():
            target = workspace / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        (workspace / ".relay-adr-validation.toml").write_text(policy)
        base.run([str(runtime / "egolint-bin"), "--workspace", str(workspace), "validate",
                  "--repository-intelligence", ".relay-adr-validation.toml", "--represented-commit", args.source_commit],
                 cwd=workspace, allowed=(0, 1, 2, 3), timeout=60)
        report = base.load_json(base.read_file(workspace / ".reports/egolint/repository-intelligence.json"))
    schema = base.load_json(base.read_file(runtime / "egolint/schemas/repository-intelligence-report.schema.json"))
    if (not jsonschema.Draft202012Validator(schema).is_valid(report)
            or report["repository"] != args.repository
            or report["represented_commit"]["revision"] != args.source_commit
            or report["catalog_version"] != catalog["catalog-version"]
            or report["contracts"] != pins):
        base.fail("RUNTIME")
    return report


def project(args: argparse.Namespace, files: dict, records: list, claim: dict) -> dict:
    repository, revision = args.repository, args.source_commit
    url = f"https://github.com/{repository}"
    source = {"id": "source:adr-inventory", "kind": "git", "url": f"{url}/tree/{revision}",
              "repository": repository, "revision": revision, "observed_at": args.collected_at,
              "visibility": "public", "assertion": "authoritative", "freshness": "current"}
    root = {"id": f"ri:{repository}:repository:{repository}", "kind": "repository", "repository": repository,
            "key": repository, "title": repository, "canonical_url": url, "visibility": "public",
            "state": {"value": "unknown", "assertion": "unknown"}, "freshness": "unknown",
            "provenance": [source["id"]], "attributes": {}, "extensions": {}}
    coverage = {domain: {"collection": "uncollected", "freshness": "unknown",
                         "reason": "not_requested", "observed_at": None} for domain in DOMAINS}
    coverage["decisions"] = claim
    projection = {"schema": "egohygiene.repository-intelligence/v1", "contract_version": "1.0.0-alpha.2",
                  "projection_id": f"{repository}@{revision}", "repository": repository,
                  "represented_commit": revision, "visibility": "public", "observed_at": args.observed_at,
                  "generator": {"name": "egohygiene/relay:adr-collector", "version": "0.1.0",
                                "contract": "egohygiene.repository-intelligence/v1"},
                  "sources": [source], "entities": [root], "relationships": [], "events": [],
                  "redactions": [], "extensions": {}, "collection_coverage": coverage}
    ids = {record["metadata"]["id"] for record in records}
    edges = set()
    for record in records:
        metadata, path = record["metadata"], record["path"]
        source_id = "source:adr-" + base.digest(path.encode())[:24]
        canonical_url = f"{url}/blob/{revision}/{path}"
        projection["sources"].append({**source, "id": source_id, "kind": "architecture_decision",
                                       "url": canonical_url, "freshness": claim["freshness"]})
        attributes = {key: value for key, value in metadata.items()
                      if key not in {"schema", "id", "title", "status", "visibility", "extensions"}}
        projection["entities"].append({**root, "id": f"ri:{repository}:architecture-decision:{metadata['id']}",
            "kind": "architecture_decision", "key": metadata["id"], "title": metadata["title"],
            "canonical_url": canonical_url, "state": {"value": metadata["status"], "assertion": "authoritative"},
            "freshness": claim["freshness"], "provenance": [source_id], "attributes": attributes})
        for old in metadata["supersedes"]:
            if old in ids:
                edges.add((metadata["id"], old))
        for new in metadata["superseded_by"]:
            if new in ids:
                edges.add((new, metadata["id"]))
    for new, old in sorted(edges):
        projection["relationships"].append({"id": "relationship:" + base.digest(f"{new}:{old}".encode())[:32],
            "type": "supersedes", "source": f"ri:{repository}:architecture-decision:{new}",
            "target": f"ri:{repository}:architecture-decision:{old}", "direction": "directed",
            "assertion": "authoritative", "freshness": claim["freshness"],
            "provenance": sorted(e["provenance"][0] for e in projection["entities"] if e["key"] in {new, old}),
            "extensions": {}})
    for key in ("sources", "entities", "relationships"):
        projection[key].sort(key=lambda value: value["id"])
    return projection


def normalize(runtime: Path, projection: dict) -> tuple[dict | None, dict]:
    hygiene = base.module(runtime / "hygiene/tools/intelligence.py", "pinned_adr_hygiene")
    vocabulary = base.load_json(base.read_file(runtime / "hygiene/catalog/repository-intelligence-vocabulary.json"))
    schema = base.load_json(base.read_file(runtime / "hygiene/schemas/repository-intelligence.alpha2.schema.json"))
    valid = (jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).is_valid(projection)
             and not hygiene.validate_snapshot(projection, vocabulary))
    if not valid:
        return None, {"hygiene": "invalid", "coverage": "not-run", "observatory": "not-run"}
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "projection.json"
        path.write_bytes(base.json_bytes(projection))
        report = base.load_json(base.run([str(runtime / "egolint-bin"), "intelligence", "validate-coverage", "--input", str(path)],
                                         allowed=(0, 1, 2)))
    schema = base.load_json(base.read_file(runtime / "egolint/schemas/intelligence-coverage-report.schema.json"))
    if (not jsonschema.Draft202012Validator(schema).is_valid(report)
            or report["status"] != "valid" or report["coverage"] != "explicit"
            or report["domains"] != projection["collection_coverage"]):
        base.fail("RUNTIME")
    observatory = base.module(runtime / "observatory/src/observatory/intelligence.py", "pinned_adr_observatory")
    snapshot = observatory.build_repository_snapshot(projection)
    schema = base.load_json(base.read_file(runtime / "observatory/schemas/repository-intelligence-read-model.v1.schema.json"))
    if (not jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).is_valid(snapshot)
            or snapshot["coverage"]["domains"] != projection["collection_coverage"]):
        base.fail("PIN")
    return snapshot, {"hygiene": "valid", "coverage": "valid", "observatory": "normalized"}


def collect(args: argparse.Namespace, *, on_stage=None) -> dict:
    stage = on_stage or (lambda _name: None)
    stage("collection")
    if args.visibility != "public":
        base.fail("VISIBILITY")
    if not base.REPOSITORY.fullmatch(args.repository) or not base.SHA.fullmatch(args.source_commit):
        base.fail("INPUT")
    for path in (args.decision_directory, args.index, args.policy_reference):
        relative(path)
        if base.SECRET.search(path):
            base.fail("VISIBILITY")
    observed = base.utc(args.observed_at)
    args.collected_at = args.collected_at or args.observed_at
    age = (observed - base.utc(args.collected_at)).total_seconds()
    if age < 0 or not 1 <= args.maximum_age_seconds <= 2678400:
        base.fail("INPUT")
    lock, receipt = base.runtime_files(args.runtime, lock_path=LOCK_PATH)
    commit = base.git(args.repository_root, "cat-file", "commit", args.source_commit, limit=base.MAX_SOURCE)
    diagnostics, records, files = [], [], {}
    available, partial = False, False
    if args.adoption != "unknown":
        files, directory_present = inventory(args)
        records, diagnostics, partial = extract(files, args, args.runtime)
        available = directory_present and args.index in files
        if args.adoption == "not-applicable":
            if records or partial or any(PurePosixPath(p).name.startswith("ADR-") and not p.endswith("ADR-TEMPLATE.md") for p in files):
                base.fail("INPUT")
        elif not available:
            records = []
            diagnostics.append(diagnostic("UNAVAILABLE"))
    freshness = "stale" if age > args.maximum_age_seconds else "current"
    claim = {"collection": "uncollected", "freshness": "unknown", "reason": "not_requested", "observed_at": None}
    status = "uncollected"
    if args.adoption == "not-applicable":
        claim = {"collection": "not_applicable", "freshness": "not_applicable",
                 "reason": "explicit_not_applicable", "observed_at": args.collected_at}
        status = "not_applicable"
    elif args.adoption != "unknown":
        if not available:
            claim.update(collection="unavailable", reason="provider_unavailable")
            status = "unavailable"
        else:
            claim = {"collection": "partial" if partial else "observed" if records else "observed_empty",
                     "freshness": freshness, "reason": "incomplete" if partial else "complete",
                     "observed_at": args.collected_at}
            status = "partial" if partial else "ready"
    stage("source-validation")
    report = source_validate(args, files, commit, available)
    catalog = tomllib.loads(base.read_file(args.runtime / "egolint/.config/rules/repository-intelligence.v1.toml").decode())
    rules = {r["id"]: r["remediation"] for r in catalog["rules"]}
    for item in report["diagnostics"][:base.MAX_RECORDS]:
        if item["rule_id"] not in rules:
            base.fail("PIN")
        location = item.get("location") or {}
        path = location.get("path") if location.get("path") in files else None
        finding = diagnostic(item["rule_id"], "egolint", path, location.get("line") if path else None)
        finding["remediation"] = rules[item["rule_id"]]
        diagnostics.append(finding)
    stage("normalization")
    projection = project(args, files, records, claim)
    snapshot, validation = normalize(args.runtime, projection)
    if report["status"] == "invalid" or validation["hygiene"] == "invalid":
        status = "invalid"
    if validation["hygiene"] == "invalid":
        diagnostics.append(diagnostic("HYGIENE", "hygiene"))
    diagnostics.append(diagnostic("INTEGRATION"))
    return {"schema": SCHEMA, "status": status, "publication": "denied", "repository": args.repository,
            "represented_commit": args.source_commit, "observed_at": args.observed_at,
            "inputs": {"adoption": args.adoption, "policy_reference": args.policy_reference,
                       "decision_directory": args.decision_directory, "index": args.index,
                       "collected_at": args.collected_at, "maximum_age_seconds": args.maximum_age_seconds,
                       "sources": [{"path": p, "sha256": base.digest(b)} for p, b in sorted(files.items())]},
            "runtime": {**receipt, "pins": lock, "collector_sha256": base.digest(Path(__file__).read_bytes()),
                        "shared_runtime_sha256": base.digest(Path(base.__file__).read_bytes())},
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
    schema = base.load_json(base.read_file(ROOT / "schemas/adr-collection-review.v1.schema.json"))
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
    command.add_argument("--adoption", choices=("present", "legacy", "unknown", "not-applicable"), required=True)
    command.add_argument("--policy-reference", default="docs/decisions/policy-reference.json")
    command.add_argument("--decision-directory", default="docs/decisions")
    command.add_argument("--index", default="docs/decisions/README.md")
    command.add_argument("--collected-at")
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
        print("ADR collection retained for review; publication denied")
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
        print("ADR collector: " + code, file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
