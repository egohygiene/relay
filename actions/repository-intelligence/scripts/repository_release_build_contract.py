#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Bind fresh release/deployment collection to a closed native build receipt."""

from __future__ import annotations

from datetime import datetime, UTC
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "egohygiene.relay.source-release-build/v1"
DOMAINS = ("releases", "deployments")
CONTRIBUTED_DOMAINS = (*DOMAINS, "git", "history")
SHA = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")
STATUSES = {"ready", "partial", "stale", "unavailable", "uncollected", "not_applicable"}
INVENTORIES = {"complete", "truncated", "filtered", "incomplete", "denied", "unavailable",
               "failed", "uncollected", "not_applicable"}
UNCOLLECTED = {"collection": "uncollected", "freshness": "unknown", "reason": "not_requested", "observed_at": None}
RELAY_FILES = (
    "actions/repository-intelligence/scripts/collect_repository_releases.py",
    "actions/repository-intelligence/scripts/collect_repository_roadmap.py",
    "actions/repository-intelligence/scripts/collect_repository_adrs.py",
    "actions/repository-intelligence/scripts/repository_adr_inputs.py",
    "actions/repository-intelligence/contracts/release-collector.v1.lock.json",
    "actions/repository-intelligence/contracts/roadmap-collector-requirements.txt",
    "actions/repository-intelligence/schemas/release-provider-capture.v1.schema.json",
    "actions/repository-intelligence/schemas/release-collection-review.v1.schema.json",
    "actions/repository-intelligence-deployment-provenance/schemas/deployment-receipt.schema.json",
)


def require(value):
    if not value:
        raise ValueError("Release source build provenance is incompatible")


def digest(content):
    return hashlib.sha256(content).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()


def instant(value):
    require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value))
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def implementation():
    """Match the existing collector's exact executed-helper binding."""
    repository_root = ROOT.parents[1]
    return {path: digest((repository_root / path).read_bytes()) for path in RELAY_FILES}


def input_contracts():
    return {"provider_capture": digest((ROOT / "schemas/release-provider-capture.v1.schema.json").read_bytes()),
            "review": digest((ROOT / "schemas/release-collection-review.v1.schema.json").read_bytes()),
            "deployment_receipt": digest((ROOT.parent / "repository-intelligence-deployment-provenance/schemas/deployment-receipt.schema.json").read_bytes())}


def from_result(result):
    """Use only an in-memory result from a fresh trusted collector invocation."""
    require(result["schema"] == "egohygiene.relay.release-collection-review/v1"
        and result["publication"] == "denied" and result["status"] in STATUSES
        and isinstance(result["projection_candidate"], dict) and isinstance(result["snapshot_candidate"], dict)
        and result["validation"] == {"hygiene": "valid", "coverage": "valid", "observatory": "normalized"})
    projection, snapshot = result["projection_candidate"], result["snapshot_candidate"]
    require(projection["collection_coverage"] == snapshot["coverage"]["domains"] == result["coverage"]
        and projection["repository"] == result["repository"] == snapshot["repository"]["key"]
        and projection["represented_commit"] == result["represented_commit"] == snapshot["represented_commit"]
        and projection["observed_at"] == result["observed_at"] == snapshot["observed_at"])
    counts = {domain: sum(item["kind"] == kind for item in projection["entities"])
              for domain, kind in (("releases", "release"), ("deployments", "deployment"), ("git", "commit"))}
    counts["history"] = len(projection["events"])
    require(result["candidate_digests"] == {"projection_sha256": digest(encoded(projection)),
        "snapshot_sha256": digest(encoded(snapshot))})
    receipt = {"schema": SCHEMA, "kind": "releases", "admission": "fresh-captured-input",
        "repository": result["repository"], "source_commit": result["represented_commit"],
        "generator_commit": result["generator_commit"], "observed_at": result["observed_at"],
        "status": result["status"], "inputs": {**result["inputs"], "record_counts": counts,
            "commit_revisions": sorted(item["attributes"]["sha"] for item in projection["entities"] if item["kind"] == "commit"),
                                                "contracts": input_contracts()},
        "runtime": result["runtime"], "validation": result["validation"], "coverage": result["coverage"],
        "diagnostics": [{"code": item["code"], "owner": item["owner"]} for item in result["diagnostics"]],
        "candidate_digests": result["candidate_digests"]}
    validate(receipt, receipt["repository"], receipt["source_commit"], receipt["observed_at"])
    return receipt


def inventory_claim(value, count, observed, maximum_age):
    require(isinstance(value, dict) and set(value) == {"status", "observed_at", "pages_captured", "pagination_complete"}
        and value["status"] in INVENTORIES and type(value["pages_captured"]) is int
        and 0 <= value["pages_captured"] <= 10000 and type(value["pagination_complete"]) is bool)
    state, captured = value["status"], value["observed_at"]
    if state in {"complete", "truncated", "filtered", "incomplete", "not_applicable"}:
        captured_instant = instant(captured)
        require(captured_instant <= observed)
        freshness = "stale" if (observed - captured_instant).total_seconds() > maximum_age else "current"
        if state == "not_applicable":
            require(count == 0 and value["pages_captured"] == 0 and value["pagination_complete"] is False)
            return {"collection": "not_applicable", "freshness": "not_applicable",
                    "reason": "explicit_not_applicable", "observed_at": captured}
        require(value["pages_captured"] > 0 and (state != "complete" or value["pagination_complete"] is True)
            and (state != "truncated" or value["pagination_complete"] is False))
        return {"collection": ("observed" if count else "observed_empty") if state == "complete" else "partial",
                "freshness": freshness, "reason": "complete" if state == "complete" else state, "observed_at": captured}
    require(captured is None and count == 0 and value["pages_captured"] == 0 and value["pagination_complete"] is False)
    collection, reason = {"denied": ("unavailable", "access_denied"),
        "unavailable": ("unavailable", "provider_unavailable"), "failed": ("failed", "collection_failed"),
        "uncollected": ("uncollected", "not_requested")}[state]
    return {"collection": collection, "freshness": "unknown", "reason": reason, "observed_at": None}


def validate(value, repository, source_commit, observed_at):
    """Verify a bounded public receipt without loading native or consumer code."""
    require(isinstance(value, dict) and set(value) == {"schema", "kind", "admission", "repository",
        "source_commit", "generator_commit", "observed_at", "status", "inputs", "runtime", "validation",
        "coverage", "diagnostics", "candidate_digests"})
    require(value["schema"] == SCHEMA and value["kind"] == "releases" and value["admission"] == "fresh-captured-input"
        and value["repository"] == repository and isinstance(repository, str)
        and re.fullmatch(r"egohygiene/(?:\.github|[a-z0-9][a-z0-9.-]*)", repository)
        and value["source_commit"] == source_commit and isinstance(source_commit, str) and SHA.fullmatch(source_commit)
        and isinstance(value["generator_commit"], str) and SHA.fullmatch(value["generator_commit"])
        and value["observed_at"] == observed_at and value["status"] in STATUSES)
    observed = instant(observed_at)
    require(value["validation"] == {"hygiene": "valid", "coverage": "valid", "observatory": "normalized"})
    raw_lock = (ROOT / "contracts/release-collector.v1.lock.json").read_bytes()
    runtime = value["runtime"]
    require(isinstance(runtime, dict) and set(runtime) == {"lock_sha256", "egolint_sha256", "pins", "relay_files_sha256"}
        and runtime["lock_sha256"] == digest(raw_lock) and runtime["pins"] == json.loads(raw_lock)
        and isinstance(runtime["egolint_sha256"], str) and SHA256.fullmatch(runtime["egolint_sha256"])
        and runtime["relay_files_sha256"] == implementation())
    inputs = value["inputs"]
    require(isinstance(inputs, dict) and set(inputs) == {"capture_sha256", "receipt_sha256", "public_environments",
        "maximum_age_seconds", "inventory", "record_counts", "commit_revisions", "contracts"}
        and type(inputs["maximum_age_seconds"]) is int and 1 <= inputs["maximum_age_seconds"] <= 2678400
        and inputs["contracts"] == input_contracts())
    selected = inputs["receipt_sha256"]
    require(isinstance(selected, list) and len(selected) <= 256
        and all(isinstance(item, str) and SHA256.fullmatch(item) for item in selected)
        and selected == sorted(set(selected)))
    environments = inputs["public_environments"]
    require(isinstance(environments, list) and len(environments) <= 64
        and all(isinstance(item, str) and 1 <= len(item) <= 64 and item == item.strip()
                and re.fullmatch(r"[A-Za-z0-9._ -]+", item) for item in environments)
        and environments == sorted(set(environments)))
    counts = inputs["record_counts"]
    require(isinstance(counts, dict) and set(counts) == set(CONTRIBUTED_DOMAINS)
        and all(type(count) is int and 0 <= count <= (256 if name in DOMAINS else 512) for name, count in counts.items()))
    total = counts["releases"] + counts["deployments"]
    revisions = inputs["commit_revisions"]
    require(isinstance(revisions, list) and len(revisions) == counts["git"]
        and all(isinstance(item, str) and SHA.fullmatch(item) for item in revisions)
        and revisions == sorted(set(revisions)))
    require((counts["git"] == 0 if total == 0 else 1 <= counts["git"] <= total)
        and counts["releases"] <= counts["history"] <= total and len(selected) <= counts["deployments"]
        and (not counts["deployments"] or bool(environments)))
    spec = importlib.util.spec_from_file_location("relay_release_receipt_coverage", Path(__file__).with_name("repository_intelligence_coverage.py"))
    coverage_contract = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(coverage_contract)
    coverage_contract.validate_domains(value["coverage"], observed_at)
    coverage, inventory = value["coverage"], inputs["inventory"]
    if inventory is None:
        require(inputs["capture_sha256"] is None and total == 0 and not selected)
        for domain in DOMAINS:
            require(coverage[domain] == {"collection": "unavailable", "freshness": "unknown",
                "reason": "provider_unavailable", "observed_at": None})
    else:
        require(isinstance(inputs["capture_sha256"], str) and SHA256.fullmatch(inputs["capture_sha256"])
            and isinstance(inventory, dict) and set(inventory) == set(DOMAINS))
        for domain in DOMAINS:
            require(coverage[domain] == inventory_claim(inventory[domain], counts[domain], observed, inputs["maximum_age_seconds"]))
    active = [coverage[domain] for domain in DOMAINS if counts[domain]]
    for domain in ("git", "history"):
        expected = {"collection": "partial", "reason": "filtered",
            "freshness": "stale" if any(claim["freshness"] == "stale" for claim in active) else "current",
            "observed_at": max(claim["observed_at"] for claim in active)} if counts[domain] else UNCOLLECTED
        require(coverage[domain] == expected)
    require(all(claim == UNCOLLECTED for domain, claim in coverage.items() if domain not in CONTRIBUTED_DOMAINS))
    diagnostics = value["diagnostics"]
    require(isinstance(diagnostics, list) and len(diagnostics) <= 256)
    require(all(isinstance(item, dict) and set(item) == {"code", "owner"}
        and item["code"] == "TARGET" and item["owner"] == "relay" for item in diagnostics))
    require(not diagnostics or counts["deployments"] > 0 and len(diagnostics) <= counts["deployments"]
        and coverage["releases"]["collection"] not in {"observed", "observed_empty"})
    states = {coverage[domain]["collection"] for domain in DOMAINS}
    expected_status = ("partial" if "partial" in states or diagnostics else "not_applicable" if states == {"not_applicable"}
        else "uncollected" if states == {"uncollected"} else "unavailable" if states & {"unavailable", "failed", "uncollected"}
        else "stale" if any(coverage[domain]["freshness"] == "stale" for domain in DOMAINS) else "ready")
    require(value["status"] == expected_status)
    digests = value["candidate_digests"]
    require(isinstance(digests, dict) and set(digests) == {"projection_sha256", "snapshot_sha256"}
        and all(isinstance(item, str) and SHA256.fullmatch(item) for item in digests.values()))
    return value
