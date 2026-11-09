#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Bind a fresh bounded Git collection to the production source plan."""

from datetime import datetime, UTC
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "egohygiene.relay.source-journey-build/v1"
SHA = re.compile(r"[0-9a-f]{40}")
HASH = re.compile(r"[0-9a-f]{64}")
UNCOLLECTED = {"collection": "uncollected", "freshness": "unknown", "reason": "not_requested", "observed_at": None}
FLAGS = {"shallow", "truncated", "time_filtered", "withheld_timestamps"}


def require(value):
    if not value:
        raise ValueError("Journey source provenance is incompatible")


def digest(content):
    return hashlib.sha256(content).hexdigest()


def instant(value):
    require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value))
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def from_result(result):
    # Only the result of this invocation is admitted. A review-envelope path is
    # never an input, and publication denial is not treated as an approval.
    require(result["schema"] == "egohygiene.relay.journey-collection-review/v1"
        and result["publication"] == "denied" and result["snapshot_candidate"] is not None)
    require(result["coverage"] == result["projection_candidate"]["collection_coverage"]
        == result["snapshot_candidate"]["coverage"]["domains"])
    for kind in ("projection", "snapshot"):
        content = (json.dumps(result[kind + "_candidate"], indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
        require(digest(content) == result["candidate_digests"][kind + "_sha256"])
    value = {"schema": SCHEMA, "admission": "fresh-immutable-git", "repository": result["repository"],
        "source_commit": result["represented_commit"], "observed_at": result["observed_at"],
        "commit_revisions": sorted(item["key"] for item in result["projection_candidate"]["entities"] if item["kind"] == "commit"),
        **{key: result[key] for key in ("status", "inputs", "scope", "runtime", "validation", "coverage", "candidate_digests")}}
    validate(value, value["repository"], value["source_commit"], value["observed_at"])
    return value


def validate(value, repository, source_commit, observed_at):
    require(isinstance(value, dict) and set(value) == {"schema", "admission", "repository", "source_commit",
        "observed_at", "status", "inputs", "scope", "runtime", "validation", "coverage", "candidate_digests", "commit_revisions"})
    require(value["schema"] == SCHEMA and value["admission"] == "fresh-immutable-git"
        and value["repository"] == repository and value["source_commit"] == source_commit
        and SHA.fullmatch(source_commit) and value["observed_at"] == observed_at)
    observed = instant(observed_at)
    inputs, scope, runtime = value["inputs"], value["scope"], value["runtime"]
    require(isinstance(inputs, dict) and set(inputs) == {"collected_at", "maximum_age_seconds", "maximum_commits",
        "since", "until", "public_subjects", "commits"})
    captured = instant(inputs["collected_at"])
    require(captured <= observed and type(inputs["maximum_age_seconds"]) is int
        and 1 <= inputs["maximum_age_seconds"] <= 2678400 and type(inputs["maximum_commits"]) is int
        and 1 <= inputs["maximum_commits"] <= 256 and inputs["public_subjects"] is False)
    since = instant(inputs["since"]) if inputs["since"] is not None else None
    until = instant(inputs["until"]) if inputs["until"] is not None else None
    require((until is None or until <= observed) and (since is None or until is None or since <= until))
    commits = inputs["commits"]
    require(isinstance(commits, list) and len(commits) <= inputs["maximum_commits"])
    revisions = []
    for item in commits:
        require(isinstance(item, dict) and set(item) == {"revision", "sha256"}
            and isinstance(item["revision"], str) and SHA.fullmatch(item["revision"])
            and isinstance(item["sha256"], str) and HASH.fullmatch(item["sha256"]))
        revisions.append(item["revision"])
    require(revisions == sorted(set(revisions)))
    projected = value["commit_revisions"]
    require(isinstance(projected, list) and all(isinstance(item, str) and SHA.fullmatch(item) for item in projected)
        and projected == sorted(set(projected)) and set(projected) <= set(revisions))
    require(isinstance(scope, dict) and set(scope) == FLAGS | {"provider_events", "parent_topology", "declared_reference_resolution"}
        and all(type(scope[flag]) is bool for flag in FLAGS)
        and scope["time_filtered"] == (since is not None or until is not None)
        and scope["provider_events"] == "uncollected" and scope["parent_topology"] == "unavailable"
        and scope["declared_reference_resolution"] == "unavailable")
    partial = any(scope[key] for key in FLAGS)
    require(value["status"] == ("partial" if partial else "ready"))
    lock_bytes = (ROOT / "contracts/adr-collector.v1.lock.json").read_bytes()
    require(isinstance(runtime, dict) and set(runtime) == {"lock_sha256", "egolint_sha256", "pins", "collector_sha256",
        "shared_runtime_sha256", "normalizer_adapter_sha256"} and runtime["pins"] == json.loads(lock_bytes)
        and runtime["lock_sha256"] == digest(lock_bytes) and isinstance(runtime["egolint_sha256"], str)
        and HASH.fullmatch(runtime["egolint_sha256"]))
    for field, filename in (("collector_sha256", "collect_repository_journey.py"),
            ("shared_runtime_sha256", "collect_repository_roadmap.py"),
            ("normalizer_adapter_sha256", "collect_repository_adrs.py")):
        require(runtime[field] == digest((ROOT / "scripts" / filename).read_bytes()))
    require(value["validation"] in [{"hygiene": "valid", "coverage": "valid", "observatory": "normalized",
        "egolint": state, "diagnostics_truncated": False} for state in ("valid", "incomplete")])
    coverage = value["coverage"]
    require(isinstance(coverage, dict) and set(coverage) == {"git", "history", "roadmap", "decisions", "issues",
        "pull_requests", "checks", "releases", "deployments"})
    freshness = "stale" if (observed - captured).total_seconds() > inputs["maximum_age_seconds"] else "current"
    reason = "truncated" if scope["truncated"] else "filtered" if scope["time_filtered"] else "incomplete" if partial else "complete"
    require(coverage["git"] == {"collection": "partial" if partial else "observed" if projected else "observed_empty",
        "freshness": freshness, "reason": reason, "observed_at": inputs["collected_at"]}
        and coverage["history"] == {"collection": "partial", "freshness": freshness,
            "reason": "incomplete", "observed_at": inputs["collected_at"]}
        and all(claim == UNCOLLECTED for domain, claim in coverage.items() if domain not in {"git", "history"}))
    hashes = value["candidate_digests"]
    require(isinstance(hashes, dict) and set(hashes) == {"projection_sha256", "snapshot_sha256"}
        and all(isinstance(item, str) and HASH.fullmatch(item) for item in hashes.values()))
    return value
