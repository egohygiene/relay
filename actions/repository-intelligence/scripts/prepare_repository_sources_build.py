#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Prepare one commit-bound native source plan before rendering."""

from __future__ import annotations

import argparse
from datetime import datetime, UTC
import importlib.util
import json
import os
from pathlib import Path
import re
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
    for name in ("projection.json", "snapshot.json", "receipt.json", "failure.json"):
        path = target / name
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError("output-path")
    for name in ("projection.json", "snapshot.json", "receipt.json", "failure.json"):
        (target / name).unlink(missing_ok=True)
    return target


def compose(projections, normalize, runtime, coverage):
    # Compose canonical owner graphs, never generated route views. Inventory
    # claims are never upgraded by unioning partial records.
    composed = json.loads(json.dumps(projections[0]))
    composed["generator"]["name"] = "egohygiene/relay:source-composer"
    for other in projections[1:]:
        for key in ("schema", "contract_version", "projection_id", "repository", "represented_commit", "visibility", "observed_at"):
            if composed[key] != other[key]:
                raise ValueError("mixed-source-plan")
        for key in ("sources", "entities", "relationships", "events"):
            records = {record["id"]: record for record in composed[key]}
            for record in other[key]:
                old = records.get(record["id"])
                if old is not None and old != record:
                    if key == "entities" and old["kind"] == record["kind"] == "commit":
                        # Independently inspected immutable Git identity wins
                        # only over the release collector's targeted placeholder.
                        # Release/deployment sources and edges retain their own
                        # states and clocks; no causal relationship is inferred.
                        fixed = ("id", "kind", "repository", "key", "canonical_url", "visibility", "attributes", "extensions")
                        if (any(old[field] != record[field] for field in fixed)
                                or old["attributes"] != {"sha": old["key"]}
                                or old["title"] != "Commit " + old["key"][:12]
                                or old["state"] != {"value": "recorded", "assertion": "authoritative"}
                                or old["freshness"] != "not_applicable" or record["title"] is not None
                                or record["state"] != {"value": "observed", "assertion": "authoritative"}
                                or record["freshness"] not in {"current", "stale"}):
                            raise ValueError("conflicting-record")
                        records[record["id"]] = {**old, "provenance": sorted(set(old["provenance"] + record["provenance"]))}
                        continue
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
    composed["collection_coverage"] = coverage
    snapshot, validation = normalize(runtime, composed)
    if snapshot is None or validation != {"hygiene": "valid", "coverage": "valid", "observatory": "normalized"}:
        raise ValueError("normalization")
    return composed, snapshot


def profile_runtime(base, original, destination, target_lock):
    """Reuse verified executable/core artifacts under an exact compatible profile.

    Native Work/Health profiles require a strict subset of the existing ADR
    runtime's immutable owner artifacts. Copy only verified required bytes; no
    consumer file, mutable dependency, new executable or review result enters.
    """
    original_lock, receipt = base.runtime_files(original,
        lock_path=Path(__file__).resolve().parents[1] / "contracts/adr-collector.v1.lock.json")
    selected = base.load_json(base.read_file(target_lock))
    if not all(original_lock["sources"].get(name) == pin for name, pin in selected["sources"].items()):
        raise ValueError("runtime-profile-incompatible")
    destination.mkdir()
    for name, pin in selected["sources"].items():
        for filename, checksum in pin["files"].items():
            content = base.read_file(original / name / filename, base.MAX_OUTPUT)
            if base.digest(content) != checksum:
                raise ValueError("runtime-profile-incompatible")
            path = destination / name / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    executable = base.read_file(original / "egolint-bin", 128 * base.MAX_JSON)
    if base.digest(executable) != receipt["egolint_sha256"]:
        raise ValueError("runtime-profile-incompatible")
    (destination / "egolint-bin").write_bytes(executable)
    (destination / "egolint-bin").chmod(0o700)
    (destination / "runtime.json").write_bytes(base.json_bytes({
        "lock_sha256": base.digest(base.read_file(target_lock)), "egolint_sha256": receipt["egolint_sha256"]}))
    base.runtime_files(destination, lock_path=target_lock)
    return destination


def captured_sources(args, base, projections, receipts, temporary):
    contract = module("relay_sources_capture_contract", "repository_capture_build_contract.py")
    for kind in ("work", "health"):
        if not getattr(args, "collect_" + kind):
            continue
        args.active_source = kind
        collector = module("relay_sources_" + kind, "collect_repository_" + kind + ".py")
        runtime = getattr(args, kind + "_runtime")
        if runtime is None:
            if args.runtime is None:
                raise ValueError("source-runtime-required")
            runtime = profile_runtime(base, args.runtime, temporary / kind, collector.LOCK_PATH)
        if base.safe_path(runtime).is_relative_to(base.safe_path(args.repository_root)):
            raise ValueError("runtime-must-be-outside-consumer")
        arguments = ["collect", "--runtime", str(runtime), "--repository-root", str(args.repository_root),
            "--repository", args.repository, "--visibility", args.visibility,
            "--source-commit", args.source_commit, "--observed-at", args.observed_at,
            "--output", str(temporary / (kind + "-collection.review.json")),
            "--maximum-age-seconds", str(getattr(args, kind + "_maximum_age_seconds"))]
        if kind == "work":
            arguments.extend(["--provider-evidence", str(args.work_capture)])
        else:
            arguments.extend(["--inventory", args.health_inventory, "--check-runs-state", args.health_check_runs_state])
            for producer in args.health_expect_report:
                arguments.extend(["--expect-report", producer])
            for selection in args.health_report:
                arguments.extend(["--report", selection])
            if args.health_check_runs is not None:
                arguments.extend(["--check-runs", str(args.health_check_runs)])
            if args.health_check_runs_observed_at is not None:
                arguments.extend(["--check-runs-observed-at", args.health_check_runs_observed_at])
        native = collector.parser().parse_args(arguments)
        # Freshly invoke trusted collection over transport captures. This path
        # never accepts a publication-denied review envelope as a build input.
        result = collector.collect(native)
        receipt = contract.from_result(kind, result)
        receipts[kind] = receipt
        projections.append(result["projection_candidate"])
    if args.collect_releases:
        args.active_source = "releases"
        collector = module("relay_sources_releases", "collect_repository_releases.py")
        runtime = args.release_runtime or profile_runtime(base, args.runtime, temporary / "releases", collector.LOCK_PATH)
        arguments = ["collect", "--runtime", str(runtime), "--repository-root", str(args.repository_root),
            "--repository", args.repository, "--visibility", args.visibility, "--source-commit", args.source_commit,
            "--generator-commit", args.generator_commit, "--observed-at", args.observed_at,
            "--maximum-age-seconds", str(args.release_maximum_age_seconds), "--output", str(temporary / "release.review.json")]
        if args.release_capture is not None:
            arguments.extend(["--capture", str(args.release_capture)])
        if args.generator_repository_root is not None:
            arguments.extend(["--generator-repository-root", str(args.generator_repository_root)])
        for environment in args.release_public_environment:
            arguments.extend(["--public-environment", environment])
        for path in args.release_deployment_receipt:
            arguments.extend(["--deployment-receipt", str(path)])
        result = collector.collect(collector.parser().parse_args(arguments))
        receipts["releases"] = module("relay_sources_release_receipt", "repository_release_build_contract.py").from_result(result)
        projections.append(result["projection_candidate"])


def collect(args, target):
    roadmap = module("relay_sources_roadmap", "collect_repository_roadmap_source.py")
    adrs, base = roadmap.adrs, roadmap.base
    for runtime in (args.runtime, args.work_runtime, args.health_runtime, args.release_runtime):
        if runtime is not None and base.safe_path(runtime).is_relative_to(base.safe_path(args.repository_root)):
            raise ValueError("runtime-must-be-outside-consumer")
    if args.runtime is not None:
        # A shared runtime can be chosen for final normalization even when all
        # captures use explicit typed runtimes. Verify it before importing any
        # owner implementation, including that otherwise-unused selection.
        base.runtime_files(args.runtime, lock_path=adrs.LOCK_PATH)
    instant = datetime.fromisoformat(args.observed_at.replace("Z", "+00:00"))
    if instant.tzinfo is None or instant.microsecond:
        raise ValueError("observation")
    args.observed_at = instant.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    projections, receipts = [], {}
    if args.collect_adrs:
        args.active_source = "decisions"
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
        args.active_source = "roadmap"
        result = roadmap.collect(args)
        receipts["roadmap"] = result["receipt"]
        projections.append(result["projection"])
    if args.collect_journey:
        args.active_source = "journey"
        collector = module("relay_sources_journey", "collect_repository_journey.py")
        arguments = ["collect", "--runtime", str(args.runtime), "--repository-root", str(args.repository_root),
            "--repository", args.repository, "--visibility", args.visibility, "--source-commit", args.source_commit,
            "--observed-at", args.observed_at, "--collected-at", args.observed_at,
            "--maximum-commits", str(args.journey_maximum_commits), "--output", str(target / "unused")]
        for name in ("since", "until"):
            if getattr(args, "journey_" + name) is not None:
                arguments.extend(["--" + name, getattr(args, "journey_" + name)])
        result = collector.collect(collector.parser().parse_args(arguments))
        receipts["journey"] = module("relay_sources_journey_receipt", "repository_journey_build_contract.py").from_result(result)
        projections.append(result["projection_candidate"])
    with tempfile.TemporaryDirectory(prefix="relay-captured-source-profiles-") as directory:
        temporary = base.safe_path(Path(directory))
        if temporary.is_relative_to(base.safe_path(args.repository_root)):
            raise ValueError("runtime-layout")
        captured_sources(args, base, projections, receipts, temporary)
        normalizer_runtime = args.runtime or args.work_runtime or args.health_runtime or args.release_runtime
        contract = module("relay_sources_contract", "repository_sources_build_contract.py")
        projection, snapshot = compose(projections, adrs.normalize, normalizer_runtime, contract.combined_coverage(receipts))
    args.active_source = None
    contract = module("relay_sources_contract", "repository_sources_build_contract.py")
    receipt = {"schema": contract.SCHEMA, "repository": args.repository, "source_commit": args.source_commit,
        "observed_at": args.observed_at, "domains": receipts, "coverage": projection["collection_coverage"],
        "candidate_digests": {"projection_sha256": base.digest(base.json_bytes(projection)),
            "snapshot_sha256": base.digest(base.json_bytes(snapshot))},
        "implementation": contract.implementation(), "input_plan_sha256": args.input_plan_sha256}
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
    value.add_argument("--capture-plan", type=Path,
        help="Closed Work/Health transport capture plan; paths are relative to the consumer root.")
    value.add_argument("--capture-root", type=Path,
        help="Optional separately admitted data root for capture-plan paths; never an executable runtime.")
    value.add_argument("--capture-intake-receipt", type=Path,
        help="Reverify exact same-run artifact admission before evaluating its private capture tree.")
    value.add_argument("--repository-root", type=Path, required=True)
    value.add_argument("--work-directory", default=".cache/repository-intelligence")
    for name in ("repository", "visibility", "source-commit", "observed-at"):
        value.add_argument("--" + name, required=True)
    value.add_argument("--collect-adrs", action="store_true")
    value.add_argument("--collect-roadmap", action="store_true")
    value.add_argument("--collect-journey", action="store_true")
    value.add_argument("--journey-maximum-commits", type=int, default=256)
    value.add_argument("--journey-since")
    value.add_argument("--journey-until")
    value.add_argument("--collect-releases", action="store_true")
    value.add_argument("--release-capture", type=Path)
    value.add_argument("--release-runtime", type=Path)
    value.add_argument("--release-public-environment", action="append", default=[])
    value.add_argument("--release-deployment-receipt", action="append", type=Path, default=[])
    value.add_argument("--release-maximum-age-seconds", type=int, default=86400)
    value.add_argument("--generator-commit", default="")
    value.add_argument("--generator-repository-root", type=Path,
        help="Trusted exact Relay Git proof for offline release collection; never selected by provider captures.")
    value.add_argument("--collect-work", action="store_true")
    value.add_argument("--work-capture", type=Path)
    value.add_argument("--work-runtime", type=Path)
    value.add_argument("--work-maximum-age-seconds", type=int, default=86400)
    value.add_argument("--collect-health", action="store_true")
    value.add_argument("--health-runtime", type=Path)
    value.add_argument("--health-inventory", choices=("partial", "complete", "not-applicable"), default="partial")
    value.add_argument("--health-expect-report", action="append", choices=("osv", "megalinter", "scorecard"), default=[])
    value.add_argument("--health-report", action="append", default=[], metavar="PRODUCER=PATH")
    value.add_argument("--health-check-runs", type=Path)
    value.add_argument("--health-check-runs-state", choices=("not-requested", "observed", "unavailable", "failed"), default="not-requested")
    value.add_argument("--health-check-runs-observed-at")
    value.add_argument("--health-maximum-age-seconds", type=int, default=86400)
    value.add_argument("--policy-owner", action="store_true")
    value.add_argument("--known-external-decisions", default="[]")
    value.add_argument("--maximum-intent-age-days", type=int, default=30)
    value.add_argument("--observatory-snapshot", default="")
    value.add_argument("--observatory-comparison", default="")
    return value


def replay_arguments(args, runtime):
    """Reconstruct normalized selections after acquisition changes directories."""
    plan = json.loads(args.capture_plan.read_bytes()) if args.capture_plan is not None else {}
    values = ["--repository-root", str(args.repository_root), "--work-directory", args.work_directory,
        "--repository", args.repository, "--visibility", args.visibility, "--source-commit", args.source_commit,
        "--observed-at", args.observed_at, "--maximum-intent-age-days", str(args.maximum_intent_age_days),
        "--known-external-decisions", args.known_external_decisions, "--runtime", str(runtime),
        "--work-maximum-age-seconds", str(86400 if "work" in plan else args.work_maximum_age_seconds),
        "--health-maximum-age-seconds", str(86400 if "health" in plan else args.health_maximum_age_seconds),
        "--health-inventory", "partial" if "health" in plan else args.health_inventory,
        "--health-check-runs-state", "not-requested" if "health" in plan else args.health_check_runs_state,
        "--journey-maximum-commits", str(args.journey_maximum_commits),
        "--release-maximum-age-seconds", str(86400 if "releases" in plan else args.release_maximum_age_seconds),
        "--generator-commit", args.generator_commit]
    if args.capture_plan is not None:
        # Reparse the same immutable plan in the acquired interpreter. Do not
        # replay its expanded selections as duplicate explicit source inputs.
        values.extend(["--capture-plan", str(args.capture_plan)])
    for name in ("capture_root", "capture_intake_receipt", "generator_repository_root", "journey_since", "journey_until"):
        if getattr(args, name) is not None:
            values.extend(["--" + name.replace("_", "-"), str(getattr(args, name))])
    for name in ("collect_adrs", "collect_roadmap", "collect_work", "collect_health", "collect_journey", "collect_releases", "policy_owner"):
        if name in {"collect_work", "collect_health", "collect_releases"} and name.removeprefix("collect_") in plan:
            continue
        if getattr(args, name):
            values.append("--" + name.replace("_", "-"))
    for name in ("work_capture", "work_runtime", "health_runtime", "health_check_runs", "health_check_runs_observed_at", "release_capture", "release_runtime"):
        if ((name == "work_capture" and "work" in plan) or (name in {"health_check_runs", "health_check_runs_observed_at"} and "health" in plan)
                or (name == "release_capture" and "releases" in plan)):
            continue
        if getattr(args, name) is not None:
            values.extend(["--" + name.replace("_", "-"), str(getattr(args, name))])
    for name in ("health_expect_report", "health_report"):
        if "health" in plan:
            continue
        for value in getattr(args, name):
            values.extend(["--" + name.replace("_", "-"), value])
    if "releases" not in plan:
        for name in ("release_public_environment", "release_deployment_receipt"):
            for value in getattr(args, name):
                values.extend(["--" + name.replace("_", "-"), str(value)])
    return values


def write_failure(target, stage, source):
    # Fixed fields keep parser/native source excerpts and filesystem paths out
    # of failure evidence. This private work namespace is never public output.
    if stage not in {"input", "acquisition", "collection-validation-normalization"}:
        stage = "input"
    if source not in {"decisions", "roadmap", "work", "health", "journey", "releases"}:
        source = None
    if any(path.is_symlink() for path in (target, *target.parents)) or not target.is_dir():
        return
    for name in ("projection.json", "snapshot.json", "receipt.json"):
        (target / name).unlink(missing_ok=True)
    content = (json.dumps({"schema": "egohygiene.relay.source-build-failure/v1", "status": "denied",
        "publication": "denied", "stage": stage, "source": source, "code": "SOURCE_BUILD_DENIED"},
        indent=2, sort_keys=True) + "\n").encode()
    descriptor, temporary = tempfile.mkstemp(dir=target)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
        os.replace(temporary, target / "failure.json")
    finally:
        Path(temporary).unlink(missing_ok=True)


def main():
    args = parser().parse_args()
    args.repository_root = args.repository_root.absolute()
    for name in ("runtime", "work_runtime", "health_runtime", "work_capture", "health_check_runs", "capture_root", "capture_intake_receipt",
            "release_runtime", "release_capture", "generator_repository_root"):
        if getattr(args, name) is not None:
            setattr(args, name, getattr(args, name).absolute())
    args.release_deployment_receipt = [path.absolute() for path in args.release_deployment_receipt]
    normalized_reports = []
    for selection in args.health_report:
        producer, separator, path = selection.partition("=")
        normalized_reports.append(producer + separator + str(Path(path).absolute()) if separator and path else selection)
    args.health_report = normalized_reports
    stage = "input"
    target = None
    try:
        args.input_plan_sha256 = None
        if not any((args.collect_roadmap, args.collect_adrs, args.collect_work, args.collect_health, args.collect_journey,
                args.collect_releases, args.capture_plan is not None)):
            raise ValueError("empty-source-plan")
        if args.observatory_snapshot or args.observatory_comparison:
            raise ValueError("conflicting-inputs")
        target = output_paths(args)
        if args.visibility != "public" or (args.policy_owner and not args.collect_adrs):
            raise ValueError("visibility-or-selection")
        if (not re.fullmatch(r"egohygiene/(?:\.github|[a-z0-9][a-z0-9.-]*)", args.repository)
                or not re.fullmatch(r"[0-9a-f]{40}", args.source_commit)
                or len(args.observed_at) > 40):
            raise ValueError("source-boundary")
        observed = datetime.fromisoformat(args.observed_at.replace("Z", "+00:00"))
        if observed.tzinfo is None or observed.microsecond:
            raise ValueError("observation")
        args.observed_at = observed.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        if not 1 <= args.journey_maximum_commits <= 256:
            raise ValueError("journey-boundary")
        for name in ("journey_since", "journey_until"):
            selected = getattr(args, name)
            if selected is not None:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", selected):
                    raise ValueError("journey-boundary")
                datetime.strptime(selected, "%Y-%m-%dT%H:%M:%SZ")
        upper = datetime.strptime(args.journey_until, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC) if args.journey_until else observed
        lower = datetime.strptime(args.journey_since, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC) if args.journey_since else None
        if upper > observed or lower is not None and lower > upper:
            raise ValueError("journey-boundary")
        if (not args.collect_journey and (args.journey_maximum_commits != 256 or args.journey_since is not None or args.journey_until is not None)):
            raise ValueError("journey-selection")
        if args.capture_plan is not None:
            args.capture_plan = args.capture_plan.absolute()
            args.input_plan_sha256 = module("relay_sources_plan_inputs", "repository_source_capture_inputs.py").apply(args)
        elif args.capture_root is not None or args.capture_intake_receipt is not None:
            raise ValueError("capture-plan-required")
        if args.capture_intake_receipt is not None:
            if args.capture_root is None or args.capture_root.is_relative_to(args.repository_root):
                raise ValueError("private-intake-root")
            module("relay_sources_intake", "repository_capture_artifact.py").verify_receipt(
                args.capture_intake_receipt, args.capture_root, args.repository,
                args.source_commit, args.observed_at, args.input_plan_sha256)
        if bool(args.work_capture) != args.collect_work or (args.work_runtime is not None and not args.collect_work):
            raise ValueError("work-selection")
        if args.collect_releases:
            if not re.fullmatch(r"[0-9a-f]{40}", args.generator_commit):
                raise ValueError("generator-boundary")
        elif (args.release_capture is not None or args.release_runtime is not None or args.release_public_environment
                or args.release_deployment_receipt or args.release_maximum_age_seconds != 86400
                or args.generator_repository_root is not None):
            raise ValueError("release-selection")
        if (not args.collect_health and (args.health_runtime is not None or args.health_expect_report or args.health_report
                or args.health_check_runs is not None or args.health_check_runs_observed_at is not None
                or args.health_check_runs_state != "not-requested" or args.health_inventory != "partial")):
            raise ValueError("health-selection")
        if any(not 1 <= age <= 2678400 for age in (args.work_maximum_age_seconds, args.health_maximum_age_seconds,
                args.release_maximum_age_seconds)):
            raise ValueError("capture-age")
        # Validate bounded declarations before network/runtime acquisition.
        module("relay_sources_inputs", "repository_adr_inputs.py").selection(
            args.known_external_decisions, "true" if args.collect_adrs else "false")
        needs_shared_runtime = (args.collect_adrs or args.collect_roadmap or args.collect_journey
            or args.collect_work and args.work_runtime is None or args.collect_health and args.health_runtime is None
            or args.collect_releases and args.release_runtime is None)
        if args.runtime is None and needs_shared_runtime:
            stage = "acquisition"
            acquisition = module("relay_sources_acquisition", "prepare_repository_adr_build.py")
            with tempfile.TemporaryDirectory(prefix="relay-sources-build-") as temporary:
                work = Path(temporary)
                if work.is_relative_to(args.repository_root.absolute()):
                    raise ValueError("runtime-layout")
                python, runtime = acquisition.acquire(work)
                if args.collect_releases and args.generator_repository_root is None:
                    # Actions are installed archives. Acquire Git proof only
                    # from Relay's fixed public origin at its resolved SHA;
                    # never materialize or execute repository checkout code.
                    proof = work / "relay-source-proof"
                    env = {"PATH": os.environ.get("PATH", os.defpath), "LC_ALL": "C.UTF-8",
                        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                        "GIT_NO_REPLACE_OBJECTS": "1", "GIT_TERMINAL_PROMPT": "0"}
                    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy",
                            "all_proxy", "no_proxy", "SSL_CERT_FILE", "SSL_CERT_DIR", "GIT_SSL_CAINFO"):
                        if key in os.environ:
                            env[key] = os.environ[key]
                    acquisition.execute(["git", "init", "--bare", str(proof)], work, env)
                    acquisition.execute(["git", "-C", str(proof), "fetch", "--no-tags", "--depth=1",
                        "https://github.com/egohygiene/relay.git", args.generator_commit], work, env)
                    args.generator_repository_root = proof
                return subprocess.run([str(python), "-I", str(Path(__file__).resolve()),
                    *replay_arguments(args, runtime)], cwd=work, check=False).returncode
        stage = "collection-validation-normalization"
        collect(args, target)
        print("Source build: validated commit-bound snapshot prepared")
        return 0
    except Exception:
        # This CLI is the sanitization boundary around parsers and native owner
        # adapters. Malformed YAML and third-party exceptions may quote source
        # text, so they must never escape as public runner tracebacks.
        print(f"Source build: {stage}: denied", file=sys.stderr)
        if target is not None:
            try:
                write_failure(target, stage, getattr(args, "active_source", None))
            except Exception:
                pass
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
