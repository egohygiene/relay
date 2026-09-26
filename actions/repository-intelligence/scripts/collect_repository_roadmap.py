#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Collect immutable roadmap evidence into a publication-denied review envelope."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import importlib.util
import importlib.metadata
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "contracts/roadmap-collector.v1.lock.json"
SCHEMA = "egohygiene.relay.roadmap-collection-review/v1"
PROVIDER_SCHEMA = "egohygiene.relay.roadmap-provider-capture/v1"
OUTPUT_NAME = "roadmap-collection.review.json"
MAX_SOURCE = 262144
MAX_JSON = 1048576
MAX_OUTPUT = 8 * MAX_JSON
MAX_RECORDS = 256
SHA = re.compile(r"[0-9a-f]{40}")
REPOSITORY = re.compile(r"egohygiene/(?:\.github|[a-z0-9][a-z0-9.-]*)")
SECRET = re.compile(r"(?i)(github_pat_|gh[pousr]_|(?:token|password|secret)\s*[:=]|[\w.+-]+@[\w.-]+\.[a-z]{2,}|/(?:home|Users|workspace|tmp)/)")
MESSAGES = {
    "INPUT": "Use bounded UTF-8 inputs, canonical identity, full revisions and explicit UTC times.",
    "VISIBILITY": "Supply verified public source visibility; protected inputs cannot be exported.",
    "PATH": "Use regular files and directories without symlinks or path traversal.",
    "PIN": "Reacquire the exact locked upstream revisions and prepare the trusted runtime again.",
    "RUNTIME": "Prepare the pinned offline runtime and inspect the owning validator locally.",
    "EXTRACTION": "Use unambiguous canonical heading, outcome and exit-criteria sections.",
    "PROVIDER": "Supply only bounded, explicitly referenced, public same-repository issue metadata.",
    "PROVIDER_UNAVAILABLE": "Recapture authorized issue metadata to observe provider state; intent is unchanged.",
    "STALE_INTENT": "Review the canonical roadmap at a new revision; collection cannot refresh intent.",
    "STALE_PROVIDER": "Recapture provider metadata at the declared observation boundary.",
    "HYGIENE": "Repair the projection against the pinned Hygiene schema and vocabulary.",
    "COVERAGE": "Resolve Observatory #25 and review new pins before enabling snapshot publication.",
}


class CollectorError(ValueError):
    """A closed diagnostic code; raw input and exception text never escape."""


def fail(code: str) -> None:
    raise CollectorError(code)


def diagnostic(code: str, owner: str = "relay", line: int | None = None) -> dict:
    return {"code": code, "owner": owner, "path": "ROADMAP.md" if line else None,
            "line": line, "remediation": MESSAGES.get(code, "Run the pinned EgoLint validator and repair its source finding.")}


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def unique_pairs(pairs: list) -> dict:
    value = {}
    for key, item in pairs:
        if key in value:
            fail("INPUT")
        value[key] = item
    return value


def load_json(data: bytes) -> dict:
    if len(data) > MAX_OUTPUT:
        fail("INPUT")
    try:
        value = json.loads(data, object_pairs_hook=unique_pairs,
                           parse_constant=lambda _: fail("INPUT"))
    except (ValueError, UnicodeError):
        fail("INPUT")
    if not isinstance(value, dict):
        fail("INPUT")
    return value


def safe_path(path: Path) -> Path:
    # Do not resolve first: that would erase evidence of a symlink ancestor.
    path = path.absolute()
    if ".." in path.parts or any(p.is_symlink() for p in (path, *path.parents)):
        fail("PATH")
    return path


def read_file(path: Path, limit: int = MAX_JSON) -> bytes:
    path = safe_path(path)
    if not path.is_file() or path.stat().st_size > limit:
        fail("INPUT")
    with path.open("rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        fail("INPUT")
    return data


def environment() -> dict:
    return {"PATH": os.environ.get("PATH", os.defpath), "LC_ALL": "C.UTF-8",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_NO_REPLACE_OBJECTS": "1", "GIT_TERMINAL_PROMPT": "0"}


def run(argv: list[str], *, cwd: Path | None = None, data: bytes | None = None,
        timeout: int = 30, limit: int = MAX_OUTPUT, allowed: tuple = (0,)) -> bytes:
    # Bound returned data and keep subprocess diagnostics out of public results.
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        try:
            result = subprocess.run(argv, cwd=cwd, input=data, stdout=output,
                                    stderr=errors, env=environment(), timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired):
            fail("RUNTIME")
        if result.returncode not in allowed or output.tell() > limit or errors.tell() > MAX_OUTPUT:
            fail("RUNTIME")
        output.seek(0)
        return output.read(limit + 1)


def git(root: Path, *args: str, data: bytes | None = None, limit: int = MAX_OUTPUT) -> bytes:
    return run(["git", "--no-optional-locks", "-c", "core.hooksPath=/dev/null",
                "-C", str(safe_path(root)), *args], data=data, limit=limit)


def git_blob(root: Path, revision: str, path: str, limit: int = MAX_SOURCE) -> bytes:
    record = git(root, "ls-tree", revision, "--", path).decode().strip().split()
    if len(record) != 4 or record[0] not in {"100644", "100755"} or record[3] != path:
        fail("PATH")
    size = int(git(root, "cat-file", "-s", record[2]))
    if size > limit:
        fail("INPUT")
    return git(root, "cat-file", "blob", record[2], limit=limit)


def prepare(args: argparse.Namespace) -> None:
    """Acquire trusted runtime bytes from Git objects; never consumer worktrees."""
    check_python_runtime()
    lock = load_json(read_file(LOCK_PATH))
    destination = safe_path(args.output)
    if destination.exists():
        fail("PATH")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        runtime = Path(temporary) / "runtime"
        runtime.mkdir()
        for name, pin in lock["sources"].items():
            source = args.hygiene if name == "hygiene_semantics" else getattr(args, name)
            if git(source, "rev-parse", pin["revision"] + "^{tree}").decode().strip() != pin["tree"]:
                fail("PIN")
            for path, expected in pin["files"].items():
                content = git_blob(source, pin["revision"], path, MAX_OUTPUT)
                if digest(content) != expected:
                    fail("PIN")
                target = runtime / name / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
        # The full source tree (including embedded catalogs) is executable trust.
        archive = git(args.egolint, "archive", "--format=tar",
                      lock["sources"]["egolint"]["revision"], limit=64 * MAX_JSON)
        build = Path(temporary) / "build"
        build.mkdir()
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            for member in tar:
                name = PurePosixPath(member.name)
                if name.is_absolute() or ".." in name.parts or not (member.isdir() or member.isfile()):
                    fail("PIN")
                if member.isfile():
                    target = build / member.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(tar.extractfile(member).read())
        # Cargo's cache/toolchain are explicitly trusted acquisition inputs.
        cargo = str(args.cargo)
        build_env = environment()
        if args.cargo.is_absolute():
            build_env["PATH"] = str(args.cargo.parent) + os.pathsep + build_env["PATH"]
        for key in ("CARGO_HOME", "RUSTUP_HOME"):
            if key in os.environ:
                build_env[key] = os.environ[key]
        # rustup uses the user's installed toolchain, while compilation is offline.
        with tempfile.TemporaryFile() as log:
            try:
                result = subprocess.run([cargo, "build", "--locked", "--offline", "--bin", "egolint"],
                                        cwd=build, env=build_env, stdout=log, stderr=log,
                                        timeout=300, check=False)
            except (OSError, subprocess.TimeoutExpired):
                fail("RUNTIME")
            if result.returncode != 0:
                fail("RUNTIME")
        binary = build / "target/debug/egolint"
        executable = runtime / "egolint-bin"
        shutil.copyfile(binary, executable)
        executable.chmod(0o700)
        receipt = {"lock_sha256": digest(read_file(LOCK_PATH)),
                   "egolint_sha256": digest(read_file(executable, 128 * MAX_JSON))}
        (runtime / "runtime.json").write_bytes(json_bytes(receipt))
        runtime.rename(destination)


def runtime_files(root: Path) -> tuple[dict, dict]:
    check_python_runtime()
    lock = load_json(read_file(LOCK_PATH))
    receipt = load_json(read_file(root / "runtime.json"))
    if set(receipt) != {"lock_sha256", "egolint_sha256"} or receipt["lock_sha256"] != digest(read_file(LOCK_PATH)):
        fail("PIN")
    for name, pin in lock["sources"].items():
        for path, expected in pin["files"].items():
            if digest(read_file(root / name / path, MAX_OUTPUT)) != expected:
                fail("PIN")
    if digest(read_file(root / "egolint-bin", 128 * MAX_JSON)) != receipt["egolint_sha256"]:
        fail("PIN")
    return lock, receipt


def check_python_runtime() -> None:
    for line in (ROOT / "contracts/roadmap-collector-requirements.txt").read_text().splitlines():
        if line and not line.startswith("#"):
            name, version = line.split("==")
            if importlib.metadata.version(name) != version:
                fail("RUNTIME")


def utc(value: str) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        fail("INPUT")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        fail("INPUT")


def metadata(value: str) -> dict:
    class ClosedLoader(yaml.BaseLoader):
        pass

    def mapping(loader, node):
        if not isinstance(node, yaml.MappingNode):
            fail("EXTRACTION")
        return unique_pairs([(loader.construct_object(k), loader.construct_object(v)) for k, v in node.value])

    ClosedLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    # Anchors/aliases/tags are unnecessary for this bounded comment profile.
    if any(isinstance(t, (yaml.tokens.AnchorToken, yaml.tokens.AliasToken, yaml.tokens.TagToken))
           for t in yaml.scan(value)):
        fail("EXTRACTION")
    result = yaml.load(value, Loader=ClosedLoader)
    if not isinstance(result, dict):
        fail("EXTRACTION")
    return result


def comments(text: str, kind: str) -> list:
    return list(re.finditer(r"<!--\s*" + kind + r"\s*\n(.*?)-->", text, re.DOTALL))


def manifest(text: str) -> dict:
    blocks = comments(text, "roadmap-manifest")
    if len(blocks) != 1:
        fail("EXTRACTION")
    return metadata(blocks[0][1])


def extract(text: str) -> list[dict]:
    blocks = comments(text, "roadmap-step")
    if not 0 < len(blocks) <= MAX_RECORDS:
        fail("EXTRACTION")
    steps = []
    for i, block in enumerate(blocks):
        step = metadata(block[1])
        body = text[block.end():blocks[i + 1].start() if i + 1 < len(blocks) else len(text)]
        heading = re.search(r"^#{3,6}\s+" + re.escape(str(step.get("id"))) + r"\s+(.+)$", body, re.MULTILINE)
        outcome = re.search(r"^\*\*Outcome:\*\*\s*([^\n]+(?:\n(?!\n|\*\*|#|- \[)[^\n]+)*)", body, re.MULTILINE)
        criteria = re.search(r"^\*\*Exit criteria:\*\*\s*\n(.*?)(?=^\*\*|^#{1,6} |<!--|\Z)", body, re.MULTILINE | re.DOTALL)
        if not heading or not outcome or not criteria:
            fail("EXTRACTION")
        items = []
        for line in criteria[1].splitlines():
            match = re.fullmatch(r"- \[([ xX])\] (.+)", line)
            if match:
                items.append({"text": match[2], "complete": match[1] != " "})
            elif line.startswith("  ") and line.strip() and items:
                items[-1]["text"] += " " + line.strip()
            elif line.strip():
                fail("EXTRACTION")
        if not items or len(items) > MAX_RECORDS:
            fail("EXTRACTION")
        for field in ("depends_on", "issues"):
            step.setdefault(field, [])
            if not isinstance(step[field], list) or len(step[field]) > MAX_RECORDS:
                fail("EXTRACTION")
        step.update(title=heading[1].lstrip("—–- "), outcome=" ".join(outcome[1].split()),
                    exit_criteria=items, line=text[:block.start()].count("\n") + 1)
        steps.append(step)
    return steps


def ego_validate(runtime: Path, repository: str, revision: str, raw: bytes, commit: bytes) -> dict:
    catalog = tomllib.loads(read_file(runtime / "egolint/.config/rules/repository-intelligence.v1.toml").decode())
    rules = [r["id"] for r in catalog["rules"] if r["id"] in {
        "EGO-INTEL-CONTRACT-001", "EGO-INTEL-ADOPTION-001", "EGO-INTEL-ROADMAP-STRUCTURE-001",
        "EGO-INTEL-ROADMAP-STATE-001", "EGO-INTEL-LINK-001", "EGO-INTEL-CYCLE-001"}]
    policy = f'schema-version = 1\nid = "egolint.repository-intelligence-validation/v1"\nrepository = "{repository}"\n'
    policy += '[profile]\nid = "relay-roadmap-review"\nenforcement = "blocking"\nenabled-rules = ' + json.dumps(rules) + "\n"
    for contract in catalog["upstream-contracts"]:
        policy += "\n[[contracts]]\n" + "".join(f"{k} = {json.dumps(v)}\n" for k, v in contract.items())
    policy += '\n[adrs]\nstate = "unknown"\npolicy-reference = "uncollected/policy-reference.json"\ndecision-directory = "uncollected/decisions"\nindex = "uncollected/index.md"\n[roadmap]\nstate = "present"\npath = "ROADMAP.md"\n[commit-history]\nstate = "unknown"\nmaximum-commits = 1\n'
    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory)
        (workspace / "template").mkdir()
        git(workspace, "init", "--quiet", "--template", str(workspace / "template"))
        # Keep the exact commit object, bounded to one shallow record. No history
        # or consumer configuration/code enters the validation inventory.
        actual = git(workspace, "hash-object", "-t", "commit", "-w", "--stdin", data=commit).decode().strip()
        if actual != revision:
            fail("INPUT")
        (workspace / ".git/shallow").write_text(revision + "\n")
        (workspace / "ROADMAP.md").write_bytes(raw)
        (workspace / "collector-policy.toml").write_text(policy)
        run([str(runtime / "egolint-bin"), "--workspace", str(workspace), "validate",
             "--repository-intelligence", "collector-policy.toml", "--represented-commit", revision],
            cwd=workspace, allowed=(0, 1, 2, 3), timeout=60)
        report = load_json(read_file(workspace / ".reports/egolint/repository-intelligence.json"))
    schema = load_json(read_file(runtime / "egolint/schemas/repository-intelligence-report.schema.json"))
    if not jsonschema.Draft202012Validator(schema).is_valid(report) or report["repository"] != repository or report["represented_commit"]["revision"] != revision:
        fail("RUNTIME")
    return report


def provider_capture(path: Path | None, repository: str, numbers: set[int], observed: datetime,
                     maximum_age: int) -> tuple[dict, str, str | None]:
    if path is None:
        return {}, "unavailable", None
    raw = read_file(path)
    value = load_json(raw)
    if set(value) != {"schema", "repository", "visibility", "observed_at", "status", "issues"}:
        fail("PROVIDER")
    if value["visibility"] != "public":
        fail("VISIBILITY")
    if value["schema"] != PROVIDER_SCHEMA or value["repository"] != repository or value["status"] not in {"observed", "unavailable"}:
        fail("PROVIDER")
    age = (observed - utc(value["observed_at"])).total_seconds()
    records = value["issues"]
    if age < 0 or not isinstance(records, list) or len(records) > MAX_RECORDS:
        fail("PROVIDER")
    if value["status"] == "unavailable" and records:
        fail("PROVIDER")
    accepted = {}
    for record in records:
        if not isinstance(record, dict) or set(record) != {"number", "state"}:
            fail("PROVIDER")
        number = record["number"]
        if type(number) is not int or number not in numbers or number in accepted or record["state"] not in {"open", "closed"}:
            fail("PROVIDER")
        accepted[number] = {**record, "observed_at": value["observed_at"],
                            "freshness": "stale" if age > maximum_age else "current"}
    status = "unavailable" if value["status"] == "unavailable" else "stale" if age > maximum_age else "partial"
    return accepted, status, digest(raw)


def module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def project(repository: str, revision: str, observed_at: str, steps: list, freshness: str,
            issues: dict) -> dict:
    url = f"https://github.com/{repository}"
    source = {"id": "source:roadmap", "kind": "roadmap", "url": f"{url}/blob/{revision}/ROADMAP.md",
              "repository": repository, "revision": revision, "observed_at": observed_at,
              "visibility": "public", "assertion": "authoritative", "freshness": freshness}

    def entity(kind, key, title, state, provenance, attributes, current=freshness):
        return {"id": f"ri:{repository}:{kind.replace('_', '-')}:{key}", "kind": kind,
                "repository": repository, "key": key, "title": title, "canonical_url": url,
                "visibility": "public", "state": {"value": state, "assertion": "authoritative"},
                "freshness": current, "provenance": provenance, "attributes": attributes, "extensions": {}}

    root = entity("repository", repository, repository, "unknown", [source["id"]], {}, "unknown")
    root["state"]["assertion"] = "unknown"
    projection = {"schema": "egohygiene.repository-intelligence/v1", "contract_version": "1.0.0-alpha.1",
                  "projection_id": f"{repository}@{revision}", "repository": repository,
                  "represented_commit": revision, "visibility": "public", "observed_at": observed_at,
                  "generator": {"name": "egohygiene/relay:roadmap-collector", "version": "0.1.0",
                                "contract": "egohygiene.repository-intelligence/v1"},
                  "sources": [source], "entities": [root], "relationships": [], "events": [],
                  "redactions": [], "extensions": {}}

    def edge(kind, step, target, sources):
        source_id = f"ri:{repository}:roadmap-step:{step['id']}"
        edge_id = digest(f"{kind}:{source_id}:{target}".encode())[:32]
        projection["relationships"].append({"id": "relationship:" + edge_id, "type": kind,
            "source": source_id, "target": target, "direction": "directed", "assertion": "authoritative",
            "freshness": freshness, "provenance": sources, "extensions": {}})

    for number, record in sorted(issues.items()):
        link = f"{url}/issues/{number}"
        provider = {**source, "id": f"source:issue-{number}", "kind": "github_issue", "url": link,
                    "revision": None, "observed_at": record["observed_at"], "freshness": record["freshness"]}
        projection["sources"].append(provider)
        issue = entity("issue", str(number), None, record["state"], [provider["id"]],
                       {"number": number}, record["freshness"])
        issue["canonical_url"] = link
        projection["entities"].append(issue)
    for step in steps:
        record = entity("roadmap_step", step["id"], step["title"], step["status"], [source["id"]],
                        {"outcome": step["outcome"], "exit_criteria": step["exit_criteria"]})
        record["canonical_url"] = source["url"] + f"#L{step['line']}"
        projection["entities"].append(record)
        for dependency in step["depends_on"]:
            edge("depends-on", step, f"ri:{repository}:roadmap-step:{dependency}", [source["id"]])
        for number in sorted(set(step["issue_numbers"])):
            if number in issues:
                edge("tracks", step, f"ri:{repository}:issue:{number}", [source["id"], f"source:issue-{number}"])
    for key in ("sources", "entities", "relationships"):
        projection[key].sort(key=lambda record: record["id"])
    return projection


def collect(args: argparse.Namespace) -> dict:
    if args.visibility != "public":
        fail("VISIBILITY")
    if not REPOSITORY.fullmatch(args.repository) or not SHA.fullmatch(args.source_commit):
        fail("INPUT")
    observed = utc(args.observed_at)
    if not 1 <= args.maximum_intent_age_days <= 3650 or not 1 <= args.maximum_provider_age_seconds <= 2678400:
        fail("INPUT")
    lock, receipt = runtime_files(args.runtime)
    raw = git_blob(args.repository_root, args.source_commit, "ROADMAP.md")
    text = raw.decode("utf-8")
    declared = manifest(text)
    if declared.get("visibility") != "public" or declared.get("publication") not in {"canonical", "composed", "central"}:
        fail("VISIBILITY")
    if declared.get("repository") != args.repository or SECRET.search(text):
        fail("VISIBILITY")
    commit = git(args.repository_root, "cat-file", "commit", args.source_commit, limit=MAX_SOURCE)
    report = ego_validate(args.runtime, args.repository, args.source_commit, raw, commit)
    diagnostics = []
    for item in report["diagnostics"][:MAX_RECORDS]:
        loc = item.get("location") or {}
        line = loc.get("line") if loc.get("path") == "ROADMAP.md" else None
        finding = diagnostic(item["rule_id"], "egolint", line)
        # Remediation is fixed text from the verified upstream rule catalog,
        # unlike the diagnostic message, which can contain consumer payloads.
        finding["remediation"] = item["remediation"]
        diagnostics.append(finding)
    try:
        steps = extract(text)
    except (CollectorError, yaml.YAMLError, TypeError, ValueError):
        # Keep the owning validator's findings even when extraction cannot form
        # a candidate. Never return partially parsed source text as a diagnostic.
        return {"schema": SCHEMA, "publication": "denied", "status": "invalid",
                "repository": args.repository, "represented_commit": args.source_commit,
                "observed_at": args.observed_at, "inputs": {"roadmap_sha256": digest(raw)},
                "runtime": {**receipt, "collector_sha256": digest(Path(__file__).read_bytes()), "pins": lock},
                "validation": {"egolint": report["status"], "hygiene": "not-run", "observatory": "not-run",
                               "diagnostics_truncated": len(report["diagnostics"]) > MAX_RECORDS},
                "diagnostics": diagnostics + [diagnostic("EXTRACTION")],
                "projection_candidate": None, "snapshot_candidate": None}
    try:
        intent_date = datetime.strptime(declared["updated"], "%Y-%m-%d").replace(tzinfo=UTC)
    except (KeyError, ValueError, TypeError):
        fail("EXTRACTION")
    if intent_date > observed:
        fail("INPUT")
    freshness = "stale" if (observed - intent_date).days > args.maximum_intent_age_days else "current"
    if freshness == "stale":
        diagnostics.append(diagnostic("STALE_INTENT"))
    references = []
    numbers = set()
    for step in steps:
        step["issue_numbers"] = []
        for value in step["issues"]:
            ref = str(value)
            match = re.fullmatch(r"(?:#)?([1-9][0-9]{0,9})", ref) or re.fullmatch(
                r"https://github\.com/" + re.escape(args.repository) + r"/issues/([1-9][0-9]{0,9})", ref)
            if not match:
                # Cross-repository visibility is deliberately unsupported here.
                fail("PROVIDER")
            number = int(match[1])
            numbers.add(number)
            step["issue_numbers"].append(number)
            references.append({"step": step["id"], "url": f"https://github.com/{args.repository}/issues/{number}"})
    issues, provider_state, provider_digest = provider_capture(args.provider_evidence, args.repository, numbers, observed,
                                                             args.maximum_provider_age_seconds)
    if set(issues) != numbers or provider_state == "unavailable":
        diagnostics.append(diagnostic("PROVIDER_UNAVAILABLE"))
    if provider_state == "stale":
        diagnostics.append(diagnostic("STALE_PROVIDER"))
    projection = project(args.repository, args.source_commit, args.observed_at, steps, freshness, issues)
    hygiene = module(args.runtime / "hygiene/tools/intelligence.py", "pinned_hygiene_intelligence")
    vocabulary = load_json(read_file(args.runtime / "hygiene/catalog/repository-intelligence-vocabulary.json"))
    errors = hygiene.validate_snapshot(projection, vocabulary)
    for name in ("hygiene", "hygiene_semantics"):
        schema = load_json(read_file(args.runtime / name / "schemas/repository-intelligence.v1.schema.json"))
        errors += list(jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).iter_errors(projection))
    snapshot = None
    if not errors:
        observatory = module(args.runtime / "observatory/src/observatory/intelligence.py", "pinned_observatory_intelligence")
        snapshot = observatory.build_repository_snapshot(projection)
        schema = load_json(read_file(args.runtime / "observatory/schemas/repository-intelligence-read-model.v1.schema.json"))
        if not jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).is_valid(snapshot):
            fail("PIN")
    else:
        diagnostics.append(diagnostic("HYGIENE", "hygiene"))
    diagnostics.append(diagnostic("COVERAGE", "observatory"))
    return {"schema": SCHEMA, "publication": "denied", "status": "invalid" if report["status"] == "invalid" or errors else "blocked",
            "repository": args.repository, "represented_commit": args.source_commit, "observed_at": args.observed_at,
            "inputs": {"roadmap_sha256": digest(raw), "provider_sha256": provider_digest,
                       "maximum_intent_age_days": args.maximum_intent_age_days,
                       "maximum_provider_age_seconds": args.maximum_provider_age_seconds},
            "runtime": {**receipt, "collector_sha256": digest(Path(__file__).read_bytes()), "pins": lock},
            "coverage": {"roadmap": "invalid" if report["status"] == "invalid" else "observed",
                         "issue_references": provider_state,
                         **{key: "uncollected" for key in ("adrs", "checks", "releases", "deployments", "work_inventory", "history")}},
            "validation": {"egolint": report["status"], "hygiene": "invalid" if errors else "valid",
                           "observatory": "normalized" if snapshot else "not-run",
                           "diagnostics_truncated": len(report["diagnostics"]) > MAX_RECORDS},
            "references": sorted(references, key=lambda r: (r["step"], r["url"])),
            "diagnostics": diagnostics, "projection_candidate": projection,
            "snapshot_candidate": snapshot,
            "candidate_digests": {"projection_sha256": digest(json_bytes(projection)),
                                  "snapshot_sha256": digest(json_bytes(snapshot)) if snapshot else None}}


def write_result(path: Path, result: dict) -> None:
    path = safe_path(path)
    if path.name != OUTPUT_NAME or (path.exists() and not path.is_file()):
        fail("PATH")
    schema = load_json(read_file(ROOT / "schemas/roadmap-collection-review.v1.schema.json"))
    if not jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).is_valid(result):
        fail("INPUT")
    content = json_bytes(result)
    if len(content) > MAX_OUTPUT:
        fail("INPUT")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = result.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("prepare", allow_abbrev=False)
    for owner in ("hygiene", "egolint", "observatory"):
        setup.add_argument("--" + owner, type=Path, required=True)
    setup.add_argument("--cargo", type=Path, default=Path("cargo"))
    setup.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("collect", allow_abbrev=False)
    command.add_argument("--runtime", type=Path, required=True)
    command.add_argument("--repository-root", type=Path, required=True)
    command.add_argument("--repository", required=True)
    command.add_argument("--visibility", required=True)
    command.add_argument("--source-commit", required=True)
    command.add_argument("--observed-at", required=True)
    command.add_argument("--provider-evidence", type=Path)
    command.add_argument("--maximum-intent-age-days", type=int, default=30)
    command.add_argument("--maximum-provider-age-seconds", type=int, default=86400)
    command.add_argument("--output", type=Path, required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "prepare":
            prepare(args)
            return 0
        result = collect(args)
        write_result(args.output, result)
        print("roadmap collection retained for review; publication denied")
        return 2
    except (CollectorError, OSError, ValueError, KeyError, TypeError, yaml.YAMLError, RecursionError):
        error = sys.exception()
        code = str(error) if isinstance(error, CollectorError) and str(error) in MESSAGES else "INPUT"
        if args.command == "collect":
            try:
                write_result(args.output, {"schema": SCHEMA, "status": "denied", "publication": "denied",
                                           "diagnostics": [diagnostic(code)]})
            except (CollectorError, OSError):
                pass
        print("roadmap collector: " + code, file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
