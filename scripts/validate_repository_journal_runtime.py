# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Validate the repository-journal runtime and inspect safe connection state."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Mapping, Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = REPOSITORY_ROOT / "catalog/repository-journal-runtime.json"
AETHER_PROFILE_PATH = REPOSITORY_ROOT / "catalog/repository-journal-aether.json"
PROFILE_SCHEMA = "relay.repository-journal-runtime-profile/v1"
AETHER_PROFILE_SCHEMA = "relay.repository-journal-aether-profile/v1"
RESULT_SCHEMA = "relay.repository-journal-runtime-preflight-result/v1"
AUTH_MODES = {"github-token", "fine-grained-pat"}
POLICY_STATES = {"enabled", "disabled", "unknown", "not-applicable"}
PERMISSION_STATES = {"granted", "missing", "unknown"}
CHECK_STATES = {"pass", "fail", "not-applicable"}
SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SRI_SHA512 = re.compile(r"^sha512-[A-Za-z0-9+/]+={0,2}$")
VERSION_IN_TEXT = re.compile(r"(?<![0-9])([0-9]+\.[0-9]+\.[0-9]+)(?![0-9])")
FAILURE_REASONS = {
    "cli-unavailable",
    "cli-version-mismatch",
    "credential-missing",
    "credential-type-unsupported",
    "credential-precedence-conflict",
    "organization-policy-disabled",
    "organization-policy-unverified",
    "permission-missing",
    "permission-unverified",
    "billing-unacknowledged",
    "authentication-rejected",
    "rate-limited",
}
PREFLIGHT_FAILURE_REASONS = FAILURE_REASONS - {
    "authentication-rejected",
    "rate-limited",
}
REQUIRED_CONNECTION_CHECKS = {
    "organization-policy-enabled",
    "workflow-permission-granted",
    "billing-principal-acknowledged",
    "exact-cli-version-observed",
    "approved-credential-present",
    "conflicting-credentials-absent",
}
SECRET_ENVIRONMENT_VARIABLES = {
    "COPILOT_GITHUB_TOKEN",
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "COPILOT_PROVIDER_API_KEY",
}
AETHER_REVISION = "aa0cb090a7ca4a47f22268784af0ce34aaf69b48"
AETHER_TREE = "f123061d1eb494a70feff8bab49261b2066dc2f4"
AETHER_FILES = {
    "schema": (
        "catalog/schemas/aether.repository-journal.v1.schema.json",
        "vendor/aether/catalog/schemas/aether.repository-journal.v1.schema.json",
        "8788ec86d062baf73d6320f080643396abc5d4dadd69996b88b6493b6d2c654e",
        1518,
    ),
    "distribution-metadata": (
        "dist/skills/create-repository-journal/distribution-manifest.v1.json",
        "vendor/aether/distribution-manifest.v1.json",
        "ecf0dcebb6fadba38273c1883ae8366b35b0f87c2531d198d21f06447367c53d",
        1045,
    ),
    "skill-metadata": (
        "library/organization/skills/quality/create-repository-journal/SKILL.md",
        "vendor/aether/library/organization/skills/quality/"
        "create-repository-journal/SKILL.md",
        "20478640d878d5d9b4d06e934f6a72f825e7292bec9acfc78c909e4f8f4702c7",
        1961,
    ),
    "report-contract": (
        "library/organization/skills/quality/create-repository-journal/"
        "references/report-contract.md",
        "vendor/aether/library/organization/skills/quality/"
        "create-repository-journal/references/report-contract.md",
        "a29016e80a49c80e26ce263905e5e41492df16f27a903c5996965d023d3d9786",
        401,
    ),
    "renderer": (
        "library/organization/skills/quality/create-repository-journal/"
        "scripts/repository-journal.py",
        "vendor/aether/library/organization/skills/quality/"
        "create-repository-journal/scripts/repository-journal.py",
        "be5652953a0cbaa038e5c98cf2b093b100153ffcd85d69068cff8affae5adee3",
        4771,
    ),
    "input-template": (
        "library/organization/skills/quality/create-repository-journal/"
        "templates/repository-journal-input.template.json",
        "vendor/aether/library/organization/skills/quality/"
        "create-repository-journal/templates/repository-journal-input.template.json",
        "2b617aec8b572bf6924d9d08162eaeffc06b70f6404bbacc01b79533a75ca074",
        239,
    ),
    "specification": (
        "library/organization/specs/quality/repository-journal.spec.md",
        "vendor/aether/library/organization/specs/quality/"
        "repository-journal.spec.md",
        "330ffbc376821cff40c95ff25c8f53538a61846ced2f86d35acb6b8b10c7251b",
        2291,
    ),
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


def file_sha256(path: Path) -> str:
    """Return the lowercase SHA-256 digest for one local file."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_relative_path(value: Any) -> bool:
    """Return whether a value is a traversal-safe repository-relative path."""

    if not isinstance(value, str) or not value or value.startswith("/"):
        return False
    return ".." not in Path(value).parts


def validate_profile(profile: dict[str, Any]) -> list[str]:
    """Validate the closed runtime, authentication, cost, and failure contract."""

    errors: list[str] = []
    if not exact_keys(
        profile,
        {
            "$schema",
            "schema_version",
            "version",
            "status",
            "owner",
            "updated",
            "purpose",
            "toolchain",
            "authentication",
            "execution",
            "cost",
            "failure",
            "connection",
            "references",
        },
        "profile",
        errors,
    ):
        return errors
    if profile["$schema"] != "../schemas/repository-journal-runtime-profile.v1.schema.json":
        errors.append("profile.$schema is unsupported")
    if profile["schema_version"] != PROFILE_SCHEMA:
        errors.append("profile.schema_version is unsupported")
    if profile["status"] != "proposed":
        errors.append("profile must remain proposed until live connection evidence exists")
    if profile["owner"] != "egohygiene/relay":
        errors.append("profile.owner must be egohygiene/relay")

    toolchain = profile["toolchain"]
    if exact_keys(toolchain, {"node", "package", "lock"}, "profile.toolchain", errors):
        node = toolchain["node"]
        if exact_keys(
            node,
            {"minimum_major", "selected_major"},
            "profile.toolchain.node",
            errors,
        ):
            if node["minimum_major"] != 22:
                errors.append(
                    "profile.toolchain.node.minimum_major must match GitHub's "
                    "supported minimum"
                )
            if node["selected_major"] != 24:
                errors.append("profile.toolchain.node.selected_major must remain explicitly pinned")

        package = toolchain["package"]
        if exact_keys(
            package,
            {"name", "version", "integrity", "license", "repository"},
            "profile.toolchain.package",
            errors,
        ):
            if package["name"] != "@github/copilot":
                errors.append("profile tool package must be @github/copilot")
            if not isinstance(package["version"], str) or not SEMVER.fullmatch(
                package["version"]
            ):
                errors.append("profile tool package version must be exact SemVer")
            if not isinstance(package["integrity"], str) or not SRI_SHA512.fullmatch(
                package["integrity"]
            ):
                errors.append("profile tool package integrity must be SHA-512 SRI")
            if package["repository"] != "https://github.com/github/copilot-cli":
                errors.append("profile tool repository must be GitHub's Copilot CLI repository")

        lock = toolchain["lock"]
        if exact_keys(
            lock,
            {
                "manifest_path",
                "manifest_sha256",
                "lock_path",
                "lock_sha256",
                "install_command",
            },
            "profile.toolchain.lock",
            errors,
        ):
            for field in ("manifest_path", "lock_path"):
                if not safe_relative_path(lock[field]):
                    errors.append(f"profile.toolchain.lock.{field} must be repository-relative")
            for field in ("manifest_sha256", "lock_sha256"):
                if not isinstance(lock[field], str) or not SHA256.fullmatch(lock[field]):
                    errors.append(f"profile.toolchain.lock.{field} must be lowercase SHA-256")
            if lock["install_command"] != [
                "npm",
                "ci",
                "--ignore-scripts",
                "--no-audit",
                "--no-fund",
            ]:
                errors.append("profile install command must use the locked non-scripted npm path")

    authentication = profile["authentication"]
    if exact_keys(
        authentication,
        {
            "preferred",
            "fallback",
            "credential_precedence",
            "unexpected_credential_behavior",
        },
        "profile.authentication",
        errors,
    ):
        preferred = authentication["preferred"]
        if exact_keys(
            preferred,
            {
                "mode",
                "credential_environment",
                "required_workflow_permissions",
                "organization_policy",
                "billing_principal",
                "long_lived_secret",
            },
            "profile.authentication.preferred",
            errors,
        ):
            if preferred != {
                "mode": "github-token",
                "credential_environment": "GITHUB_TOKEN",
                "required_workflow_permissions": {
                    "contents": "read",
                    "copilot-requests": "write",
                },
                "organization_policy": "allow-copilot-cli-billed-to-organization",
                "billing_principal": "organization",
                "long_lived_secret": False,
            }:
                errors.append(
                    "profile preferred authentication must use the least-privilege "
                    "GitHub token contract"
                )

        fallback = authentication["fallback"]
        if exact_keys(
            fallback,
            {
                "mode",
                "workflow_secret",
                "credential_environment",
                "required_account_permission",
                "required_token_prefix",
                "repository_access",
                "billing_principal",
                "automatic",
                "classic_pat_allowed",
            },
            "profile.authentication.fallback",
            errors,
        ):
            if fallback != {
                "mode": "fine-grained-pat",
                "workflow_secret": "REPOSITORY_JOURNAL_COPILOT_TOKEN",
                "credential_environment": "COPILOT_GITHUB_TOKEN",
                "required_account_permission": "Copilot Requests",
                "required_token_prefix": "github_pat_",
                "repository_access": "selected-repositories",
                "billing_principal": "token-owner",
                "automatic": False,
                "classic_pat_allowed": False,
            }:
                errors.append(
                    "profile fallback must remain explicit, fine-grained, and "
                    "non-automatic"
                )
        if authentication["credential_precedence"] != [
            "COPILOT_GITHUB_TOKEN",
            "GH_TOKEN",
            "GITHUB_TOKEN",
        ]:
            errors.append("profile credential precedence must match Copilot CLI")
        if authentication["unexpected_credential_behavior"] != "fail-closed":
            errors.append("profile must fail closed on unexpected credentials")

    execution = profile["execution"]
    if exact_keys(
        execution,
        {
            "mode",
            "interactive_authentication",
            "credential_persistence",
            "repository_checkout",
            "consumer_code_execution",
            "tool_authority",
            "maximum_agent_invocations_per_run",
            "maximum_attempts_per_invocation",
            "timeout_minutes",
        },
        "profile.execution",
        errors,
    ):
        expected_execution = {
            "mode": "programmatic",
            "interactive_authentication": "forbidden",
            "credential_persistence": "forbidden",
            "repository_checkout": "forbidden",
            "consumer_code_execution": "forbidden",
            "tool_authority": "deny-by-default",
            "maximum_agent_invocations_per_run": 1,
            "maximum_attempts_per_invocation": 1,
            "timeout_minutes": 5,
        }
        if execution != expected_execution:
            errors.append("profile execution must retain the bounded non-interactive contract")

    cost = profile["cost"]
    if exact_keys(
        cost,
        {
            "preferred_billing",
            "fallback_billing",
            "automatic_fallback",
            "maximum_scheduled_runs_per_day",
            "usage_observation",
        },
        "profile.cost",
        errors,
    ):
        if cost != {
            "preferred_billing": "organization-metered",
            "fallback_billing": "token-owner-seat",
            "automatic_fallback": False,
            "maximum_scheduled_runs_per_day": 1,
            "usage_observation": "github-organization-billing-and-usage",
        }:
            errors.append("profile cost controls must remain explicit and bounded")

    failure = profile["failure"]
    if exact_keys(
        failure,
        {"default_outcome", "preflight_authorizes_journal", "fail_closed_on", "secret_output"},
        "profile.failure",
        errors,
    ):
        if failure["default_outcome"] != "unavailable":
            errors.append("profile failure default must be unavailable")
        if failure["preflight_authorizes_journal"] is not False:
            errors.append("runtime preflight cannot authorize a successful journal")
        fail_closed_on = failure["fail_closed_on"]
        if (
            not isinstance(fail_closed_on, list)
            or any(not isinstance(reason, str) for reason in fail_closed_on)
            or set(fail_closed_on) != FAILURE_REASONS
        ):
            errors.append("profile failure reasons must retain the complete closed set")
        if failure["secret_output"] != "forbidden":
            errors.append("profile must forbid secret output")

    connection = profile["connection"]
    if exact_keys(
        connection,
        {"status", "live_probe", "required_checks"},
        "profile.connection",
        errors,
    ):
        if connection["status"] != "manual-verification-required":
            errors.append("profile connection must remain manually unverified")
        if connection["live_probe"] != "deferred-until-user-authorized":
            errors.append("profile live probe must remain separately authorized")
        required_checks = connection["required_checks"]
        if (
            not isinstance(required_checks, list)
            or any(not isinstance(check, str) for check in required_checks)
            or set(required_checks) != REQUIRED_CONNECTION_CHECKS
        ):
            errors.append("profile connection must retain every required check")

    references = profile["references"]
    if not isinstance(references, list) or len(references) < 3:
        errors.append("profile references must include the primary GitHub documentation")
    elif any(
        not isinstance(reference, str)
        or not reference.startswith("https://docs.github.com/")
        for reference in references
    ):
        errors.append("profile references must use official GitHub documentation")
    return errors


def validate_locked_toolchain(
    profile: dict[str, Any],
    repository_root: Path = REPOSITORY_ROOT,
) -> list[str]:
    """Verify the selected npm package and every recorded local lock digest."""

    errors: list[str] = []
    toolchain = profile.get("toolchain", {})
    lock = toolchain.get("lock", {}) if isinstance(toolchain, dict) else {}
    package = toolchain.get("package", {}) if isinstance(toolchain, dict) else {}
    if not isinstance(lock, dict) or not isinstance(package, dict):
        return ["profile toolchain is unavailable for lock validation"]

    resolved: dict[str, Path] = {}
    for kind, path_field, digest_field in (
        ("manifest", "manifest_path", "manifest_sha256"),
        ("lock", "lock_path", "lock_sha256"),
    ):
        relative = lock.get(path_field)
        expected_digest = lock.get(digest_field)
        if not safe_relative_path(relative):
            errors.append(f"toolchain {kind} path is unsafe")
            continue
        path = repository_root / relative
        resolved[kind] = path
        if not path.is_file():
            errors.append(f"toolchain {kind} file is missing: {relative}")
            continue
        if file_sha256(path) != expected_digest:
            errors.append(f"toolchain {kind} digest mismatch: {relative}")
    if errors:
        return errors

    manifest = load_object(resolved["manifest"])
    lockfile = load_object(resolved["lock"])
    package_name = package.get("name")
    package_version = package.get("version")
    package_integrity = package.get("integrity")
    if manifest.get("dependencies") != {package_name: package_version}:
        errors.append("toolchain manifest must contain one exact Copilot CLI dependency")
    if lockfile.get("lockfileVersion") != 3:
        errors.append("toolchain npm lockfile must use lockfileVersion 3")
    packages = lockfile.get("packages")
    if not isinstance(packages, dict):
        return errors + ["toolchain npm lockfile packages must be an object"]
    root = packages.get("")
    if not isinstance(root, dict) or root.get("dependencies") != {package_name: package_version}:
        errors.append("toolchain lock root must retain the exact Copilot CLI dependency")
    locked = packages.get(f"node_modules/{package_name}")
    if not isinstance(locked, dict):
        errors.append("toolchain lock is missing the Copilot CLI package")
    else:
        if locked.get("version") != package_version:
            errors.append("toolchain lock Copilot CLI version mismatch")
        if locked.get("integrity") != package_integrity:
            errors.append("toolchain lock Copilot CLI integrity mismatch")
        if locked.get("hasInstallScript") is True:
            errors.append("toolchain lock must not require a Copilot CLI install script")
    for path, record in packages.items():
        if path == "" or not isinstance(record, dict):
            continue
        resolved_url = record.get("resolved")
        integrity = record.get("integrity")
        if not isinstance(resolved_url, str) or not resolved_url.startswith(
            "https://registry.npmjs.org/"
        ):
            errors.append(f"toolchain package has unsupported registry source: {path}")
        if not isinstance(integrity, str) or not SRI_SHA512.fullmatch(integrity):
            errors.append(f"toolchain package lacks SHA-512 integrity: {path}")
        if (
            path.startswith("node_modules/@github/copilot-")
            and record.get("version") != package_version
        ):
            errors.append(f"toolchain platform package version mismatch: {path}")
    return errors


def validate_aether_profile(
    profile: dict[str, Any],
    repository_root: Path = REPOSITORY_ROOT,
) -> list[str]:
    """Verify the immutable Aether journal contract and every vendored byte."""

    errors: list[str] = []
    if not exact_keys(
        profile,
        {
            "$schema",
            "schema_version",
            "version",
            "status",
            "owner",
            "updated",
            "source",
            "contract",
            "distribution",
            "files",
            "execution",
        },
        "Aether profile",
        errors,
    ):
        return errors
    expected_header = {
        "$schema": "../schemas/repository-journal-aether-profile.v1.schema.json",
        "schema_version": AETHER_PROFILE_SCHEMA,
        "version": "1.0.0-alpha.1",
        "status": "proposed",
        "owner": "egohygiene/relay",
        "updated": "2026-09-20",
    }
    for field, expected in expected_header.items():
        if profile[field] != expected:
            errors.append(f"Aether profile {field} is unsupported")

    if profile["source"] != {
        "repository": "egohygiene/aether",
        "revision": AETHER_REVISION,
        "tree": AETHER_TREE,
        "pull_request": "https://github.com/egohygiene/aether/pull/59",
    }:
        errors.append("Aether profile source must remain pinned to merged PR #59")
    if profile["contract"] != {
        "id": "repository-journal",
        "version": "1.0.0",
        "lifecycle": "draft",
        "schema_id": "https://egohygiene.io/schemas/aether/repository-journal/v1.json",
        "spec_digest": {
            "algorithm": "sha256-utf8-lf",
            "value": AETHER_FILES["specification"][2],
        },
    }:
        errors.append("Aether journal contract identity or maturity drifted")
    if profile["distribution"] != {
        "id": "distribution/create-repository-journal",
        "artifact_id": "skill/create-repository-journal",
        "version": "1.0.0",
        "source_digest": {
            "algorithm": "sha256-utf8-lf",
            "value": AETHER_FILES["skill-metadata"][2],
        },
    }:
        errors.append("Aether journal distribution identity drifted")
    if profile["execution"] != {
        "renderer": AETHER_FILES["renderer"][1],
        "network": "forbidden",
        "upstream_maturity_behavior": "observe-with-explicit-draft-provenance",
    }:
        errors.append("Aether journal execution boundary drifted")

    records = profile["files"]
    if not isinstance(records, list):
        return [*errors, "Aether profile files must be an array"]
    observed: dict[str, tuple[Any, Any, Any, Any]] = {}
    for index, record in enumerate(records):
        label = f"Aether profile files[{index}]"
        if not exact_keys(
            record,
            {"role", "upstream_path", "vendor_path", "sha256", "bytes"},
            label,
            errors,
        ):
            continue
        role = record["role"]
        if not isinstance(role, str) or role not in AETHER_FILES:
            errors.append(f"{label}.role is unsupported")
            continue
        if role in observed:
            errors.append(f"Aether profile contains duplicate role {role}")
            continue
        observed[role] = (
            record["upstream_path"],
            record["vendor_path"],
            record["sha256"],
            record["bytes"],
        )
    if observed != AETHER_FILES:
        errors.append("Aether profile file inventory does not match the pinned distribution")

    for role, (_, vendor_path, expected_sha, expected_bytes) in AETHER_FILES.items():
        if not safe_relative_path(vendor_path) or not vendor_path.startswith(
            "vendor/aether/"
        ):
            errors.append(f"Aether {role} vendor path is unsafe")
            continue
        path = repository_root / vendor_path
        if not path.is_file():
            errors.append(f"Aether {role} is missing: {vendor_path}")
            continue
        content = path.read_bytes()
        if len(content) != expected_bytes:
            errors.append(f"Aether {role} byte count mismatch")
        if hashlib.sha256(content).hexdigest() != expected_sha:
            errors.append(f"Aether {role} checksum mismatch")

    manifest_path = repository_root / AETHER_FILES["distribution-metadata"][1]
    schema_path = repository_root / AETHER_FILES["schema"][1]
    if manifest_path.is_file():
        manifest = load_object(manifest_path)
        if manifest.get("distribution_id") != profile["distribution"]["id"]:
            errors.append("Aether distribution manifest ID mismatch")
        if manifest.get("artifact_version") != profile["distribution"]["version"]:
            errors.append("Aether distribution manifest version mismatch")
        if manifest.get("source_digest") != profile["distribution"]["source_digest"]:
            errors.append("Aether distribution manifest source digest mismatch")
    if schema_path.is_file():
        schema = load_object(schema_path)
        if schema.get("$id") != profile["contract"]["schema_id"]:
            errors.append("Aether journal schema identity mismatch")
        if schema.get("additionalProperties") is not False:
            errors.append("Aether journal schema must remain closed")
    return errors


def inspect_cli_version(command: str) -> str | None:
    """Read an installed Copilot CLI version without passing credentials."""

    candidate = Path(command)
    executable = str(candidate) if candidate.is_file() else shutil.which(command)
    if executable is None:
        return None
    allowed_environment_variables = {
        "LANG",
        "LC_ALL",
        "NO_COLOR",
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "TMPDIR",
        "WINDIR",
    }
    sanitized_environment = {
        variable: value
        for variable, value in os.environ.items()
        if variable in allowed_environment_variables
    }
    sanitized_environment["COPILOT_OFFLINE"] = "true"
    try:
        completed = subprocess.run(
            [executable, "--version"],
            check=False,
            capture_output=True,
            env=sanitized_environment,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    match = VERSION_IN_TEXT.search(f"{completed.stdout}\n{completed.stderr}")
    return match.group(1) if match else None


def build_preflight_result(
    profile: dict[str, Any],
    *,
    auth_mode: str,
    environment: Mapping[str, str],
    observed_cli_version: str | None,
    policy_state: str,
    permission_state: str,
    billing_acknowledged: bool,
    profile_bytes: bytes,
) -> dict[str, Any]:
    """Return a secret-free, fail-closed runtime readiness result."""

    if auth_mode not in AUTH_MODES:
        raise ValueError(f"unsupported auth mode: {auth_mode}")
    if policy_state not in POLICY_STATES:
        raise ValueError(f"unsupported policy state: {policy_state}")
    if permission_state not in PERMISSION_STATES:
        raise ValueError(f"unsupported permission state: {permission_state}")

    expected_version = profile["toolchain"]["package"]["version"]
    failures: set[str] = set()
    checks: dict[str, str] = {}

    if observed_cli_version is None:
        checks["cli_version"] = "fail"
        failures.add("cli-unavailable")
    elif observed_cli_version != expected_version:
        checks["cli_version"] = "fail"
        failures.add("cli-version-mismatch")
    else:
        checks["cli_version"] = "pass"

    if auth_mode == "github-token":
        credential = environment.get("GITHUB_TOKEN", "")
        conflicts = sorted(
            variable
            for variable in ("COPILOT_GITHUB_TOKEN", "GH_TOKEN")
            if environment.get(variable)
        )
        checks["organization_policy"] = "pass" if policy_state == "enabled" else "fail"
        if policy_state == "disabled":
            failures.add("organization-policy-disabled")
        elif policy_state != "enabled":
            failures.add("organization-policy-unverified")
    else:
        credential = environment.get("COPILOT_GITHUB_TOKEN", "")
        conflicts = ["GH_TOKEN"] if environment.get("GH_TOKEN") else []
        policy_state = "not-applicable"
        checks["organization_policy"] = "not-applicable"

    if not credential:
        checks["credential"] = "fail"
        failures.add("credential-missing")
    elif auth_mode == "fine-grained-pat" and not credential.startswith("github_pat_"):
        checks["credential"] = "fail"
        failures.add("credential-type-unsupported")
    else:
        checks["credential"] = "pass"

    if conflicts:
        checks["credential_precedence"] = "fail"
        failures.add("credential-precedence-conflict")
    else:
        checks["credential_precedence"] = "pass"

    if permission_state == "granted":
        checks["permission"] = "pass"
    elif permission_state == "missing":
        checks["permission"] = "fail"
        failures.add("permission-missing")
    else:
        checks["permission"] = "fail"
        failures.add("permission-unverified")

    if billing_acknowledged:
        checks["billing"] = "pass"
    else:
        checks["billing"] = "fail"
        failures.add("billing-unacknowledged")

    safe_to_invoke = not failures
    return {
        "schema_version": RESULT_SCHEMA,
        "profile_version": profile["version"],
        "profile_sha256": hashlib.sha256(profile_bytes).hexdigest(),
        "status": "ready" if safe_to_invoke else "unavailable",
        "auth_mode": auth_mode,
        "safe_to_invoke": safe_to_invoke,
        "checks": checks,
        "observed": {
            "cli_version": observed_cli_version,
            "credential_present": bool(credential),
            "policy_state": policy_state,
            "permission_state": permission_state,
            "billing_acknowledged": billing_acknowledged,
            "conflicting_environment_variables": conflicts,
        },
        "failure_reasons": sorted(failures),
    }


def validate_result(result: dict[str, Any]) -> list[str]:
    """Validate one secret-free preflight result and its state consistency."""

    errors: list[str] = []
    if not exact_keys(
        result,
        {
            "schema_version",
            "profile_version",
            "profile_sha256",
            "status",
            "auth_mode",
            "safe_to_invoke",
            "checks",
            "observed",
            "failure_reasons",
        },
        "result",
        errors,
    ):
        return errors
    if result["schema_version"] != RESULT_SCHEMA:
        errors.append("result.schema_version is unsupported")
    if not isinstance(result["profile_sha256"], str) or not SHA256.fullmatch(
        result["profile_sha256"]
    ):
        errors.append("result.profile_sha256 must be lowercase SHA-256")
    if (
        not isinstance(result["auth_mode"], str)
        or result["auth_mode"] not in AUTH_MODES
    ):
        errors.append("result.auth_mode is unsupported")

    checks = result["checks"]
    checks_are_closed = exact_keys(
        checks,
        {
            "cli_version",
            "credential",
            "credential_precedence",
            "organization_policy",
            "permission",
            "billing",
        },
        "result.checks",
        errors,
    )
    if checks_are_closed:
        if any(state not in CHECK_STATES for state in checks.values()):
            errors.append("result checks contain an unsupported state")

    observed = result["observed"]
    if exact_keys(
        observed,
        {
            "cli_version",
            "credential_present",
            "policy_state",
            "permission_state",
            "billing_acknowledged",
            "conflicting_environment_variables",
        },
        "result.observed",
        errors,
    ):
        if observed["policy_state"] not in POLICY_STATES:
            errors.append("result observed policy state is unsupported")
        if observed["permission_state"] not in PERMISSION_STATES:
            errors.append("result observed permission state is unsupported")
        conflicts = observed["conflicting_environment_variables"]
        if not isinstance(conflicts, list) or any(
            value not in {"COPILOT_GITHUB_TOKEN", "GH_TOKEN"}
            for value in conflicts
        ):
            errors.append("result observed credential conflicts are unsupported")

    reasons = result["failure_reasons"]
    if (
        not isinstance(reasons, list)
        or any(not isinstance(reason, str) for reason in reasons)
        or len(reasons) != len(set(reasons))
    ):
        errors.append("result failure reasons must be a unique list")
        reasons = []
    if any(reason not in PREFLIGHT_FAILURE_REASONS for reason in reasons):
        errors.append("result failure reasons contain an unsupported value")
    ready = result["status"] == "ready"
    if result["status"] not in {"ready", "unavailable"}:
        errors.append("result status is unsupported")
    if ready != (result["safe_to_invoke"] is True):
        errors.append("result status and safe_to_invoke disagree")
    if ready and reasons:
        errors.append("ready result cannot contain failure reasons")
    if not ready and not reasons:
        errors.append("unavailable result requires at least one failure reason")
    if ready and checks_are_closed and any(state == "fail" for state in checks.values()):
        errors.append("ready result cannot contain a failed check")
    return errors


def validate_repository(repository_root: Path = REPOSITORY_ROOT) -> list[str]:
    """Validate the runtime, Aether distribution, and owned JSON schemas."""

    profile_path = repository_root / "catalog/repository-journal-runtime.json"
    try:
        profile = load_object(profile_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return [str(error)]
    errors = validate_profile(profile)
    errors.extend(validate_locked_toolchain(profile, repository_root))
    try:
        aether_profile = load_object(
            repository_root / "catalog/repository-journal-aether.json"
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        errors.append(str(error))
    else:
        errors.extend(validate_aether_profile(aether_profile, repository_root))
    expected_schemas = {
        "repository-journal-aether-profile.v1.schema.json": (
            "https://egohygiene.github.io/relay/contracts/"
            "repository-journal-aether-profile/v1/schema.json"
        ),
        "repository-journal-runtime-profile.v1.schema.json": (
            "https://egohygiene.github.io/relay/contracts/"
            "repository-journal-runtime-profile/v1/schema.json"
        ),
        "repository-journal-runtime-preflight-result.v1.schema.json": (
            "https://egohygiene.github.io/relay/contracts/"
            "repository-journal-runtime-preflight-result/v1/schema.json"
        ),
        "repository-journal-evidence.v1.schema.json": (
            "https://egohygiene.github.io/relay/contracts/"
            "repository-journal-evidence/v1/schema.json"
        ),
        "repository-journal-candidate.v1.schema.json": (
            "https://egohygiene.github.io/relay/contracts/"
            "repository-journal-candidate/v1/schema.json"
        ),
        "repository-journal-result.v1.schema.json": (
            "https://egohygiene.github.io/relay/contracts/"
            "repository-journal-result/v1/schema.json"
        ),
    }
    for filename, schema_id in expected_schemas.items():
        path = repository_root / "schemas" / filename
        try:
            schema = load_object(path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(str(error))
            continue
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append(f"{filename} must use JSON Schema draft 2020-12")
        if schema.get("$id") != schema_id:
            errors.append(f"{filename} uses an unsupported contract ID")
        if schema.get("additionalProperties") is not False:
            errors.append(f"{filename} must be closed at its root")
    return errors


def write_result(result: dict[str, Any], output: Path | None) -> None:
    """Write or print one normalized result without credential material."""

    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if output is None:
        sys.stdout.write(rendered)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    """Build the explicit validation and offline-preflight command surface."""

    parser = argparse.ArgumentParser(
        description="Validate Relay's repository-journal runtime contract."
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("validate", help="Validate the profile and npm lock.")

    preflight = subcommands.add_parser(
        "preflight",
        help="Inspect local runtime readiness without making a Copilot request.",
    )
    preflight.add_argument("--auth-mode", choices=sorted(AUTH_MODES), required=True)
    preflight.add_argument(
        "--organization-policy-state",
        choices=sorted(POLICY_STATES - {"not-applicable"}),
        default="unknown",
    )
    preflight.add_argument(
        "--permission-state",
        choices=sorted(PERMISSION_STATES),
        default="unknown",
    )
    preflight.add_argument("--billing-acknowledged", action="store_true")
    preflight.add_argument("--copilot-command", default="copilot")
    preflight.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run contract validation or a secret-free offline readiness check."""

    args = build_parser().parse_args(argv)
    repository_errors = validate_repository()
    if repository_errors:
        for error in repository_errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    if args.command == "validate":
        print("Repository journal runtime profile and npm lock are valid.")
        return 0

    profile_bytes = PROFILE_PATH.read_bytes()
    profile = json.loads(profile_bytes)
    result = build_preflight_result(
        profile,
        auth_mode=args.auth_mode,
        environment=os.environ,
        observed_cli_version=inspect_cli_version(args.copilot_command),
        policy_state=args.organization_policy_state,
        permission_state=args.permission_state,
        billing_acknowledged=args.billing_acknowledged,
        profile_bytes=profile_bytes,
    )
    result_errors = validate_result(result)
    if result_errors:
        for error in result_errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    write_result(result, args.output)
    return 0 if result["safe_to_invoke"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
