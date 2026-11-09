#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Verify the bounded public declaration receipt without native owner execution."""

from datetime import datetime, UTC
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "egohygiene.relay.source-dependency-build/v1"
DOMAINS = ("roadmap", "decisions", "git", "issues", "pull_requests", "checks", "releases", "deployments", "history")
SHA = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")
UNCOLLECTED = {"collection": "uncollected", "freshness": "unknown", "reason": "not_requested", "observed_at": None}
FILES = ("collect_repository_dependency_source.py", "collect_repository_dependencies.py", "public_catalog_admission.py",
         "repository_dependency_build_contract.py", "collect_repository_roadmap.py", "collect_repository_adrs.py",
         "repository_adr_inputs.py")
PUBLIC_FILES = ("contracts/public-catalog-admission.v1.lock.json", "contracts/public-repositories.hygiene-49639c1.json",
                "contracts/public-dependency-declarations.hygiene-49639c1.json", "schemas/dependency-source-build.v1.schema.json")
SCOPE = {"kind": "declared_consumption", "authority": "egohygiene/hygiene", "bounded": True,
         "runtime_adoption": "uncollected", "package_dependencies": "uncollected", "excluded_topology": "uncollected"}


def require(value):
    if not value:
        raise ValueError("Dependency source build provenance is incompatible")


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def digest(content):
    return hashlib.sha256(content).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()


def instant(value):
    require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value))
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def implementation():
    return {**{filename: digest((ROOT / "scripts" / filename).read_bytes()) for filename in FILES},
            **{filename: digest((ROOT / filename).read_bytes()) for filename in PUBLIC_FILES}}


def validate(value, repository, source_commit, observed_at):
    require(isinstance(value, dict) and set(value) == {"schema", "kind", "admission", "repository",
        "source_commit", "observed_at", "status", "inputs", "runtime", "validation", "coverage", "candidate_digests"})
    require(value["schema"] == SCHEMA and value["kind"] == "dependencies"
        and value["admission"] == "fresh-owner-declarations" and value["repository"] == repository
        and isinstance(repository, str) and re.fullmatch(r"egohygiene/(?:\.github|[a-z0-9][a-z0-9.-]*)", repository)
        and value["source_commit"] == source_commit and isinstance(source_commit, str) and SHA.fullmatch(source_commit)
        and value["observed_at"] == observed_at and value["status"] in {"ready", "stale"})
    observed = instant(observed_at)
    require(value["validation"] == {"hygiene": "valid", "coverage": "valid", "observatory": "normalized"}
        and value["coverage"] == {domain: UNCOLLECTED for domain in DOMAINS})
    runtime = value["runtime"]
    raw_lock = (ROOT / "contracts/adr-collector.v1.lock.json").read_bytes()
    require(isinstance(runtime, dict) and set(runtime) == {"lock_sha256", "egolint_sha256", "pins", "relay_files_sha256"}
        and runtime["pins"] == json.loads(raw_lock) and runtime["lock_sha256"] == digest(raw_lock)
        and isinstance(runtime["egolint_sha256"], str) and SHA256.fullmatch(runtime["egolint_sha256"])
        and runtime["relay_files_sha256"] == implementation())
    inputs = value["inputs"]
    require(isinstance(inputs, dict) and set(inputs) == {"catalog_admission", "authorized_repositories",
        "declaration_reference_sha256", "public_evidence", "public_evidence_sha256",
        "declarations_observed_at", "maximum_depth", "maximum_catalog_age_days", "catalog_freshness", "scope"}
        and type(inputs["maximum_depth"]) is int and 1 <= inputs["maximum_depth"] <= 8
        and type(inputs["maximum_catalog_age_days"]) is int and 1 <= inputs["maximum_catalog_age_days"] <= 3650
        and encoded(inputs["scope"]) == encoded(SCOPE))
    evidence = inputs["public_evidence"]
    require(isinstance(evidence, dict) and set(evidence) == {"repositories", "relationships", "boundary_evidence"})
    catalog = module("relay_dependency_receipt_public_catalog", "public_catalog_admission.py")
    # Authenticate visibility/membership before reading endpoint identity.
    authorized_rows = catalog.validate_identities(inputs["authorized_repositories"], inputs["catalog_admission"])
    catalog.validate_rows(evidence["repositories"])
    authorized = {row["full_name"] for row in authorized_rows}
    captured = instant(inputs["catalog_admission"]["observed_at"])
    require(isinstance(inputs["declarations_observed_at"], str)
        and re.fullmatch(r"\d{4}-\d{2}-\d{2}", inputs["declarations_observed_at"]))
    declared = datetime.strptime(inputs["declarations_observed_at"], "%Y-%m-%d").replace(tzinfo=UTC)
    declaration_pin = json.loads((ROOT / "contracts/dependency-source.v1.lock.json").read_bytes())
    require(inputs["declarations_observed_at"] == declaration_pin["declarations_observed_at"]
        and inputs["catalog_admission"]["revision"] == declaration_pin["revision"])
    reference_bytes = (ROOT / "contracts/public-dependency-declarations.hygiene-49639c1.json").read_bytes()
    require(inputs["declaration_reference_sha256"] == declaration_pin["public_reference_sha256"] == digest(reference_bytes))
    reference = json.loads(reference_bytes)
    require(reference["owner"] == "egohygiene/hygiene" and reference["revision"] == declaration_pin["revision"]
        and reference["declarations_observed_at"] == inputs["declarations_observed_at"]
        and reference["public_catalog_sha256"] == inputs["catalog_admission"]["artifact_sha256"])
    require(declared <= observed and captured <= observed)
    freshness = ("stale" if (observed - declared).days > inputs["maximum_catalog_age_days"]
                 or (observed - captured).days > inputs["maximum_catalog_age_days"] else "current")
    require(inputs["catalog_freshness"] == freshness
        and value["status"] == ("stale" if freshness == "stale" else "ready"))
    names = {row["full_name"] for row in evidence["repositories"]}
    require(repository in names and names <= authorized)
    edges, policies = evidence["relationships"], evidence["boundary_evidence"]
    require(isinstance(edges, list) and len(edges) <= 2048 and isinstance(policies, list) and len(policies) == len(edges))
    pairs = []
    for edge in edges:
        require(isinstance(edge, dict) and set(edge) == {"source", "target"}
            and isinstance(edge["source"], str) and isinstance(edge["target"], str)
            and edge["source"] in names and edge["target"] in names and edge["source"] != edge["target"])
        pairs.append((edge["source"], edge["target"]))
    require(pairs == sorted(set(pairs)))
    for pair, record in zip(pairs, policies):
        require(isinstance(record, dict) and set(record) == {"source", "target", "policies"}
            and (record["source"], record["target"]) == pair
            and isinstance(record["policies"], list) and 1 <= len(record["policies"]) <= 256)
        identifiers = []
        for policy in record["policies"]:
            require(isinstance(policy, dict) and set(policy) == {"id", "contract", "contract_status", "pinning"}
                and isinstance(policy["id"], str) and re.fullmatch(r"RELATIONSHIP-[0-9]{3}", policy["id"])
                and (policy["contract"] is None or isinstance(policy["contract"], str) and 1 <= len(policy["contract"]) <= 2048)
                and policy["contract_status"] in {"active", "required"}
                and policy["pinning"] in {"immutable", "immutable-or-versioned", "versioned"})
            identifiers.append(policy["id"])
        require(identifiers == sorted(set(identifiers)))
    # Independently verify exact direct declarations from the public-only
    # reference. It is a transport mirror of immutable authored facts, not a
    # canonical registry or an inferred graph. Authorization precedes lookup.
    reached, frontier, expected = {repository}, {repository}, {}
    for _depth in range(inputs["maximum_depth"]):
        following = set()
        for declaration in reference["declarations"]:
            source, target = declaration["source"], declaration["target"]
            if source not in frontier or source not in authorized or target not in authorized:
                continue
            require(not declaration["forbidden"] and bool(declaration["policies"]))
            expected[(source, target)] = {"source": source, "target": target, "policies": declaration["policies"]}
            if target not in reached:
                following.add(target)
            reached.add(target)
        frontier = following
    require(reached == names and pairs == sorted(expected)
        and encoded(policies) == encoded([expected[pair] for pair in sorted(expected)]))
    require(inputs["public_evidence_sha256"] == digest(encoded(evidence)))
    digests = value["candidate_digests"]
    require(isinstance(digests, dict) and set(digests) == {"projection_sha256", "snapshot_sha256"}
        and all(isinstance(item, str) and SHA256.fullmatch(item) for item in digests.values()))
    return value
