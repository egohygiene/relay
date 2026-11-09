#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Compare reviewed public snapshots and retain an immutable local baseline.

This is an offline, consumer-owned artifact adapter. It neither collects source
evidence nor publishes or changes canonical repository content.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import importlib.util
import os
from pathlib import Path
import re
import sys
import tempfile

import jsonschema

_spec = importlib.util.spec_from_file_location(
    "relay_compare_adr_runtime", Path(__file__).with_name("collect_repository_adrs.py"))
adr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adr)
base = adr.base
SCHEMA = "egohygiene.relay.snapshot-retention-receipt/v1"
POINTER_SCHEMA = "egohygiene.relay.snapshot-baseline/v1"
SHA256 = re.compile(r"[0-9a-f]{64}")
MAX_AGE = 31536000
MESSAGES = {
    "INPUT": "Supply bounded public snapshots, full source revisions and explicit UTC observation times.",
    "PIN": "Prepare the exact ADR collector runtime selected by this Relay revision.",
    "PATH": "Use a new attempt directory and regular, separate retention storage without symbolic links.",
    "VISIBILITY": "Use a separately reviewed public-only snapshot; this adapter is not a redaction engine.",
    "INCOMPATIBLE": "Rebuild the snapshot with the locked Observatory alpha.2 generator and upstream contracts.",
    "REPOSITORY": "Select a baseline and current snapshot for the same declared repository.",
    "REVISION": "Regenerate current evidence at the declared represented source commit.",
    "STALE": "Recapture current evidence; stale snapshots cannot replace the retained baseline.",
    "LEASE": "Inspect the current baseline digest and retry with that explicit expected baseline.",
    "STORAGE": "Restore the immutable retained object or select a reviewed recovery baseline.",
    "COVERAGE": "Retain the last good baseline until collected domains recover without lost or downgraded inventory.",
    "INACCESSIBLE": "Restore authorized read access to the retained public artifact without changing its identity.",
}


class RetentionError(ValueError):
    """Closed, non-sensitive operational diagnostic."""


def fail(code):
    raise RetentionError(code)


def read(path, *, limit=base.MAX_OUTPUT):
    try:
        return base.read_file(path, limit)
    except PermissionError:
        fail("INACCESSIBLE")
    except (base.CollectorError, OSError):
        fail("INPUT")


def load(path):
    return base.load_json(read(path))


def atomic(path, content):
    path = base.safe_path(path)
    if path.exists() and not path.is_file():
        fail("PATH")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def projection(snapshot):
    upstream = snapshot["upstream"]
    result = {**snapshot["graph"], "schema": upstream["schema"],
              "contract_version": upstream["contract_version"],
              "projection_id": upstream["projection_id"],
              "repository": snapshot["repository"]["repository"],
              "represented_commit": snapshot["represented_commit"],
              "observed_at": snapshot["observed_at"], "visibility": snapshot["visibility"]}
    if upstream["contract_version"] == "1.0.0-alpha.2":
        result["collection_coverage"] = snapshot["coverage"]["domains"]
    return result


def accepted_snapshot(path, args, observatory, *, current=False):
    raw = read(path)
    value = base.load_json(raw)
    schema = load(args.runtime / "observatory/schemas/repository-intelligence-read-model.v1.schema.json")
    if not jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).is_valid(value):
        fail("INCOMPATIBLE")
    if value["contract_version"] != "1.0.0-alpha.2" or value["upstream"]["contract_version"] != "1.0.0-alpha.2":
        fail("INCOMPATIBLE")
    if value["repository"]["repository"] != args.repository:
        fail("REPOSITORY")
    if current and value["represented_commit"] != args.source_commit:
        fail("REVISION")
    graph = value["graph"]
    if (value["visibility"] != "public" or graph["redactions"] or graph["extensions"]
            or value["extensions"] or any(record.get("visibility") != "public"
               for name in ("sources", "entities", "events") for record in graph[name])):
        fail("VISIBILITY")
    # Captures must already be reviewed public projections. Reject obvious
    # credentials, emails and machine paths without echoing their contents.
    if base.SECRET.search(raw.decode("utf-8")):
        fail("VISIBILITY")
    projected = projection(value)
    normalized, validation = adr.normalize(args.runtime, projected)
    if normalized is None or validation["coverage"] != "valid" or normalized != value:
        fail("INCOMPATIBLE")
    age = (base.utc(args.observed_at) - base.utc(value["observed_at"])).total_seconds()
    if age < 0:
        fail("INPUT")
    content = base.json_bytes(value)
    return value, content, base.digest(content), age, base.digest(raw)


def boundary(value, digest, input_digest):
    return {"repository": value["repository"]["repository"],
            "represented_commit": value["represented_commit"],
            "snapshot_id": value["snapshot_id"], "observed_at": value["observed_at"],
            "contract_version": value["contract_version"], "snapshot_sha256": digest,
            "input_sha256": input_digest,
            "upstream_digest": value["upstream"]["digest"],
            "collection_coverage": value["coverage"]["domains"]}


def store_root(args):
    path = base.safe_path(args.store) / args.repository.replace("/", "--")
    base.safe_path(path)
    if path.exists() and not path.is_dir():
        fail("PATH")
    return path


@contextmanager
def lease(root):
    root.mkdir(parents=True, exist_ok=True)
    path = base.safe_path(root / ".baseline.lock")
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            fail("LEASE")
        yield
    finally:
        os.close(descriptor)


def pointer(root, repository):
    path = base.safe_path(root / "baseline.json")
    if not path.exists():
        return None
    try:
        value = load(path)
        if (set(value) != {"schema", "repository", "snapshot_sha256", "retained_at", "runtime_lock_sha256"}
                or value["schema"] != POINTER_SCHEMA or value["repository"] != repository
                or not isinstance(value["snapshot_sha256"], str)
                or not SHA256.fullmatch(value["snapshot_sha256"])
                or not isinstance(value["runtime_lock_sha256"], str)
                or not SHA256.fullmatch(value["runtime_lock_sha256"])):
            fail("STORAGE")
        base.utc(value["retained_at"])
        return value
    except (ValueError, TypeError, KeyError, OSError):
        fail("STORAGE")


def baseline(args, root, observatory, selected):
    if args.baseline is None and selected is None:
        return None, "missing", None
    path = args.baseline if args.baseline is not None else root / "snapshots" / (selected["snapshot_sha256"] + ".json")
    if not path.exists():
        return None, "missing" if args.baseline is not None else "inaccessible", None
    try:
        value, content, digest, age, input_digest = accepted_snapshot(path, args, observatory)
        if selected is not None and args.baseline is None and digest != selected["snapshot_sha256"]:
            fail("STORAGE")
        if base.utc(value["observed_at"]) > base.utc(args.current_observed_at):
            fail("INPUT")
        status = "expired" if age > args.maximum_baseline_age_seconds else "available"
        return (value, digest, input_digest), status, None
    except RetentionError as error:
        code = str(error)
        state = {"REPOSITORY": "wrong_repository", "INCOMPATIBLE": "incompatible",
                 "VISIBILITY": "redacted", "STORAGE": "malformed",
                 "INACCESSIBLE": "inaccessible"}.get(code, "malformed")
        return None, state, code
    except (base.CollectorError, ValueError, TypeError, KeyError, OSError, RecursionError):
        return None, "malformed", "INPUT"


def partial(value):
    return any(claim["collection"] in {"partial", "failed", "unavailable", "uncollected"}
               or claim["freshness"] in {"unknown", "stale"}
               for claim in value["coverage"]["domains"].values())


def retainable(before, current):
    claims = current["coverage"]["domains"]
    if not any(claim["collection"] in {"observed", "observed_empty", "partial", "not_applicable"}
               for claim in claims.values()) or any(claim["collection"] == "failed" for claim in claims.values()):
        return False
    if before is not None:
        for name, prior in before[0]["coverage"]["domains"].items():
            state = claims[name]["collection"]
            if prior["collection"] in {"observed", "observed_empty", "partial", "not_applicable"} and state in {
                    "uncollected", "failed", "unavailable"}:
                return False
            if prior["collection"] in {"observed", "observed_empty"} and state == "partial":
                return False
    return True


def execute(args):
    if not base.REPOSITORY.fullmatch(args.repository) or not base.SHA.fullmatch(args.source_commit):
        fail("INPUT")
    base.utc(args.observed_at)
    for value in (args.maximum_baseline_age_seconds, args.maximum_current_age_seconds):
        if not 1 <= value <= MAX_AGE:
            fail("INPUT")
    if args.command == "refresh" and args.baseline is not None:
        fail("INPUT")
    lock, runtime = base.runtime_files(args.runtime, lock_path=adr.LOCK_PATH)
    observatory = base.module(args.runtime / "observatory/src/observatory/intelligence.py", "pinned_retention_observatory")
    current, content, digest, age, input_digest = accepted_snapshot(args.snapshot, args, observatory, current=True)
    args.current_observed_at = current["observed_at"]
    # Age is operational evidence and never changes the immutable snapshot.
    if age > args.maximum_current_age_seconds or current["coverage"]["record_status"] == "stale" or any(
            claim["freshness"] == "stale" for claim in current["coverage"]["domains"].values()):
        fail("STALE")
    root = store_root(args)
    selected = pointer(root, args.repository)
    if selected is not None and base.utc(selected["retained_at"]) > base.utc(args.observed_at):
        fail("INPUT")
    expected = selected["snapshot_sha256"] if selected else "none"
    if args.command == "refresh" and args.expected_baseline != expected:
        fail("LEASE")
    before, state, code = baseline(args, root, observatory, selected)
    comparison = None
    status = "unavailable"
    usable = retainable(before, current)
    if before is not None and state == "available" and usable:
        comparison = observatory.compare_snapshots(before[0], current)
        status = "partial" if partial(before[0]) or partial(current) else "ready"
    receipt = {"schema": SCHEMA, "publication": "denied", "status": status,
               "observed_at": args.observed_at, "repository": args.repository,
               "current": boundary(current, digest, input_digest), "baseline": boundary(*before) if before else None,
               "baseline_state": state, "diagnostics": ([code] if code else []) + ([] if usable else ["COVERAGE"]),
               "baseline_retention_lock_sha256": selected["runtime_lock_sha256"] if selected else None,
               "limits": {"maximum_baseline_age_seconds": args.maximum_baseline_age_seconds,
                          "maximum_current_age_seconds": args.maximum_current_age_seconds},
               "runtime": {**runtime, "observatory_revision": lock["sources"]["observatory"]["revision"],
                           "source_revisions": {name: pin["revision"] for name, pin in lock["sources"].items()},
                           "adapter_sha256": base.digest(Path(__file__).read_bytes()),
                           "normalization_adapter_sha256": base.digest(Path(adr.__file__).read_bytes()),
                           "shared_runtime_sha256": base.digest(Path(base.__file__).read_bytes())},
               "comparison_sha256": base.digest(base.json_bytes(comparison)) if comparison else None,
               "retention": "unchanged"}
    # A failed/malformed baseline is a recovery event, never implicit permission
    # to replace a corrupt or inaccessible retention surface.
    if args.command == "refresh":
        if state not in {"available", "expired", "missing"} or (selected is not None and before is None):
            return receipt, comparison
        if not usable:
            receipt["retention"] = "denied"
            return receipt, comparison
        with lease(root):
            latest = pointer(root, args.repository)
            if (latest["snapshot_sha256"] if latest else "none") != args.expected_baseline:
                fail("LEASE")
            target = base.safe_path(root / "snapshots" / (digest + ".json"))
            if target.exists():
                if read(target) != content:
                    fail("STORAGE")
            else:
                atomic(target, content)
            atomic(root / "baseline.json", base.json_bytes({"schema": POINTER_SCHEMA,
                   "repository": args.repository, "snapshot_sha256": digest,
                   "retained_at": args.observed_at, "runtime_lock_sha256": runtime["lock_sha256"]}))
            receipt["retention"] = "retained"
    return receipt, comparison


def write_attempt(output, receipt, comparison=None):
    output = base.safe_path(output)
    if output.exists():
        fail("PATH")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        stage = Path(temporary) / "attempt"
        stage.mkdir()
        (stage / "retention.receipt.json").write_bytes(base.json_bytes(receipt))
        if comparison is not None:
            content = base.json_bytes(comparison)
            if len(content) > base.MAX_OUTPUT:
                fail("INPUT")
            (stage / "comparison.json").write_bytes(content)
        stage.rename(output)


def parser():
    result = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = result.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("prepare", allow_abbrev=False)
    for owner in ("hygiene", "egolint", "observatory"):
        setup.add_argument("--" + owner, type=Path, required=True)
    setup.add_argument("--cargo", type=Path, default=Path("cargo"))
    setup.add_argument("--output", type=Path, required=True)
    for name in ("compare", "refresh"):
        command = commands.add_parser(name, allow_abbrev=False)
        for field in ("runtime", "snapshot", "store", "output"):
            command.add_argument("--" + field, type=Path, required=True)
        command.add_argument("--repository-root", type=Path, required=True)
        for field in ("repository", "source-commit", "observed-at"):
            command.add_argument("--" + field, required=True)
        command.add_argument("--baseline", type=Path)
        command.add_argument("--maximum-baseline-age-seconds", type=int, default=2592000)
        command.add_argument("--maximum-current-age-seconds", type=int, default=86400)
        if name == "refresh":
            command.add_argument("--expected-baseline", required=True)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    can_write_receipt = False
    try:
        if args.command == "prepare":
            base.prepare(args, lock_path=adr.LOCK_PATH, reproducible=True)
            return 0
        output, store = base.safe_path(args.output), base.safe_path(args.store)
        consumer = base.safe_path(args.repository_root)
        if (output.exists() or output.is_relative_to(store) or store.is_relative_to(output)
                or output.is_relative_to(consumer) or store.is_relative_to(consumer)):
            fail("PATH")
        can_write_receipt = True
        receipt, comparison = execute(args)
        write_attempt(output, receipt, comparison)
        print("snapshot comparison retained locally; publication denied")
        return 0 if comparison is not None and receipt["retention"] != "denied" and not (
            args.command == "refresh" and receipt["retention"] == "unchanged") else 2
    except (RetentionError, base.CollectorError, OSError, ValueError, TypeError, KeyError,
            ImportError, RuntimeError, AttributeError, OverflowError,
            RecursionError, jsonschema.exceptions.SchemaError):
        error = sys.exception()
        code = str(error) if isinstance(error, (RetentionError, base.CollectorError)) and str(error) in MESSAGES else "INPUT"
        if can_write_receipt:
            try:
                write_attempt(args.output, {"schema": SCHEMA, "publication": "denied", "status": "denied",
                                           "diagnostics": [code], "remediation": MESSAGES[code],
                                           "retention": "unchanged"})
            except (RetentionError, base.CollectorError, OSError):
                pass
        print("snapshot retention: " + code, file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
