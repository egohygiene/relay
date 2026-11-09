#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Bind freshly evaluated Work/Health captures to the native source build plan."""

from __future__ import annotations

from datetime import datetime, UTC
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "egohygiene.relay.source-capture-build/v1"
SOURCE_DOMAINS = {"work": ("issues", "pull_requests"), "health": ("checks",)}
SHA256 = re.compile(r"[0-9a-f]{64}")
STATUSES = {
    "work": {"ready", "partial", "stale", "unavailable", "uncollected", "failed"},
    "health": {"ready", "partial", "unavailable", "uncollected", "failed", "not_applicable"},
}
HEALTH_PRODUCERS = {"osv", "megalinter", "scorecard", "github-check-runs"}
UNCOLLECTED = {"collection": "uncollected", "freshness": "unknown", "reason": "not_requested", "observed_at": None}


def require(value):
    if not value:
        raise ValueError("Captured source build provenance is incompatible")


def digest(content):
    return hashlib.sha256(content).hexdigest()


def artifact_digest(name):
    return digest((ROOT / name).read_bytes())


def lock(kind):
    path = ROOT / "contracts" / (kind + "-collector.v1.lock.json")
    return path.read_bytes(), json.loads(path.read_bytes())


def instant(value):
    require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value))
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def input_contracts(kind, selected_lock):
    return {"review": artifact_digest("schemas/" + kind + "-collection-review.v1.schema.json"),
            **({"provider_capture": artifact_digest("schemas/work-provider-capture.v1.schema.json")}
               if kind == "work" else {"report_summary": selected_lock["report_summary"]["schema_sha256"]})}


def from_result(kind, result):
    """Project bounded receipt fields after fresh collection; never read a review file."""
    require(kind in SOURCE_DOMAINS and result["publication"] == "denied"
        and result["schema"] == f"egohygiene.relay.{kind}-collection-review/v1"
        and result["snapshot_candidate"] is not None
        and result["validation"] == {"hygiene": "valid", "coverage": "valid", "observatory": "normalized"})
    original = result["inputs"]
    if kind == "work":
        times = [claim["observed_at"] for name, claim in result["coverage"].items()
                 if name in SOURCE_DOMAINS[kind] and claim["observed_at"] is not None]
        captures = [{"producer": "work-capture", "status": "admitted", "sha256": original["provider_sha256"],
                     "observed_at": min(times) if times else None, "expires_at": None}]
        scope = "provider-inventories"
    else:
        captures = [{"producer": item["producer"], "status": item["status"], "sha256": item["sha256"],
                     "observed_at": item.get("observed_at") or item.get("generated_at"),
                     "expires_at": item.get("expires_at")} for item in original["captures"]]
        scope = original["inventory"]
    runtime = result["runtime"]
    normalizer = runtime["normalizer_adapter_sha256"] if kind == "work" else runtime["normalization_sha256"]
    receipt = {"schema": SCHEMA, "kind": kind, "admission": "fresh-captured-input",
        "repository": result["repository"], "source_commit": result["represented_commit"],
        "observed_at": result["observed_at"], "status": result["status"],
        "inputs": {"scope": scope, "maximum_age_seconds": original["maximum_age_seconds"],
                   "captures": captures, "contracts": input_contracts(kind, runtime["pins"])},
        "runtime": {key: runtime[key] for key in ("lock_sha256", "egolint_sha256", "pins", "collector_sha256", "shared_runtime_sha256")},
        "validation": result["validation"], "coverage": result["coverage"],
        "diagnostics": [{"code": item["code"], "owner": item["owner"], "producer": item.get("producer")}
                        for item in result["diagnostics"]],
        "candidate_digests": result["candidate_digests"]}
    receipt["runtime"]["normalizer_sha256"] = normalizer
    validate(receipt, kind, receipt["repository"], receipt["source_commit"], receipt["observed_at"])
    return receipt


def validate(value, kind, repository, source_commit, observed_at):
    """Stdlib validation remains usable by the ordinary bundle verifier."""
    require(kind in SOURCE_DOMAINS and isinstance(value, dict) and set(value) == {
        "schema", "kind", "admission", "repository", "source_commit", "observed_at", "status",
        "inputs", "runtime", "validation", "coverage", "diagnostics", "candidate_digests"})
    require(value["schema"] == SCHEMA and value["kind"] == kind and value["admission"] == "fresh-captured-input"
        and value["repository"] == repository and value["source_commit"] == source_commit
        and value["observed_at"] == observed_at and value["status"] in STATUSES[kind])
    observed = instant(observed_at)
    require(value["validation"] == {"hygiene": "valid", "coverage": "valid", "observatory": "normalized"})
    raw_lock, selected_lock = lock(kind)
    runtime = value["runtime"]
    require(isinstance(runtime, dict) and set(runtime) == {"lock_sha256", "egolint_sha256", "pins",
        "collector_sha256", "shared_runtime_sha256", "normalizer_sha256"})
    require(runtime["pins"] == selected_lock and runtime["lock_sha256"] == digest(raw_lock)
        and runtime["collector_sha256"] == artifact_digest("scripts/collect_repository_" + kind + ".py")
        and runtime["shared_runtime_sha256"] == artifact_digest("scripts/collect_repository_roadmap.py")
        and runtime["normalizer_sha256"] == artifact_digest("scripts/collect_repository_adrs.py")
        and isinstance(runtime["egolint_sha256"], str) and SHA256.fullmatch(runtime["egolint_sha256"]))
    inputs = value["inputs"]
    require(isinstance(inputs, dict) and set(inputs) == {"scope", "maximum_age_seconds", "captures", "contracts"}
        and inputs["scope"] in ({"provider-inventories"} if kind == "work" else {"partial", "complete", "not-applicable"})
        and type(inputs["maximum_age_seconds"]) is int and 1 <= inputs["maximum_age_seconds"] <= 2678400
        and inputs["contracts"] == input_contracts(kind, selected_lock))
    captures = inputs["captures"]
    require(isinstance(captures, list) and 1 <= len(captures) <= (1 if kind == "work" else 4))
    seen = set()
    for capture in captures:
        require(isinstance(capture, dict) and set(capture) == {"producer", "status", "sha256", "observed_at", "expires_at"})
        producer = capture["producer"]
        require(producer in ({"work-capture"} if kind == "work" else HEALTH_PRODUCERS) and producer not in seen)
        seen.add(producer)
        state = capture["status"]
        require(state in {"admitted", "partial", "missing", "rejected", "not-requested", "unavailable", "failed"})
        hashed = capture["sha256"]
        require((isinstance(hashed, str) and SHA256.fullmatch(hashed)) if state in {"admitted", "partial"} else hashed is None)
        captured = instant(capture["observed_at"]) if capture["observed_at"] is not None else None
        expires = instant(capture["expires_at"]) if capture["expires_at"] is not None else None
        require(captured is None or captured <= observed)
        require(expires is None or captured is not None and expires > captured)
        if kind == "health" and state in {"admitted", "partial"}:
            require(captured is not None)
        if state not in {"admitted", "partial"}:
            require(captured is None and expires is None)
    if kind == "work":
        require(captures[0]["status"] == "admitted")
    else:
        require("github-check-runs" in seen)
    diagnostics = value["diagnostics"]
    require(isinstance(diagnostics, list) and len(diagnostics) <= 1024)
    for item in diagnostics:
        require(isinstance(item, dict) and set(item) == {"code", "owner", "producer"}
            and isinstance(item["code"], str) and re.fullmatch(r"[A-Z_]{1,64}", item["code"])
            and item["owner"] in {"relay", "hygiene", "egolint", "observatory"}
            and (item["producer"] is None or kind == "health" and item["producer"] in HEALTH_PRODUCERS))
    require(isinstance(value["coverage"], dict))
    for name, claim in value["coverage"].items():
        if name not in SOURCE_DOMAINS[kind]:
            require(claim == UNCOLLECTED)
    claims = [value["coverage"][name] for name in SOURCE_DOMAINS[kind]]
    if kind == "work":
        states = {claim["collection"] for claim in claims}
        expected_status = ("partial" if "partial" in states or any(item["code"] == "LINK_UNAVAILABLE" for item in diagnostics)
            else "failed" if "failed" in states else "unavailable" if "unavailable" in states
            else "uncollected" if "uncollected" in states
            else "stale" if any(claim["freshness"] == "stale" for claim in claims) else "ready")
        times = [claim["observed_at"] for claim in claims if claim["observed_at"] is not None]
        require(captures[0]["observed_at"] == (min(times) if times else None))
    else:
        claim = claims[0]
        state = claim["collection"]
        expected_status = "ready" if state in {"observed", "observed_empty"} else state
        times = [item["observed_at"] for item in captures if item["status"] in {"admitted", "partial"}]
        if state in {"observed", "observed_empty", "partial"}:
            require(times and claim["observed_at"] == min(times))
        if state in {"observed", "observed_empty"}:
            require(inputs["scope"] == "complete"
                and all(item["status"] in {"admitted", "not-requested"} for item in captures))
        if state == "not_applicable":
            require(inputs["scope"] == "not-applicable"
                and len(captures) == 1 and captures[0]["status"] == "not-requested")
    require(value["status"] == expected_status)
    digests = value["candidate_digests"]
    require(isinstance(digests, dict) and set(digests) == {"projection_sha256", "snapshot_sha256"}
        and all(isinstance(item, str) and SHA256.fullmatch(item) for item in digests.values()))
    return value
