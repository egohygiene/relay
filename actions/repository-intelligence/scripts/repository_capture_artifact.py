#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Pack or admit exact same-run JSON capture artifacts without executing content."""

from __future__ import annotations

import argparse
from datetime import datetime, UTC
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import time
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PLAN = "source-plan.json"
MANIFEST = "capture-bundle.json"
SCHEMA = "egohygiene.relay.source-capture-bundle/v1"
RECEIPT = "egohygiene.relay.source-capture-intake/v1"
MAX_FILE = 1024 * 1024
MAX_TOTAL = 6 * MAX_FILE
MAX_ARCHIVE = 8 * MAX_FILE
SHA = re.compile(r"[0-9a-f]{40}")
REPOSITORY = re.compile(r"egohygiene/(?:\.github|[a-z0-9][a-z0-9.-]*)")


def require(value):
    if not value:
        raise ValueError("Capture artifact denied")


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result)
        result[key] = value
    return result


def load(content, limit=MAX_FILE):
    require(len(content) <= limit)
    value = json.loads(content, object_pairs_hook=pairs, parse_constant=lambda _value: require(False))
    require(isinstance(value, dict))
    return value


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()


def digest(content):
    return hashlib.sha256(content).hexdigest()


def integer(value):
    text = str(value)
    require(re.fullmatch(r"[1-9][0-9]{0,19}", text))
    return int(text)


def instant(value, *, provider=False):
    require(isinstance(value, str) and len(value) <= 40 and value.endswith("Z"))
    if not provider:
        require(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value))
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None)
    return parsed.astimezone(UTC)


def safe(path):
    path = path.absolute()
    require(".." not in path.parts and not any(item.is_symlink() for item in (path, *path.parents)))
    return path


def relative(value):
    require(isinstance(value, str) and 1 <= len(value) <= 240
        and re.fullmatch(r"[A-Za-z0-9._/-]+", value) and value.endswith(".json")
        and not value.startswith("/")
        and all(part not in {"", ".", "..", ".git"} for part in value.split("/")))
    require(value not in {MANIFEST, "intake-receipt.json"})
    return value


def read(path, limit=MAX_FILE):
    path = safe(path)
    require(path.is_file() and path.stat().st_size <= limit)
    with path.open("rb") as handle:
        content = handle.read(limit + 1)
    require(len(content) <= limit)
    return content


def identity(args):
    require(args.visibility == "public" and REPOSITORY.fullmatch(args.repository) and SHA.fullmatch(args.source_commit))
    # PR merge revisions and provider workflow-run heads are distinct. This
    # initial artifact seam supports only events whose represented/head identity
    # can be checked directly; ordinary PR/no-capture builds remain unchanged.
    require(args.event_name in {"push", "workflow_dispatch"})
    observed = instant(args.observed_at)
    result = {"repository": args.repository, "repository_id": integer(args.repository_id),
        "source_commit": args.source_commit, "run_id": integer(args.run_id),
        "run_attempt": integer(args.run_attempt), "observed_at": args.observed_at, "event_name": args.event_name}
    require(result["run_attempt"] <= 1000000)
    name = ("repository-intelligence-captures-v1-" + str(result["repository_id"]) + "-"
        + args.source_commit + "-" + str(result["run_id"]) + "-" + str(result["run_attempt"]))
    return result, name, observed


def plan_selection(root, plan_bytes):
    spec = importlib.util.spec_from_file_location("relay_capture_plan", Path(__file__).with_name("repository_source_capture_inputs.py"))
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    # The existing closed data-only plan reader selects references; it cannot
    # supply code, modules, runtime locations or consumer command arguments.
    args = SimpleNamespace(capture_plan=root / PLAN, repository_root=root,
        collect_work=False, work_capture=None, work_maximum_age_seconds=86400,
        collect_health=False, health_expect_report=[], health_report=[], health_check_runs=None,
        health_check_runs_observed_at=None, health_check_runs_state="not-requested",
        health_inventory="partial", health_maximum_age_seconds=86400)
    require(read(root / PLAN, 65536) == plan_bytes)
    helper.apply(args)
    selections = {PLAN: "plan"}
    if args.collect_work:
        selections[relative(args.work_capture.relative_to(root).as_posix())] = "work"
    if args.collect_health:
        for selection in args.health_report:
            producer, _, path = selection.partition("=")
            key = relative(Path(path).relative_to(root).as_posix())
            require(key not in selections)
            selections[key] = producer
        if args.health_check_runs is not None:
            key = relative(args.health_check_runs.relative_to(root).as_posix())
            require(key not in selections)
            selections[key] = "github-check-runs"
    require(1 <= len(selections) <= 6 and len({name.casefold() for name in selections}) == len(selections))
    return selections


def source_identity(content, kind, expected, observed):
    document = load(content, 65536 if kind == "plan" else MAX_FILE)
    if kind == "work":
        require(document.get("schema") == "egohygiene.relay.work-provider-capture/v1"
            and document.get("visibility") == "public" and document.get("repository") == expected["repository"]
            and document.get("source_commit") == expected["source_commit"])
        inventories = document.get("inventories")
        require(isinstance(inventories, dict) and set(inventories) == {"issues", "pull_requests"})
        for inventory in inventories.values():
            require(isinstance(inventory, dict))
            if inventory.get("captured_at") is not None:
                require(instant(inventory["captured_at"]) <= observed)
    elif kind in {"osv", "megalinter", "scorecard"}:
        require(document.get("schema") == "egohygiene.repository-report-summary/v1"
            and document.get("producer") == kind and document.get("repository") == expected["repository"]
            and document.get("commit") == expected["source_commit"]
            and instant(document.get("generated_at")) <= observed)
    elif kind == "github-check-runs":
        runs = document.get("check_runs")
        require(type(document.get("total_count")) is int and document["total_count"] >= 0
            and isinstance(runs, list) and len(runs) <= 256 and document["total_count"] >= len(runs))
        for run in runs:
            require(isinstance(run, dict) and run.get("head_sha") == expected["source_commit"])
    else:
        require(kind == "plan")
        checks = document.get("health", {}).get("check_runs", {})
        if checks.get("state") == "observed":
            require(instant(checks.get("observed_at")) <= observed)


def new_output(args):
    parent = safe(args.runner_temp)
    consumer = safe(args.repository_root)
    require(parent.is_dir() and not parent.is_relative_to(consumer))
    return Path(tempfile.mkdtemp(prefix="relay-capture-intake-", dir=parent))


def outputs(args, values):
    if args.github_output:
        with safe(Path(args.github_output)).open("a", encoding="utf-8") as handle:
            for key, value in values.items():
                require("\n" not in str(value) and "\r" not in str(value))
                handle.write(f"{key}={value}\n")
    print("Capture artifact: bounded JSON handoff prepared")


def pack(args):
    expected, name, observed = identity(args)
    root = safe(args.source_directory)
    require(root.is_dir())
    plan_bytes = read(root / PLAN, 65536)
    selections = plan_selection(root, plan_bytes)
    files, total, content = [], 0, {}
    for path, kind in sorted(selections.items()):
        data = read(root / path, 65536 if kind == "plan" else MAX_FILE)
        source_identity(data, kind, expected, observed)
        total += len(data)
        require(total <= MAX_TOTAL)
        content[path] = data
        files.append({"path": path, "size_bytes": len(data), "sha256": digest(data)})
    manifest = {"schema": SCHEMA, **expected, "visibility": "public", "plan": PLAN, "files": files}
    destination = new_output(args)
    for path, data in content.items():
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o600)
    manifest_bytes = encoded(manifest)
    (destination / MANIFEST).write_bytes(manifest_bytes)
    (destination / MANIFEST).chmod(0o600)
    outputs(args, {"artifact-name": name, "artifact-directory": str(destination),
        "manifest-sha256": digest(manifest_bytes), "as-of": args.observed_at})


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def request(url, token, limit, deadline, *, allow_redirect=False):
    parsed = urlsplit(url)
    require(parsed.scheme == "https" and not parsed.username and not parsed.password and not parsed.fragment)
    is_api = parsed.netloc == "api.github.com"
    require(is_api or not token and parsed.hostname and (parsed.hostname.endswith(".blob.core.windows.net")
        or parsed.hostname.endswith(".actions.githubusercontent.com")) and parsed.port in {None, 443})
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if is_api:
        headers["Authorization"] = "Bearer " + token
    require(time.monotonic() < deadline)
    opener = build_opener(ProxyHandler(), NoRedirect())
    try:
        response = opener.open(Request(url, headers=headers), timeout=15)
    except HTTPError as error:
        if allow_redirect and error.code in {301, 302, 303, 307, 308}:
            location = error.headers.get("Location", "")
            error.close()
            require(location and location != url)
            # One CDN hop only. Authorization is never forwarded to storage.
            return request(location, "", limit, deadline, allow_redirect=False)
        raise ValueError("Capture artifact unavailable") from None
    with response:
        require(response.status == 200)
        declared = response.headers.get("Content-Length")
        if declared is not None:
            require(declared.isdigit() and int(declared) <= limit)
        data = bytearray()
        while True:
            require(time.monotonic() < deadline)
            chunk = response.read(min(65536, limit + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
            require(len(data) <= limit)
        return bytes(data)


def unpack(archive, destination, expected, observed):
    with zipfile.ZipFile(io.BytesIO(archive)) as package:
        members = package.infolist()
        require(1 <= len(members) <= 24)
        files, directories = {}, set()
        for item in members:
            require(not item.flag_bits & 1 and item.compress_type in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED})
            mode = item.external_attr >> 16
            if item.is_dir():
                path = item.filename.rstrip("/")
                require(re.fullmatch(r"[A-Za-z0-9._/-]+", path)
                    and not path.startswith("/") and all(part not in {"", ".", "..", ".git"} for part in path.split("/"))
                    and (not stat.S_IFMT(mode) or stat.S_ISDIR(mode)))
                require(path not in directories)
                directories.add(path)
                continue
            path = item.filename
            require(path == MANIFEST or relative(path))
            require(path not in files and (not stat.S_IFMT(mode) or stat.S_ISREG(mode)) and not mode & 0o111
                and item.file_size <= (65536 if path in {MANIFEST, PLAN} else MAX_FILE)
                and item.file_size <= item.compress_size * 200 + 1024)
            files[path] = item
        require(MANIFEST in files and PLAN in files and len({name.casefold() for name in files}) == len(files))
        with package.open(files[MANIFEST]) as handle:
            manifest_bytes = handle.read(65537)
        manifest = load(manifest_bytes, 65536)
        require(set(manifest) == {"schema", "repository", "repository_id", "source_commit", "run_id", "run_attempt",
            "observed_at", "event_name", "visibility", "plan", "files"} and manifest["schema"] == SCHEMA
            and manifest["visibility"] == "public" and manifest["plan"] == PLAN
            and all(manifest[key] == value for key, value in expected.items()))
        require(all(type(manifest[key]) is int for key in ("repository_id", "run_id", "run_attempt")))
        rows = manifest["files"]
        require(isinstance(rows, list) and 1 <= len(rows) <= 6)
        content, total = {}, 0
        for row in rows:
            require(isinstance(row, dict) and set(row) == {"path", "size_bytes", "sha256"})
            path = relative(row["path"])
            require(path in files and path not in content and type(row["size_bytes"]) is int
                and row["size_bytes"] == files[path].file_size
                and isinstance(row["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]))
            with package.open(files[path]) as handle:
                data = handle.read(MAX_FILE + 1)
            total += len(data)
            require(len(data) == row["size_bytes"] and digest(data) == row["sha256"] and total <= MAX_TOTAL)
            content[path] = data
        require(list(content) == sorted(content) and set(files) == {*content, MANIFEST})
        require(all(any(path.startswith(directory + "/") for path in content) for directory in directories))
        # Materialize only the checked allowlist. Do not call ZipFile.extract.
        for path, data in content.items():
            target = destination / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            target.chmod(0o600)
        selections = plan_selection(destination, content[PLAN])
        require(set(selections) == set(content))
        for path, kind in selections.items():
            source_identity(content[path], kind, expected, observed)
        (destination / MANIFEST).write_bytes(manifest_bytes)
        (destination / MANIFEST).chmod(0o600)
        return manifest_bytes, content[PLAN]


def verify_receipt(path, root, repository, source_commit, observed_at, plan_sha256):
    """Reverify the private admitted bytes before fresh native collection."""
    root = safe(root)
    receipt = load(read(path, 65536), 65536)
    require(set(receipt) == {"schema", "repository", "repository_id", "source_commit", "run_id", "run_attempt",
        "observed_at", "event_name", "artifact", "manifest_sha256", "plan_sha256", "intake"}
        and receipt["schema"] == RECEIPT and receipt["intake"] == "same-run-attempt-head-json-only"
        and receipt["repository"] == repository and receipt["source_commit"] == source_commit
        and receipt["observed_at"] == observed_at and receipt["plan_sha256"] == plan_sha256)
    expected, name, observed = identity(SimpleNamespace(**receipt, visibility="public"))
    artifact = receipt["artifact"]
    require(isinstance(artifact, dict) and set(artifact) == {"id", "name", "sha256", "size_bytes"}
        and type(artifact["id"]) is int and integer(artifact["id"]) == artifact["id"] and artifact["name"] == name
        and re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"])
        and type(artifact["size_bytes"]) is int and 0 < artifact["size_bytes"] <= MAX_ARCHIVE)
    manifest_bytes = read(root / MANIFEST, 65536)
    require(digest(manifest_bytes) == receipt["manifest_sha256"])
    manifest = load(manifest_bytes, 65536)
    require(set(manifest) == {"schema", "repository", "repository_id", "source_commit", "run_id", "run_attempt",
        "observed_at", "event_name", "visibility", "plan", "files"} and manifest["schema"] == SCHEMA
        and manifest["visibility"] == "public" and manifest["plan"] == PLAN
        and all(manifest[key] == value for key, value in expected.items()))
    plan_bytes = read(root / PLAN, 65536)
    require(digest(plan_bytes) == receipt["plan_sha256"])
    selections = plan_selection(root, plan_bytes)
    rows = manifest["files"]
    require(isinstance(rows, list) and len(rows) == len(selections))
    seen, total = [], 0
    for row in rows:
        require(isinstance(row, dict) and set(row) == {"path", "size_bytes", "sha256"})
        key = relative(row["path"])
        require(key in selections and key not in seen)
        content = read(root / key, 65536 if key == PLAN else MAX_FILE)
        total += len(content)
        require(type(row["size_bytes"]) is int and len(content) == row["size_bytes"]
            and digest(content) == row["sha256"] and total <= MAX_TOTAL)
        source_identity(content, selections[key], expected, observed)
        seen.append(key)
    require(seen == sorted(selections))
    return receipt


def admit(args):
    expected, name, observed = identity(args)
    artifact_id = integer(args.artifact_id)
    checksum = args.artifact_digest.removeprefix("sha256:")
    require(re.fullmatch(r"[0-9a-f]{64}", checksum))
    token = os.environ.get("CAPTURE_GITHUB_TOKEN", "")
    require(token and len(token) <= 4096 and not any(ord(c) < 32 for c in token))
    deadline = time.monotonic() + 60
    api = "https://api.github.com/repos/" + args.repository + "/actions/"
    run = load(request(api + f"runs/{expected['run_id']}/attempts/{expected['run_attempt']}", token, 262144, deadline), 262144)
    require(run.get("id") == expected["run_id"] and run.get("run_attempt") == expected["run_attempt"]
        and run.get("head_sha") == expected["source_commit"]
        and run.get("event") == expected["event_name"]
        and run.get("repository", {}).get("id") == expected["repository_id"]
        and run["repository"].get("full_name") == expected["repository"]
        and run["repository"].get("private") is False)
    started = instant(run.get("run_started_at"), provider=True)
    require(started <= observed)
    artifact = load(request(api + f"artifacts/{artifact_id}", token, 262144, deadline), 262144)
    bound = artifact.get("workflow_run", {})
    require(artifact.get("id") == artifact_id and artifact.get("name") == name and artifact.get("expired") is False
        and artifact.get("digest") == "sha256:" + checksum
        and type(artifact.get("size_in_bytes")) is int and 0 < artifact["size_in_bytes"] <= MAX_ARCHIVE
        and bound.get("id") == expected["run_id"] and bound.get("repository_id") == expected["repository_id"]
        and bound.get("head_sha") == expected["source_commit"]
        and instant(artifact.get("created_at"), provider=True) >= started)
    archive = request(api + f"artifacts/{artifact_id}/zip", token, MAX_ARCHIVE, deadline, allow_redirect=True)
    require(digest(archive) == checksum)
    destination = new_output(args)
    try:
        manifest_bytes, plan_bytes = unpack(archive, destination, expected, observed)
        receipt = {"schema": RECEIPT, **expected, "artifact": {"id": artifact_id, "name": name,
            "sha256": checksum, "size_bytes": len(archive)}, "manifest_sha256": digest(manifest_bytes),
            "plan_sha256": digest(plan_bytes), "intake": "same-run-attempt-head-json-only"}
        receipt_path = destination / "intake-receipt.json"
        receipt_path.write_bytes(encoded(receipt))
        receipt_path.chmod(0o600)
        outputs(args, {"plan-path": str(destination / PLAN), "capture-root": str(destination),
            "receipt-path": str(receipt_path), "receipt-sha256": digest(encoded(receipt))})
    except Exception:
        # No admitted plan is exposed on a failed extraction. Remove only the
        # new private candidate tree, never consumer-owned files or baselines.
        import shutil
        shutil.rmtree(destination)
        raise


def parser():
    value = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    value.add_argument("operation", choices=("pack", "admit"))
    for name in ("repository", "repository-id", "source-commit", "run-id", "run-attempt", "observed-at", "event-name", "visibility"):
        value.add_argument("--" + name, required=True)
    for name in ("runner-temp", "repository-root"):
        value.add_argument("--" + name, required=True, type=Path)
    value.add_argument("--source-directory", type=Path)
    value.add_argument("--artifact-id", default="")
    value.add_argument("--artifact-digest", default="")
    value.add_argument("--github-output", default="")
    return value


def main():
    try:
        args = parser().parse_args()
        if args.operation == "pack":
            require(args.source_directory is not None and not args.artifact_id and not args.artifact_digest)
            pack(args)
        else:
            require(args.source_directory is None)
            admit(args)
        return 0
    except Exception:
        print("Capture artifact: request, provider binding or JSON admission denied", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
