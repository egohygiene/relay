# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Validate Relay's pinned repository-architecture contracts offline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = REPOSITORY_ROOT / "catalog/repository-architecture-validation.json"
FIXTURES_PATH = (
    REPOSITORY_ROOT
    / "tests/fixtures/repository-architecture-validation/cases.v1.json"
)
SCHEMA_DIRECTORY = REPOSITORY_ROOT / "schemas"
PROFILE_SCHEMA = "relay.repository-architecture-validation-profile/v1"
REQUEST_SCHEMA = "relay.repository-architecture-validation-request/v1"
RESULT_SCHEMA = "relay.repository-architecture-validation-result/v1"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$")
ISO_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
SAFE_PATH = re.compile(r"^[A-Za-z0-9._/@-]+$")
REPOSITORY_ID = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
RULE_ID = re.compile(r"^[A-Z][A-Z0-9-]+-[0-9]{3}$")
RULE_FAMILY = re.compile(r"^[A-Z][A-Z0-9-]+$")
SOURCE_ROLES = {
    "organization-policy",
    "validator",
    "materializer",
}
EXPECTED_SOURCE_OWNERS = {
    "organization-policy": "egohygiene/hygiene",
    "validator": "egohygiene/egolint",
    "materializer": "egohygiene/holon",
}
CAPABILITIES = {
    "repository-contracts",
    "architecture-records",
    "diagram-sources",
}
ADOPTION_STATES = {"present", "legacy", "unknown", "not-applicable"}
COVERAGE_STATES = {
    "passed",
    "failed",
    "partial",
    "unavailable",
    "not-applicable",
}
MODES = {"advisory", "required"}
SEMANTIC_STATUSES = {
    "conformant",
    "nonconformant",
    "legacy",
    "incomplete",
    "not-applicable",
    "unavailable",
}
OUTCOMES = {"passed", "warning", "failed", "unavailable"}
SEVERITIES = {"info", "warning", "error", "critical"}
FINDING_SOURCES = {"egolint", "diagram-validator", "relay"}
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
REQUIRED_EXCLUSIONS = {
    "secrets-and-credentials",
    "absolute-local-paths",
    "raw-file-content",
    "environment-values",
    "provider-tokens",
    "workflow-logs",
    "private-cross-repository-content",
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
    """Return whether a value is a bounded repository-relative path."""

    if not isinstance(value, str) or not value or len(value) > 240:
        return False
    if value.startswith("/") or not SAFE_PATH.fullmatch(value):
        return False
    segments = value.split("/")
    return all(segment not in {"", ".", ".."} for segment in segments)


def _is_choice(value: Any, choices: set[str]) -> bool:
    """Return whether an untrusted value is a supported string choice."""

    return isinstance(value, str) and value in choices


def _expected_profile_reference(profile: dict[str, Any]) -> dict[str, str]:
    """Return the exact version and byte digest represented by the profile."""

    return {
        "version": str(profile.get("version", "")),
        "sha256": hashlib.sha256(PROFILE_PATH.read_bytes()).hexdigest(),
    }


def _bounded_text(
    value: Any,
    maximum: int,
    label: str,
    errors: list[str],
) -> None:
    if not isinstance(value, str) or not value or len(value) > maximum:
        errors.append(f"{label} must contain 1-{maximum} characters")


def validate_profile(profile: dict[str, Any]) -> list[str]:
    """Validate the closed profile, ownership boundary, pins, and rollout."""

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
        "capabilities",
        "interfaces",
        "execution",
        "bounds",
        "information_safety",
        "ownership",
    }
    if not exact_keys(profile, expected, "profile", errors):
        return errors
    if profile["schema_version"] != PROFILE_SCHEMA:
        errors.append("profile.schema_version is unsupported")
    if profile["$schema"] != "../schemas/repository-architecture-validation-profile.v1.schema.json":
        errors.append("profile.$schema must reference the Relay-owned v1 schema")
    if profile["owner"] != "egohygiene/relay":
        errors.append("profile.owner must be egohygiene/relay")
    if not _is_choice(profile["status"], {"proposed", "active", "deprecated"}):
        errors.append("profile.status is unsupported")
    if not isinstance(profile["version"], str) or not SEMVER.fullmatch(
        profile["version"]
    ):
        errors.append("profile.version must be semantic-version shaped")
    if not isinstance(profile["updated"], str) or not ISO_DATE.fullmatch(
        profile["updated"]
    ):
        errors.append("profile.updated must be an ISO date")
    _bounded_text(profile["purpose"], 1024, "profile.purpose", errors)

    rollout = profile["rollout"]
    if exact_keys(
        rollout,
        {
            "default_mode",
            "supported_modes",
            "maximum_mode_before_release",
            "activation_gate",
            "unavailable_behavior",
        },
        "profile.rollout",
        errors,
    ):
        if rollout["default_mode"] != "advisory":
            errors.append("profile rollout must default to advisory")
        if rollout["supported_modes"] != ["advisory", "required"]:
            errors.append("profile rollout modes must retain canonical order")
        if rollout["maximum_mode_before_release"] != "advisory":
            errors.append("unreleased profile must remain capped at advisory")
        if rollout["unavailable_behavior"] != "explicit-unavailable-result":
            errors.append("profile unavailable behavior must remain explicit")
        gates = rollout["activation_gate"]
        if (
            not isinstance(gates, list)
            or not gates
            or any(not isinstance(item, str) or not item for item in gates)
            or len(gates) != len(set(gates))
        ):
            errors.append("profile.rollout.activation_gate must be non-empty and unique")

    sources = profile["sources"]
    if not isinstance(sources, list) or len(sources) != 3:
        errors.append("profile.sources must contain exactly three owning sources")
        sources = []
    roles: list[str] = []
    source_ids: set[str] = set()
    release_incomplete = False
    for index, source in enumerate(sources):
        label = f"profile.sources[{index}]"
        if not exact_keys(
            source,
            {
                "id",
                "role",
                "repository",
                "revision",
                "version",
                "lifecycle",
                "release_included",
                "artifacts",
            },
            label,
            errors,
        ):
            continue
        source_id = source["id"]
        if not isinstance(source_id, str) or not re.fullmatch(
            r"[a-z0-9]+(?:-[a-z0-9]+)*", source_id
        ):
            errors.append(f"{label}.id is invalid")
        elif source_id in source_ids:
            errors.append(f"{label}.id must be unique")
        source_ids.add(str(source_id))
        role = source["role"]
        if isinstance(role, str):
            roles.append(role)
        if not _is_choice(role, SOURCE_ROLES):
            errors.append(f"{label}.role is unsupported")
        if source["repository"] != EXPECTED_SOURCE_OWNERS.get(str(role)):
            errors.append(f"{label}.repository does not match its authority role")
        if not isinstance(source["revision"], str) or not FULL_SHA.fullmatch(
            source["revision"]
        ):
            errors.append(f"{label}.revision must be a full immutable commit SHA")
        if not isinstance(source["version"], str) or not source["version"]:
            errors.append(f"{label}.version must be non-empty")
        if not _is_choice(source["lifecycle"], {
            "draft",
            "proposed",
            "accepted",
            "stable",
            "deprecated",
        }):
            errors.append(f"{label}.lifecycle is unsupported")
        if not isinstance(source["release_included"], bool):
            errors.append(f"{label}.release_included must be boolean")
        elif source["release_included"] is not True:
            release_incomplete = True
        if source["release_included"] and source["lifecycle"] != "stable":
            errors.append(f"{label} cannot be release-included before stable")
        artifacts = source["artifacts"]
        if not isinstance(artifacts, list) or not artifacts:
            errors.append(f"{label}.artifacts must be non-empty")
            continue
        artifact_ids: set[str] = set()
        artifact_paths: set[str] = set()
        for artifact_index, artifact in enumerate(artifacts):
            artifact_label = f"{label}.artifacts[{artifact_index}]"
            if not exact_keys(
                artifact,
                {"id", "path", "sha256"},
                artifact_label,
                errors,
            ):
                continue
            artifact_id = artifact["id"]
            if not isinstance(artifact_id, str) or not re.fullmatch(
                r"[a-z0-9]+(?:-[a-z0-9]+)*",
                artifact_id,
            ):
                errors.append(f"{artifact_label}.id is invalid")
            elif artifact_id in artifact_ids:
                errors.append(f"{artifact_label}.id must be unique within its source")
            else:
                artifact_ids.add(artifact_id)
            artifact_path = artifact["path"]
            if isinstance(artifact_path, str) and artifact_path in artifact_paths:
                errors.append(f"{artifact_label}.path must be unique within its source")
            elif isinstance(artifact_path, str):
                artifact_paths.add(artifact_path)
            if not relative_path(artifact["path"]):
                errors.append(f"{artifact_label}.path must be repository-relative")
            if not isinstance(artifact["sha256"], str) or not SHA256.fullmatch(
                artifact["sha256"]
            ):
                errors.append(f"{artifact_label}.sha256 must be lowercase SHA-256")
    if set(roles) != SOURCE_ROLES or len(roles) != len(set(roles)):
        errors.append("profile.sources must contain each authority role exactly once")
    rollout_maximum = (
        rollout.get("maximum_mode_before_release")
        if isinstance(rollout, dict)
        else None
    )
    if release_incomplete and (
        profile["status"] != "proposed"
        or rollout_maximum != "advisory"
    ):
        errors.append("unreleased sources require proposed advisory-only status")

    capabilities = profile["capabilities"]
    if not isinstance(capabilities, list) or len(capabilities) != 3:
        errors.append("profile.capabilities must contain exactly three surfaces")
        capabilities = []
    capability_ids: list[str] = []
    for index, capability in enumerate(capabilities):
        label = f"profile.capabilities[{index}]"
        if not exact_keys(
            capability,
            {
                "id",
                "owner",
                "state",
                "policy_sources",
                "rule_families",
                "unavailable_behavior",
            },
            label,
            errors,
        ):
            continue
        capability_id = capability["id"]
        capability_ids.append(capability_id)
        if not _is_choice(capability_id, CAPABILITIES):
            errors.append(f"{label}.id is unsupported")
        expected_owner = (
            "egohygiene/relay"
            if capability_id == "diagram-sources"
            else "egohygiene/egolint"
        )
        if capability["owner"] != expected_owner:
            errors.append(f"{label}.owner violates the capability boundary")
        if not _is_choice(capability["state"], {"available", "planned", "deprecated"}):
            errors.append(f"{label}.state is unsupported")
        policy_sources = capability["policy_sources"]
        if (
            not isinstance(policy_sources, list)
            or not policy_sources
            or any(
                not isinstance(source, str) or source not in source_ids
                for source in policy_sources
            )
        ):
            errors.append(f"{label}.policy_sources must reference pinned source ids")
        rule_families = capability["rule_families"]
        if not isinstance(rule_families, list) or any(
            not isinstance(rule, str) or not RULE_FAMILY.fullmatch(rule)
            for rule in rule_families
        ):
            errors.append(f"{label}.rule_families are invalid")
        if capability_id == "diagram-sources":
            if capability["state"] != "planned" or rule_families:
                errors.append("diagram-source semantics must remain explicitly planned")
        elif capability["state"] != "available" or not rule_families:
            errors.append(f"{label} must expose available EgoLint rule families")
        if capability["unavailable_behavior"] != "incomplete":
            errors.append(f"{label}.unavailable_behavior must be incomplete")
    if capability_ids != [
        "repository-contracts",
        "architecture-records",
        "diagram-sources",
    ]:
        errors.append("profile capabilities must retain canonical order")

    interfaces = profile["interfaces"]
    if exact_keys(
        interfaces,
        {
            "request_contract",
            "result_contract",
            "validator_report_contract",
            "local_ci_result_parity",
            "coverage_surfaces",
        },
        "profile.interfaces",
        errors,
    ):
        if interfaces["request_contract"] != REQUEST_SCHEMA:
            errors.append("profile.interfaces.request_contract is unsupported")
        if interfaces["result_contract"] != RESULT_SCHEMA:
            errors.append("profile.interfaces.result_contract is unsupported")
        if (
            interfaces["validator_report_contract"]
            != "egolint.repository-intelligence-validation/v1"
        ):
            errors.append("profile must consume the EgoLint v1 validation contract")
        if interfaces["local_ci_result_parity"] is not True:
            errors.append("local and CI results must share one contract")
        if interfaces["coverage_surfaces"] != [
            "repository-contracts",
            "architecture-records",
            "diagram-sources",
        ]:
            errors.append("profile coverage surfaces must retain canonical order")

    execution = profile["execution"]
    if exact_keys(
        execution,
        {
            "default_network",
            "consumer_code_execution",
            "semantic_authoring",
            "implicit_writes",
            "forbidden_authority",
        },
        "profile.execution",
        errors,
    ):
        if execution["default_network"] != "denied-after-acquisition":
            errors.append("profile execution must be offline after acquisition")
        if execution["consumer_code_execution"] != "forbidden":
            errors.append("profile execution must forbid consumer code execution")
        if execution["semantic_authoring"] != "forbidden":
            errors.append("Relay must not author consumer semantic state")
        if execution["implicit_writes"] != "reports-and-temporary-workspace-only":
            errors.append("profile writes must be limited to reports and temporary work")
        forbidden = execution["forbidden_authority"]
        if (
            not isinstance(forbidden, list)
            or any(not isinstance(item, str) for item in forbidden)
            or set(forbidden) != FORBIDDEN_AUTHORITY
        ):
            errors.append("profile execution must prohibit the complete authority set")

    bounds = profile["bounds"]
    bound_keys = {
        "maximum_repository_contracts",
        "maximum_diagram_roots",
        "maximum_findings",
        "maximum_annotations",
        "maximum_scanned_files",
        "maximum_scanned_bytes",
        "maximum_result_bytes",
    }
    if exact_keys(bounds, bound_keys, "profile.bounds", errors):
        limits = {
            "maximum_repository_contracts": (1, 64),
            "maximum_diagram_roots": (1, 64),
            "maximum_findings": (1, 1000),
            "maximum_annotations": (1, 100),
            "maximum_scanned_files": (1, 100000),
            "maximum_scanned_bytes": (1, 1024 * 1024 * 1024),
            "maximum_result_bytes": (1024, 10 * 1024 * 1024),
        }
        for key, (minimum, maximum) in limits.items():
            value = bounds[key]
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or not minimum <= value <= maximum
            ):
                errors.append(f"profile.bounds.{key} is outside the safe range")
        if (
            isinstance(bounds.get("maximum_annotations"), int)
            and isinstance(bounds.get("maximum_findings"), int)
            and bounds["maximum_annotations"] > bounds["maximum_findings"]
        ):
            errors.append("profile annotation bound cannot exceed finding bound")

    safety = profile["information_safety"]
    if exact_keys(
        safety,
        {
            "minimum_necessary",
            "repository_paths",
            "private_output",
            "annotations",
            "untrusted_content",
            "excluded",
        },
        "profile.information_safety",
        errors,
    ):
        if safety["minimum_necessary"] is not True:
            errors.append("profile must require minimum-necessary evidence")
        if safety["repository_paths"] != "relative-only":
            errors.append("profile paths must remain repository-relative")
        if safety["private_output"] != "workflow-access-controlled-artifact":
            errors.append("private output must remain workflow-access-controlled")
        if safety["annotations"] != "bounded-diagnostics-only":
            errors.append("annotations must contain bounded diagnostics only")
        if safety["untrusted_content"] != "data-only-no-authority":
            errors.append("untrusted content must never grant authority")
        excluded = safety["excluded"]
        if (
            not isinstance(excluded, list)
            or any(not isinstance(item, str) for item in excluded)
            or set(excluded) != REQUIRED_EXCLUSIONS
        ):
            errors.append("profile must retain the complete information-safety exclusion set")

    ownership = profile["ownership"]
    expected_ownership = {
        "organization_policy": "egohygiene/hygiene",
        "validation_semantics": "egohygiene/egolint",
        "materialization": "egohygiene/holon",
        "local_records": "consumer-repository",
        "orchestration_and_evidence": "egohygiene/relay",
        "fleet_rollout": "egohygiene/pace",
        "aggregation": "egohygiene/observatory",
    }
    if exact_keys(ownership, set(expected_ownership), "profile.ownership", errors):
        if ownership != expected_ownership:
            errors.append("profile ownership map must retain sibling authority")
    return errors


def _validate_profile_reference(
    value: Any,
    label: str,
    errors: list[str],
) -> None:
    if not exact_keys(value, {"version", "sha256"}, label, errors):
        return
    if not isinstance(value["version"], str) or not value["version"]:
        errors.append(f"{label}.version must be non-empty")
    if not isinstance(value["sha256"], str) or not SHA256.fullmatch(value["sha256"]):
        errors.append(f"{label}.sha256 must be lowercase SHA-256")


def validate_request(
    request: dict[str, Any],
    profile: dict[str, Any] | None = None,
) -> list[str]:
    """Validate one closed future local or CI architecture request."""

    errors: list[str] = []
    if not exact_keys(
        request,
        {
            "schema_version",
            "profile",
            "repository",
            "mode",
            "adoption",
            "inputs",
            "bounds",
            "output",
        },
        "request",
        errors,
    ):
        return errors
    if request["schema_version"] != REQUEST_SCHEMA:
        errors.append("request.schema_version is unsupported")
    _validate_profile_reference(request["profile"], "request.profile", errors)
    active_profile = profile if profile is not None else load_object(PROFILE_PATH)
    if request["profile"] != _expected_profile_reference(active_profile):
        errors.append("request.profile must match the exact local profile bytes")

    repository = request["repository"]
    if exact_keys(
        repository,
        {"id", "visibility", "root", "represented_revision"},
        "request.repository",
        errors,
    ):
        if not isinstance(repository["id"], str) or not REPOSITORY_ID.fullmatch(
            repository["id"]
        ):
            errors.append("request.repository.id is invalid")
        if not _is_choice(repository["visibility"], {"public", "private", "internal"}):
            errors.append("request.repository.visibility is unsupported")
        if repository["root"] != ".":
            errors.append("request.repository.root must be the explicit current repository")
        revision = repository["represented_revision"]
        if not _is_choice(
            revision,
            {"working-tree", "unknown", "not-applicable"},
        ) and (
            not isinstance(revision, str) or not FULL_SHA.fullmatch(revision)
        ):
            errors.append("request.repository.represented_revision is invalid")

    if not _is_choice(request["mode"], MODES):
        errors.append("request.mode is unsupported")

    adoption = request["adoption"]
    if exact_keys(adoption, CAPABILITIES, "request.adoption", errors):
        for surface, state in adoption.items():
            if not _is_choice(state, ADOPTION_STATES):
                errors.append(f"request.adoption.{surface} is unsupported")

    inputs = request["inputs"]
    if exact_keys(
        inputs,
        {"repository_contracts", "repository_intelligence_policy", "diagram_roots"},
        "request.inputs",
        errors,
    ):
        contracts = inputs["repository_contracts"]
        if (
            not isinstance(contracts, list)
            or len(contracts) > 16
            or len(contracts) != len(set(map(str, contracts)))
            or any(not relative_path(path) for path in contracts)
        ):
            errors.append(
                "request.inputs.repository_contracts must contain at most 16 unique safe paths"
            )
        policy = inputs["repository_intelligence_policy"]
        if policy is not None and not relative_path(policy):
            errors.append(
                "request.inputs.repository_intelligence_policy must be null or a safe path"
            )
        diagram_roots = inputs["diagram_roots"]
        if (
            not isinstance(diagram_roots, list)
            or len(diagram_roots) > 16
            or len(diagram_roots) != len(set(map(str, diagram_roots)))
            or any(not relative_path(path) for path in diagram_roots)
        ):
            errors.append(
                "request.inputs.diagram_roots must contain at most 16 unique safe paths"
            )

        if isinstance(adoption, dict):
            contract_state = adoption.get("repository-contracts")
            if _is_choice(contract_state, {"present", "legacy"}) and not contracts:
                errors.append("present or legacy repository contracts require input paths")
            if _is_choice(contract_state, {"unknown", "not-applicable"}) and contracts:
                errors.append("unknown or not-applicable repository contracts cannot claim paths")
            architecture_state = adoption.get("architecture-records")
            if _is_choice(architecture_state, {"present", "legacy"}) and policy is None:
                errors.append("present or legacy architecture records require an EgoLint policy")
            if _is_choice(architecture_state, {"unknown", "not-applicable"}) and policy is not None:
                errors.append(
                    "unknown or not-applicable architecture records cannot claim a policy"
                )
            diagram_state = adoption.get("diagram-sources")
            if _is_choice(diagram_state, {"present", "legacy"}) and not diagram_roots:
                errors.append("present or legacy diagram sources require input roots")
            if _is_choice(diagram_state, {"unknown", "not-applicable"}) and diagram_roots:
                errors.append("unknown or not-applicable diagram sources cannot claim roots")

    bounds = request["bounds"]
    if exact_keys(
        bounds,
        {"maximum_findings", "maximum_scanned_files", "maximum_scanned_bytes"},
        "request.bounds",
        errors,
    ):
        safe_maximums = {
            "maximum_findings": 256,
            "maximum_scanned_files": 10000,
            "maximum_scanned_bytes": 100 * 1024 * 1024,
        }
        for key, maximum in safe_maximums.items():
            value = bounds[key]
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 1
                or value > maximum
            ):
                errors.append(f"request.bounds.{key} exceeds the profile ceiling")

    output = request["output"]
    if exact_keys(output, {"format", "path"}, "request.output", errors):
        if output["format"] != "json":
            errors.append("request.output.format must be json")
        if (
            not relative_path(output["path"])
            or not output["path"].startswith(".reports/architecture-validation/")
            or not output["path"].endswith(".json")
        ):
            errors.append(
                "request.output.path must be a safe JSON path under "
                ".reports/architecture-validation"
            )
    return errors


def _validate_result_status(
    result: dict[str, Any],
    coverage: dict[str, Any],
    errors: list[str],
) -> None:
    mode = result["mode"]
    status = result["semantic_status"]
    outcome = result["outcome"]
    if not _is_choice(mode, MODES):
        errors.append("result.mode is unsupported")
    if not _is_choice(status, SEMANTIC_STATUSES):
        errors.append("result.semantic_status is unsupported")
    if not _is_choice(outcome, OUTCOMES):
        errors.append("result.outcome is unsupported")
    if status == "conformant" and outcome != "passed":
        errors.append("conformant semantic status requires passed outcome")
    if status == "unavailable" and outcome != "unavailable":
        errors.append("unavailable semantic status requires unavailable outcome")
    if _is_choice(status, {"nonconformant", "legacy", "incomplete"}):
        expected = "warning" if mode == "advisory" else "failed"
        if outcome != expected:
            errors.append(f"{status} {mode} result must produce {expected}")
    if status == "not-applicable" and outcome != "passed":
        errors.append("not-applicable semantic status requires passed outcome")
    states = list(coverage.values()) if isinstance(coverage, dict) else []
    if status == "conformant" and any(
        not _is_choice(state, {"passed", "not-applicable"}) for state in states
    ):
        errors.append("conformant status cannot contain incomplete coverage")
    if status == "not-applicable" and any(state != "not-applicable" for state in states):
        errors.append("not-applicable status requires every surface to be not-applicable")
    if status == "unavailable" and "unavailable" not in states:
        errors.append("unavailable status requires unavailable coverage")


def validate_result(
    result: dict[str, Any],
    profile: dict[str, Any] | None = None,
) -> list[str]:
    """Validate one normalized result and its privacy and outcome invariants."""

    errors: list[str] = []
    if not exact_keys(
        result,
        {
            "schema_version",
            "profile",
            "repository",
            "mode",
            "semantic_status",
            "outcome",
            "coverage",
            "provenance",
            "findings",
            "counts",
            "bounds",
            "artifacts",
            "privacy",
        },
        "result",
        errors,
    ):
        return errors
    if result["schema_version"] != RESULT_SCHEMA:
        errors.append("result.schema_version is unsupported")
    _validate_profile_reference(result["profile"], "result.profile", errors)
    active_profile = profile if profile is not None else load_object(PROFILE_PATH)
    if result["profile"] != _expected_profile_reference(active_profile):
        errors.append("result.profile must match the exact local profile bytes")

    repository = result["repository"]
    if exact_keys(
        repository,
        {"id", "visibility", "represented_revision"},
        "result.repository",
        errors,
    ):
        if not isinstance(repository["id"], str) or not REPOSITORY_ID.fullmatch(
            repository["id"]
        ):
            errors.append("result.repository.id is invalid")
        if not _is_choice(repository["visibility"], {"public", "private", "internal"}):
            errors.append("result.repository.visibility is unsupported")
        revision = repository["represented_revision"]
        if not _is_choice(
            revision,
            {"working-tree", "unknown", "not-applicable"},
        ) and (
            not isinstance(revision, str) or not FULL_SHA.fullmatch(revision)
        ):
            errors.append("result.repository.represented_revision is invalid")

    coverage = result["coverage"]
    if exact_keys(coverage, CAPABILITIES, "result.coverage", errors):
        for surface, state in coverage.items():
            if not _is_choice(state, COVERAGE_STATES):
                errors.append(f"result.coverage.{surface} is unsupported")
    _validate_result_status(result, coverage, errors)

    provenance = result["provenance"]
    if not isinstance(provenance, list) or len(provenance) != 3:
        errors.append("result.provenance must contain exactly three source pins")
        provenance = []
    repositories: set[str] = set()
    source_ids: set[str] = set()
    for index, item in enumerate(provenance):
        label = f"result.provenance[{index}]"
        if not exact_keys(
            item,
            {"repository", "revision", "profile_source_id"},
            label,
            errors,
        ):
            continue
        if not isinstance(item["repository"], str) or not REPOSITORY_ID.fullmatch(
            item["repository"]
        ):
            errors.append(f"{label}.repository is invalid")
        if isinstance(item["repository"], str) and item["repository"] in repositories:
            errors.append(f"{label}.repository must be unique")
        elif isinstance(item["repository"], str):
            repositories.add(item["repository"])
        if not isinstance(item["revision"], str) or not FULL_SHA.fullmatch(
            item["revision"]
        ):
            errors.append(f"{label}.revision must be a full SHA")
        source_id = item["profile_source_id"]
        if not isinstance(source_id, str) or not re.fullmatch(
            r"[a-z0-9]+(?:-[a-z0-9]+)*",
            source_id,
        ):
            errors.append(f"{label}.profile_source_id is invalid")
        elif source_id in source_ids:
            errors.append(f"{label}.profile_source_id must be unique")
        else:
            source_ids.add(source_id)
    expected_provenance = {
        (
            source["id"],
            source["repository"],
            source["revision"],
        )
        for source in active_profile.get("sources", [])
        if isinstance(source, dict)
        and all(key in source for key in ("id", "repository", "revision"))
        and all(
            isinstance(source[key], str)
            for key in ("id", "repository", "revision")
        )
    }
    actual_provenance = {
        (
            item.get("profile_source_id"),
            item.get("repository"),
            item.get("revision"),
        )
        for item in provenance
        if isinstance(item, dict)
        and all(
            isinstance(item.get(key), str)
            for key in ("profile_source_id", "repository", "revision")
        )
    }
    if actual_provenance != expected_provenance:
        errors.append("result.provenance must exactly match the pinned profile sources")

    findings = result["findings"]
    if not isinstance(findings, list) or len(findings) > 256:
        errors.append("result.findings must contain at most 256 items")
        findings = []
    severity_counts = {severity: 0 for severity in sorted(SEVERITIES)}
    for index, finding in enumerate(findings):
        label = f"result.findings[{index}]"
        if not exact_keys(
            finding,
            {"id", "severity", "source", "path", "line", "summary", "remediation"},
            label,
            errors,
        ):
            continue
        if not isinstance(finding["id"], str) or not RULE_ID.fullmatch(finding["id"]):
            errors.append(f"{label}.id is invalid")
        if not _is_choice(finding["severity"], SEVERITIES):
            errors.append(f"{label}.severity is unsupported")
        else:
            severity_counts[finding["severity"]] += 1
        if not _is_choice(finding["source"], FINDING_SOURCES):
            errors.append(f"{label}.source is unsupported")
        if finding["path"] is not None and not relative_path(finding["path"]):
            errors.append(f"{label}.path must be null or repository-relative")
        if finding["line"] is not None and (
            not isinstance(finding["line"], int)
            or isinstance(finding["line"], bool)
            or finding["line"] < 1
        ):
            errors.append(f"{label}.line must be null or a positive integer")
        _bounded_text(finding["summary"], 512, f"{label}.summary", errors)
        _bounded_text(finding["remediation"], 1024, f"{label}.remediation", errors)

    counts = result["counts"]
    if exact_keys(
        counts,
        {"info", "warning", "error", "critical", "total"},
        "result.counts",
        errors,
    ):
        expected_counts = {
            "info": severity_counts["info"],
            "warning": severity_counts["warning"],
            "error": severity_counts["error"],
            "critical": severity_counts["critical"],
            "total": len(findings),
        }
        if counts != expected_counts:
            errors.append("result.counts must exactly match retained findings")

    bounds = result["bounds"]
    bound_keys = {
        "maximum_findings",
        "observed_findings",
        "findings_truncated",
        "maximum_scanned_files",
        "observed_scanned_files",
        "maximum_scanned_bytes",
        "observed_scanned_bytes",
        "scan_truncated",
    }
    if exact_keys(bounds, bound_keys, "result.bounds", errors):
        maximum_findings = bounds["maximum_findings"]
        observed_findings = bounds["observed_findings"]
        if (
            not isinstance(maximum_findings, int)
            or isinstance(maximum_findings, bool)
            or not 1 <= maximum_findings <= 256
        ):
            errors.append("result.bounds.maximum_findings is invalid")
        if (
            not isinstance(observed_findings, int)
            or isinstance(observed_findings, bool)
            or observed_findings < len(findings)
        ):
            errors.append("result.bounds.observed_findings cannot be below retained findings")
        if not isinstance(bounds["findings_truncated"], bool):
            errors.append("result.bounds.findings_truncated must be boolean")
        elif isinstance(observed_findings, int) and not isinstance(
            observed_findings,
            bool,
        ) and bounds["findings_truncated"] != (observed_findings > len(findings)):
            errors.append("result finding truncation must match observed and retained counts")
        for observed_key, maximum_key, ceiling in (
            ("observed_scanned_files", "maximum_scanned_files", 10000),
            ("observed_scanned_bytes", "maximum_scanned_bytes", 100 * 1024 * 1024),
        ):
            maximum = bounds[maximum_key]
            observed = bounds[observed_key]
            if (
                not isinstance(maximum, int)
                or isinstance(maximum, bool)
                or not 1 <= maximum <= ceiling
            ):
                errors.append(f"result.bounds.{maximum_key} is invalid")
            if (
                not isinstance(observed, int)
                or isinstance(observed, bool)
                or observed < 0
            ):
                errors.append(f"result.bounds.{observed_key} is invalid")
        if not isinstance(bounds["scan_truncated"], bool):
            errors.append("result.bounds.scan_truncated must be boolean")
        elif not bounds["scan_truncated"]:
            file_values = (
                bounds["observed_scanned_files"],
                bounds["maximum_scanned_files"],
            )
            byte_values = (
                bounds["observed_scanned_bytes"],
                bounds["maximum_scanned_bytes"],
            )
            numeric_bounds = all(
                isinstance(value, int) and not isinstance(value, bool)
                for value in (*file_values, *byte_values)
            )
            if numeric_bounds and (
                file_values[0] > file_values[1]
                or byte_values[0] > byte_values[1]
            ):
                errors.append("untruncated scan cannot exceed its requested bounds")

    artifacts = result["artifacts"]
    if exact_keys(
        artifacts,
        {"egolint_run", "egolint_sarif", "repository_intelligence", "diagram_evidence"},
        "result.artifacts",
        errors,
    ):
        for key, path in artifacts.items():
            if path is not None and (
                not relative_path(path)
                or not path.startswith((".reports/egolint/", ".reports/architecture-validation/"))
            ):
                errors.append(f"result.artifacts.{key} must be null or a safe report path")

    privacy = result["privacy"]
    if exact_keys(
        privacy,
        {"classification", "contains_source_content", "path_policy", "redaction"},
        "result.privacy",
        errors,
    ):
        visibility = repository.get("visibility") if isinstance(repository, dict) else None
        expected_classification = f"{visibility}-repository"
        if privacy["classification"] != expected_classification:
            errors.append("result privacy classification must match repository visibility")
        if privacy["contains_source_content"] is not False:
            errors.append("result must not contain consumer source content")
        if privacy["path_policy"] != "repository-relative-only":
            errors.append("result path policy must remain repository-relative")
        if privacy["redaction"] != "bounded-diagnostics-only":
            errors.append("result redaction must retain bounded diagnostics only")
    return errors


def verify_sources(profile: dict[str, Any], roots: dict[str, Path]) -> list[str]:
    """Verify every pinned artifact byte against explicit local checkouts."""

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
                f"{repository} revision mismatch: expected {source['revision']}, "
                f"got {actual_revision}"
            )
            continue
        for artifact in source["artifacts"]:
            path = root / artifact["path"]
            if not path.is_file() or path.is_symlink():
                errors.append(
                    f"{repository} artifact is missing or not a regular file: "
                    f"{artifact['path']}"
                )
                continue
            actual_digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual_digest != artifact["sha256"]:
                errors.append(
                    f"{repository} artifact digest mismatch for {artifact['path']}: "
                    f"expected {artifact['sha256']}, got {actual_digest}"
                )
    return errors


def _git_revision(root: Path) -> str:
    """Resolve HEAD from a local checkout without invoking Git or the network."""

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
        ref_name = value.removeprefix("ref: ")
        reference = git_directory / ref_name
        if reference.is_file():
            value = reference.read_text(encoding="utf-8").strip()
        else:
            packed = git_directory / "packed-refs"
            if packed.is_file():
                matches = [
                    line.split(" ", maxsplit=1)[0]
                    for line in packed.read_text(encoding="utf-8").splitlines()
                    if line.endswith(f" {ref_name}")
                ]
                value = matches[0] if matches else ""
    if not FULL_SHA.fullmatch(value):
        raise ValueError(f"source checkout HEAD is not a full commit SHA: {root}")
    return value


def validate_fixtures(fixtures: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    """Validate the checked-in publish-safe request and result corpus."""

    errors: list[str] = []
    if not exact_keys(
        fixtures,
        {"schema_version", "profile_sha256", "requests", "results"},
        "fixtures",
        errors,
    ):
        return errors
    if fixtures["schema_version"] != "relay.repository-architecture-validation-fixtures/v1":
        errors.append("fixtures.schema_version is unsupported")
    profile_digest = hashlib.sha256(PROFILE_PATH.read_bytes()).hexdigest()
    if fixtures["profile_sha256"] != profile_digest:
        errors.append("fixtures.profile_sha256 does not match the profile bytes")
    expected_reference = {
        "version": profile["version"],
        "sha256": profile_digest,
    }
    requests = fixtures["requests"]
    if not isinstance(requests, dict) or not requests:
        errors.append("fixtures.requests must be a non-empty object")
    else:
        for fixture_id, request in sorted(requests.items()):
            for error in validate_request(request, profile):
                errors.append(f"fixture request {fixture_id}: {error}")
            if isinstance(request, dict) and request.get("profile") != expected_reference:
                errors.append(f"fixture request {fixture_id}: profile reference drifted")
    results = fixtures["results"]
    if not isinstance(results, dict) or not results:
        errors.append("fixtures.results must be a non-empty object")
    else:
        for fixture_id, result in sorted(results.items()):
            for error in validate_result(result, profile):
                errors.append(f"fixture result {fixture_id}: {error}")
            if isinstance(result, dict) and result.get("profile") != expected_reference:
                errors.append(f"fixture result {fixture_id}: profile reference drifted")
    return errors


def print_errors(errors: Iterable[str]) -> int:
    """Print deterministic diagnostics and return a conventional status code."""

    ordered = sorted(set(errors))
    if not ordered:
        print("PASS repository architecture validation contract")
        return 0
    for error in ordered:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    """Build the long-form-only command-line interface."""

    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "validate",
        help="validate the Relay-owned profile, fixtures, and schemas",
        allow_abbrev=False,
    )
    verify = subparsers.add_parser(
        "verify-sources",
        help="verify pinned bytes in explicit local source checkouts",
        allow_abbrev=False,
    )
    verify.add_argument("--hygiene-source", required=True, type=Path)
    verify.add_argument("--egolint-source", required=True, type=Path)
    verify.add_argument("--holon-source", required=True, type=Path)
    return parser


def main(arguments: list[str] | None = None) -> int:
    """Validate the local contract or explicitly supplied source bytes."""

    namespace = build_parser().parse_args(arguments)
    profile = load_object(PROFILE_PATH)
    errors = validate_profile(profile)
    schema_paths = sorted(
        SCHEMA_DIRECTORY.glob("repository-architecture-validation-*.schema.json")
    )
    if len(schema_paths) != 3:
        errors.append("exactly three repository architecture schemas are required")
    for schema_path in schema_paths:
        schema = load_object(schema_path)
        if schema.get("additionalProperties") is not False:
            errors.append(
                f"schema root must be closed: {schema_path.relative_to(REPOSITORY_ROOT)}"
            )
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append(
                f"schema must use JSON Schema 2020-12: "
                f"{schema_path.relative_to(REPOSITORY_ROOT)}"
            )
    if FIXTURES_PATH.is_file():
        errors.extend(validate_fixtures(load_object(FIXTURES_PATH), profile))
    else:
        errors.append("repository architecture fixture corpus is missing")
    if namespace.command == "verify-sources" and not errors:
        errors.extend(
            verify_sources(
                profile,
                {
                    "egohygiene/hygiene": namespace.hygiene_source,
                    "egohygiene/egolint": namespace.egolint_source,
                    "egohygiene/holon": namespace.holon_source,
                },
            )
        )
    return print_errors(errors)


if __name__ == "__main__":
    raise SystemExit(main())
