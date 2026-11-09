#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Prepare one commit-bound native Roadmap/Decisions snapshot before rendering."""

from __future__ import annotations

import argparse
from datetime import datetime, UTC
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

SCRIPTS = Path(__file__).parent


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def output_paths(args):
    # Stdlib preflight, before acquisition. Own a private, untracked namespace.
    root = args.repository_root.absolute()
    relative = Path(args.work_directory)
    if (".." in root.parts or relative.is_absolute() or not relative.parts or ".." in relative.parts
            or relative.as_posix() != args.work_directory
            or relative.parts[0] not in {".cache", ".staging", "build", "dist"}):
        raise ValueError("output-layout")
    target = root / relative / "sources"
    if any(path.is_symlink() for path in (target, *target.parents)):
        raise ValueError("output-path")
    tracked = subprocess.check_output(["git", "--no-optional-locks", "-c", "core.hooksPath=/dev/null",
        "-c", "core.fsmonitor=false", "-C", str(root), "ls-files", "--", str(relative / "sources")],
        stderr=subprocess.DEVNULL)
    if tracked or (target.exists() and not target.is_dir()):
        raise ValueError("output-tracked")
    target.mkdir(parents=True, exist_ok=True)
    for name in ("projection.json", "snapshot.json", "receipt.json"):
        path = target / name
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError("output-path")
    for name in ("projection.json", "snapshot.json", "receipt.json"):
        (target / name).unlink(missing_ok=True)
    return target


def compose(projections, normalize, runtime):
    # Compose canonical owner graphs, never generated route views. Inventory
    # claims are never upgraded by unioning partial records.
    composed = json.loads(json.dumps(projections[0]))
    composed["generator"]["name"] = "egohygiene/relay:source-composer"
    for other in projections[1:]:
        for key in ("schema", "contract_version", "projection_id", "repository", "represented_commit", "visibility", "observed_at"):
            if composed[key] != other[key]:
                raise ValueError("mixed-source-plan")
        for domain, claim in other["collection_coverage"].items():
            existing = composed["collection_coverage"][domain]
            if claim["collection"] != "uncollected":
                if existing["collection"] != "uncollected":
                    raise ValueError("conflicting-domain")
                composed["collection_coverage"][domain] = claim
        for key in ("sources", "entities", "relationships", "events"):
            records = {record["id"]: record for record in composed[key]}
            for record in other[key]:
                old = records.get(record["id"])
                if old is not None and old != record:
                    if key != "entities" or old["kind"] != "repository" or record["kind"] != "repository":
                        raise ValueError("conflicting-record")
                    # Only identical repository identity records may merge their
                    # source links; their unknown state cannot become success.
                    left, right = dict(old), dict(record)
                    left.pop("provenance")
                    right.pop("provenance")
                    if left != right:
                        raise ValueError("conflicting-record")
                    record = {**old, "provenance": sorted(set(old["provenance"] + record["provenance"]))}
                records[record["id"]] = record
            composed[key] = sorted(records.values(), key=lambda item: item["id"])
    snapshot, validation = normalize(runtime, composed)
    if snapshot is None or validation != {"hygiene": "valid", "coverage": "valid", "observatory": "normalized"}:
        raise ValueError("normalization")
    return composed, snapshot


def collect(args, target):
    roadmap = module("relay_sources_roadmap", "collect_repository_roadmap_source.py")
    adrs, base = roadmap.adrs, roadmap.base
    if base.safe_path(args.runtime).is_relative_to(base.safe_path(args.repository_root)):
        raise ValueError("runtime-must-be-outside-consumer")
    instant = datetime.fromisoformat(args.observed_at.replace("Z", "+00:00"))
    if instant.tzinfo is None or instant.microsecond:
        raise ValueError("observation")
    args.observed_at = instant.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    projections, receipts = [], {}
    if args.collect_adrs:
        native = adrs.parser().parse_args(["collect", "--runtime", str(args.runtime),
            "--repository-root", str(args.repository_root), "--repository", args.repository,
            "--visibility", args.visibility, "--source-commit", args.source_commit,
            "--observed-at", args.observed_at, "--adoption", "present", "--output", str(target / "unused")])
        native.policy_owner = args.policy_owner
        native.known_external_decisions = args.known_external_decisions
        result = adrs.collect(native)
        if (result["status"] != "ready" or result["validation"]["diagnostics_truncated"]
                or result["coverage"]["decisions"]["freshness"] != "current"):
            raise ValueError("source-validation")
        contract = module("relay_sources_adr_contract", "repository_adr_build_contract.py")
        receipt = {"schema": contract.SCHEMA, "repository": args.repository, "source_commit": args.source_commit,
            "observed_at": args.observed_at, **result["inputs"], "runtime": result["runtime"],
            "validation": result["validation"], "coverage": result["coverage"],
            "candidate_digests": result["candidate_digests"]}
        contract.validate(receipt, args.repository, args.source_commit)
        receipts["decisions"] = receipt
        projections.append(result["projection_candidate"])
    if args.collect_roadmap:
        result = roadmap.collect(args)
        receipts["roadmap"] = result["receipt"]
        projections.append(result["projection"])
    projection, snapshot = compose(projections, adrs.normalize, args.runtime)
    contract = module("relay_sources_contract", "repository_sources_build_contract.py")
    receipt = {"schema": contract.SCHEMA, "repository": args.repository, "source_commit": args.source_commit,
        "observed_at": args.observed_at, "domains": receipts, "coverage": projection["collection_coverage"],
        "candidate_digests": {"projection_sha256": base.digest(base.json_bytes(projection)),
            "snapshot_sha256": base.digest(base.json_bytes(snapshot))},
        "implementation": contract.implementation()}
    contract.validate(receipt, args.repository, args.source_commit)
    # A receipt is the completion marker. On a failed write neither candidate
    # survives, and a retry cannot promote a previous invocation's snapshot.
    try:
        for name, value in (("projection.json", projection), ("snapshot.json", snapshot), ("receipt.json", receipt)):
            content = base.json_bytes(value)
            if len(content) > base.MAX_OUTPUT:
                raise ValueError("output-size")
            descriptor, temporary = tempfile.mkstemp(dir=target)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(content)
                os.replace(temporary, target / name)
            finally:
                Path(temporary).unlink(missing_ok=True)
    except BaseException:
        for name in ("projection.json", "snapshot.json", "receipt.json"):
            (target / name).unlink(missing_ok=True)
        raise


def parser():
    value = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    value.add_argument("--runtime", type=Path)
    value.add_argument("--repository-root", type=Path, required=True)
    value.add_argument("--work-directory", default=".cache/repository-intelligence")
    for name in ("repository", "visibility", "source-commit", "observed-at"):
        value.add_argument("--" + name, required=True)
    value.add_argument("--collect-adrs", action="store_true")
    value.add_argument("--collect-roadmap", action="store_true")
    value.add_argument("--policy-owner", action="store_true")
    value.add_argument("--known-external-decisions", default="[]")
    value.add_argument("--maximum-intent-age-days", type=int, default=30)
    value.add_argument("--observatory-snapshot", default="")
    value.add_argument("--observatory-comparison", default="")
    return value


def main():
    args = parser().parse_args()
    args.repository_root = args.repository_root.absolute()
    if args.runtime is not None:
        args.runtime = args.runtime.absolute()
    stage = "input"
    try:
        if not args.collect_roadmap and not args.collect_adrs:
            raise ValueError("empty-source-plan")
        if args.observatory_snapshot or args.observatory_comparison:
            raise ValueError("conflicting-inputs")
        target = output_paths(args)
        if args.visibility != "public" or (args.policy_owner and not args.collect_adrs):
            raise ValueError("visibility-or-selection")
        # Validate bounded declarations before network/runtime acquisition.
        module("relay_sources_inputs", "repository_adr_inputs.py").selection(
            args.known_external_decisions, "true" if args.collect_adrs else "false")
        if args.runtime is None:
            stage = "acquisition"
            acquisition = module("relay_sources_acquisition", "prepare_repository_adr_build.py")
            with tempfile.TemporaryDirectory(prefix="relay-sources-build-") as temporary:
                work = Path(temporary)
                if work.is_relative_to(args.repository_root.absolute()):
                    raise ValueError("runtime-layout")
                python, runtime = acquisition.acquire(work)
                return subprocess.run([str(python), "-I", str(Path(__file__).resolve()),
                    *sys.argv[1:], "--repository-root", str(args.repository_root),
                    "--runtime", str(runtime)], cwd=work, check=False).returncode
        stage = "collection-validation-normalization"
        collect(args, target)
        print("Source build: validated commit-bound snapshot prepared")
        return 0
    except Exception:
        # This CLI is the sanitization boundary around parsers and native owner
        # adapters. Malformed YAML and third-party exceptions may quote source
        # text, so they must never escape as public runner tracebacks.
        print(f"Source build: {stage}: denied", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
