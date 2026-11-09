#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Project allowlisted canonical declared dependencies through pinned Intelligence owners."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

import jsonschema
import yaml

_spec = importlib.util.spec_from_file_location(
    "relay_dependency_native", Path(__file__).with_name("collect_repository_adrs.py"))
native = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(native)
base = native.base

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "contracts/dependency-collector.v1.lock.json"
SCHEMA = "egohygiene.relay.dependency-collection-review/v1"
OUTPUT_NAME = "dependency-collection.review.json"
MAX_EDGES = 2048
MESSAGES = {
    **base.MESSAGES,
    "CATALOG": "Inspect the pinned Hygiene catalog, context mapping and boundary register with their owning validators.",
    "ENDPOINT": "Review the explicitly allowed repository identities against the selected canonical catalog; no endpoint is guessed or renamed.",
    "BOUNDARY": "Review the declared consumer/producer pair against Hygiene's permitted direction and contract; no forbidden pair is projected.",
    "SCOPE": "This is an allowlisted, depth-bounded graph of declared intent; package adoption, provider inventories and excluded topology are uncollected.",
    "INTEGRATION": "Review Hygiene #36's catalog/public allowlist and the source mapping before consumer adoption or publication.",
}


def diagnostic(code: str, owner: str = "relay") -> dict:
    return {"code": code, "owner": owner,
            "remediation": MESSAGES.get(code, MESSAGES["CATALOG"])}


def allowlist(raw: str) -> list[str]:
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > 16384:
        base.fail("VISIBILITY")
    try:
        values = json.loads(raw, parse_constant=lambda _value: base.fail("VISIBILITY"))
    except (ValueError, UnicodeError, RecursionError):
        base.fail("VISIBILITY")
    if (not isinstance(values, list) or not 1 <= len(values) <= base.MAX_RECORDS
            or any(not isinstance(item, str) or not base.REPOSITORY.fullmatch(item) for item in values)
            or len(set(values)) != len(values)):
        base.fail("VISIBILITY")
    return sorted(values)


def source_validate(runtime: Path) -> dict:
    """Validate only the exact locked public owner corpus, never consumer code."""
    # The profile's complete source corpus is public and immutable. Operational
    # allowlisting below still precedes graph lookup, matching and expansion.
    # Arbitrary/mixed/private catalogs are not accepted by this initial profile.
    program = r'''
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(root / "tools"))
import catalog, context, boundaries
load = lambda path: json.loads((root / path).read_bytes())
data = load("catalog/repositories.yaml")
policy = load("catalog/repository-context.json")
register = load("catalog/dependency-boundaries.yaml")
contracts = load("catalog/contracts.yaml")
result = {"catalog": not catalog.validate_catalog(data),
          "context": not context.validate_policy(data, policy),
          "boundaries": not boundaries.validate_register(register, data, contracts)}
print(json.dumps(result, sort_keys=True))
'''
    result = base.load_json(base.run([sys.executable, "-I", "-c", program,
                                      str(base.safe_path(runtime / "hygiene_catalog"))], limit=4096))
    if result != {"catalog": True, "context": True, "boundaries": True}:
        base.fail("CATALOG")
    owner = runtime / "hygiene_catalog"
    for filename, schema_name in (("catalog/repositories.yaml", "repository-catalog.v1.schema.json"),
                                  ("catalog/dependency-boundaries.yaml", "dependency-boundary-register.v1.schema.json")):
        document = base.load_json(base.read_file(owner / filename))
        schema = base.load_json(base.read_file(owner / "schemas" / schema_name))
        if not jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).is_valid(document):
            base.fail("CATALOG")
    return {key: "valid" for key in result}


def collect_graph(args: argparse.Namespace, catalog: dict, context: dict, register: dict,
                  permitted: list[str]) -> tuple[list[dict], list[dict], list[dict]]:
    """Resolve only already allowed identities and direct authored consumption."""
    permitted_set = set(permitted)
    if args.repository not in permitted_set:
        base.fail("VISIBILITY")
    # Do not index, traverse, count or emit placeholders for excluded records.
    visible = {record["full_name"]: record for record in catalog["repositories"]
               if record.get("full_name") in permitted_set and record.get("visibility") == "public"}
    if args.repository not in visible:
        base.fail("ENDPOINT")
    seen, edges, boundary_evidence = {args.repository}, {}, {}
    frontier = {args.repository}
    for _depth in range(args.maximum_depth):
        following = set()
        for consumer in sorted(frontier):
            if "target_name" in visible[consumer]:
                # An alias/rename is an owner disposition, never a guessed
                # graph node. Unvisited allowlist entries stay irrelevant.
                base.fail("ENDPOINT")
            for consumed in visible[consumer]["consumes"]:
                for producer in context["dependency_sources"][consumed]:
                    # Apply projection authorization before any endpoint lookup,
                    # boundary expansion or existence diagnostic.
                    if producer not in permitted_set or producer == consumer:
                        continue
                    if producer not in visible or "target_name" in visible[producer]:
                        base.fail("ENDPOINT")
                    forbidden = any(item["source"] == consumer and item["target"] == producer
                                    for item in register["forbidden_dependencies"])
                    matches = [item for item in register["relationships"]
                               if item["producer"] == producer
                               and (consumer in item["consumers"] or "egohygiene/*" in item["consumers"])]
                    if forbidden or not matches:
                        base.fail("BOUNDARY")
                    key = (consumer, producer)
                    edges[key] = {"source": consumer, "target": producer}
                    # Preserve policy delivery gaps as policy evidence, rather
                    # than deriving runtime adoption or invented blocks edges.
                    boundary_evidence[key] = {"source": consumer, "target": producer,
                        "policies": [{field: item[field] for field in
                                      ("id", "contract", "contract_status", "pinning")}
                                     for item in sorted(matches, key=lambda item: item["id"])]}
                    if producer not in seen:
                        following.add(producer)
                    seen.add(producer)
                    if len(seen) > base.MAX_RECORDS or len(edges) > MAX_EDGES:
                        base.fail("INPUT")
        frontier = following
    nodes = [visible[name] for name in sorted(seen)]
    return nodes, [edges[key] for key in sorted(edges)], [boundary_evidence[key] for key in sorted(boundary_evidence)]


def project(args: argparse.Namespace, nodes: list[dict], edges: list[dict], catalog_revision: str) -> dict:
    owner_url = f"https://github.com/egohygiene/hygiene/blob/{catalog_revision}/"
    sources = [{"id": "source:dependency-" + name, "kind": "git", "url": owner_url + path,
                "repository": "egohygiene/hygiene", "revision": catalog_revision,
                "observed_at": args.collected_at, "visibility": "public",
                "assertion": "authoritative", "freshness": args.catalog_freshness}
               for name, path in (("catalog", "catalog/repositories.yaml"),
                                  ("context", "catalog/repository-context.json"),
                                  ("boundaries", "catalog/dependency-boundaries.yaml"))]
    entities = []
    for row in nodes:
        name = row["full_name"]
        entities.append({"id": f"ri:{name}:repository:{name}", "kind": "repository", "repository": name,
            "key": name, "title": name, "canonical_url": f"https://github.com/{name}", "visibility": "public",
            "state": {"value": row["lifecycle"], "assertion": "authoritative"},
            "freshness": args.catalog_freshness, "provenance": ["source:dependency-catalog"],
            "attributes": {"lifecycle": row["lifecycle"], "maturity": row["maturity"], "plane": row["plane"]},
            "extensions": {}})
    relationships = [{"id": "relationship:declared-" + base.digest(
        f"{edge['source']}:{edge['target']}".encode())[:32], "type": "depends-on",
        "source": f"ri:{edge['source']}:repository:{edge['source']}",
        "target": f"ri:{edge['target']}:repository:{edge['target']}", "direction": "directed",
        "assertion": "authoritative", "freshness": args.catalog_freshness,
        "provenance": [source["id"] for source in sources], "extensions": {}} for edge in edges]
    coverage = {domain: {"collection": "uncollected", "freshness": "unknown", "reason": "not_requested",
                         "observed_at": None} for domain in native.DOMAINS}
    return {"schema": "egohygiene.repository-intelligence/v1", "contract_version": "1.0.0-alpha.2",
        "projection_id": f"{args.repository}@{args.source_commit}", "repository": args.repository,
        "represented_commit": args.source_commit, "visibility": "public", "observed_at": args.observed_at,
        "generator": {"name": "egohygiene/relay:declared-dependency-collector", "version": "0.1.0",
                      "contract": "egohygiene.repository-intelligence/v1"},
        "sources": sorted(sources, key=lambda item: item["id"]),
        "entities": sorted(entities, key=lambda item: item["id"]),
        "relationships": sorted(relationships, key=lambda item: item["id"]),
        "events": [], "redactions": [], "extensions": {}, "collection_coverage": coverage}


def collect(args: argparse.Namespace) -> dict:
    args = argparse.Namespace(**vars(args))
    if args.visibility != "public":
        base.fail("VISIBILITY")
    if (not base.REPOSITORY.fullmatch(args.repository) or not base.SHA.fullmatch(args.source_commit)
            or not 1 <= args.maximum_depth <= 8 or not 1 <= args.maximum_catalog_age_days <= 3650
            or not 1 <= args.maximum_age_seconds <= 2678400):
        base.fail("INPUT")
    permitted = allowlist(args.public_repositories)
    if args.repository not in permitted:
        base.fail("VISIBILITY")
    root, runtime = base.safe_path(args.repository_root), base.safe_path(args.runtime)
    if runtime.is_relative_to(root):
        base.fail("PATH")
    args.collected_at = args.collected_at or args.observed_at
    age = (base.utc(args.observed_at) - base.utc(args.collected_at)).total_seconds()
    if age < 0:
        base.fail("INPUT")
    lock, receipt = base.runtime_files(runtime, lock_path=LOCK_PATH)
    owner = runtime / "hygiene_catalog"
    catalog = base.load_json(base.read_file(owner / "catalog/repositories.yaml"))
    # This initial immutable profile supports the pinned public source corpus.
    # It does not admit arbitrary mixed-visibility registries or discoveries.
    if any(item.get("visibility") != "public" for item in catalog["repositories"]):
        base.fail("PIN")
    validation = source_validate(runtime)
    context = base.load_json(base.read_file(owner / "catalog/repository-context.json"))
    register = base.load_json(base.read_file(owner / "catalog/dependency-boundaries.yaml"))
    if register["exceptions"]:
        base.fail("PIN")
    catalog_time = datetime.strptime(catalog["observed_at"], "%Y-%m-%d").replace(tzinfo=UTC)
    if catalog_time > base.utc(args.collected_at):
        base.fail("INPUT")
    args.catalog_freshness = "stale" if ((base.utc(args.observed_at) - catalog_time).days
        > args.maximum_catalog_age_days or age > args.maximum_age_seconds) else "current"
    # Verify the represented consumer object exists without executing checkout
    # files, Git hooks, filters, provider requests or runtime/package scans.
    base.git(root, "cat-file", "commit", args.source_commit, limit=base.MAX_SOURCE)
    nodes, edges, policies = collect_graph(args, catalog, context, register, permitted)
    projection = project(args, nodes, edges, lock["sources"]["hygiene_catalog"]["revision"])
    snapshot, normalized = native.normalize(runtime, projection)
    status = "ready" if snapshot is not None else "invalid"
    diagnostics = [diagnostic("SCOPE"), diagnostic("INTEGRATION")]
    if snapshot is None:
        diagnostics.append(diagnostic("HYGIENE", "hygiene"))
    public_input = {"repositories": [{key: item[key] for key in ("full_name", "lifecycle", "maturity", "plane")}
                                     for item in nodes], "relationships": edges, "policies": policies}
    return {"schema": SCHEMA, "status": status, "publication": "denied", "repository": args.repository,
        "represented_commit": args.source_commit, "observed_at": args.observed_at,
        "inputs": {"collected_at": args.collected_at, "maximum_depth": args.maximum_depth,
            "maximum_catalog_age_days": args.maximum_catalog_age_days, "maximum_age_seconds": args.maximum_age_seconds,
            "catalog_revision": lock["sources"]["hygiene_catalog"]["revision"],
            "catalog_observed_at": catalog["observed_at"], "catalog_freshness": args.catalog_freshness,
            "public_projection_sha256": base.digest(base.json_bytes(public_input))},
        "scope": {"kind": "declared_consumption", "authority": "egohygiene/hygiene", "bounded": True,
            "runtime_adoption": "uncollected", "package_dependencies": "uncollected", "excluded_topology": "uncollected"},
        "runtime": {**receipt, "pins": lock, "collector_sha256": base.digest(Path(__file__).read_bytes()),
                    "shared_runtime_sha256": base.digest(Path(base.__file__).read_bytes()),
                    "normalizer_adapter_sha256": base.digest(Path(native.__file__).read_bytes())},
        "validation": {**validation, **normalized}, "coverage": projection["collection_coverage"],
        "boundary_evidence": policies, "diagnostics": diagnostics,
        "projection_candidate": projection, "snapshot_candidate": snapshot,
        "candidate_digests": {"projection_sha256": base.digest(base.json_bytes(projection)),
                              "snapshot_sha256": base.digest(base.json_bytes(snapshot)) if snapshot else None}}


def write_result(path: Path, result: dict, repository_root: Path) -> None:
    path, consumer = base.safe_path(path), base.safe_path(repository_root)
    if path.is_relative_to(consumer) or path.name != OUTPUT_NAME or (path.exists() and not path.is_file()):
        base.fail("PATH")
    schema = base.load_json(base.read_file(ROOT / "schemas/dependency-collection-review.v1.schema.json"))
    if not jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).is_valid(result):
        base.fail("INPUT")
    content = base.json_bytes(result)
    if len(content) > base.MAX_OUTPUT:
        base.fail("INPUT")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = value.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("prepare", allow_abbrev=False)
    for owner in ("hygiene", "egolint", "observatory"):
        setup.add_argument("--" + owner, type=Path, required=True)
    setup.add_argument("--cargo", type=Path, default=Path("cargo"))
    setup.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("collect", allow_abbrev=False)
    for name in ("runtime", "repository-root", "output"):
        command.add_argument("--" + name, type=Path, required=True)
    for name in ("repository", "visibility", "source-commit", "observed-at", "public-repositories"):
        command.add_argument("--" + name, required=True)
    command.add_argument("--collected-at")
    command.add_argument("--maximum-depth", type=int, default=2)
    command.add_argument("--maximum-catalog-age-days", type=int, default=30)
    command.add_argument("--maximum-age-seconds", type=int, default=86400)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "prepare":
            base.prepare(args, lock_path=LOCK_PATH, reproducible=True)
            return 0
        result = collect(args)
        write_result(args.output, result, args.repository_root)
        print("Declared dependency collection retained for review; publication denied")
        return 0 if result["status"] == "ready" else 2
    except (base.CollectorError, OSError, ValueError, KeyError, TypeError, ImportError,
            yaml.YAMLError, RecursionError):
        error = sys.exception()
        code = str(error) if isinstance(error, base.CollectorError) and str(error) in MESSAGES else "INPUT"
        if args.command == "collect":
            try:
                owner = "hygiene" if code in {"CATALOG", "ENDPOINT", "BOUNDARY"} else "relay"
                write_result(args.output, {"schema": SCHEMA, "status": "denied", "publication": "denied",
                                          "diagnostics": [diagnostic(code, owner)]}, args.repository_root)
            except (base.CollectorError, OSError):
                pass
        print("Declared dependency collector: " + code, file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
