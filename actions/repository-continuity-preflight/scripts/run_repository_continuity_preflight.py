# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Run the pinned offline EgoLint continuity capability and normalize its evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any


ACTION_ROOT = Path(__file__).resolve().parents[3]
PROFILE_PATH = ACTION_ROOT / "catalog/repository-continuity-preflight.json"
CONTRACT_MODULE_PATH = ACTION_ROOT / "scripts/validate_continuity_preflight_contract.py"
RAW_REPORT = Path(".reports/egolint/repository-continuity.json")
MAX_CAPTURE_BYTES = 64 * 1024


def _load_contract() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location("relay_continuity_contract", CONTRACT_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Relay continuity contract validator is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


contract = _load_contract()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def resolve_relative(root: Path, value: str, label: str) -> Path:
    if not contract.relative_path(value):
        raise ValueError(f"{label} must be repository-relative and traversal-safe")
    root = root.resolve()
    path = (root / value).resolve()
    if path != root and root not in path.parents:
        raise ValueError(f"{label} escapes the repository root")
    return path


def profile_digest() -> str:
    return hashlib.sha256(PROFILE_PATH.read_bytes()).hexdigest()


def verify_egolint_source(source: Path, profile: dict[str, Any]) -> None:
    selected = next(item for item in profile["sources"] if item["role"] == "validator")
    errors = contract.verify_sources({"sources": [selected]}, {selected["repository"]: source})
    if errors:
        raise ValueError("; ".join(sorted(errors)))


def snapshot_repository(source: Path, destination: Path, output: Path) -> None:
    output_relative = output.relative_to(source)

    def ignore(directory: str, names: list[str]) -> set[str]:
        current = Path(directory).resolve()
        ignored: set[str] = set()
        if current == source.resolve() and ".reports" in names:
            ignored.add(".reports")
        candidate = current / output_relative.name
        if candidate == output and output_relative.name in names:
            ignored.add(output_relative.name)
        return ignored

    shutil.copytree(source, destination, symlinks=True, ignore=ignore)


def build_command(source: Path, workspace: Path, policy: str, request: dict[str, Any]) -> list[str]:
    comparison = request["comparison"]
    live = request["live_evidence"]
    command = [
        "cargo", "run", "--offline", "--quiet", "--locked",
        "--manifest-path", str(source.resolve() / "Cargo.toml"), "--",
        "--workspace", str(workspace), "validate",
        "--repository-continuity", policy,
        "--continuity-base", comparison["base_revision"],
        "--continuity-head", comparison["head_revision"],
        "--continuity-disposition", comparison["disposition"],
        "--continuity-transition", "post-merge" if comparison["transition"] == "post-merge" else "pull-request",
        "--continuity-live-verification", "verified" if live["status"] == "verified" else "unavailable",
        "--continuity-evaluation-date", comparison["evaluation_date"],
    ]
    if live["status"] == "verified":
        for reference in live["references"]:
            command.extend(["--continuity-live-evidence", reference])
    for head in request["parallel_heads"]:
        command.extend(["--continuity-parallel-head", head])
    return command


def _layer(rule_id: str) -> str:
    if "-LIVE-" in rule_id:
        return "external-live"
    if "-COMPARISON-" in rule_id or "-PARALLEL-" in rule_id:
        return "local-git"
    if "-FRESHNESS-" in rule_id or "-EXCEPTION-" in rule_id:
        return "freshness-declaration"
    return "structural"


def _evidence(value: str) -> str:
    return {
        "valid": "passed", "verified": "passed", "invalid": "failed",
        "incomplete": "partial", "requires_external_verification": "partial",
        "unavailable": "unavailable", "not_applicable": "not-applicable",
    }[value]


def normalize(raw: dict[str, Any], request: dict[str, Any], digest: str) -> dict[str, Any]:
    status = raw["status"].replace("_", "-")
    if request["comparison"]["disposition"] == "exception" and status == "valid":
        status = "exempt"
    mode = request["policy"]["rollout_mode"]
    if status in {"valid", "exempt", "not-applicable"}:
        outcome = "passed"
    elif mode == "observe":
        outcome = "warning"
    else:
        outcome = "failed"
    findings = [
        {
            "id": item["rule_id"],
            "severity": item["severity"],
            "layer": _layer(item["rule_id"]),
            "summary": item["message"][:512],
            "remediation": item["remediation"][:1024],
        }
        for item in raw["diagnostics"][:256]
    ]
    counts = {key: sum(item["severity"] == key for item in findings) for key in ("info", "warning", "error", "critical")}
    counts["total"] = len(findings)
    comparison = raw["comparison"]
    result = {
        "schema_version": contract.RESULT_SCHEMA,
        "profile": {"version": request["profile"]["version"], "sha256": digest},
        "repository": {"id": request["repository"]["id"], "visibility": request["repository"]["visibility"]},
        "rollout_mode": mode,
        "semantic_status": status,
        "outcome": outcome,
        "comparison": {
            "requested_base": comparison["base"]["requested"],
            "requested_head": comparison["head"]["requested"],
            "resolved_base": comparison["base"].get("resolved_revision"),
            "resolved_head": comparison["head"].get("resolved_revision"),
            "topology": comparison["topology"].replace("_", "-"),
        },
        "evidence_layers": {
            "structural": _evidence(raw["evidence_layers"]["structural"]),
            "freshness-declaration": _evidence(raw["evidence_layers"]["freshness_declaration"]),
            "local-git": _evidence(raw["evidence_layers"]["local_git"]),
            "external-live": {
                "verified": "passed",
                "partial": "partial",
                "unavailable": "unavailable",
                "not-required": "not-applicable",
            }[request["live_evidence"]["status"]],
        },
        "findings": findings,
        "counts": counts,
        "corrective_actions": list(dict.fromkeys(item["remediation"] for item in findings))[:32],
        "privacy": {
            "classification": f"{request['repository']['visibility']}-repository",
            "contains_handoff_content": False,
            "redaction": "allowlisted-metadata-only",
        },
    }
    errors = contract.validate_result(result)
    if errors:
        raise ValueError("normalized result is invalid: " + "; ".join(errors))
    return result


def unavailable(request: dict[str, Any], digest: str, summary: str) -> dict[str, Any]:
    safe_summary = summary.replace("\n", " ")[:512]
    finding = {
        "id": "RELAY-CONT-AVAIL-001", "severity": "error", "layer": "local-git",
        "summary": safe_summary,
        "remediation": "Provide the exact pinned EgoLint source and an offline Cargo toolchain, then rerun the preflight.",
    }
    return {
        "schema_version": contract.RESULT_SCHEMA,
        "profile": {"version": request["profile"]["version"], "sha256": digest},
        "repository": {"id": request["repository"]["id"], "visibility": request["repository"]["visibility"]},
        "rollout_mode": request["policy"]["rollout_mode"], "semantic_status": "unavailable", "outcome": "unavailable",
        "comparison": {"requested_base": request["comparison"]["base_revision"], "requested_head": request["comparison"]["head_revision"], "resolved_base": None, "resolved_head": None, "topology": "unavailable"},
        "evidence_layers": {"structural": "unavailable", "freshness-declaration": "unavailable", "local-git": "unavailable", "external-live": "not-applicable"},
        "findings": [finding], "counts": {"info": 0, "warning": 0, "error": 1, "critical": 0, "total": 1},
        "corrective_actions": [finding["remediation"]],
        "privacy": {"classification": f"{request['repository']['visibility']}-repository", "contains_handoff_content": False, "redaction": "allowlisted-metadata-only"},
    }


def write_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def run(namespace: argparse.Namespace) -> tuple[dict[str, Any], Path]:
    root = namespace.repository_root.resolve()
    request_path = resolve_relative(root, namespace.request, "request")
    policy_path = resolve_relative(root, namespace.continuity_policy, "continuity policy")
    request = load_object(request_path)
    errors = contract.validate_request(request)
    profile = load_object(PROFILE_PATH)
    digest = profile_digest()
    if errors:
        raise ValueError("invalid request: " + "; ".join(errors))
    if request["profile"] != {"version": profile["version"], "sha256": digest}:
        raise ValueError("request profile does not match the installed Relay profile bytes")
    output = resolve_relative(root, request["output"]["path"], "output")
    try:
        verify_egolint_source(namespace.egolint_source.resolve(), profile)
        if shutil.which("cargo") is None:
            raise RuntimeError("the offline Cargo runner is unavailable")
        with tempfile.TemporaryDirectory(prefix="relay-continuity-") as temporary:
            snapshot = Path(temporary) / "repository"
            snapshot_repository(root, snapshot, output)
            relative_policy = policy_path.relative_to(root).as_posix()
            completed = subprocess.run(
                build_command(namespace.egolint_source, snapshot, relative_policy, request),
                cwd=snapshot, env={**os.environ, "CARGO_NET_OFFLINE": "true", "GIT_OPTIONAL_LOCKS": "0"},
                capture_output=True, check=False,
            )
            raw_path = snapshot / RAW_REPORT
            if not raw_path.is_file():
                stderr = completed.stderr[-MAX_CAPTURE_BYTES:].decode("utf-8", errors="replace")
                raise RuntimeError(f"EgoLint produced no continuity report (exit {completed.returncode}): {stderr}")
            result = normalize(load_object(raw_path), request, digest)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError):
        result = unavailable(request, digest, "The exact offline EgoLint continuity capability was unavailable or produced incompatible evidence.")
    write_atomic(output, result)
    return result, output


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    value.add_argument("--repository-root", required=True, type=Path)
    value.add_argument("--request", required=True)
    value.add_argument("--egolint-source", required=True, type=Path)
    value.add_argument("--continuity-policy", required=True)
    return value


def main(arguments: list[str] | None = None) -> int:
    result, output = run(parser().parse_args(arguments))
    print(f"{result['outcome'].upper()} repository continuity preflight: {output}")
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with Path(github_output).open("a", encoding="utf-8") as stream:
            stream.write(f"result={output}\noutcome={result['outcome']}\n")
    return 1 if result["outcome"] in {"failed", "unavailable"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
