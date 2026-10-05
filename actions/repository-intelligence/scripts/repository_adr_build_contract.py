# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Bind canonical ADR build evidence into existing deterministic provenance."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "egohygiene.relay.adr-build/v1"
KEYS = {"schema", "repository", "source_commit", "observed_at", "adoption", "policy_reference",
        "decision_directory", "index", "collected_at", "maximum_age_seconds", "sources", "runtime",
        "validation", "coverage", "candidate_digests"}
SHA256 = re.compile(r"[0-9a-f]{64}")
_spec = importlib.util.spec_from_file_location("relay_adr_coverage", Path(__file__).with_name("repository_intelligence_coverage.py"))
coverage = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(coverage)


def digest(content):
    return hashlib.sha256(content).hexdigest()


def require(value):
    if not value:
        raise ValueError("ADR build provenance is incompatible")


def validate(value, repository, source_commit):
    require(isinstance(value, dict) and set(value) == KEYS)
    require(value["schema"] == SCHEMA and value["repository"] == repository and value["source_commit"] == source_commit)
    require(value["adoption"] == "present" and value["decision_directory"] == "docs/decisions"
            and value["policy_reference"] == "docs/decisions/policy-reference.json"
            and value["index"] == "docs/decisions/README.md"
            and value["collected_at"] == value["observed_at"] and value["maximum_age_seconds"] == 86400)
    coverage.validate_domains(value["coverage"], value["observed_at"])
    require(value["coverage"]["decisions"]["collection"] in {"observed", "observed_empty"}
            and value["coverage"]["decisions"]["freshness"] == "current"
            and value["coverage"]["decisions"]["observed_at"] == value["observed_at"])
    for name, claim in value["coverage"].items():
        if name != "decisions":
            require(claim["collection"] == "uncollected")
    validation = value["validation"]
    require(validation in [dict(hygiene="valid", coverage="valid", observatory="normalized", egolint=status,
                               diagnostics_truncated=False) for status in ("valid", "incomplete")])
    runtime = value["runtime"]
    require(isinstance(runtime, dict) and set(runtime) == {"lock_sha256", "egolint_sha256", "pins",
                                                        "collector_sha256", "shared_runtime_sha256"})
    lock_bytes = (ROOT / "contracts/adr-collector.v1.lock.json").read_bytes()
    require(runtime["pins"] == json.loads(lock_bytes) and runtime["lock_sha256"] == digest(lock_bytes))
    require(runtime["collector_sha256"] == digest((ROOT / "scripts/collect_repository_adrs.py").read_bytes())
            and runtime["shared_runtime_sha256"] == digest((ROOT / "scripts/collect_repository_roadmap.py").read_bytes())
            and isinstance(runtime["egolint_sha256"], str) and SHA256.fullmatch(runtime["egolint_sha256"]))
    require(isinstance(value["sources"], list) and 2 <= len(value["sources"]) <= 256)
    names = []
    for source in value["sources"]:
        require(isinstance(source, dict) and set(source) == {"path", "sha256"})
        path = source["path"]
        require(isinstance(path, str) and re.fullmatch(r"docs/decisions/[A-Za-z0-9._/-]+", path)
                and all(p not in {"", ".", ".."} for p in path.split("/")))
        require(isinstance(source["sha256"], str) and SHA256.fullmatch(source["sha256"]))
        names.append(path)
    require(names == sorted(set(names)) and value["index"] in names and value["policy_reference"] in names)
    digests = value["candidate_digests"]
    require(isinstance(digests, dict) and set(digests) == {"snapshot_sha256", "projection_sha256"}
            and all(isinstance(item, str) and SHA256.fullmatch(item) for item in digests.values()))
    return value


def attach(provenance_path, receipt_path, snapshot_path):
    for path in (provenance_path, receipt_path, snapshot_path):
        require(not any(p.is_symlink() for p in (path, *path.parents)))
        require(path.is_file() and path.stat().st_size <= 8 * 1024 * 1024)
    provenance = json.loads(provenance_path.read_bytes())
    receipt = validate(json.loads(receipt_path.read_bytes()), provenance["consumer"]["repository"],
                       provenance["consumer"]["source_commit"])
    require(provenance["consumer"]["visibility"] == "public")
    require(digest(snapshot_path.read_bytes()) == receipt["candidate_digests"]["snapshot_sha256"])
    snapshot = json.loads(snapshot_path.read_bytes())
    require(snapshot["coverage"]["domains"] == receipt["coverage"] and snapshot["observed_at"] == receipt["observed_at"])
    provenance["adr_collection"] = receipt
    content = (json.dumps(provenance, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
    descriptor, temporary = tempfile.mkstemp(dir=provenance_path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
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
    except (OSError, ValueError, KeyError, TypeError):
        raise SystemExit("ADR build: provenance: denied")


if __name__ == "__main__":
    raise SystemExit(main())
