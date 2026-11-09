#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Verify native source-plan receipts before attaching them to public provenance."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "egohygiene.relay.source-build/v1"
SHA256 = re.compile(r"[0-9a-f]{64}")
FILES = ("collect_repository_roadmap_source.py", "prepare_repository_sources_build.py",
         "collect_repository_roadmap.py", "collect_repository_adrs.py", "repository_adr_inputs.py")


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def digest(content):
    return hashlib.sha256(content).hexdigest()


def implementation():
    return {name: digest((ROOT / "scripts" / name).read_bytes()) for name in FILES}


def require(condition):
    if not condition:
        raise ValueError("Source build provenance is incompatible")


def validate(value, repository, source_commit):
    require(isinstance(value, dict) and set(value) == {"schema", "repository", "source_commit", "observed_at",
        "domains", "coverage", "candidate_digests", "implementation"})
    require(value["schema"] == SCHEMA and value["repository"] == repository and value["source_commit"] == source_commit)
    require(isinstance(value["observed_at"], str)
        and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value["observed_at"]))
    require(value["implementation"] == implementation())
    require(isinstance(value["domains"], dict) and bool(value["domains"])
        and set(value["domains"]) <= {"decisions", "roadmap"})
    coverage = module("relay_sources_coverage", "repository_intelligence_coverage.py")
    coverage.validate_domains(value["coverage"], value["observed_at"])
    uncollected = {"collection": "uncollected", "freshness": "unknown", "reason": "not_requested", "observed_at": None}
    for domain, claim in value["coverage"].items():
        if domain not in value["domains"]:
            require(claim == uncollected)
    runtimes = []
    for domain, receipt in value["domains"].items():
        require(receipt["repository"] == repository and receipt["source_commit"] == source_commit
            and receipt["observed_at"] == value["observed_at"])
        if domain == "decisions":
            module("relay_sources_adr_receipt", "repository_adr_build_contract.py").validate(receipt, repository, source_commit)
        else:
            require(set(receipt) == {"repository", "source_commit", "observed_at", "roadmap_sha256",
                "maximum_intent_age_days", "intent_freshness", "reference_count", "runtime", "validation", "coverage",
                "projection_sha256", "snapshot_sha256"})
            require(type(receipt["maximum_intent_age_days"]) is int and 1 <= receipt["maximum_intent_age_days"] <= 3650
                and receipt["intent_freshness"] in {"current", "stale"}
                and type(receipt["reference_count"]) is int and 0 <= receipt["reference_count"] <= 65536)
            for field in ("roadmap_sha256", "projection_sha256", "snapshot_sha256"):
                require(isinstance(receipt[field], str) and SHA256.fullmatch(receipt[field]))
            runtime = receipt["runtime"]
            require(isinstance(runtime, dict) and set(runtime) == {"lock_sha256", "egolint_sha256", "pins"})
            require(receipt["validation"] in [{"hygiene": "valid", "coverage": "valid", "observatory": "normalized",
                "egolint": state, "diagnostics_truncated": False} for state in ("valid", "incomplete")])
            coverage.validate_domains(receipt["coverage"], value["observed_at"])
            require(receipt["coverage"]["roadmap"] == {"collection": "observed", "freshness": "current",
                "reason": "complete", "observed_at": value["observed_at"]})
            require(all(claim == uncollected for name, claim in receipt["coverage"].items() if name != "roadmap"))
        runtime = receipt["runtime"]
        lock_bytes = (ROOT / "contracts/adr-collector.v1.lock.json").read_bytes()
        require(runtime["pins"] == json.loads(lock_bytes) and runtime["lock_sha256"] == digest(lock_bytes)
            and isinstance(runtime["egolint_sha256"], str) and SHA256.fullmatch(runtime["egolint_sha256"]))
        runtimes.append({key: runtime[key] for key in ("lock_sha256", "egolint_sha256", "pins")})
        require(value["coverage"][domain] == receipt["coverage"][domain])
    require(all(runtime == runtimes[0] for runtime in runtimes))
    digests = value["candidate_digests"]
    require(isinstance(digests, dict) and set(digests) == {"snapshot_sha256", "projection_sha256"}
        and all(isinstance(item, str) and SHA256.fullmatch(item) for item in digests.values()))
    return value


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def read(path):
    require(not any(parent.is_symlink() for parent in (path, *path.parents))
        and path.is_file() and path.stat().st_size <= 8 * 1024 * 1024)
    content = path.read_bytes()
    return content, json.loads(content, object_pairs_hook=unique_pairs,
        parse_constant=lambda _value: require(False))


def attach(provenance_path, receipt_path, snapshot_path):
    _, provenance = read(provenance_path)
    _, receipt = read(receipt_path)
    snapshot_bytes, snapshot = read(snapshot_path)
    validate(receipt, provenance["consumer"]["repository"], provenance["consumer"]["source_commit"])
    require(provenance["consumer"]["visibility"] == "public" and "adr_collection" not in provenance)
    require(digest(snapshot_bytes) == receipt["candidate_digests"]["snapshot_sha256"]
        and snapshot["repository"]["key"] == receipt["repository"]
        and snapshot["repository"]["repository"] == receipt["repository"]
        and snapshot["represented_commit"] == receipt["source_commit"]
        and snapshot["coverage"]["domains"] == receipt["coverage"] and snapshot["observed_at"] == receipt["observed_at"])
    provenance["source_collection"] = receipt
    descriptor, temporary = tempfile.mkstemp(dir=provenance_path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write((json.dumps(provenance, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode())
        os.replace(temporary, provenance_path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ("provenance", "receipt", "snapshot"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    try:
        attach(args.provenance.absolute(), args.receipt.absolute(), args.snapshot.absolute())
        return 0
    except (ValueError, OSError, KeyError, TypeError, RecursionError):
        raise SystemExit("Source build: provenance denied") from None


if __name__ == "__main__":
    raise SystemExit(main())
