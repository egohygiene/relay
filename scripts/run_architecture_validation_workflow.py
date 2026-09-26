# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Internal, read-only architecture workflow orchestration and bounded evidence."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import re
import sys
import tempfile

# -I removes the caller checkout and PYTHONPATH. Import only adjacent Relay code.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_repository_architecture_validation as adapter


SCHEMA = "relay.repository-architecture-workflow-evidence/v1"
WORKFLOW = "egohygiene/relay/.github/workflows/repository-architecture-validation.yml"
STAGES = ("harden", "preflight", "checkout", "hygiene", "egolint", "holon", "acquire", "build", "validate")
OUTCOMES = {"success", "failure", "cancelled", "skipped"}
EVENTS = {"pull_request", "push", "workflow_dispatch", "schedule"}
MAX_REPORT = 32768
MAX_BUNDLE = 6 * adapter.MAX_REPORT
RESULT_PATH = ".reports/architecture-validation/result.json"
MESSAGES = {
    "AW-OK": "Architecture evidence is retained; advisory findings do not block this run.",
    "AW-INPUT": "Workflow identity, event, or bounded inputs are invalid; review the caller contract.",
    "AW-STAGE": "An execution prerequisite failed or did not run; inspect the recorded stage outcomes.",
    "AW-EVIDENCE": "Fresh normalized validation evidence is unavailable; previous reports were not reused.",
    "AW-REQUIRED": "Required enforcement is unavailable until the profile release and acceptance gates are satisfied.",
    "AW-UNAVAILABLE": "The shared adapter reported unavailable validation; inspect the normalized result.",
    "AW-CANCELLED": "Execution was cancelled; retained evidence may be incomplete.",
}


def require(condition: bool) -> None:
    if not condition:
        raise ValueError("Architecture workflow contract rejected")


def field(env: dict, name: str, maximum: int = 4096) -> str:
    value = env.get(name, "")
    require(isinstance(value, str) and len(value.encode()) <= maximum)
    return value


def number(value: str, maximum: int) -> int:
    require(bool(re.fullmatch(r"[1-9][0-9]{0,19}", value)))
    result = int(value)
    require(result <= maximum)
    return result


def identity(env: dict, *, strict: bool = True) -> dict:
    repository = field(env, "GITHUB_REPOSITORY", 140)
    revision = field(env, "GITHUB_SHA", 40)
    visibility = field(env, "RELAY_ARCH_VISIBILITY", 16)
    relay_revision = field(env, "RELAY_ARCH_WORKFLOW_SHA", 40)
    require(bool(adapter.contract.REPOSITORY_ID.fullmatch(repository)))
    require(all(part not in {".", ".."} for part in repository.split("/")))
    require(bool(adapter.contract.FULL_SHA.fullmatch(revision)))
    require(visibility in {"public", "private", "internal"})
    require(bool(adapter.contract.FULL_SHA.fullmatch(relay_revision)))
    caller = field(env, "GITHUB_WORKFLOW_REF", 1024)
    require(bool(re.fullmatch(re.escape(repository) + r"/\.github/workflows/[A-Za-z0-9_.-]+\.ya?ml@[^\x00-\x20]+", caller)))
    event = field(env, "GITHUB_EVENT_NAME", 80)
    if strict:
        require(event in EVENTS)
        require(field(env, "RELAY_ARCH_WORKFLOW_REPOSITORY") == "egohygiene/relay")
        require(field(env, "RELAY_ARCH_WORKFLOW_REF") == WORKFLOW + "@" + relay_revision)
        ref = field(env, "GITHUB_REF", 1024)
        require(bool(re.fullmatch(r"refs/pull/[1-9][0-9]*/merge", ref)) if event == "pull_request"
                else ref.startswith("refs/heads/") and len(ref) > len("refs/heads/"))
    return {"repository": repository, "revision": revision, "visibility": visibility,
            "relay_revision": relay_revision, "run_id": number(field(env, "GITHUB_RUN_ID"), 10**20 - 1),
            "run_attempt": number(field(env, "GITHUB_RUN_ATTEMPT"), 10**6),
            "caller_workflow_sha256": adapter.digest(caller.encode()),
            "event": event if event in EVENTS else "unsupported"}


def request_from_inputs(env: dict) -> tuple[dict, dict]:
    context = identity(env)
    check_id = field(env, "INPUT_CHECK_ID", 48)
    require(bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", check_id)))
    retention = number(field(env, "INPUT_RETENTION_DAYS"), 90)
    selected = adapter.profile()
    request = {
        "schema_version": adapter.contract.REQUEST_SCHEMA,
        "profile": {"version": selected["version"], "sha256": adapter.digest(adapter.read_file(adapter.PROFILE_PATH))},
        "repository": {"id": context["repository"], "visibility": context["visibility"], "root": ".",
                       "represented_revision": context["revision"]},
        "mode": field(env, "INPUT_MODE"),
        "adoption": {"repository-contracts": field(env, "INPUT_CONTRACT_ADOPTION"),
                     "architecture-records": field(env, "INPUT_ADR_ADOPTION"),
                     "diagram-sources": field(env, "INPUT_DIAGRAM_ADOPTION")},
        "inputs": {"repository_contracts": json.loads(field(env, "INPUT_CONTRACTS")),
                   "repository_intelligence_policy": field(env, "INPUT_ADR_POLICY") or None,
                   "diagram_roots": json.loads(field(env, "INPUT_DIAGRAM_ROOTS"))},
        "bounds": {"maximum_findings": 256, "maximum_scanned_files": 10000, "maximum_scanned_bytes": 104857600},
        "output": {"format": "json", "path": RESULT_PATH},
    }
    require(not adapter.contract.validate_request(request, selected))
    return request, {"identity": context, "check_id": check_id, "retention_days": retention}


def native_needed(request: dict) -> bool:
    return request["mode"] == "advisory" and any(
        request["adoption"][key] != "not-applicable" for key in ("repository-contracts", "architecture-records"))


def temp_root(env: dict) -> Path:
    path = adapter.safe_path(Path(field(env, "RUNNER_TEMP")))
    require(path.is_dir() and Path(env["RUNNER_TEMP"]).is_absolute())
    return path


def work_root(env: dict) -> Path:
    value = field(env, "INPUT_WORK_DIRECTORY")
    path = adapter.safe_path(Path(value))
    base = temp_root(env)
    require(Path(value).is_absolute() and path.parent == base and path.name.startswith("relay-architecture-work-"))
    require(path.is_dir())
    return path


def load_state(env: dict) -> tuple[Path, dict, dict]:
    work = work_root(env)
    state = adapter.decode(adapter.read_file(work / "state.json", MAX_REPORT))
    request = adapter.decode(adapter.read_file(work / "request.json", MAX_REPORT))
    require(state["identity"] == identity(env))
    require(not adapter.contract.validate_request(request, adapter.profile()))
    require(request["repository"] == {"id": state["identity"]["repository"], "visibility": state["identity"]["visibility"],
                                       "represented_revision": state["identity"]["revision"], "root": "."})
    return work, state, request


def outputs(env: dict, values: dict) -> None:
    # Values are trusted fixed strings, validated identities, or generated paths.
    lines = []
    for key, value in values.items():
        value = str(value)
        require("\n" not in value and "\r" not in value)
        lines.append(f"{key}={value}\n")
    with Path(env["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as handle:
        handle.write("".join(lines))


def preflight(env: dict) -> dict:
    request, state = request_from_inputs(env)
    work = Path(tempfile.mkdtemp(prefix="relay-architecture-work-", dir=temp_root(env)))
    adapter.write_atomic(work / "request.json", adapter.encoded(request))
    adapter.write_atomic(work / "state.json", adapter.encoded(state))
    return {"work-directory": str(work), "native-needed": str(native_needed(request)).lower(),
            "retention-days": state["retention_days"], "producer": "architecture-" + state["check_id"]}


def source_root(env: dict, name: str) -> Path:
    return adapter.safe_path(Path(env["GITHUB_WORKSPACE"]) / "relay-architecture-sources" / name)


def build_environment(work: Path) -> dict:
    result = adapter.environment()
    # Dependency acquisition has no caller configuration, shared caches, or credentials.
    for name in ("home", "cargo", "rustup"):
        (work / name).mkdir(exist_ok=True)
    result.update({"HOME": str(work / "home"), "CARGO_HOME": str(work / "cargo"),
                   "RUSTUP_HOME": str(work / "rustup"), "RUSTUP_TOOLCHAIN": "1.85.1"})
    return result


def acquire(env: dict) -> None:
    work, _state, request = load_state(env)
    require(native_needed(request))
    require(sys.version_info[:2] == (3, 12) and sys.platform == "linux" and platform.machine() == "x86_64")
    for source in adapter.profile()["sources"]:
        root = source_root(env, source["repository"].split("/")[1])
        require(adapter.git(root, "rev-parse", "HEAD").decode().strip() == source["revision"])
    build_env = build_environment(work)
    adapter.execute([sys.executable, "-I", "-m", "venv", str(work / "venv")], cwd=work, env=build_env)
    python = str(work / "venv/bin/python")
    pip = [python, "-I", "-m", "pip", "--isolated", "--disable-pip-version-check", "--no-cache-dir"]
    adapter.execute([*pip, "download", "--only-binary=:all:", "--require-hashes", "--requirement", str(adapter.REQUIREMENTS),
                     "--dest", str(work / "wheels")], cwd=work, env=build_env, timeout=180)
    adapter.execute([*pip, "install", "--no-index", "--find-links", str(work / "wheels"), "--require-hashes",
                     "--requirement", str(adapter.REQUIREMENTS)], cwd=work, env=build_env, timeout=120)
    adapter.execute(["rustup", "toolchain", "install", "1.85.1", "--profile", "minimal", "--no-self-update"],
                    cwd=work, env=build_env, timeout=180)
    _, cargo = adapter.execute(["rustup", "which", "--toolchain", "1.85.1", "cargo"], cwd=work, env=build_env)
    cargo_path = adapter.safe_path(Path(cargo.decode().strip()))
    require(cargo_path.is_relative_to(work / "rustup") and cargo_path.is_file())
    build_env["PATH"] = str(cargo_path.parent) + os.pathsep + build_env["PATH"]
    adapter.execute([str(cargo_path), "fetch", "--locked", "--manifest-path", str(source_root(env, "egolint") / "Cargo.toml")],
                    cwd=work, env=build_env, timeout=180)
    adapter.write_atomic(work / "toolchain.json", adapter.encoded({"cargo": str(cargo_path)}))


def build(env: dict) -> None:
    work, _state, request = load_state(env)
    require(native_needed(request))
    toolchain = adapter.decode(adapter.read_file(work / "toolchain.json", MAX_REPORT))
    cargo = adapter.safe_path(Path(toolchain["cargo"]))
    require(cargo.is_relative_to(work / "rustup"))
    # A separate isolated Python process supplies exactly the hash-locked wheels.
    bootstrap = "import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module('run_repository_architecture_validation',run_name='__main__')"
    args = [str(work / "venv/bin/python"), "-I", "-c", bootstrap, str(adapter.ROOT / "scripts"), "prepare"]
    for name in ("hygiene", "egolint", "holon"):
        args.extend(["--" + name + "-source", str(source_root(env, name))])
    args.extend(["--cargo", str(cargo), "--output", str(work / "runtime")])
    adapter.execute(args, cwd=work, env=build_environment(work), timeout=360)


def validate(env: dict, *, runtime: Path | None = None) -> dict:
    work, _state, request = load_state(env)
    root = adapter.safe_path(Path(env["GITHUB_WORKSPACE"]) / "caller")
    require(adapter.git(root, "rev-parse", "HEAD").decode().strip() == request["repository"]["represented_revision"])
    # Never accept a prior result when the adapter fails before returning fresh evidence.
    require(not (work / "validation.json").exists() and not (work / "evidence").exists())
    result = adapter.run(argparse.Namespace(repository_root=root, request=work / "request.json", runtime=runtime or work / "runtime"))
    require(not adapter.contract.validate_result(result, adapter.profile()))
    files = {RESULT_PATH: adapter.encoded(result)}
    for path in result["artifacts"].values():
        if path is not None:
            files[path] = adapter.read_file(root / path)
    require(len(files) <= 5 and sum(len(value) for value in files.values()) <= 5 * adapter.MAX_REPORT)
    for path, value in files.items():
        adapter.write_atomic(work / "evidence" / path, value)
    receipt = {"identity": identity(env), "files": {path: adapter.digest(value) for path, value in sorted(files.items())}}
    adapter.write_atomic(work / "validation.json", adapter.encoded(receipt))
    return result


def stage_outcomes(env: dict) -> dict:
    raw = adapter.decode(field(env, "INPUT_STAGES", 65536).encode() or b"{}")
    outcomes = {}
    for name in STAGES:
        item = raw.get(name, {})
        require(isinstance(item, dict))
        value = item.get("outcome", "skipped")
        require(value in OUTCOMES)
        outcomes[name] = value
    return outcomes


def fresh_evidence(env: dict, work: Path, request: dict) -> tuple[dict, dict]:
    receipt = adapter.decode(adapter.read_file(work / "validation.json", MAX_REPORT))
    require(set(receipt) == {"identity", "files"} and receipt["identity"] == identity(env))
    require(isinstance(receipt["files"], dict) and 1 <= len(receipt["files"]) <= 5)
    result_bytes = adapter.read_file(work / "evidence" / RESULT_PATH)
    result = adapter.decode(result_bytes)
    require(not adapter.contract.validate_result(result, adapter.profile()))
    require(result["repository"] == {key: value for key, value in request["repository"].items() if key != "root"})
    require(result["profile"] == request["profile"] and result["mode"] == request["mode"])
    expected = {RESULT_PATH, *(p for p in result["artifacts"].values() if p is not None)}
    require(set(receipt["files"]) == expected)
    files = {}
    for path, sha in receipt["files"].items():
        require(adapter.contract.relative_path(path) and path.startswith(".reports/architecture-validation/"))
        data = adapter.read_file(work / "evidence" / path)
        require(adapter.digest(data) == sha)
        files[path] = data
    return result, files


def decision(stages: dict, request: dict | None, result: dict | None, evidence_error: bool) -> tuple[str, str]:
    if "cancelled" in stages.values():
        return "cancelled", "AW-CANCELLED"
    if stages["preflight"] != "success" or request is None:
        return "failure", "AW-INPUT"
    if request["mode"] == "required":
        return "failure", "AW-REQUIRED"
    required = ["harden", "checkout"] + (["hygiene", "egolint", "holon", "acquire", "build"] if native_needed(request) else [])
    if any(stages[name] != "success" for name in required):
        return "failure", "AW-STAGE"
    if result is None or evidence_error:
        return "failure", "AW-EVIDENCE"
    if result["outcome"] == "unavailable":
        return "failure", "AW-UNAVAILABLE"
    if stages["validate"] != "success" or result["outcome"] == "failed":
        return "failure", "AW-STAGE"
    return "success", "AW-OK"


def finalize(env: dict) -> tuple[dict, dict]:
    context = identity(env, strict=False)
    stages = stage_outcomes(env)
    request, result, files, state, evidence_error = None, None, {}, None, False
    if stages["preflight"] == "success":
        try:
            work, state, request = load_state(env)
            if stages["checkout"] == "success" and stages["validate"] in {"success", "failure"}:
                result, files = fresh_evidence(env, work, request)
        except (adapter.AdapterError, OSError, ValueError, KeyError, TypeError):
            result, files, evidence_error = None, {}, True
    outcome, code = decision(stages, request, result, evidence_error)
    check_id = state["check_id"] if state else "rejected"
    retention = state["retention_days"] if state else 30
    # Isolate each caller workflow and check within a shared run/artifact namespace.
    caller_hash = context["caller_workflow_sha256"][:16]
    producer = f"architecture-{check_id}-{caller_hash}"
    directory = Path(tempfile.mkdtemp(prefix="relay-architecture-report-", dir=temp_root(env)))
    report = {"schema_version": SCHEMA, "identity": context, "check_id": check_id,
              "mode": request["mode"] if request else "unknown", "retention_days": retention,
              "stages": stages, "validation": {"evidence": "retained" if result else "unavailable",
              "semantic_status": result["semantic_status"] if result else "unavailable",
              "outcome": result["outcome"] if result else "unavailable"},
              "reporting": {"normalization": "success", "artifact_upload": "pending"},
              "enforcement": {"planned_job_outcome": outcome, "code": code, "required_mode_available": False},
              "files": [{"path": path, "bytes": len(data), "sha256": adapter.digest(data)} for path, data in sorted(files.items())],
              "privacy": {"classification": context["visibility"] + "-repository", "contains_source_content": False}}
    require(len(adapter.encoded(report)) <= MAX_REPORT)
    require(sum(map(len, files.values())) + len(adapter.encoded(report)) <= MAX_BUNDLE)
    for path, data in files.items():
        adapter.write_atomic(directory / path, data)
    adapter.write_atomic(directory / "workflow.json", adapter.encoded(report))
    return report, {"report-directory": str(directory), "producer": producer, "retention-days": retention,
                    "workflow-outcome": outcome, "semantic-status": report["validation"]["semantic_status"],
                    "validation-outcome": report["validation"]["outcome"], "error-code": code}


def escape_command(value: str, *, property_value: bool = False) -> str:
    for original, replacement in (("%", "%25"), ("\r", "%0D"), ("\n", "%0A")):
        value = value.replace(original, replacement)
    return value.replace(":", "%3A").replace(",", "%2C") if property_value else value


def annotations(result: dict | None, code: str) -> list[str]:
    lines = []
    for finding in (result["findings"] if result else [])[:20]:
        kind = "warning" if finding["severity"] in {"warning", "error", "critical"} else "notice"
        properties = ["title=" + escape_command(finding["id"], property_value=True)]
        if finding["path"]:
            # Checkout lives at caller/, while retained source locations stay repository-relative.
            properties.append("file=" + escape_command("caller/" + finding["path"], property_value=True))
            if finding["line"] is not None:
                properties.append("line=" + str(finding["line"]))
        message = (finding["summary"] + " " + finding["remediation"])[:2048]
        lines.append(f"::{kind} {','.join(properties)}::{escape_command(message)}")
    if code != "AW-OK":
        lines = lines[:19]
        lines.append(f"::error title={code}::{MESSAGES[code]}")
    return lines


def present(env: dict) -> int:
    # Report only observed upload state; an artifact name alone never means success.
    directory = adapter.safe_path(Path(field(env, "INPUT_REPORT_DIRECTORY")))
    require(directory.parent == temp_root(env) and directory.name.startswith("relay-architecture-report-"))
    report = adapter.decode(adapter.read_file(directory / "workflow.json", MAX_REPORT))
    require(report["identity"] == identity(env, strict=False))
    code = report["enforcement"]["code"]
    require(code in MESSAGES)
    result = None
    if report["validation"]["evidence"] == "retained":
        result = adapter.decode(adapter.read_file(directory / RESULT_PATH))
        require(not adapter.contract.validate_result(result, adapter.profile()))
    upload = field(env, "INPUT_UPLOAD_OUTCOME")
    require(upload in OUTCOMES)
    digest = field(env, "INPUT_ARTIFACT_DIGEST", 71)
    require(not digest or bool(re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", digest)))
    uploaded = upload == "success" and bool(digest)
    lines = annotations(result, code)
    if not uploaded:
        lines = lines[:19] + ["::error title=AW-REPORT::Report preservation did not succeed; the job fails closed."]
    for line in lines:
        print(line)
    summary = ["## Repository architecture validation", "",
               f"- Semantic status: `{report['validation']['semantic_status']}`",
               f"- Validation outcome: `{report['validation']['outcome']}`",
               f"- Mode: `{report['mode']}`; required enforcement available: `false`",
               f"- Evidence upload: `{upload}`; archive digest: `{digest if uploaded else 'unavailable'}`",
               f"- Planned job outcome: `{report['enforcement']['planned_job_outcome']}`; code: `{code}`", "",
               "| Stage | Outcome |", "| --- | --- |"]
    summary.extend(f"| {name} | {value} |" for name, value in report["stages"].items())
    summary.extend(["", "Annotations are capped at 20. Full bounded findings are in the retained result.",
                    "Diagram inventory does not establish semantic validity. Reports contain no raw source or tool logs.", ""])
    with Path(env["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as handle:
        handle.write("\n".join(summary))
    return 0 if uploaded and report["enforcement"]["planned_job_outcome"] == "success" else 1


def main() -> int:
    env = dict(os.environ)
    operation = env.get("INPUT_OPERATION")
    try:
        if operation == "preflight":
            outputs(env, preflight(env))
        elif operation == "acquire":
            acquire(env)
        elif operation == "build":
            build(env)
        elif operation == "validate":
            result = validate(env)
            return 2 if result["outcome"] == "unavailable" else 1 if result["outcome"] == "failed" else 0
        elif operation == "finalize":
            _report, values = finalize(env)
            outputs(env, values)
        elif operation == "present":
            return present(env)
        else:
            require(False)
        return 0
    except (adapter.AdapterError, OSError, ValueError, KeyError, TypeError, RuntimeError, RecursionError):
        if operation == "present":
            print("::error title=AW-EVIDENCE::Architecture evidence presentation or preservation is unavailable.")
            if env.get("GITHUB_STEP_SUMMARY"):
                try:
                    with Path(env["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as handle:
                        handle.write("## Repository architecture validation\n\nEvidence presentation is unavailable; this job fails closed.\n")
                except OSError:
                    pass
        print("Architecture workflow operation failed; inspect the bounded stage report.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
