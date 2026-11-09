#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Retain exact public projection/snapshot pairs through explicit ordinary artifacts."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import zipfile

SCRIPTS = Path(__file__).resolve().parent
MANIFEST = "snapshot-bundle.json"
SCHEMA = "egohygiene.relay.snapshot-artifact-bundle/v1"
RECEIPT = "egohygiene.relay.snapshot-artifact-intake/v1"
FILES = ("projection.json", "snapshot.json")
MAX_FILE = 8 * 1024 * 1024
MAX_ARCHIVE = 2 * MAX_FILE + 131072
HASH = re.compile(r"[0-9a-f]{64}")
STATES = {"missing", "available", "expired", "inaccessible", "incompatible", "wrong_repository", "malformed", "redacted"}


class ArtifactError(ValueError):
    """A closed baseline admission state without captured text or provider URLs."""


def require(value, state="malformed"):
    if not value:
        raise ArtifactError(state)


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


transport = module("relay_snapshot_transport", "repository_capture_artifact.py")


def encoded(value):
    return transport.encoded(value)


def digest(content):
    return hashlib.sha256(content).hexdigest()


def artifact_name(identity):
    return ("repository-intelligence-snapshot-v1-" + str(identity["repository_id"]) + "-"
            + identity["source_commit"] + "-" + str(identity["run_id"]) + "-" + str(identity["run_attempt"]))


def identity(args):
    expected, _unused, observed = transport.identity(SimpleNamespace(
        repository=args.repository, repository_id=args.repository_id, source_commit=args.source_commit,
        run_id=args.run_id, run_attempt=args.run_attempt, event_name=args.event_name,
        visibility=args.visibility, observed_at=args.as_of))
    expected.pop("observed_at")
    return expected, observed


def output(args, values):
    if args.github_output:
        with transport.safe(Path(args.github_output)).open("a", encoding="utf-8") as handle:
            for name, value in values.items():
                require("\n" not in str(value) and "\r" not in str(value))
                handle.write(f"{name}={value}\n")


def write(path, value):
    content = encoded(value)
    require(len(content) <= 131072)
    descriptor, name = tempfile.mkstemp(dir=transport.safe(path.parent))
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
        os.replace(name, path)
        path.chmod(0o600)
    finally:
        Path(name).unlink(missing_ok=True)


def provider_document(url, token, deadline):
    try:
        data = transport.request(url, token, 262144, deadline)
    except (OSError, ValueError):
        raise ArtifactError("inaccessible") from None
    return transport.load(data, 262144)


def selected(args):
    fields = (args.baseline_artifact_id, args.baseline_artifact_digest, args.baseline_source_commit,
              args.baseline_run_id, args.baseline_run_attempt)
    if not any(fields):
        require(args.expected_baseline == "none")
        return None
    require(all(fields) and transport.SHA.fullmatch(args.baseline_source_commit))
    checksum = args.baseline_artifact_digest.removeprefix("sha256:")
    require(HASH.fullmatch(checksum))
    pair = args.expected_baseline.split(":")
    require(len(pair) == 2 and all(HASH.fullmatch(value) for value in pair))
    require(transport.integer(args.baseline_run_attempt) <= 1000000)
    return {"id": transport.integer(args.baseline_artifact_id), "sha256": checksum,
            "source_commit": args.baseline_source_commit, "run_id": transport.integer(args.baseline_run_id),
            "run_attempt": transport.integer(args.baseline_run_attempt),
            "snapshot_sha256": pair[0], "projection_sha256": pair[1]}


def archive_files(archive):
    with zipfile.ZipFile(io.BytesIO(archive)) as package:
        members = package.infolist()
        require(len(members) == 3 and {item.filename for item in members} == {MANIFEST, *FILES})
        content = {}
        for item in members:
            mode = item.external_attr >> 16
            limit = 65536 if item.filename == MANIFEST else MAX_FILE
            require(not item.is_dir() and not item.flag_bits & 1
                    and item.compress_type in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                    and (not stat.S_IFMT(mode) or stat.S_ISREG(mode)) and not mode & 0o111
                    and 0 < item.file_size <= limit and item.file_size <= item.compress_size * 200 + 1024)
            with package.open(item) as handle:
                data = handle.read(limit + 1)
            require(len(data) == item.file_size and item.filename not in content)
            content[item.filename] = data
        return content


def admission(args, choice, current_identity, observed, root, retention, runtime_identity):
    """Select one prior successful attempt and one immutable archive, never a list/latest lookup."""
    token = os.environ.get("COMPARE_GITHUB_TOKEN", "")
    require(token and len(token) <= 4096 and not any(ord(char) < 32 for char in token), "inaccessible")
    require(choice["run_id"] != current_identity["run_id"])
    deadline = time.monotonic() + 60
    api = "https://api.github.com/repos/" + args.repository + "/actions/"
    run = provider_document(api + f"runs/{choice['run_id']}/attempts/{choice['run_attempt']}", token, deadline)
    require(run.get("id") == choice["run_id"] and run.get("run_attempt") == choice["run_attempt"]
            and run.get("head_sha") == choice["source_commit"] and run.get("status") == "completed"
            and run.get("conclusion") == "success" and run.get("event") in {"push", "workflow_dispatch"})
    repository = run.get("repository", {})
    require(isinstance(repository, dict) and repository.get("id") == current_identity["repository_id"]
            and repository.get("full_name") == args.repository and repository.get("private") is False, "wrong_repository")
    expected = {**current_identity, "source_commit": choice["source_commit"], "run_id": choice["run_id"],
                "run_attempt": choice["run_attempt"], "event_name": run["event"]}
    start = transport.instant(run.get("run_started_at"), provider=True)
    end = transport.instant(run.get("updated_at"), provider=True)
    artifact = provider_document(api + f"artifacts/{choice['id']}", token, deadline)
    bound = artifact.get("workflow_run", {})
    require(isinstance(bound, dict) and artifact.get("id") == choice["id"]
            and artifact.get("name") == artifact_name(expected)
            and artifact.get("digest") == "sha256:" + choice["sha256"]
            and type(artifact.get("size_in_bytes")) is int and 0 < artifact["size_in_bytes"] <= MAX_ARCHIVE
            and bound.get("id") == expected["run_id"] and bound.get("repository_id") == expected["repository_id"]
            and bound.get("head_sha") == expected["source_commit"])
    created = transport.instant(artifact.get("created_at"), provider=True)
    require(start <= created <= end and created <= observed)
    if artifact.get("expired") is True or transport.instant(artifact.get("expires_at"), provider=True) <= observed:
        raise ArtifactError("expired")
    require(artifact.get("expired") is False)
    try:
        archive = transport.request(api + f"artifacts/{choice['id']}/zip", token, MAX_ARCHIVE, deadline, allow_redirect=True)
    except (OSError, ValueError):
        raise ArtifactError("inaccessible") from None
    require(digest(archive) == choice["sha256"])
    content = archive_files(archive)
    manifest = transport.load(content[MANIFEST], 65536)
    require(set(manifest) == {"schema", "visibility", "repository", "repository_id", "source_commit", "run_id",
                            "run_attempt", "event_name", "retained_at", "runtime_lock_sha256", "normalization_profile", "boundary", "files"}
            and manifest["schema"] == SCHEMA and manifest["visibility"] == "public"
            and all(manifest.get(key) == value for key, value in expected.items())
            and all(type(manifest[key]) is int for key in ("repository_id", "run_id", "run_attempt")))
    retained = transport.instant(manifest.get("retained_at"))
    require(start <= retained <= created)
    require(manifest["normalization_profile"] == args.normalization_profile, "incompatible")
    require(manifest["runtime_lock_sha256"] == runtime_identity["lock_sha256"], "incompatible")
    rows = manifest["files"]
    require(isinstance(rows, list) and len(rows) == 2)
    for row, name in zip(rows, FILES, strict=True):
        require(isinstance(row, dict) and set(row) == {"path", "sha256", "size_bytes"}
                and row["path"] == name and row["sha256"] == digest(content[name])
                and type(row["size_bytes"]) is int and row["size_bytes"] == len(content[name]))
    destination = root / "baseline"
    destination.mkdir()
    for name in FILES:
        (destination / name).write_bytes(content[name])
        (destination / name).chmod(0o600)
    try:
        baseline_args = SimpleNamespace(runtime=args.runtime, repository=args.repository, observed_at=args.as_of)
        captured = retention.accepted_snapshot(destination / "snapshot.json", destination / "projection.json", baseline_args)
    except retention.RetentionError as error:
        state = {"REPOSITORY": "wrong_repository", "INCOMPATIBLE": "incompatible", "VISIBILITY": "redacted",
                 "INACCESSIBLE": "inaccessible"}.get(str(error), "malformed")
        raise ArtifactError(state) from None
    require(captured["snapshot_sha256"] == choice["snapshot_sha256"]
            and captured["projection_sha256"] == choice["projection_sha256"], "incompatible")
    require(manifest["boundary"] == retention.boundary(captured), "incompatible")
    return captured, manifest, {**choice, "name": artifact_name(expected), "size_bytes": len(archive),
                                "manifest_sha256": digest(content[MANIFEST])}


def native_args(args, root):
    return SimpleNamespace(command="refresh", runtime=args.runtime, repository_root=args.repository_root,
        repository=args.repository, source_commit=args.source_commit, observed_at=args.as_of,
        snapshot=args.source_directory / "snapshot.json", projection=args.source_directory / "projection.json",
        store=root / "store", output=root / "comparison", expected_baseline="none", baseline=None,
        baseline_projection=None, maximum_baseline_age_seconds=args.maximum_baseline_age_seconds,
        maximum_current_age_seconds=args.maximum_current_age_seconds, retention_state="unchanged")


def retention_adapter(profile):
    """Closed normalization seam; profile migrations must supply an exact owner adapter."""
    if profile == "legacy-adr":
        return module("relay_artifact_retention", "retain_repository_intelligence_snapshots.py")
    if profile == "search-attribution-v1":
        helper = module("relay_artifact_search_normalization", "repository_search_normalization.py")
        require(helper.PROFILE == profile, "incompatible")
        return helper.retention_adapter()
    raise ArtifactError("incompatible")


def prepare(args, root):
    expected, observed = identity(args)
    choice = selected(args)
    require(1 <= args.retention_days <= 90)
    for limit in (args.maximum_baseline_age_seconds, args.maximum_current_age_seconds):
        require(1 <= limit <= 31536000)
    args.source_directory = transport.safe(args.source_directory)
    require(args.source_directory.is_dir())
    if args.runtime is None:
        if args.normalization_profile == "legacy-adr":
            acquisition = module("relay_compare_runtime_acquisition", "prepare_repository_adr_build.py")
        else:
            require(args.normalization_profile == "search-attribution-v1", "incompatible")
            acquisition = module("relay_compare_search_acquisition", "repository_search_normalization.py")
            require(acquisition.PROFILE == args.normalization_profile, "incompatible")
        with tempfile.TemporaryDirectory(prefix="relay-compare-runtime-", dir=transport.safe(args.runner_temp)) as temporary:
            python, runtime = acquisition.acquire(Path(temporary))
            replay = [str(python), "-I", str(Path(__file__).resolve()), *sys.argv[1:], "--runtime", str(runtime)]
            return subprocess.run(replay, check=False).returncode
    args.runtime = transport.safe(args.runtime)
    require(not args.runtime.is_relative_to(transport.safe(args.repository_root)))
    retention = retention_adapter(args.normalization_profile)
    _lock, runtime_identity = retention.base.runtime_files(args.runtime, lock_path=retention.adr.LOCK_PATH)
    native = native_args(args, root)
    current = retention.accepted_snapshot(native.snapshot, native.projection, native, current=True)
    require(current["age"] <= args.maximum_current_age_seconds, "expired")
    require(current["snapshot"]["coverage"]["record_status"] != "stale" and not any(
        claim["freshness"] == "stale" for claim in current["snapshot"]["coverage"]["domains"].values()), "expired")
    require(retention.retainable(None, current["snapshot"]), "incompatible")
    current_directory = root / "current"
    current_directory.mkdir()
    for name, content in (("projection.json", current["projection_bytes"]), ("snapshot.json", current["snapshot_bytes"])):
        (current_directory / name).write_bytes(content)
        (current_directory / name).chmod(0o600)
    # Compare and package one frozen admission, even if a concurrent producer
    # changes its original work directory while provider intake is in flight.
    native.projection = current_directory / "projection.json"
    native.snapshot = current_directory / "snapshot.json"
    state, baseline_receipt = "missing", None
    if choice is not None:
        try:
            before, manifest, baseline_receipt = admission(args, choice, expected, observed, root, retention, runtime_identity)
            store = retention.store_root(native)
            retention.atomic(store / "snapshots" / (before["snapshot_sha256"] + ".json"), before["snapshot_bytes"])
            retention.atomic(store / "projections" / (before["projection_sha256"] + ".json"), before["projection_bytes"])
            retention.atomic(store / "baseline.json", encoded({"schema": retention.POINTER_SCHEMA,
                "repository": args.repository, "snapshot_sha256": before["snapshot_sha256"],
                "projection_sha256": before["projection_sha256"], "retained_at": manifest["retained_at"],
                "runtime_lock_sha256": manifest["runtime_lock_sha256"]}))
            native.expected_baseline = before["snapshot_sha256"]
            state = "available"
        except (ArtifactError, OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
            state = str(error) if isinstance(error, ArtifactError) and str(error) in STATES else "malformed"
            receipt = {"schema": RECEIPT, "repository": args.repository, "source_commit": args.source_commit,
                "observed_at": args.as_of, "status": "unavailable", "baseline_state": state,
                "baseline_artifact": choice, "current": retention.boundary(current),
                "normalization_profile": args.normalization_profile,
                "retention": "unchanged", "retention_days": args.retention_days, "artifact": None}
            write(root / "artifact.receipt.json", receipt)
            output(args, {"receipt-path": str(root / "artifact.receipt.json"), "status": "unavailable",
                          "baseline-state": state, "retention-eligible": "false", "comparison-path": ""})
            output(args, {"snapshot-path": str(current_directory / "snapshot.json"),
                          "projection-path": str(current_directory / "projection.json")})
            return 0
    receipt, comparison = retention.execute(native)
    retention.write_attempt(native.output, receipt, comparison)
    eligible = receipt["retention"] == "retained"
    if eligible:
        manifest = {"schema": SCHEMA, "visibility": "public", **expected, "retained_at": args.as_of,
            "normalization_profile": args.normalization_profile,
            "runtime_lock_sha256": runtime_identity["lock_sha256"],
            "boundary": {**retention.boundary(current), "input_sha256": current["snapshot_sha256"],
                         "projection_input_sha256": current["projection_sha256"]},
            "files": [{"path": name, "size_bytes": len((current_directory / name).read_bytes()),
                       "sha256": digest((current_directory / name).read_bytes())} for name in FILES]}
        write(current_directory / MANIFEST, manifest)
    operational = {"schema": RECEIPT, "repository": args.repository, "source_commit": args.source_commit,
        "observed_at": args.as_of, "status": receipt["status"], "baseline_state": receipt["baseline_state"],
        "normalization_profile": args.normalization_profile,
        "baseline_artifact": baseline_receipt, "current": retention.boundary(current),
        "retention": "candidate" if eligible else "unchanged", "retention_days": args.retention_days, "artifact": None}
    write(root / "artifact.receipt.json", operational)
    output(args, {"receipt-path": str(root / "artifact.receipt.json"), "status": receipt["status"],
        "baseline-state": receipt["baseline_state"], "retention-eligible": str(eligible).lower(),
        "artifact-name": artifact_name(expected) if eligible else "", "artifact-directory": str(current_directory) if eligible else "",
        "snapshot-path": str(current_directory / "snapshot.json"), "projection-path": str(current_directory / "projection.json"),
        "comparison-path": str(native.output / "comparison.json") if comparison is not None else "",
        "retention-receipt-path": str(native.output / "retention.receipt.json"),
        "next-baseline-lease": current["snapshot_sha256"] + ":" + current["projection_sha256"] if eligible else ""})
    return 0


def finalize(args):
    receipt_path = transport.safe(args.receipt)
    value = transport.load(transport.read(receipt_path, 131072), 131072)
    require(value.get("schema") == RECEIPT and args.upload_outcome in {"success", "failure", "cancelled", "skipped"})
    artifact = None
    if args.upload_outcome == "success":
        require(value.get("retention") == "candidate")
        checksum = args.upload_digest.removeprefix("sha256:")
        require(HASH.fullmatch(checksum))
        artifact = {"id": transport.integer(args.upload_id), "sha256": checksum}
        value["retention"] = "uploaded"
    elif value.get("retention") == "candidate":
        value["retention"] = "unchanged" if args.upload_outcome == "skipped" else "unknown"
    value["artifact"] = artifact
    value["upload_outcome"] = args.upload_outcome
    write(receipt_path, value)
    return 0


def parser():
    result = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = result.add_subparsers(dest="command", required=True)
    prepare_command = commands.add_parser("prepare", allow_abbrev=False)
    for name in ("repository", "repository-id", "source-commit", "run-id", "run-attempt", "event-name", "visibility", "as-of", "expected-baseline"):
        prepare_command.add_argument("--" + name, required=True)
    for name in ("runner-temp", "repository-root", "source-directory"):
        prepare_command.add_argument("--" + name, required=True, type=Path)
    prepare_command.add_argument("--runtime", type=Path)
    prepare_command.add_argument("--normalization-profile", default="legacy-adr")
    for name in ("baseline-artifact-id", "baseline-artifact-digest", "baseline-source-commit", "baseline-run-id", "baseline-run-attempt"):
        prepare_command.add_argument("--" + name, default="")
    prepare_command.add_argument("--maximum-baseline-age-seconds", type=int, default=2592000)
    prepare_command.add_argument("--maximum-current-age-seconds", type=int, default=86400)
    prepare_command.add_argument("--retention-days", type=int, default=30)
    prepare_command.add_argument("--github-output", default="")
    final = commands.add_parser("finalize", allow_abbrev=False)
    final.add_argument("--receipt", type=Path, required=True)
    final.add_argument("--upload-outcome", required=True)
    final.add_argument("--upload-id", default="")
    final.add_argument("--upload-digest", default="")
    return result


def main():
    root = None
    args = parser().parse_args()
    try:
        if args.command == "finalize":
            return finalize(args)
        consumer, temporary = transport.safe(args.repository_root), transport.safe(args.runner_temp)
        require(temporary.is_dir() and not temporary.is_relative_to(consumer))
        root = Path(tempfile.mkdtemp(prefix="relay-compare-artifact-", dir=temporary))
        return prepare(args, root)
    except Exception:
        # Never expose input text, network exceptions, archive paths or signed URLs.
        if root is not None:
            shutil.rmtree(root, ignore_errors=True)
            try:
                root.mkdir()
                write(root / "artifact.receipt.json", {"schema": RECEIPT, "status": "denied",
                    "baseline_state": "not_evaluated", "retention": "unchanged", "artifact": None,
                    "error_code": "SOURCE_OR_INTAKE_DENIED"})
                output(args, {"receipt-path": str(root / "artifact.receipt.json"), "status": "denied",
                    "baseline-state": "not_evaluated", "retention-eligible": "false", "comparison-path": ""})
            except (OSError, ValueError):
                pass
        print("Snapshot artifact: source, baseline lease or retention admission denied", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
