# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Prepare and run Relay's source-pinned, offline architecture validation adapter."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import tomllib

import validate_repository_architecture_contract as contract


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "catalog/repository-architecture-validation.json"
REQUIREMENTS = ROOT / "scripts/architecture-validation-requirements.txt"
MAX_REPORT = 1024 * 1024
MAX_PROCESS = 16 * MAX_REPORT
MAX_HISTORY = 256
MAX_COMMIT = 256 * 1024
EXCLUDED = {".git", ".reports"}
TOOLS = {"EGOLINT_PORTABILITY", "EGOLINT_REPOSITORY_CONTRACT", "EGOLINT_REPOSITORY_INTELLIGENCE"}
MESSAGES = {
    "PATH": ("An input or output path is unsafe.", "Use regular files and normalized repository-relative paths without symlinks."),
    "INPUT": ("An adapter input is malformed or unavailable.", "Check the request and declared local source files; rerun from a stable checkout."),
    "PIN": ("The prepared runtime does not match the pinned source profile.", "Prepare a trusted runtime from the exact profile commits and checksum-locked dependencies."),
    "RUNTIME": ("The pinned offline validator could not produce bounded structured evidence.", "Provide the documented toolchain and runtime, then rerun the local command."),
    "BOUND": ("The repository snapshot exceeded its declared bounds.", "Review the file/byte ceilings and scope before retrying; partial input is not conformance."),
    "MODE": ("Required enforcement is unavailable for this unreleased profile.", "Use advisory mode until the immutable release, reviewed workflow, and consumer opt-in gates are satisfied."),
    "POLICY": ("The caller policy and requested validation coverage disagree.", "Align repository identity and ADR adoption, enable the profile's ADR rules, and preserve the caller policy."),
    "COMPAT": ("The pinned EgoLint ADR catalog still references an earlier Hygiene policy revision.", "Reconcile the supported policy pins in EgoLint, then review and adopt a new Relay profile."),
    "DIAGRAM": ("Diagram validation is unavailable in this adapter checkpoint.", "Complete Relay #99 checkpoint 3; declared diagram sources remain unavailable meanwhile."),
    "UNKNOWN": ("One or more validation surfaces have unknown adoption.", "Resolve adoption explicitly before claiming complete architecture evidence."),
    "LEGACY": ("The caller declares a legacy architecture surface.", "Preserve existing records and complete the reviewed migration before claiming conformance."),
    "REVISION": ("An immutable revision was not established for this working-tree snapshot.", "Validate an explicit full source commit when immutable evidence is required."),
}


class AdapterError(ValueError):
    """A fixed, publish-safe failure code; never includes caller text or logs."""


def fail(code: str) -> None:
    raise AdapterError(code)


def encoded(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unique_pairs(pairs: list) -> dict:
    value = {}
    for key, item in pairs:
        if key in value:
            fail("INPUT")
        value[key] = item
    return value


def decode(data: bytes) -> dict:
    try:
        value = json.loads(data, object_pairs_hook=unique_pairs)
    except (ValueError, UnicodeError, RecursionError):
        fail("INPUT")
    if not isinstance(value, dict):
        fail("INPUT")
    return value


def safe_path(path: Path) -> Path:
    path = path.absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        fail("PATH")
    return path.resolve()


def read_file(path: Path, limit: int = MAX_REPORT) -> bytes:
    path = safe_path(path)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
        fail("BOUND")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as handle:
        metadata = os.fstat(handle.fileno())
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limit
                or (before.st_dev, before.st_ino) != (metadata.st_dev, metadata.st_ino)):
            fail("BOUND")
        data = handle.read(limit + 1)
    if len(data) > limit:
        fail("BOUND")
    return data


def environment() -> dict:
    # Do not inherit credentials, EGOLINT_*, Git overrides, or build wrappers.
    return {"PATH": os.environ.get("PATH", os.defpath), "LC_ALL": "C.UTF-8", "CI": "true",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_NO_REPLACE_OBJECTS": "1", "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_COUNT": "3", "GIT_CONFIG_KEY_0": "core.hooksPath",
            "GIT_CONFIG_VALUE_0": os.devnull, "GIT_CONFIG_KEY_1": "core.fsmonitor",
            "GIT_CONFIG_VALUE_1": "false", "GIT_CONFIG_KEY_2": "protocol.allow",
            "GIT_CONFIG_VALUE_2": "never"}


def execute(argv: list[str], *, cwd: Path, data: bytes | None = None,
            limit: int = MAX_PROCESS, timeout: int = 60, env: dict | None = None,
            allowed: tuple = (0,)) -> tuple[int, bytes]:
    # Pipes are drained concurrently; kill a noisy process before unbounded capture.
    import selectors
    import time

    with tempfile.TemporaryFile() as input_file:
        if data is not None:
            input_file.write(data)
        input_file.seek(0)
        process = subprocess.Popen(argv, cwd=cwd, env=env or environment(), stdin=input_file,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True)
        output = bytearray()
        count = 0
        deadline = time.monotonic() + timeout
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                selector.register(process.stderr, selectors.EVENT_READ)
                while selector.get_map():
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        fail("RUNTIME")
                    for key, _ in selector.select(min(remaining, 0.1)):
                        block = os.read(key.fileobj.fileno(), 65536)
                        if not block:
                            selector.unregister(key.fileobj)
                            continue
                        count += len(block)
                        if count > limit:
                            fail("BOUND")
                        if key.fileobj is process.stdout:
                            output.extend(block)
                code = process.wait(timeout=max(0.1, deadline - time.monotonic()))
            if code not in allowed:
                fail("RUNTIME")
            return code, bytes(output)
        finally:
            import signal
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            process.stdout.close()
            process.stderr.close()


def git(root: Path, *args: str, data: bytes | None = None, limit: int = MAX_PROCESS) -> bytes:
    return execute(["git", "--no-optional-locks", "--literal-pathspecs", "-c", "core.fsmonitor=false",
                    "-c", "core.hooksPath=/dev/null", "-C", str(safe_path(root)), *args],
                   cwd=safe_path(root), data=data, limit=limit)[1]


def git_blob(root: Path, revision: str, path: str, limit: int = MAX_REPORT) -> bytes:
    listing = git(root, "ls-tree", "-z", revision, "--", path).split(b"\0")
    if len(listing) != 2 or not listing[0]:
        fail("PIN")
    header, name = listing[0].split(b"\t", 1)
    mode, kind, oid = header.decode().split()
    if mode not in {"100644", "100755"} or kind != "blob" or name.decode() != path:
        fail("PIN")
    if int(git(root, "cat-file", "-s", oid)) > limit:
        fail("BOUND")
    return git(root, "cat-file", "blob", oid, limit=limit)


def profile() -> dict:
    value = decode(read_file(PROFILE_PATH))
    if contract.validate_profile(value):
        fail("PIN")
    return value


def check_dependencies() -> None:
    for line in REQUIREMENTS.read_text().splitlines():
        if line and not line.startswith("#"):
            name, version = line.split()[0].split("==")
            try:
                installed = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                fail("RUNTIME")
            if installed != version:
                fail("RUNTIME")


def prepare(args: argparse.Namespace) -> None:
    """Extract trusted Git objects and compile with the pinned Cargo lock offline."""
    check_dependencies()
    selected = profile()
    destination = safe_path(args.output)
    if destination.exists():
        fail("PATH")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        work = Path(temporary)
        runtime = work / "runtime"
        runtime.mkdir()
        for source in selected["sources"]:
            name = source["repository"].split("/")[1]
            checkout = getattr(args, name + "_source")
            if git(checkout, "rev-parse", source["revision"] + "^{commit}").decode().strip() != source["revision"]:
                fail("PIN")
            for item in source["artifacts"]:
                data = git_blob(checkout, source["revision"], item["path"], MAX_PROCESS)
                if digest(data) != item["sha256"]:
                    fail("PIN")
                path = runtime / name / item["path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
        source = next(s for s in selected["sources"] if s["role"] == "validator")
        archive = git(args.egolint_source, "archive", "--format=tar", source["revision"],
                      "Cargo.toml", "Cargo.lock", "src", ".config", "schemas", "vendor", limit=64 * MAX_REPORT)
        build = work / "build"
        build.mkdir()
        total = 0
        with tarfile.open(fileobj=io.BytesIO(archive)) as package:
            for index, member in enumerate(package):
                path = PurePosixPath(member.name)
                total += member.size
                if (index > 10000 or total > 64 * MAX_REPORT or path.is_absolute() or ".." in path.parts
                        or not (member.isdir() or member.isfile())):
                    fail("PIN")
                if member.isfile():
                    target = build / member.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(package.extractfile(member).read())
        build_env = environment()
        for key in ("CARGO_HOME", "RUSTUP_HOME"):
            if key in os.environ:
                build_env[key] = os.environ[key]
        if args.cargo.is_absolute():
            build_env["PATH"] = str(args.cargo.parent) + os.pathsep + build_env["PATH"]
        build_env["CARGO_NET_OFFLINE"] = "true"
        execute([str(args.cargo), "build", "--frozen", "--offline", "--bin", "egolint"],
                cwd=build, env=build_env, timeout=300)
        executable = runtime / "egolint-bin"
        shutil.copyfile(build / "target/debug/egolint", executable)
        executable.chmod(0o700)
        receipt = {"profile_sha256": digest(read_file(PROFILE_PATH)),
                   "egolint_sha256": digest(read_file(executable, 128 * MAX_REPORT))}
        (runtime / "runtime.json").write_bytes(encoded(receipt))
        runtime.rename(destination)


def runtime_files(root: Path, selected: dict) -> dict:
    check_dependencies()
    receipt = decode(read_file(root / "runtime.json"))
    if (set(receipt) != {"profile_sha256", "egolint_sha256"}
            or receipt["profile_sha256"] != digest(read_file(PROFILE_PATH))
            or receipt["egolint_sha256"] != digest(read_file(root / "egolint-bin", 128 * MAX_REPORT))):
        fail("PIN")
    for source in selected["sources"]:
        name = source["repository"].split("/")[1]
        for item in source["artifacts"]:
            if digest(read_file(root / name / item["path"], MAX_PROCESS)) != item["sha256"]:
                fail("PIN")
    return receipt


def excluded(path: str) -> bool:
    return path.split("/")[0] in EXCLUDED


def snapshot(root: Path, workspace: Path, request: dict, evidence: dict) -> None:
    """Materialize bounded regular files and a fresh, inert Git index/config."""
    if safe_path(Path(git(root, "rev-parse", "--show-toplevel").decode().strip())) != root:
        fail("PATH")
    revision = request["repository"]["represented_revision"]
    immutable = bool(contract.FULL_SHA.fullmatch(revision))
    records = []
    if immutable:
        listing = git(root, "ls-tree", "--full-tree", "-r", "--long", "-z", revision)
        for entry in listing.split(b"\0"):
            if entry:
                header, path = entry.split(b"\t", 1)
                mode, kind, oid, size = header.decode().split()
                records.append((path.decode(), mode, oid, int(size) if kind == "blob" else -1))
    else:
        modes = {}
        for entry in git(root, "ls-files", "--stage", "-z").split(b"\0"):
            if entry:
                header, path = entry.split(b"\t", 1)
                mode, _, stage = header.decode().split()
                if stage != "0":
                    fail("INPUT")
                modes[path.decode()] = mode
        names = git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
        for name in sorted(set(p.decode() for p in names.split(b"\0") if p)):
            if excluded(name):
                continue
            path = safe_path(root / name)
            if not path.exists():
                continue
            metadata = path.lstat()
            mode = modes.get(name, "100755" if metadata.st_mode & stat.S_IXUSR else "100644")
            records.append((name, mode, None, metadata.st_size if stat.S_ISREG(metadata.st_mode) else -1))
    files = []
    for name, mode, oid, size in sorted(records):
        if excluded(name):
            continue
        if (not contract.relative_path(name) or ".git" in PurePosixPath(name).parts
                or mode not in {"100644", "100755"} or size < 0):
            fail("PATH")
        evidence["files"] += 1
        evidence["bytes"] += size
        if (evidence["files"] > request["bounds"]["maximum_scanned_files"]
                or evidence["bytes"] > request["bounds"]["maximum_scanned_bytes"]):
            evidence["truncated"] = True
            fail("BOUND")
        files.append((name, mode, oid, size))
    workspace.mkdir()
    template = workspace.parent / "empty-template"
    template.mkdir()
    git(workspace, "init", "--quiet", "--template", str(template))
    identity = hashlib.sha256()
    index = bytearray()
    for name, mode, oid, size in files:
        data = (git(root, "cat-file", "blob", oid, limit=size + 1) if immutable
                else read_file(root / name, size))
        if len(data) != size:
            fail("INPUT")
        identity.update(encoded([name, mode, digest(data)]))
        target = workspace / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o700 if mode == "100755" else 0o600)
        blob = git(workspace, "hash-object", "-w", "--no-filters", "--stdin", data=data).decode().strip()
        index.extend(f"{mode} {blob}\t{name}\0".encode())
    git(workspace, "update-index", "-z", "--index-info", data=bytes(index))
    evidence["sha256"] = identity.hexdigest()
    if immutable:
        # Only commit objects enter the isolated store; no consumer Git config,
        # hooks, filters, alternates, replace refs, or executable helpers do.
        commits = git(root, "rev-list", "--max-count", str(MAX_HISTORY), revision).decode().splitlines()
        known = set(commits)
        shallow = []
        for oid in commits:
            if not contract.FULL_SHA.fullmatch(oid):
                fail("INPUT")
            raw = git(root, "cat-file", "commit", oid, limit=MAX_COMMIT)
            actual = git(workspace, "hash-object", "-t", "commit", "-w", "--stdin", data=raw).decode().strip()
            if actual != oid:
                fail("INPUT")
            parents = [line[7:].decode() for line in raw.split(b"\n\n", 1)[0].splitlines() if line.startswith(b"parent ")]
            if any(parent not in known for parent in parents):
                shallow.append(oid)
        if shallow:
            (workspace / ".git/shallow").write_text("\n".join(sorted(shallow)) + "\n")
        evidence["history_commits"] = len(commits)
        evidence["history_truncated"] = bool(shallow)
        (workspace / ".git/HEAD").write_text(revision + "\n")


def relay_finding(code: str) -> dict:
    summary, remediation = MESSAGES[code]
    return {"id": f"RELAY-ARCH-{code}-001", "severity": "warning", "source": "relay",
            "path": None, "line": None, "summary": summary, "remediation": remediation}


def catalog(root: Path) -> dict:
    value = tomllib.loads(read_file(root / "egolint/.config/rules/repository-intelligence.v1.toml").decode())
    rules = {r["id"]: (r["title"], r["remediation"]) for r in value["rules"]}
    portability = tomllib.loads(read_file(root / "egolint/.config/rules/portability.toml").decode())
    rules.update({r["id"]: (r["title"], r["description"]) for r in portability["rules"]})
    # These three rule IDs have no catalog remediation; this is adapter routing,
    # not an alternative implementation of their source-owned semantics.
    for name in ("SOURCE", "FILE", "CONTEXT"):
        rules[f"EGO-CONTRACT-{name}-001"] = (
            "The declared repository contract has a validation finding.",
            "Review the referenced requirement and source path against the pinned caller contract.")
    return {"rules": rules, "pins": value["upstream-contracts"]}


def inspect_policy(workspace: Path, request: dict, definitions: dict, runtime: Path) -> dict | None:
    import jsonschema
    for path in request["inputs"]["repository_contracts"]:
        try:
            value = tomllib.loads(read_file(workspace / path).decode())
            schema = decode(read_file(runtime / "egolint/schemas/repository-contract.schema.json"))
            jsonschema.Draft202012Validator(schema).validate(value)
        except (ValueError, UnicodeError, jsonschema.ValidationError):
            fail("POLICY")
    path = request["inputs"]["repository_intelligence_policy"]
    if path is None:
        return None
    try:
        value = tomllib.loads(read_file(workspace / path).decode())
        schema = decode(read_file(runtime / "egolint/schemas/repository-intelligence.schema.json"))
        jsonschema.Draft202012Validator(schema).validate(value)
    except (ValueError, UnicodeError, jsonschema.ValidationError):
        fail("POLICY")
    required = {r for r in definitions["rules"] if r.startswith("EGO-INTEL-")
                and "-ROADMAP-" not in r and "-TRAILER-" not in r}
    if (value.get("repository") != request["repository"]["id"]
            or value.get("adrs", {}).get("state") != "present"
            or not required.issubset(value.get("profile", {}).get("enabled-rules", []))):
        fail("POLICY")
    return value


def validate_raw(value: dict, runtime: Path, filename: str) -> None:
    import jsonschema
    schema = decode(read_file(runtime / "egolint/schemas" / filename))
    try:
        jsonschema.Draft202012Validator(schema).validate(value)
    except jsonschema.ValidationError:
        fail("RUNTIME")


def validate_evidence(value: dict) -> None:
    import jsonschema
    schema = decode(read_file(ROOT / "schemas/architecture-validation-evidence.v1.schema.json"))
    try:
        jsonschema.Draft202012Validator(schema).validate(value)
    except jsonschema.ValidationError:
        fail("RUNTIME")


def safe_finding(item: dict, definitions: dict) -> dict:
    rule = item["rule"]["rule_id"]
    if rule not in definitions["rules"] or not contract.RULE_ID.fullmatch(rule):
        fail("RUNTIME")
    location = item.get("location") or {}
    path = location.get("path")
    if path is not None and not contract.relative_path(path):
        path = None
    summary, remediation = definitions["rules"][rule]
    return {"id": rule, "severity": item["severity"], "source": "egolint", "path": path,
            "line": location.get("start_line") if path else None,
            "summary": summary[:512], "remediation": remediation[:1024]}


def run_engine(runtime: Path, workspace: Path, request: dict, definitions: dict) -> tuple[dict, dict | None, dict]:
    arguments = [str(safe_path(runtime / "egolint-bin")), "--workspace", str(workspace), "validate",
                 "--network", "none", "--pull-policy", "never"]
    for path in request["inputs"]["repository_contracts"]:
        arguments.extend(["--repository-contract", path])
    intelligence = request["inputs"]["repository_intelligence_policy"]
    if intelligence is not None:
        revision = request["repository"]["represented_revision"]
        arguments.extend(["--repository-intelligence", intelligence, "--represented-commit",
                          "unknown" if revision == "working-tree" else revision])
    _, _ = execute(arguments, cwd=workspace, allowed=(0, 1, 2, 3))
    reports = workspace / ".reports/egolint"
    run = decode(read_file(reports / "run.json"))
    validate_raw(run, runtime, "report.schema.json")
    if run["status"] == "execution_error":
        fail("RUNTIME")
    raw_intelligence = None
    if intelligence is not None:
        raw_intelligence = decode(read_file(reports / "repository-intelligence.json"))
        validate_raw(raw_intelligence, runtime, "repository-intelligence-report.schema.json")
        expected = request["repository"]["represented_revision"]
        if (raw_intelligence["repository"] != request["repository"]["id"]
                or raw_intelligence["policy_path"] != intelligence
                or raw_intelligence["represented_commit"]["revision"] != (expected if contract.FULL_SHA.fullmatch(expected) else None)):
            fail("RUNTIME")
    sarif = decode(read_file(reports / "egolint.sarif"))
    if sarif.get("version") != "2.1.0" or len(sarif.get("runs", [])) != 1:
        fail("RUNTIME")
    return run, raw_intelligence, sarif


def sanitize_sarif(raw: dict, retained: list[dict], definitions: dict) -> dict:
    """Retain upstream SARIF locations/levels, with catalog-only diagnostic prose."""
    rule_names = {r["id"]: r["name"] for r in raw["runs"][0]["tool"]["driver"]["rules"]}
    projected = []
    for item in raw["runs"][0]["results"]:
        if item.get("properties", {}).get("egolintToolId") not in TOOLS:
            continue
        rule = rule_names.get(item["ruleId"])
        if rule not in definitions["rules"]:
            fail("RUNTIME")
        projected.append((rule, item))
    # Match occurrences against the same retained native ordering, not console text.
    results = []
    for finding in retained:
        match = next(((i, item) for i, (rule, item) in enumerate(projected) if rule == finding["id"]
                      and (item.get("locations", [{}])[0].get("physicalLocation", {}).get("artifactLocation", {}).get("uri") == finding["path"])), None)
        if match is None:
            fail("RUNTIME")
        index, item = match
        projected.pop(index)
        value = {"ruleId": item["ruleId"], "level": item["level"], "message": {"text": finding["summary"]}}
        if finding["path"] is not None:
            physical = {"artifactLocation": {"uri": finding["path"]}}
            original = item["locations"][0]["physicalLocation"].get("region", {})
            region = {key: value for key, value in original.items()
                      if key in {"startLine", "startColumn", "endLine", "endColumn"}
                      and isinstance(value, int) and not isinstance(value, bool) and value > 0}
            if region:
                physical["region"] = region
            value["locations"] = [{"physicalLocation": physical}]
        value["properties"] = {"egolintRuleId": finding["id"], "remediation": finding["remediation"]}
        results.append(value)
    rules = [{"id": key, "name": rule_names[key]} for key in sorted({r["ruleId"] for r in results})]
    return {"$schema": "https://json.schemastore.org/sarif-2.1.0.json", "version": "2.1.0",
            "runs": [{"tool": {"driver": {"name": "Egolint", "semanticVersion": "0.1.0-alpha.1", "rules": rules}},
                      "results": results}]}


def result_base(request: dict, selected: dict, scan: dict) -> dict:
    return {"schema_version": contract.RESULT_SCHEMA, "profile": request["profile"],
            "repository": {k: v for k, v in request["repository"].items() if k != "root"},
            "mode": request["mode"], "semantic_status": "incomplete", "outcome": "warning",
            "coverage": {s: "not-applicable" if a == "not-applicable" else "unavailable"
                         for s, a in request["adoption"].items()},
            "provenance": [{"repository": s["repository"], "revision": s["revision"], "profile_source_id": s["id"]}
                           for s in selected["sources"]],
            "findings": [], "counts": {},
            "bounds": {"maximum_findings": request["bounds"]["maximum_findings"], "observed_findings": 0,
                       "findings_truncated": False, "maximum_scanned_files": request["bounds"]["maximum_scanned_files"],
                       "observed_scanned_files": scan["files"], "maximum_scanned_bytes": request["bounds"]["maximum_scanned_bytes"],
                       "observed_scanned_bytes": scan["bytes"], "scan_truncated": scan["truncated"]},
            "artifacts": {"egolint_run": None, "egolint_sarif": None, "repository_intelligence": None, "diagram_evidence": None},
            "privacy": {"classification": request["repository"]["visibility"] + "-repository",
                        "contains_source_content": False, "path_policy": "repository-relative-only", "redaction": "bounded-diagnostics-only"}}


def finish(result: dict, findings: list[dict], status: str) -> dict:
    result["findings"] = findings[:result["bounds"]["maximum_findings"]]
    result["bounds"]["observed_findings"] = len(findings)
    result["bounds"]["findings_truncated"] = len(findings) > len(result["findings"])
    if result["bounds"]["findings_truncated"] and status == "conformant":
        status = "incomplete"
    result["semantic_status"] = status
    result["outcome"] = ("passed" if status in {"conformant", "not-applicable"} else "unavailable"
                         if status == "unavailable" else "warning" if result["mode"] == "advisory" else "failed")
    result["counts"] = {s: sum(f["severity"] == s for f in result["findings"]) for s in sorted(contract.SEVERITIES)}
    result["counts"]["total"] = len(result["findings"])
    if contract.validate_result(result) or len(encoded(result)) > MAX_REPORT:
        fail("RUNTIME")
    return result


def write_atomic(path: Path, data: bytes) -> None:
    path = safe_path(path)
    if len(data) > MAX_REPORT:
        fail("BOUND")
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_path(path)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".architecture-", delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
            safe_path(path)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def run(args: argparse.Namespace) -> dict:
    selected = profile()
    request = decode(read_file(args.request))
    if contract.validate_request(request, selected):
        fail("INPUT")
    root = safe_path(args.repository_root)
    output = safe_path(root / request["output"]["path"])
    scan = {"files": 0, "bytes": 0, "truncated": False, "sha256": None,
            "history_commits": 0, "history_truncated": False}
    findings = []
    result = result_base(request, selected, scan)
    artifacts = {}
    try:
        if request["mode"] != "advisory":
            fail("MODE")
        if all(value == "not-applicable" for value in request["adoption"].values()):
            result = finish(result, [], "not-applicable")
            write_atomic(output, encoded(result))
            return result
        args.runtime = safe_path(args.runtime)
        if args.runtime.is_relative_to(root):
            fail("PATH")
        receipt = runtime_files(args.runtime, selected)
        definitions = catalog(args.runtime)
        with tempfile.TemporaryDirectory(prefix="relay-architecture-") as temporary:
            workspace = Path(temporary) / "repository"
            snapshot(root, workspace, request, scan)
            inspect_policy(workspace, request, definitions, args.runtime)
            run_report, intel, sarif = run_engine(args.runtime, workspace, request, definitions)
            result = result_base(request, selected, scan)
            selected_tools = {"EGOLINT_REPOSITORY_INTELLIGENCE"} if intel is not None else set()
            if request["inputs"]["repository_contracts"]:
                selected_tools.update({"EGOLINT_PORTABILITY", "EGOLINT_REPOSITORY_CONTRACT"})
            native = [f for f in run_report["findings"] if f["rule"]["tool_id"] in selected_tools]
            findings = [safe_finding(f, definitions) for f in native]
            coverage = result["coverage"]
            if request["adoption"]["repository-contracts"] in {"present", "legacy"}:
                relevant = [f for f in native if f["rule"]["tool_id"] != "EGOLINT_REPOSITORY_INTELLIGENCE"]
                coverage["repository-contracts"] = "failed" if any(f["severity"] in {"error", "critical"} for f in relevant) else "passed"
            if intel is not None:
                coverage["architecture-records"] = {"valid": "passed", "invalid": "failed", "incomplete": "partial", "not_applicable": "not-applicable"}[intel["status"]]
                authority = next(s for s in selected["sources"] if s["role"] == "organization-policy")
                adr_pin = next(p for p in definitions["pins"] if p["id"] == "egohygiene.architecture-decision/v1")
                if adr_pin["source-revision"] != authority["revision"]:
                    findings.append(relay_finding("COMPAT"))
                    if coverage["architecture-records"] == "passed":
                        coverage["architecture-records"] = "partial"
            if request["adoption"]["diagram-sources"] != "not-applicable":
                findings.append(relay_finding("DIAGRAM"))
            if "unknown" in request["adoption"].values():
                findings.append(relay_finding("UNKNOWN"))
            if "legacy" in request["adoption"].values():
                findings.append(relay_finding("LEGACY"))
            if not contract.FULL_SHA.fullmatch(request["repository"]["represented_revision"]):
                findings.append(relay_finding("REVISION"))
            status = ("nonconformant" if "failed" in coverage.values() else "legacy"
                      if "legacy" in request["adoption"].values() else "not-applicable"
                      if all(v == "not-applicable" for v in coverage.values()) else "incomplete"
                      if any(v in {"partial", "unavailable"} for v in coverage.values())
                      or not contract.FULL_SHA.fullmatch(request["repository"]["represented_revision"]) else "conformant")
            result = finish(result, findings, status)
            retained = [f for f in result["findings"] if f["source"] == "egolint"]
            evidence = {"schema_version": "relay.repository-architecture-validation-evidence/v1",
                        "profile": request["profile"], "repository": result["repository"], "runtime": receipt, "scan": scan,
                        "upstream": {"status": run_report["status"], "egolint_exit_code": run_report["egolint_exit_code"],
                                     "completeness": run_report["completeness"], "repository_intelligence_status": intel["status"] if intel else None},
                        "findings": retained}
            artifacts["egolint_run"] = ("egolint-run.json", evidence)
            validate_evidence(evidence)
            artifacts["egolint_sarif"] = ("egolint.sarif", sanitize_sarif(sarif, retained, definitions))
            if intel is not None:
                artifacts["repository_intelligence"] = ("repository-intelligence.json", {
                    "schema_version": "relay.repository-architecture-validation-intelligence-evidence/v1",
                    "status": intel["status"], "adrs": intel["adrs"], "roadmap": intel["roadmap"],
                    "commit_history": intel["commit_history"], "commit_history_truncated": intel["commit_history_truncated"],
                    "summary": intel["summary"], "findings": [f for f in retained if f["id"].startswith("EGO-INTEL-")]})
                validate_evidence(artifacts["repository_intelligence"][1])
    except (AdapterError, OSError, ValueError, KeyError, TypeError, StopIteration, subprocess.SubprocessError) as error:
        code = str(error) if isinstance(error, AdapterError) else "RUNTIME"
        result = result_base(request, selected, scan)
        result["coverage"] = {s: "unavailable" for s in result["coverage"]}
        status = "unavailable" if code in {"PIN", "RUNTIME", "MODE"} else "nonconformant" if code == "POLICY" else "incomplete"
        if code == "POLICY":
            result["coverage"] = {s: "failed" if a in {"present", "legacy"} else "not-applicable"
                                  if a == "not-applicable" else "unavailable" for s, a in request["adoption"].items()}
        result = finish(result, [relay_finding(code)], status)
        artifacts = {}
    if artifacts:
        identity = digest(encoded({"result": result, "artifacts": artifacts}))[:24]
        directory = f".reports/architecture-validation/evidence-{identity}"
        for key, (filename, artifact) in artifacts.items():
            path = directory + "/" + filename
            write_atomic(root / path, encoded(artifact))
            result["artifacts"][key] = path
    if contract.validate_result(result, selected):
        fail("RUNTIME")
    write_atomic(output, encoded(result))
    return result


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = value.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("prepare", allow_abbrev=False)
    for name in ("hygiene", "egolint", "holon"):
        setup.add_argument("--" + name + "-source", type=Path, required=True)
    setup.add_argument("--output", type=Path, required=True)
    setup.add_argument("--cargo", type=Path, default=Path("cargo"))
    check = commands.add_parser("run", allow_abbrev=False)
    check.add_argument("--repository-root", type=Path, required=True)
    check.add_argument("--request", type=Path, required=True)
    check.add_argument("--runtime", type=Path, required=True)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "prepare":
            prepare(args)
            print("Prepared pinned offline architecture runtime")
            return 0
        result = run(args)
        status, outcome, count = result["semantic_status"], result["outcome"], result["counts"]["total"]
        print(f"{status}: {outcome} ({count} retained findings)")
        return 2 if result["outcome"] == "unavailable" else 1 if result["outcome"] == "failed" else 0
    except (AdapterError, OSError, ValueError, KeyError, TypeError, StopIteration, subprocess.SubprocessError):
        print("Architecture adapter failed before safe evidence could be written; verify inputs and output paths.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
