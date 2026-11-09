#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Acquire exact public repository artifacts and retain an ordinary fleet handoff.

No repository discovery, latest-run lookup, consumer code execution or publisher
is included. Captured input replays use the same admission path as provider reads.
"""

from __future__ import annotations

import argparse
from datetime import timedelta
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import zipfile

SCRIPTS = Path(__file__).resolve().parent
SCHEMA = "egohygiene.relay.public-fleet-artifact/v1"
PLAN = "egohygiene.relay.public-fleet-artifact-plan/v1"
MAX_PLAN = 262144
MAX_FLEET = 64 * 1024 * 1024
STATES = {"missing", "available", "expired", "inaccessible", "incompatible", "malformed", "wrong_repository"}
HASH = re.compile(r"[0-9a-f]{64}")


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


snapshot = module("relay_fleet_snapshot_artifact", "repository_compare_artifact.py")
transport = snapshot.transport


def require(value, state="malformed"):
    if not value:
        raise snapshot.ArtifactError(state)


def write(path, content):
    path = transport.safe(path)
    require(not path.exists())
    require(len(content) <= MAX_FLEET)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    path.chmod(0o600)


def plan(args):
    value = transport.load(transport.read(args.plan, MAX_PLAN), MAX_PLAN)
    require(set(value) == {"schema", "organization", "visibility", "catalog_revision", "repositories"}
            and value["schema"] == PLAN and value["organization"] == "egohygiene"
            and value["visibility"] == "public" and isinstance(value["repositories"], list))
    # Do not inspect artifact identities, paths or digests before public admission.
    requested = {row.get("repository") for row in value["repositories"]
                 if isinstance(row, dict) and isinstance(row.get("repository"), str)}
    catalog = module("relay_fleet_artifact_catalog", "public_catalog_admission.py")
    rows, metadata = catalog.load(args.catalog_root, requested)
    require(value["catalog_revision"] == metadata["revision"], "incompatible")
    public = {row["full_name"]: row for row in rows}
    selected = [row for row in value["repositories"]
                if isinstance(row, dict) and row.get("repository") in public]
    require(len(selected) <= 64 and len({row["repository"] for row in selected}) == len(selected))
    for row in selected:
        require(set(row) == {"repository", "represented_commit", "candidate", "last_known"}
                and isinstance(row["represented_commit"], str)
                and transport.SHA.fullmatch(row["represented_commit"]))
        for key in ("candidate", "last_known"):
            choice = row[key]
            if choice is None:
                continue
            require(isinstance(choice, dict) and set(choice) == {
                "artifact_id", "artifact_sha256", "source_commit", "run_id", "run_attempt"})
            require(isinstance(choice["artifact_sha256"], str) and HASH.fullmatch(choice["artifact_sha256"])
                    and isinstance(choice["source_commit"], str) and transport.SHA.fullmatch(choice["source_commit"]))
            for field in ("artifact_id", "run_id", "run_attempt"):
                require(type(choice[field]) is int)
                transport.integer(choice[field])
            require(choice["run_attempt"] <= 1000000)
    import jsonschema
    schema = transport.load(transport.read(SCRIPTS.parent / "schemas/public-fleet-artifact-plan.v1.schema.json", MAX_PLAN), MAX_PLAN)
    require(jsonschema.Draft202012Validator(schema).is_valid({**value, "repositories": selected}))
    return sorted(selected, key=lambda row: row["repository"]), public, metadata


def document(url, token, deadline):
    try:
        return transport.load(transport.request(url, token, MAX_PLAN, deadline), MAX_PLAN)
    except (OSError, ValueError):
        raise snapshot.ArtifactError("inaccessible") from None


def captured(args, repository, choice, slot):
    """Fetch only an admitted identity; offline replay never supplies executable code."""
    folder = args.capture_root / slot
    if args.captured_inputs is not None:
        folder = transport.safe(args.captured_inputs) / slot
        return (transport.load(transport.read(folder / "run.json", MAX_PLAN), MAX_PLAN),
                transport.load(transport.read(folder / "artifact.json", MAX_PLAN), MAX_PLAN),
                transport.read(folder / "artifact.zip", snapshot.MAX_ARCHIVE))
    token = os.environ.get("FLEET_GITHUB_TOKEN", "")
    require(len(token) <= 4096 and not any(ord(char) < 32 for char in token), "inaccessible")
    deadline = time.monotonic() + 60
    api = "https://api.github.com/repos/" + repository + "/actions/"
    run = document(api + f"runs/{choice['run_id']}/attempts/{choice['run_attempt']}", token, deadline)
    artifact = document(api + f"artifacts/{choice['artifact_id']}", token, deadline)
    # Validate metadata before downloading a possibly expired or foreign archive.
    provider_identity(args, repository, choice, run, artifact)
    try:
        archive = transport.request(api + f"artifacts/{choice['artifact_id']}/zip", token,
                                    snapshot.MAX_ARCHIVE, deadline, allow_redirect=True)
    except (OSError, ValueError):
        raise snapshot.ArtifactError("inaccessible") from None
    for name, content in (("run.json", transport.encoded(run)), ("artifact.json", transport.encoded(artifact)),
                          ("artifact.zip", archive)):
        write(folder / name, content)
    return run, artifact, archive


def provider_identity(args, repository, choice, run, artifact):
    selected = args.public[repository]
    expected = {"repository": repository, "repository_id": selected["repository_id"],
                "source_commit": choice["source_commit"], "run_id": choice["run_id"],
                "run_attempt": choice["run_attempt"]}
    require(run.get("id") == expected["run_id"] and run.get("run_attempt") == expected["run_attempt"]
            and type(run.get("id")) is int and type(run.get("run_attempt")) is int
            and run.get("head_sha") == expected["source_commit"] and run.get("status") == "completed"
            and run.get("conclusion") == "success" and run.get("event") in {"push", "workflow_dispatch"})
    owner = run.get("repository", {})
    require(isinstance(owner, dict) and owner.get("id") == expected["repository_id"]
            and owner.get("full_name") == repository and owner.get("private") is False, "wrong_repository")
    expected["event_name"] = run["event"]
    bound = artifact.get("workflow_run", {})
    require(isinstance(bound, dict) and artifact.get("id") == choice["artifact_id"]
            and type(artifact.get("id")) is int
            and artifact.get("name") == snapshot.artifact_name(expected)
            and artifact.get("digest") == "sha256:" + choice["artifact_sha256"]
            and type(artifact.get("size_in_bytes")) is int
            and 0 < artifact["size_in_bytes"] <= snapshot.MAX_ARCHIVE
            and bound.get("id") == expected["run_id"] and bound.get("repository_id") == expected["repository_id"]
            and bound.get("head_sha") == expected["source_commit"])
    start = transport.instant(run.get("run_started_at"), provider=True)
    end = transport.instant(run.get("updated_at"), provider=True)
    created = transport.instant(artifact.get("created_at"), provider=True)
    require(start <= created <= end and created <= args.observed)
    if artifact.get("expired") is True or transport.instant(artifact.get("expires_at"), provider=True) <= args.observed:
        raise snapshot.ArtifactError("expired")
    require(artifact.get("expired") is False)
    return expected, start, created


def admit(args, repository, choice, slot):
    run, artifact, archive = captured(args, repository, choice, slot)
    expected, start, created = provider_identity(args, repository, choice, run, artifact)
    require(snapshot.digest(archive) == choice["artifact_sha256"])
    content = snapshot.archive_files(archive)
    manifest = transport.load(content[snapshot.MANIFEST], 65536)
    require(set(manifest) == {"schema", "visibility", "repository", "repository_id", "source_commit", "run_id",
        "run_attempt", "event_name", "retained_at", "runtime_lock_sha256", "normalization_profile", "boundary", "files"}
        and manifest["schema"] == snapshot.SCHEMA and manifest["visibility"] == "public"
        and all(manifest.get(key) == value for key, value in expected.items())
        and all(type(manifest[key]) is int for key in ("repository_id", "run_id", "run_attempt")))
    require(start <= transport.instant(manifest["retained_at"]) <= created)
    profile = manifest["normalization_profile"]
    require(profile in {"legacy-adr", "search-attribution-v1"}, "incompatible")
    lock = SCRIPTS.parent / "contracts" / ("adr-collector.v1.lock.json" if profile == "legacy-adr"
                                            else "search-attribution-normalizer.v1.lock.json")
    require(manifest["runtime_lock_sha256"] == snapshot.digest(transport.read(lock)), "incompatible")
    rows = manifest["files"]
    require(isinstance(rows, list) and len(rows) == 2)
    for row, name in zip(rows, snapshot.FILES, strict=True):
        require(isinstance(row, dict) and set(row) == {"path", "sha256", "size_bytes"}
                and row["path"] == name and row["sha256"] == snapshot.digest(content[name])
                and type(row["size_bytes"]) is int and row["size_bytes"] == len(content[name]))
    projection = transport.load(content["projection.json"], snapshot.MAX_FILE)
    original = transport.load(content["snapshot.json"], snapshot.MAX_FILE)
    boundary = manifest["boundary"]
    require(isinstance(boundary, dict) and boundary.get("repository") == repository
            and boundary.get("represented_commit") == choice["source_commit"]
            and boundary.get("projection_sha256") == snapshot.digest(content["projection.json"])
            and boundary.get("snapshot_sha256") == snapshot.digest(content["snapshot.json"])
            and projection.get("repository") == repository and projection.get("represented_commit") == choice["source_commit"]
            and original.get("repository", {}).get("repository") == repository
            and original.get("represented_commit") == choice["source_commit"], "incompatible")
    # Preserve the exact original projection. The existing assembler validates
    # and normalizes that source; it does not trust or forward captured views.
    path = slot + ".json"
    write(args.artifact_root / path, content["projection.json"])
    return {"path": path, "sha256": snapshot.digest(content["projection.json"]), "kind": "projection",
            "represented_commit": choice["source_commit"]}


def prepare(args):
    require(args.visibility == "public")
    args.observed = transport.instant(args.as_of)
    producer, _unused, _observed = transport.identity(SimpleNamespace(repository=args.repository,
        repository_id=args.repository_id, source_commit=args.source_commit, run_id=args.run_id,
        run_attempt=args.run_attempt, event_name=args.event_name, visibility=args.visibility,
        observed_at=args.as_of))
    producer.pop("observed_at")
    require(1 <= args.retention_days <= 90 and 1 <= args.maximum_age_seconds <= 2678400
            and args.maximum_age_seconds <= args.maximum_last_known_age_seconds <= 31622400)
    args.output = transport.safe(args.output)
    root = transport.safe(args.runner_temp)
    consumer = transport.safe(args.repository_root)
    require(root.is_dir() and not root.is_relative_to(consumer) and not args.output.exists()
            and not args.output.is_relative_to(consumer) and args.output.is_relative_to(root) and args.output != root)
    if args.catalog_root is None:
        catalog = module("relay_fleet_catalog_acquisition", "public_catalog_admission.py")
        with tempfile.TemporaryDirectory(prefix="relay-fleet-catalog-", dir=root) as temporary:
            args.catalog_root = catalog.acquire(Path(temporary))
            return prepare(args)
    require(not args.output.is_relative_to(transport.safe(args.catalog_root)))
    if args.runtime is None:
        acquisition = module("relay_fleet_runtime_acquisition", "prepare_repository_adr_build.py")
        with tempfile.TemporaryDirectory(prefix="relay-fleet-runtime-", dir=root) as temporary:
            python, runtime = acquisition.acquire(Path(temporary), normalization_profile="public-fleet-v1")
            return subprocess.run([str(python), "-I", str(Path(__file__).resolve()), *sys.argv[1:],
                                   "--runtime", str(runtime), "--catalog-root", str(args.catalog_root)], check=False).returncode
    require(not transport.safe(args.runtime).is_relative_to(consumer))
    require(not args.output.is_relative_to(transport.safe(args.runtime)))
    if args.captured_inputs is not None:
        require(not args.output.is_relative_to(transport.safe(args.captured_inputs)))
    selected, args.public, metadata = plan(args)
    args.output.mkdir(mode=0o700)
    args.capture_root = args.output / "captures"
    args.artifact_root = args.output / "repository-inputs"
    args.artifact_root.mkdir()
    local, availability = [], []
    for index, row in enumerate(selected):
        current = {"repository": row["repository"], "represented_commit": row["represented_commit"],
                   "candidate": None, "last_known": None}
        states = {}
        for key in ("candidate", "last_known"):
            choice = row[key]
            state = "missing"
            if choice is not None:
                try:
                    if key == "candidate":
                        require(choice["source_commit"] == row["represented_commit"])
                    current[key] = admit(args, row["repository"], choice, f"{index:02d}-{key}")
                    state = "available"
                except (snapshot.ArtifactError, OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
                    state = str(error) if isinstance(error, snapshot.ArtifactError) and str(error) in STATES else "malformed"
            states[key] = state
        local.append(current)
        availability.append({"repository": row["repository"], **states})
    assembler = module("relay_fleet_handoff_assembler", "assemble_public_fleet.py")
    local_plan = args.output / "local-plan.json"
    write(local_plan, transport.encoded({"schema": "egohygiene.relay.public-fleet-plan/v1", "organization": "egohygiene",
        "visibility": "public", "catalog_revision": metadata["revision"],
        "review_reference": "https://github.com/egohygiene/hygiene/pull/97", "repositories": local}))
    native = SimpleNamespace(runtime=args.runtime, catalog_root=args.catalog_root, artifact_root=args.artifact_root,
        plan=local_plan, observed_at=args.as_of, maximum_age_seconds=args.maximum_age_seconds,
        maximum_last_known_age_seconds=args.maximum_last_known_age_seconds, maximum_catalog_age_days=31,
        catalog_profile="public-catalog-v1")
    result = assembler.assemble(native)
    write(args.output / "public-fleet.review.json", transport.encoded(result))
    bundle = args.output / "handoff"
    bundle.mkdir()
    fleet = result["fleet_snapshot_candidate"]
    state = result["status"]
    manifest = {"schema": SCHEMA, "visibility": "public", "organization": "egohygiene", "status": state,
        "observed_at": args.as_of, "expires_at": (args.observed + timedelta(days=args.retention_days)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "catalog": metadata, "generator": {"repository": "egohygiene/relay", "revision": args.generator_commit,
        "implementation_sha256": snapshot.digest(Path(__file__).read_bytes())},
        "producer": producer, "runtime": result["runtime"],
        "acquisition": "captured-inputs" if args.captured_inputs else "github-read-only",
        "repositories": [{**row, "acquisition": acquisition} for row, acquisition in zip(result["repositories"], availability, strict=True)],
        "files": []}
    if fleet is not None:
        content = transport.encoded(fleet)
        require(snapshot.digest(content) == result["candidate_sha256"])
        write(bundle / "fleet.json", content)
        manifest["files"] = [{"path": "fleet.json", "sha256": snapshot.digest(content), "size_bytes": len(content)}]
    require(assembler.validator(SCRIPTS.parent / "schemas/public-fleet-artifact.v1.schema.json").is_valid(manifest))
    write(bundle / "fleet-artifact.json", transport.encoded(manifest))
    snapshot.output(args, {"status": state, "artifact-directory": str(bundle),
        "manifest-path": str(bundle / "fleet-artifact.json"), "as-of": args.as_of,
        "manifest-sha256": snapshot.digest(transport.read(bundle / "fleet-artifact.json", MAX_FLEET)),
        "fleet-path": str(bundle / "fleet.json") if fleet is not None else "",
        "fleet-sha256": result["candidate_sha256"] or "",
        "review-path": str(args.output / "public-fleet.review.json")})
    return 0


def parser():
    result = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ("plan", "runner-temp", "repository-root", "output"):
        result.add_argument("--" + name, type=Path, required=True)
    result.add_argument("--catalog-root", type=Path)
    result.add_argument("--runtime", type=Path)
    result.add_argument("--captured-inputs", type=Path)
    result.add_argument("--github-output", type=Path)
    result.add_argument("--as-of", required=True)
    result.add_argument("--generator-commit", required=True)
    result.add_argument("--visibility", choices=("public", "private", "internal"), required=True)
    for name in ("repository", "repository-id", "source-commit", "run-id", "run-attempt", "event-name"):
        result.add_argument("--" + name, required=True)
    result.add_argument("--retention-days", type=int, default=30)
    result.add_argument("--maximum-age-seconds", type=int, default=86400)
    result.add_argument("--maximum-last-known-age-seconds", type=int, default=2678400)
    return result


def main():
    args = parser().parse_args()
    try:
        require(transport.SHA.fullmatch(args.generator_commit))
        return prepare(args)
    except (snapshot.ArtifactError, OSError, ValueError, KeyError, TypeError, ImportError,
            RecursionError, subprocess.SubprocessError):
        print("Public fleet artifact: catalog, source or artifact admission denied", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
