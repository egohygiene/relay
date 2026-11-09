#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Collect admitted public declared dependencies for a fresh native build.

The review collector remains unchanged. This adapter reuses its direct-edge
mapping over an exact public catalog admission and selected owner declarations.
It never accepts a previously generated review envelope as a source.
"""

from __future__ import annotations

import argparse
from datetime import datetime, UTC
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "contracts/dependency-source.v1.lock.json"


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


review = module("relay_production_dependency_mapping", "collect_repository_dependencies.py")
native, base = review.native, review.base
admission = module("relay_dependency_public_catalog", "public_catalog_admission.py")
contract = module("relay_dependency_build_contract", "repository_dependency_build_contract.py")


def require(value):
    if not value:
        raise ValueError("Dependency source admission is incompatible")


def owner_documents(root):
    """Read exact immutable owner objects; raw mixed-source hashes stay private."""
    pin = base.load_json(base.read_file(LOCK_PATH))
    public_pin = admission.lock()
    require(pin["owner"] == public_pin["owner"] and pin["revision"] == public_pin["revision"]
        and pin["tree"] == public_pin["tree"])
    require(base.git(root, "rev-parse", pin["revision"] + "^{tree}").decode().strip() == pin["tree"])
    documents = {}
    for path, checksum in pin["files"].items():
        content = base.git_blob(root, pin["revision"], path, base.MAX_OUTPUT)
        require(base.digest(content) == checksum)
        documents[path] = base.load_json(content)
    return pin, documents


def selected_declarations(documents, rows):
    """Select public identities before inspecting declarations or boundaries."""
    permitted = {row["full_name"]: row for row in rows}
    catalog = documents["catalog/repositories.yaml"]
    schema = documents["schemas/repository-catalog.v1.schema.json"]
    validator = jsonschema.Draft202012Validator({"$ref": "#/$defs/repository", "$defs": schema["$defs"]},
                                               format_checker=jsonschema.FormatChecker())
    selected = []
    for item in catalog["repositories"]:
        if not isinstance(item, dict) or item.get("visibility") != "public":
            continue
        name = item.get("full_name")
        if not isinstance(name, str) or name not in permitted:
            continue
        require(validator.is_valid(item) and "target_name" not in item)
        public = permitted[name]
        require(item["name"] == public["name"] and item["source_url"] == public["source_url"]
            and all(item[field] == public["role"][field] for field in
                    ("plane", "lifecycle", "maturity", "owns", "excludes", "outputs")))
        selected.append(item)
    require(len(selected) == len(permitted) and len({item["full_name"] for item in selected}) == len(selected))
    context = documents["catalog/repository-context.json"]
    require(context.get("schema_version") == "2.0.0" and context.get("architecture_release") == catalog["architecture_release"]
        and isinstance(context.get("dependency_sources"), dict))
    # Only consumed terms attached to already admitted public rows are read.
    mapping = {}
    for row in selected:
        for term in row["consumes"]:
            values = context["dependency_sources"].get(term)
            require(isinstance(values, list))
            mapping[term] = sorted({name for name in values if isinstance(name, str) and name in permitted})
    raw = documents["catalog/dependency-boundaries.yaml"]
    require(raw.get("architecture_release") == catalog["architecture_release"])
    boundary_schema = documents["schemas/dependency-boundary-register.v1.schema.json"]
    relationship_validator = jsonschema.Draft202012Validator(
        {"$ref": "#/$defs/relationship", "$defs": boundary_schema["$defs"]},
        format_checker=jsonschema.FormatChecker())
    relationships = []
    for item in raw["relationships"]:
        if not isinstance(item, dict) or item.get("producer") not in permitted:
            continue
        consumers = item.get("consumers")
        require(isinstance(consumers, list))
        consumers = [name for name in consumers if isinstance(name, str)
                     and (name in permitted or name == "egohygiene/*")]
        if not consumers:
            continue
        selected_item = {**item, "consumers": consumers}
        require(relationship_validator.is_valid(selected_item))
        relationships.append(selected_item)
    forbidden = [item for item in raw["forbidden_dependencies"] if isinstance(item, dict)
                 and item.get("source") in permitted and item.get("target") in permitted]
    # No exception is silently promoted to an approved integration. The pinned
    # owner corpus has none; a selected future exception requires a new adapter.
    require(not any(isinstance(item, dict) and isinstance(item.get("affected_repositories"), list)
        and any(name in permitted for name in item["affected_repositories"] if isinstance(name, str))
        for item in raw["exceptions"]))
    return {"repositories": selected}, {"dependency_sources": mapping}, {
        "relationships": relationships, "forbidden_dependencies": forbidden}, catalog["observed_at"]


def collect(args):
    """Return fresh canonical projection, normalized snapshot and public receipt.

    Required args: runtime, catalog_root, repository_root, repository, visibility,
    source_commit, observed_at. Optional public_repositories is a JSON list;
    maximum_depth defaults to 1 and maximum_catalog_age_days defaults to 30.
    """
    args = argparse.Namespace(**vars(args))
    args.maximum_depth = getattr(args, "maximum_depth", 1)
    args.maximum_catalog_age_days = getattr(args, "maximum_catalog_age_days", 30)
    require(args.visibility == "public" and isinstance(args.repository, str) and base.REPOSITORY.fullmatch(args.repository)
        and isinstance(args.source_commit, str) and base.SHA.fullmatch(args.source_commit)
        and type(args.maximum_depth) is int and 1 <= args.maximum_depth <= 8
        and type(args.maximum_catalog_age_days) is int and 1 <= args.maximum_catalog_age_days <= 3650)
    observed = contract.instant(args.observed_at)
    root, runtime, source = (base.safe_path(Path(value)) for value in
                             (args.repository_root, args.runtime, args.catalog_root))
    require(not runtime.is_relative_to(root) and not source.is_relative_to(root)
        and not runtime.is_relative_to(source) and not source.is_relative_to(runtime))
    selection = getattr(args, "public_repositories", None)
    requested = None if selection is None else review.allowlist(selection)
    # Admit public inventory before resolving any declared source or endpoint.
    rows, metadata = admission.load(source, requested)
    require(args.repository in {row["full_name"] for row in rows})
    lock, runtime_receipt = base.runtime_files(runtime, lock_path=native.LOCK_PATH)
    pin, documents = owner_documents(source)
    catalog, context, register, declaration_date = selected_declarations(documents, rows)
    require(declaration_date == pin["declarations_observed_at"])
    declared = datetime.strptime(declaration_date, "%Y-%m-%d").replace(tzinfo=UTC)
    captured = contract.instant(metadata["observed_at"])
    require(declared <= observed and captured <= observed)
    args.collected_at = args.observed_at
    args.catalog_freshness = ("stale" if (observed - declared).days > args.maximum_catalog_age_days
                              or (observed - captured).days > args.maximum_catalog_age_days else "current")
    base.git(root, "cat-file", "commit", args.source_commit, limit=base.MAX_SOURCE)
    permitted = [row["full_name"] for row in rows]
    nodes, edges, policies = review.collect_graph(args, catalog, context, register, permitted)
    projection = review.project(args, nodes, edges, pin["revision"])
    projection["generator"]["name"] = "egohygiene/relay:declared-dependency-source"
    # Catalog lifecycle is authored architectural context, not execution state.
    # Keep root identity identical to other source adapters for safe composition.
    for entity in projection["entities"]:
        entity["state"] = {"value": "unknown", "assertion": "unknown"}
        if entity["repository"] == args.repository:
            entity["freshness"], entity["attributes"] = "unknown", {}
    snapshot, validation = native.normalize(runtime, projection)
    require(snapshot is not None and validation == {"hygiene": "valid", "coverage": "valid", "observatory": "normalized"})
    visited = {row["full_name"] for row in nodes}
    selected_rows = [row for row in rows if row["full_name"] in visited]
    public_evidence = {"repositories": selected_rows, "relationships": edges, "boundary_evidence": policies}
    receipt = {"schema": contract.SCHEMA, "kind": "dependencies", "admission": "fresh-owner-declarations",
        "repository": args.repository, "source_commit": args.source_commit, "observed_at": args.observed_at,
        "status": "stale" if args.catalog_freshness == "stale" else "ready",
        "inputs": {"catalog_admission": metadata, "authorized_repositories": permitted,
            "declaration_reference_sha256": pin["public_reference_sha256"], "public_evidence": public_evidence,
            "public_evidence_sha256": base.digest(base.json_bytes(public_evidence)),
            "declarations_observed_at": declaration_date, "maximum_depth": args.maximum_depth,
            "maximum_catalog_age_days": args.maximum_catalog_age_days,
            "catalog_freshness": args.catalog_freshness,
            "scope": {"kind": "declared_consumption", "authority": "egohygiene/hygiene", "bounded": True,
                "runtime_adoption": "uncollected", "package_dependencies": "uncollected", "excluded_topology": "uncollected"}},
        "runtime": {**runtime_receipt, "pins": lock, "relay_files_sha256": contract.implementation()},
        "validation": validation, "coverage": projection["collection_coverage"],
        "candidate_digests": {"projection_sha256": base.digest(base.json_bytes(projection)),
            "snapshot_sha256": base.digest(base.json_bytes(snapshot))}}
    contract.validate(receipt, args.repository, args.source_commit, args.observed_at)
    schema = base.load_json(base.read_file(ROOT / "schemas/dependency-source-build.v1.schema.json"))
    require(jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).is_valid(receipt))
    return {"projection": projection, "snapshot": snapshot, "receipt": receipt}


def write_result(target, result, args):
    target = base.safe_path(Path(target))
    for source in (args.repository_root, args.runtime, args.catalog_root):
        require(not target.is_relative_to(base.safe_path(Path(source))))
    require(not target.exists())
    target.mkdir(mode=0o700, parents=True)
    try:
        for name, value in result.items():
            content = base.json_bytes(value)
            require(len(content) <= base.MAX_OUTPUT)
            descriptor, temporary = tempfile.mkstemp(dir=target)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(content)
                os.replace(temporary, target / (name + ".json"))
            finally:
                Path(temporary).unlink(missing_ok=True)
    except (OSError, ValueError):
        for name in ("projection", "snapshot", "receipt"):
            (target / (name + ".json")).unlink(missing_ok=True)
        raise


def parser():
    result = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ("runtime", "catalog-root", "repository-root", "output-directory"):
        result.add_argument("--" + name, type=Path, required=True)
    for name in ("repository", "visibility", "source-commit", "observed-at"):
        result.add_argument("--" + name, required=True)
    result.add_argument("--public-repositories")
    result.add_argument("--maximum-depth", type=int, default=1)
    result.add_argument("--maximum-catalog-age-days", type=int, default=30)
    return result


def main():
    args = parser().parse_args()
    try:
        write_result(args.output_directory, collect(args), args)
        print("Dependencies source: validated public declarations prepared")
        return 0
    except (ValueError, OSError, KeyError, TypeError, ImportError, RecursionError):
        print("Dependencies source: admission unavailable; inspect the reviewed public source profile", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
