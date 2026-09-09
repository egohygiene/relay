# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Validate Relay's pinned continuity-preflight contracts without network access."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = REPOSITORY_ROOT / "catalog/repository-continuity-preflight.json"
SCHEMA_DIRECTORY = REPOSITORY_ROOT / "schemas"
PROFILE_SCHEMA = "relay.repository-continuity-preflight-profile/v1"
REQUEST_SCHEMA = "relay.repository-continuity-preflight-request/v1"
RESULT_SCHEMA = "relay.repository-continuity-preflight-result/v1"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REPOSITORY_ID = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
STABLE_REFERENCE = re.compile(
    r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/(?:issues|pull)/[1-9][0-9]*$"
)
SOURCE_ROLES = {
    "portable-contract",
    "organization-policy",
    "validator",
    "materializer",
}
ROLLOUT_MODES = {"observe", "ratchet", "enforce"}
EVIDENCE_LAYERS = {
    "structural",
    "freshness-declaration",
    "local-git",
    "external-live",
}
FORBIDDEN_AUTHORITY = {
    "stage",
    "commit",
    "push",
    "open-pull-request",
    "comment",
    "merge",
    "release",
    "deploy",
    "publish",
}


def load_object(path: Path) -> dict[str, Any]:
    """Load one JSON object or raise a readable validation error."""

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def exact_keys(
    value: Any,
    expected: set[str],
    label: str,
    errors: list[str],
) -> bool:
    """Require one closed object and append deterministic key diagnostics."""

    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return False
    actual = set(value)
    for key in sorted(expected - actual):
        errors.append(f"{label} is missing {key}")
    for key in sorted(actual - expected):
        errors.append(f"{label} contains unsupported key {key}")
    return actual == expected


def relative_path(value: Any) -> bool:
    """Return whether a value is a traversal-safe repository-relative path."""

    if not isinstance(value, str) or not value or value.startswith("/"):
        return False
    return ".." not in Path(value).parts


def validate_profile(profile: dict[str, Any]) -> list[str]:
    """Validate the closed profile and its release-gated immutable sources."""

    errors: list[str] = []
    expected = {
        "$schema",
        "schema_version",
        "version",
        "status",
        "owner",
        "updated",
        "purpose",
        "rollout",
        "sources",
        "interfaces",
        "execution",
        "information_safety",
        "ownership",
    }
    if not exact_keys(profile, expected, "profile", errors):
        return errors
    if profile["schema_version"] != PROFILE_SCHEMA:
        errors.append("profile.schema_version is unsupported")
    if profile["owner"] != "egohygiene/relay":
        errors.append("profile.owner must be egohygiene/relay")

    rollout = profile["rollout"]
    if exact_keys(
        rollout,
        {"stage", "maximum_stage_before_release", "activation_gate", "unavailable_behavior"},
        "profile.rollout",
        errors,
    ):
        if rollout["stage"] not in ROLLOUT_MODES:
            errors.append("profile.rollout.stage is unsupported")
        if rollout["maximum_stage_before_release"] != "observe":
            errors.append("profile rollout must remain capped at observe before release")
        if rollout["unavailable_behavior"] != "fail-closed-with-explicit-unavailable-result":
            errors.append("profile unavailable behavior must fail closed")
        if not isinstance(rollout["activation_gate"], list) or not rollout["activation_gate"]:
            errors.append("profile.rollout.activation_gate must be non-empty")

    sources = profile["sources"]
    if not isinstance(sources, list) or len(sources) != 4:
        errors.append("profile.sources must contain exactly four owning sources")
        sources = []
    roles: list[str] = []
    source_ids: set[str] = set()
    release_incomplete = False
    for index, source in enumerate(sources):
        label = f"profile.sources[{index}]"
        if not exact_keys(
            source,
            {"id", "role", "repository", "revision", "version", "lifecycle", "release_included", "artifacts"},
            label,
            errors,
        ):
            continue
        if source["id"] in source_ids:
            errors.append(f"{label}.id must be unique")
        source_ids.add(source["id"])
        roles.append(source["role"])
        if source["role"] not in SOURCE_ROLES:
            errors.append(f"{label}.role is unsupported")
        if not isinstance(source["repository"], str) or not REPOSITORY_ID.fullmatch(source["repository"]):
            errors.append(f"{label}.repository is invalid")
        if not isinstance(source["revision"], str) or not FULL_SHA.fullmatch(source["revision"]):
            errors.append(f"{label}.revision must be a full immutable commit SHA")
        if source["lifecycle"] not in {"draft", "proposed", "stable", "deprecated"}:
            errors.append(f"{label}.lifecycle is unsupported")
        if not isinstance(source["release_included"], bool):
            errors.append(f"{label}.release_included must be boolean")
        if source["release_included"] is not True:
            release_incomplete = True
        if source["release_included"] and source["lifecycle"] != "stable":
            errors.append(f"{label} cannot be release-included before stable")
        artifacts = source["artifacts"]
        if not isinstance(artifacts, list) or not artifacts:
            errors.append(f"{label}.artifacts must be non-empty")
            continue
        artifact_ids: set[str] = set()
        for artifact_index, artifact in enumerate(artifacts):
            artifact_label = f"{label}.artifacts[{artifact_index}]"
            if not exact_keys(artifact, {"id", "path", "sha256"}, artifact_label, errors):
                continue
            if artifact["id"] in artifact_ids:
                errors.append(f"{artifact_label}.id must be unique within its source")
            artifact_ids.add(artifact["id"])
            if not relative_path(artifact["path"]):
                errors.append(f"{artifact_label}.path must be repository-relative")
            if not isinstance(artifact["sha256"], str) or not SHA256.fullmatch(artifact["sha256"]):
                errors.append(f"{artifact_label}.sha256 must be lowercase SHA-256")
    if set(roles) != SOURCE_ROLES or len(roles) != len(set(roles)):
        errors.append("profile.sources must contain each owning role exactly once")
    if release_incomplete and (profile["status"] != "proposed" or rollout.get("stage") != "observe"):
        errors.append("unreleased sources require proposed status at observe")

    interfaces = profile["interfaces"]
    if exact_keys(
        interfaces,
        {"request_contract", "result_contract", "validator_report_contract", "local_ci_result_parity", "evidence_layers"},
        "profile.interfaces",
        errors,
    ):
        if interfaces["request_contract"] != REQUEST_SCHEMA:
            errors.append("profile.interfaces.request_contract is unsupported")
        if interfaces["result_contract"] != RESULT_SCHEMA:
            errors.append("profile.interfaces.result_contract is unsupported")
        if interfaces["validator_report_contract"] != "egolint.repository-continuity-report/v1":
            errors.append("profile must consume the EgoLint v1 report")
        if interfaces["local_ci_result_parity"] is not True:
            errors.append("local and CI results must share one contract")
        if interfaces["evidence_layers"] != [
            "structural",
            "freshness-declaration",
            "local-git",
            "external-live",
        ]:
            errors.append("profile evidence layers must retain canonical order")

    execution = profile["execution"]
    if exact_keys(
        execution,
        {"default_network", "base_head_required", "semantic_authoring", "implicit_writes", "forbidden_authority"},
        "profile.execution",
        errors,
    ):
        if execution["default_network"] != "denied":
            errors.append("profile execution must default to no network")
        if execution["base_head_required"] is not True:
            errors.append("profile execution must require explicit base/head")
        if execution["semantic_authoring"] != "forbidden":
            errors.append("Relay preflight must not author semantic prose")
        if execution["implicit_writes"] != "forbidden":
            errors.append("Relay preflight must not perform implicit writes")
        if set(execution["forbidden_authority"]) != FORBIDDEN_AUTHORITY:
            errors.append("profile execution must prohibit the complete authority set")

    safety = profile["information_safety"]
    if exact_keys(
        safety,
        {"minimum_necessary", "contains_handoff_content", "private_output", "untrusted_content", "excluded"},
        "profile.information_safety",
        errors,
    ):
        if safety["contains_handoff_content"] is not False:
            errors.append("preflight evidence must exclude handoff content")
        if safety["private_output"] != "allowlisted-metadata-only":
            errors.append("private output must be allowlisted metadata only")
        if "continuity-free-form-body" not in safety["excluded"]:
            errors.append("preflight evidence must exclude continuity free-form body text")
    return errors


def validate_request(request: dict[str, Any]) -> list[str]:
    """Validate one closed future local/CI request without resolving Git state."""

    errors: list[str] = []
    if not exact_keys(
        request,
        {"schema_version", "profile", "repository", "comparison", "policy", "live_evidence", "parallel_heads", "output"},
        "request",
        errors,
    ):
        return errors
    if request["schema_version"] != REQUEST_SCHEMA:
        errors.append("request.schema_version is unsupported")
    profile = request["profile"]
    if exact_keys(profile, {"version", "sha256"}, "request.profile", errors):
        if not isinstance(profile["sha256"], str) or not SHA256.fullmatch(profile["sha256"]):
            errors.append("request.profile.sha256 must be lowercase SHA-256")
    repository = request["repository"]
    if exact_keys(repository, {"id", "visibility", "root"}, "request.repository", errors):
        if not isinstance(repository["id"], str) or not REPOSITORY_ID.fullmatch(repository["id"]):
            errors.append("request.repository.id is invalid")
        if repository["visibility"] not in {"public", "private", "internal"}:
            errors.append("request.repository.visibility is unsupported")
        if repository["root"] != ".":
            errors.append("request.repository.root must be the explicit current repository")
    comparison = request["comparison"]
    if exact_keys(
        comparison,
        {"base_revision", "head_revision", "disposition", "transition", "evaluation_date"},
        "request.comparison",
        errors,
    ):
        if comparison["base_revision"] != "unborn" and not FULL_SHA.fullmatch(str(comparison["base_revision"])):
            errors.append("request.comparison.base_revision must be a full SHA or unborn")
        if comparison["head_revision"] != "working-tree" and not FULL_SHA.fullmatch(str(comparison["head_revision"])):
            errors.append("request.comparison.head_revision must be a full SHA or working-tree")
        if comparison["disposition"] not in {"updated", "reviewed-no-change", "exception"}:
            errors.append("request.comparison.disposition is unsupported")
        if comparison["transition"] not in {"pull-request", "post-merge", "local-review"}:
            errors.append("request.comparison.transition is unsupported")
    policy = request["policy"]
    if exact_keys(policy, {"rollout_mode", "exception_reference"}, "request.policy", errors):
        if policy["rollout_mode"] not in ROLLOUT_MODES:
            errors.append("request.policy.rollout_mode is unsupported")
        exception_reference = policy["exception_reference"]
        if comparison.get("disposition") == "exception":
            if not isinstance(exception_reference, str) or not STABLE_REFERENCE.fullmatch(exception_reference):
                errors.append("exception disposition requires one stable GitHub issue or pull-request reference")
        elif exception_reference is not None:
            errors.append("non-exception disposition cannot declare an exception reference")
    live = request["live_evidence"]
    if exact_keys(live, {"status", "references"}, "request.live_evidence", errors):
        if live["status"] not in {"verified", "partial", "unavailable", "not-required"}:
            errors.append("request.live_evidence.status is unsupported")
        if not isinstance(live["references"], list):
            errors.append("request.live_evidence.references must be an array")
        elif live["status"] == "verified" and not live["references"]:
            errors.append("verified live evidence requires at least one stable reference")
        elif live["status"] in {"unavailable", "not-required"} and live["references"]:
            errors.append("unavailable or not-required live evidence cannot claim references")
    heads = request["parallel_heads"]
    if not isinstance(heads, list) or any(not isinstance(head, str) or not FULL_SHA.fullmatch(head) for head in heads):
        errors.append("request.parallel_heads must contain only full commit SHAs")
    output = request["output"]
    if exact_keys(output, {"format", "path"}, "request.output", errors):
        if output["format"] != "json":
            errors.append("request.output.format must be json")
        if not relative_path(output["path"]) or not str(output["path"]).endswith(".json"):
            errors.append("request.output.path must be a traversal-safe relative JSON path")
    return errors


def validate_result(result: dict[str, Any]) -> list[str]:
    """Validate one privacy-safe result and reject contradictory status pairs."""

    errors: list[str] = []
    if not exact_keys(
        result,
        {"schema_version", "profile", "repository", "rollout_mode", "semantic_status", "outcome", "comparison", "evidence_layers", "findings", "counts", "corrective_actions", "privacy"},
        "result",
        errors,
    ):
        return errors
    if result["schema_version"] != RESULT_SCHEMA:
        errors.append("result.schema_version is unsupported")
    if result["rollout_mode"] not in ROLLOUT_MODES:
        errors.append("result.rollout_mode is unsupported")
    semantic_status = result["semantic_status"]
    outcome = result["outcome"]
    if semantic_status == "valid" and outcome != "passed":
        errors.append("valid semantic status requires passed outcome")
    if semantic_status in {"unsupported", "unavailable"} and outcome != "unavailable":
        errors.append("unsupported or unavailable semantic status requires unavailable outcome")
    if result["rollout_mode"] == "observe" and semantic_status in {"invalid", "incomplete"} and outcome != "warning":
        errors.append("invalid or incomplete observe result must remain a warning")

    exact_keys(result["profile"], {"version", "sha256"}, "result.profile", errors)
    repository = result["repository"]
    exact_keys(repository, {"id", "visibility"}, "result.repository", errors)
    comparison = result["comparison"]
    exact_keys(
        comparison,
        {"requested_base", "requested_head", "resolved_base", "resolved_head", "topology"},
        "result.comparison",
        errors,
    )
    layers = result["evidence_layers"]
    if exact_keys(layers, EVIDENCE_LAYERS, "result.evidence_layers", errors):
        for layer, state in layers.items():
            if state not in {"passed", "failed", "partial", "unavailable", "not-applicable"}:
                errors.append(f"result.evidence_layers.{layer} is unsupported")

    findings = result["findings"]
    if not isinstance(findings, list) or len(findings) > 256:
        errors.append("result.findings must contain at most 256 items")
        findings = []
    severities = {"info": 0, "warning": 0, "error": 0, "critical": 0}
    for index, finding in enumerate(findings):
        label = f"result.findings[{index}]"
        if not exact_keys(finding, {"id", "severity", "layer", "summary", "remediation"}, label, errors):
            continue
        if finding["severity"] not in severities:
            errors.append(f"{label}.severity is unsupported")
        else:
            severities[finding["severity"]] += 1
        if finding["layer"] not in EVIDENCE_LAYERS:
            errors.append(f"{label}.layer is unsupported")
        if not isinstance(finding["summary"], str) or not finding["summary"]:
            errors.append(f"{label}.summary must be non-empty")
        if not isinstance(finding["remediation"], str) or not finding["remediation"]:
            errors.append(f"{label}.remediation must be non-empty")
    counts = result["counts"]
    if exact_keys(counts, {"info", "warning", "error", "critical", "total"}, "result.counts", errors):
        expected_counts = {**severities, "total": len(findings)}
        if counts != expected_counts:
            errors.append("result.counts must exactly match findings")
    if not isinstance(result["corrective_actions"], list) or any(
        not isinstance(action, str) or not action for action in result["corrective_actions"]
    ):
        errors.append("result.corrective_actions must contain non-empty strings")
    privacy = result["privacy"]
    if exact_keys(privacy, {"classification", "contains_handoff_content", "redaction"}, "result.privacy", errors):
        expected_classification = f"{repository.get('visibility')}-repository"
        if privacy["classification"] != expected_classification:
            errors.append("result privacy classification must match repository visibility")
        if privacy["contains_handoff_content"] is not False:
            errors.append("result must not contain handoff content")
        if privacy["redaction"] != "allowlisted-metadata-only":
            errors.append("result redaction must be allowlisted metadata only")
    return errors


def verify_sources(profile: dict[str, Any], roots: dict[str, Path]) -> list[str]:
    """Verify every pinned artifact byte against caller-supplied local checkouts."""

    errors: list[str] = []
    for source in profile.get("sources", []):
        repository = source["repository"]
        root = roots.get(repository)
        if root is None:
            errors.append(f"missing source checkout for {repository}")
            continue
        try:
            actual_revision = _git_revision(root)
        except ValueError as error:
            errors.append(str(error))
            continue
        if actual_revision != source["revision"]:
            errors.append(
                f"{repository} revision mismatch: expected {source['revision']}, got {actual_revision}"
            )
            continue
        for artifact in source["artifacts"]:
            path = root / artifact["path"]
            if not path.is_file() or path.is_symlink():
                errors.append(f"{repository} artifact is missing or not a regular file: {artifact['path']}")
                continue
            actual_digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual_digest != artifact["sha256"]:
                errors.append(
                    f"{repository} artifact digest mismatch for {artifact['path']}: "
                    f"expected {artifact['sha256']}, got {actual_digest}"
                )
    return errors


def _git_revision(root: Path) -> str:
    """Resolve HEAD from a local checkout without invoking the network."""

    git_entry = root / ".git"
    git_directory = git_entry
    if git_entry.is_file():
        pointer = git_entry.read_text(encoding="utf-8").strip()
        if not pointer.startswith("gitdir: "):
            raise ValueError(f"source checkout has an invalid .git pointer: {root}")
        git_directory = Path(pointer.removeprefix("gitdir: "))
        if not git_directory.is_absolute():
            git_directory = (root / git_directory).resolve()
    head = git_directory / "HEAD"
    if not head.is_file():
        raise ValueError(f"source checkout has no .git/HEAD: {root}")
    value = head.read_text(encoding="utf-8").strip()
    if value.startswith("ref: "):
        reference = git_directory / value.removeprefix("ref: ")
        if reference.is_file():
            value = reference.read_text(encoding="utf-8").strip()
        else:
            packed = git_directory / "packed-refs"
            if packed.is_file():
                matches = [
                    line.split(" ", maxsplit=1)[0]
                    for line in packed.read_text(encoding="utf-8").splitlines()
                    if line.endswith(f" {value.removeprefix('ref: ')}")
                ]
                value = matches[0] if matches else ""
    if not FULL_SHA.fullmatch(value):
        raise ValueError(f"source checkout HEAD is not a full commit SHA: {root}")
    return value


def print_errors(errors: Iterable[str]) -> int:
    """Print deterministic diagnostics and return a conventional status code."""

    ordered = sorted(set(errors))
    if not ordered:
        print("PASS continuity preflight contract")
        return 0
    for error in ordered:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    """Build the long-form-only command-line interface."""

    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="validate Relay-owned profile and schemas")
    verify = subparsers.add_parser(
        "verify-sources",
        help="verify pinned bytes in explicit local source checkouts",
        allow_abbrev=False,
    )
    verify.add_argument("--aether-source", required=True, type=Path)
    verify.add_argument("--hygiene-source", required=True, type=Path)
    verify.add_argument("--egolint-source", required=True, type=Path)
    verify.add_argument("--holon-source", required=True, type=Path)
    return parser


def main(arguments: list[str] | None = None) -> int:
    """Validate the local contract or verify explicitly supplied source bytes."""

    namespace = build_parser().parse_args(arguments)
    profile = load_object(PROFILE_PATH)
    errors = validate_profile(profile)
    for schema_path in sorted(SCHEMA_DIRECTORY.glob("repository-continuity-preflight-*.schema.json")):
        schema = load_object(schema_path)
        if schema.get("additionalProperties") is not False:
            errors.append(f"schema root must be closed: {schema_path.relative_to(REPOSITORY_ROOT)}")
    if namespace.command == "verify-sources" and not errors:
        errors.extend(
            verify_sources(
                profile,
                {
                    "egohygiene/aether": namespace.aether_source,
                    "egohygiene/hygiene": namespace.hygiene_source,
                    "egohygiene/egolint": namespace.egolint_source,
                    "egohygiene/holon": namespace.holon_source,
                },
            )
        )
    return print_errors(errors)


if __name__ == "__main__":
    raise SystemExit(main())
