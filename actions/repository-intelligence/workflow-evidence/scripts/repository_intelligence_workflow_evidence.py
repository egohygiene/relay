# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT
"""Prepare and finalize bounded Repository Intelligence workflow evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import tempfile
from typing import Final


WORKFLOW_CONTRACT: Final = "v1"
REPORT_CONTRACT: Final = "v1"
REPORT_RETENTION_DAYS: Final = 30
REPORT_FILENAME: Final = "repository-intelligence-run-report.json"
REPORT_SCHEMA: Final = "egohygiene.relay.repository-intelligence-workflow-report/v1"
REPORT_SCHEMA_URL: Final = (
    "https://egohygiene.github.io/relay/contracts/"
    "repository-intelligence-workflow-report/v1/schema.json"
)
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
REVISION = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^(?:sha256:)?([0-9a-f]{64})$")
RELATIVE_PATH = re.compile(r"^[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$")
WORKFLOW_FILENAME = re.compile(r"^[A-Za-z0-9_.-]+\.ya?ml$")
OUTCOMES = {"success", "failure", "cancelled", "skipped"}
DENIED_EVENTS = {
    "deployment",
    "deployment_status",
    "issue_comment",
    "pull_request_review",
    "pull_request_review_comment",
    "pull_request_target",
    "repository_dispatch",
    "workflow_run",
}
PROTECTED_ROOTS = {".git", ".github", "actions", "schemas", "scripts", "tests"}
STAGE_FAILURES: Final = (
    (
        "hardening_outcome",
        "runner-hardening",
        "RIW-001",
        "repository-intelligence.workflow.runner-hardening",
    ),
    (
        "preflight_outcome",
        "trust-and-input-validation",
        "RIW-002",
        "repository-intelligence.workflow.trust-and-input-validation",
    ),
    (
        "checkout_outcome",
        "checkout",
        "RIW-003",
        "repository-intelligence.workflow.checkout",
    ),
    (
        "generation_outcome",
        "generation",
        "RIW-004",
        "repository-intelligence.workflow.generation",
    ),
    (
        "provenance_outcome",
        "provenance-verification",
        "RIW-005",
        "repository-intelligence.workflow.provenance-verification",
    ),
    (
        "site_upload_outcome",
        "site-artifact-upload",
        "RIW-006",
        "repository-intelligence.workflow.site-artifact-upload",
    ),
)


class ContractError(ValueError):
    """A closed contract violation safe to identify by stable code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class StableArgumentParser(argparse.ArgumentParser):
    """Convert parser failures into one non-reflective contract error."""

    def error(self, _message: str) -> None:
        raise ContractError("RIW-CLI")

    def exit(self, _status: int = 0, _message: str | None = None) -> None:
        raise ContractError("RIW-CLI")


def positive_integer(value: str, code: str, maximum: int) -> int:
    """Parse a bounded positive decimal integer without echoing the value."""

    if (
        not re.fullmatch(r"[1-9][0-9]*", value)
        or len(value) > len(str(maximum))
    ):
        raise ContractError(code)
    parsed = int(value)
    if parsed > maximum:
        raise ContractError(code)
    return parsed


def valid_repository(value: str) -> bool:
    """Return whether a provider repository identity has two real segments."""

    if not REPOSITORY.fullmatch(value) or len(value) > 140:
        return False
    owner, name = value.split("/", maxsplit=1)
    return owner not in {".", ".."} and name not in {".", ".."}


def valid_git_ref_name(value: str) -> bool:
    """Apply Git's bounded ref-name exclusions without invoking checkout code."""

    if (
        not value
        or len(value) > 255
        or value == "@"
        or value.startswith(("/", "-"))
        or value.endswith(("/", "."))
        or ".." in value
        or "//" in value
        or "@{" in value
        or any(
            ord(character) < 32
            or ord(character) == 127
            or character in " ~^:?*[\\"
            for character in value
        )
    ):
        return False
    return all(
        component
        and not component.startswith(".")
        and not component.endswith(".lock")
        for component in value.split("/")
    )


def workflow_ref_identity(value: str) -> tuple[str, str, str]:
    """Parse a provider workflow ref without accepting ambiguous path shapes."""

    if not value or len(value) > 1024:
        raise ContractError("RIW-INVOCATION-IDENTITY")
    workflow, separator, ref = value.partition("@")
    marker = "/.github/workflows/"
    if separator != "@" or marker not in workflow:
        raise ContractError("RIW-INVOCATION-IDENTITY")
    repository, filename = workflow.split(marker, maxsplit=1)
    if (
        not valid_repository(repository)
        or not WORKFLOW_FILENAME.fullmatch(filename)
        or not valid_git_ref_name(ref)
    ):
        raise ContractError("RIW-INVOCATION-IDENTITY")
    return repository, filename, ref


def validate_identity(
    arguments: argparse.Namespace,
    *,
    require_immutable_pin: bool,
) -> dict[str, object]:
    """Validate provider-derived identity used by both operations."""

    if not valid_repository(arguments.repository):
        raise ContractError("RIW-IDENTITY-REPOSITORY")
    if not REVISION.fullmatch(arguments.represented_revision):
        raise ContractError("RIW-IDENTITY-REVISION")
    if not REVISION.fullmatch(arguments.called_workflow_revision):
        raise ContractError("RIW-IDENTITY-WORKFLOW-REVISION")
    if arguments.called_workflow_repository.lower() != "egohygiene/relay":
        raise ContractError("RIW-IDENTITY-WORKFLOW-REPOSITORY")
    try:
        workflow_repository, workflow_filename, workflow_pin = workflow_ref_identity(
            arguments.called_workflow_ref
        )
    except ContractError as error:
        raise ContractError("RIW-IDENTITY-WORKFLOW-REF") from error
    if (
        workflow_repository.lower() != "egohygiene/relay"
        or workflow_filename != "repository-intelligence.yml"
    ):
        raise ContractError("RIW-IDENTITY-WORKFLOW-REF")
    if REVISION.fullmatch(workflow_pin):
        if workflow_pin != arguments.called_workflow_revision:
            raise ContractError("RIW-IDENTITY-WORKFLOW-PIN")
    elif require_immutable_pin:
        direct_dispatch = arguments.caller_workflow_ref == arguments.called_workflow_ref
        repository_local_revision = (
            arguments.repository.lower() == "egohygiene/relay"
            and arguments.called_workflow_revision == arguments.represented_revision
        )
        if not direct_dispatch and not repository_local_revision:
            raise ContractError("RIW-IDENTITY-WORKFLOW-PIN")
    return {
        "repository_id": positive_integer(
            arguments.repository_id, "RIW-IDENTITY-REPOSITORY-ID", 10**20
        ),
        "run_id": positive_integer(arguments.run_id, "RIW-IDENTITY-RUN-ID", 10**20),
        "run_attempt": positive_integer(
            arguments.run_attempt, "RIW-IDENTITY-RUN-ATTEMPT", 10**6
        ),
    }


def invocation_class(arguments: argparse.Namespace) -> str:
    """Distinguish direct Relay dispatch from a reusable caller."""

    caller_repository, _caller_filename, _caller_ref = workflow_ref_identity(
        arguments.caller_workflow_ref
    )
    if caller_repository.lower() != arguments.repository.lower():
        raise ContractError("RIW-INVOCATION-IDENTITY")
    if arguments.caller_workflow_ref == arguments.called_workflow_ref:
        return "direct-dispatch"
    return "reusable-call"


def classify_event(arguments: argparse.Namespace, *, strict: bool) -> tuple[str, str, str]:
    """Return closed invocation, event, and trust classes."""

    try:
        invocation = invocation_class(arguments)
    except ContractError:
        if strict:
            raise
        return "reusable-call", "unsupported", "untrusted-content"

    event_name = arguments.event_name
    if invocation == "direct-dispatch" and (
        arguments.repository.lower() != arguments.called_workflow_repository.lower()
        or arguments.represented_revision != arguments.called_workflow_revision
    ):
        if strict:
            raise ContractError("RIW-INVOCATION-IDENTITY")
        return invocation, "unsupported", "untrusted-content"
    if invocation == "direct-dispatch" and event_name != "workflow_dispatch":
        if strict:
            raise ContractError("RIW-EVENT-UNSUPPORTED")
        return invocation, "unsupported", "untrusted-content"
    if event_name in DENIED_EVENTS:
        if strict:
            raise ContractError("RIW-EVENT-UNSUPPORTED")
        return invocation, "unsupported", "untrusted-content"

    if event_name == "pull_request":
        if not valid_repository(arguments.pull_request_head_repository):
            if strict:
                raise ContractError("RIW-EVENT-PULL-REQUEST-IDENTITY")
            return invocation, "unsupported", "untrusted-content"
        if arguments.pull_request_head_repository.lower() == arguments.repository.lower():
            return invocation, "trusted-pull-request", "untrusted-content"
        return invocation, "fork-pull-request", "untrusted-content"

    if event_name == "push":
        expected_ref = f"refs/heads/{arguments.event_default_branch}"
        if (
            not valid_git_ref_name(arguments.event_default_branch)
            or arguments.ref != expected_ref
        ):
            if strict:
                raise ContractError("RIW-EVENT-NONDEFAULT-PUSH")
            return invocation, "unsupported", "untrusted-content"
        return invocation, "default-branch-push", "trusted-default-branch"

    if event_name == "workflow_dispatch":
        return invocation, "manual-rebuild", "untrusted-content"

    if strict:
        raise ContractError("RIW-EVENT-UNSUPPORTED")
    return invocation, "unsupported", "untrusted-content"


def validate_relative_path(value: str, code: str) -> None:
    """Require one bounded canonical repository-relative path."""

    if (
        not value
        or len(value) > 240
        or not RELATIVE_PATH.fullmatch(value)
        or "/./" in f"/{value}/"
        or "/../" in f"/{value}/"
    ):
        raise ContractError(code)


def paths_overlap(first: str, second: str) -> bool:
    """Return whether either canonical path contains the other."""

    return first == second or first.startswith(f"{second}/") or second.startswith(f"{first}/")


def validate_configuration(arguments: argparse.Namespace) -> int:
    """Validate untrusted workflow inputs before checkout or generation."""

    paths = {
        "output": arguments.output_directory,
        "work": arguments.work_directory,
        "reports": arguments.reports_directory,
    }
    for label, value in paths.items():
        validate_relative_path(value, f"RIW-INPUT-{label.upper()}-PATH")
    if paths["output"].split("/", maxsplit=1)[0] in PROTECTED_ROOTS:
        raise ContractError("RIW-INPUT-OUTPUT-PROTECTED")
    if paths["work"].split("/", maxsplit=1)[0] in PROTECTED_ROOTS:
        raise ContractError("RIW-INPUT-WORK-PROTECTED")
    output_parts = paths["output"].split("/")
    if len(output_parts) < 2 or output_parts[-1] != "intelligence":
        raise ContractError("RIW-INPUT-OUTPUT-LAYOUT")
    site_root = "/".join(output_parts[:-1])
    for first, second in (("output", "work"), ("output", "reports")):
        if paths_overlap(paths[first], paths[second]):
            raise ContractError("RIW-INPUT-PATH-OVERLAP")
    for label in ("work", "reports"):
        if paths[label] == site_root or paths[label].startswith(f"{site_root}/"):
            raise ContractError("RIW-INPUT-PRIVATE-IN-SITE")
    if paths["work"] == paths["reports"] or paths["work"].startswith(
        f"{paths['reports']}/"
    ):
        raise ContractError("RIW-INPUT-WORK-REPORTS-OVERLAP")
    for child in ("activity", "analytics", "tree", "visualization"):
        if paths_overlap(paths["reports"], f"{paths['work']}/{child}"):
            raise ContractError("RIW-INPUT-WORK-REPORTS-OVERLAP")

    for label, value in (
        ("snapshot", arguments.observatory_snapshot),
        ("comparison", arguments.observatory_comparison),
    ):
        if value:
            validate_relative_path(value, f"RIW-INPUT-{label.upper()}-PATH")
            if paths_overlap(value, paths["output"]):
                raise ContractError("RIW-INPUT-EVIDENCE-OVERLAP")
    if arguments.observatory_comparison and not arguments.observatory_snapshot:
        raise ContractError("RIW-INPUT-COMPARISON-WITHOUT-SNAPSHOT")
    if arguments.observatory_comparison == arguments.observatory_snapshot and arguments.observatory_comparison:
        raise ContractError("RIW-INPUT-EVIDENCE-COLLISION")

    positive_integer(arguments.max_depth, "RIW-INPUT-MAX-DEPTH", 20)
    if (
        not arguments.activity_since
        or len(arguments.activity_since) > 128
        or any(ord(character) < 32 for character in arguments.activity_since)
    ):
        raise ContractError("RIW-INPUT-ACTIVITY-WINDOW")
    if arguments.default_branch and not valid_git_ref_name(arguments.default_branch):
        raise ContractError("RIW-INPUT-DEFAULT-BRANCH")
    return positive_integer(
        arguments.artifact_retention_days, "RIW-INPUT-RETENTION", 90
    )


def artifact_name(arguments: argparse.Namespace, identity: dict[str, object]) -> str:
    """Build a revision- and contract-isolated site artifact name."""

    return (
        "repository-intelligence-site-v1-"
        f"{identity['repository_id']}-{arguments.represented_revision}-"
        f"{identity['run_id']}-{identity['run_attempt']}"
    )


def report_artifact_name(identity: dict[str, object]) -> str:
    """Return the name emitted by preserve-ci-report for this producer."""

    return (
        "relay-report-repository-intelligence-v1-"
        f"{identity['run_id']}-{identity['run_attempt']}"
    )


def release_version(action_path: Path) -> str:
    """Read the packaged Relay release version."""

    release_path = action_path.parents[2] / "release.json"
    value = json.loads(release_path.read_text(encoding="utf-8"))
    version = value.get("version")
    if not isinstance(version, str) or not re.fullmatch(
        r"v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", version
    ):
        raise ContractError("RIW-PACKAGE-RELEASE")
    return version


def write_outputs(path: str, outputs: dict[str, str]) -> None:
    """Append single-line action outputs."""

    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as destination:
        for key, value in outputs.items():
            if "\n" in value or "\r" in value:
                raise ContractError("RIW-OUTPUT-ENCODING")
            destination.write(f"{key}={value}\n")


def prepare(arguments: argparse.Namespace) -> dict[str, str]:
    """Validate the trust/input contract and emit immutable metadata."""

    identity = validate_identity(arguments, require_immutable_pin=True)
    invocation, event_class, trust_class = classify_event(arguments, strict=True)
    retention_days = validate_configuration(arguments)
    outputs = {
        "artifact-name": artifact_name(arguments, identity),
        "event-class": event_class,
        "invocation-class": invocation,
        "trust-class": trust_class,
        "site-retention-days": str(retention_days),
        "workflow-contract": WORKFLOW_CONTRACT,
        "report-contract": REPORT_CONTRACT,
    }
    write_outputs(arguments.github_output, outputs)
    return outputs


def normalized_outcome(value: str) -> str:
    """Validate one provider-controlled step outcome."""

    if value not in OUTCOMES:
        raise ContractError("RIW-STAGE-OUTCOME")
    return value


def result_for_stages(arguments: argparse.Namespace) -> tuple[str, str, str, str]:
    """Map the first failed/skipped stage to a stable public result."""

    outcomes = [
        (stage, code, rule, normalized_outcome(getattr(arguments, field)))
        for field, stage, code, rule in STAGE_FAILURES
    ]
    failed = False
    for _stage, _code, _rule, outcome in outcomes:
        if failed and outcome != "skipped":
            raise ContractError("RIW-STAGE-SEQUENCE")
        if outcome != "success":
            failed = True
    for stage, code, rule, outcome in outcomes:
        if outcome != "success":
            return "failure", stage, code, rule
    return (
        "success",
        "completed",
        "RIW-000",
        "repository-intelligence.workflow.success",
    )


def normalize_digest(value: str, required: bool) -> str | None:
    """Return a canonical SHA-256 digest or fail closed."""

    if not value:
        if required:
            raise ContractError("RIW-SITE-DIGEST")
        return None
    match = DIGEST.fullmatch(value)
    if not match:
        raise ContractError("RIW-SITE-DIGEST")
    return f"sha256:{match.group(1)}"


def safe_report_directory(runner_temp: str) -> Path:
    """Create an unpredictable report directory inside the provider runner temp."""

    if not runner_temp:
        raise ContractError("RIW-RUNNER-TEMP")
    root = Path(runner_temp)
    if not root.is_absolute() or not root.is_dir() or root.is_symlink():
        raise ContractError("RIW-RUNNER-TEMP")
    resolved = root.resolve()
    directory = Path(tempfile.mkdtemp(prefix="relay-ri-v1-", dir=resolved))
    if directory.parent != resolved or directory.is_symlink():
        raise ContractError("RIW-RUNNER-TEMP")
    return directory


def finalize(arguments: argparse.Namespace, action_path: Path) -> dict[str, str]:
    """Write one closed, sanitized report for success or actionable failure."""

    identity = validate_identity(arguments, require_immutable_pin=False)
    invocation, event_class, trust_class = classify_event(arguments, strict=False)
    result, stage, code, rule = result_for_stages(arguments)
    configuration_valid = True
    try:
        retention_days: int | None = validate_configuration(arguments)
    except ContractError:
        configuration_valid = False
        retention_days = None
    if (
        arguments.hardening_outcome == "success"
        and (event_class == "unsupported" or not configuration_valid)
    ):
        result = "failure"
        stage = "trust-and-input-validation"
        code = "RIW-002"
        rule = "repository-intelligence.workflow.trust-and-input-validation"
    site_uploaded = result == "success"
    site_digest = None
    if site_uploaded:
        try:
            site_digest = normalize_digest(
                arguments.site_artifact_digest,
                required=True,
            )
        except ContractError:
            result = "failure"
            stage = "site-artifact-upload"
            code = "RIW-006"
            rule = "repository-intelligence.workflow.site-artifact-upload"
            site_uploaded = False
    site_name = artifact_name(arguments, identity)
    report_name = report_artifact_name(identity)
    report_directory = safe_report_directory(arguments.runner_temp)
    remediation = (
        "https://github.com/egohygiene/Relay/blob/"
        f"{arguments.called_workflow_revision}/"
        "docs/repository-intelligence-publication.md#failure-codes-and-recovery"
    )
    report = {
        "$schema": REPORT_SCHEMA_URL,
        "schema": REPORT_SCHEMA,
        "schema_version": 1,
        "result": result,
        "stage": stage,
        "code": code,
        "rule": rule,
        "repository": arguments.repository,
        "represented_revision": arguments.represented_revision,
        "run": {
            "id": identity["run_id"],
            "attempt": identity["run_attempt"],
        },
        "event": {
            "class": event_class,
            "invocation": invocation,
            "trust": trust_class,
            "authority": "contents-read-artifact-only",
        },
        "versions": {
            "relay": release_version(action_path),
            "called_workflow_revision": arguments.called_workflow_revision,
            "workflow_contract": WORKFLOW_CONTRACT,
            "report_contract": REPORT_CONTRACT,
            "provenance_contract": "v1",
            "dashboard_contract": "v3",
        },
        "artifacts": {
            "site": {
                "name": site_name,
                "status": "uploaded" if site_uploaded else "not-uploaded",
                "digest": site_digest,
                "retention_days": retention_days,
            },
            "run_report": {
                "name": report_name,
                "status": "prepared",
                "retention_days": REPORT_RETENTION_DAYS,
            },
        },
        "remediation": remediation,
        "sanitization": "allowlisted-metadata-only",
    }
    report_path = report_directory / REPORT_FILENAME
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    outputs = {
        "artifact-name": site_name,
        "event-class": event_class,
        "invocation-class": invocation,
        "trust-class": trust_class,
        "workflow-outcome": result,
        "failed-stage": "" if result == "success" else stage,
        "error-code": code,
        "rule-id": rule,
        "report-artifact-name": report_name,
        "report-directory": report_directory.as_posix(),
        "report-path": report_path.as_posix(),
        "report-retention-days": str(REPORT_RETENTION_DAYS),
    }
    write_outputs(arguments.github_output, outputs)
    return outputs


def parser() -> argparse.ArgumentParser:
    """Build the closed command-line surface used by the composite action."""

    value = StableArgumentParser(allow_abbrev=False)
    value.add_argument("--operation", choices=("prepare", "finalize"), required=True)
    value.add_argument("--action-path", required=True)
    value.add_argument("--runner-temp", default="")
    value.add_argument("--github-output", default="")
    value.add_argument("--repository", required=True)
    value.add_argument("--repository-id", required=True)
    value.add_argument("--represented-revision", required=True)
    value.add_argument("--run-id", required=True)
    value.add_argument("--run-attempt", required=True)
    value.add_argument("--event-name", default="")
    value.add_argument("--ref", default="")
    value.add_argument("--event-default-branch", default="")
    value.add_argument("--pull-request-head-repository", default="")
    value.add_argument("--caller-workflow-ref", required=True)
    value.add_argument("--called-workflow-ref", required=True)
    value.add_argument("--called-workflow-repository", required=True)
    value.add_argument("--called-workflow-revision", required=True)
    value.add_argument("--output-directory", default="dist/intelligence")
    value.add_argument("--work-directory", default=".cache/repository-intelligence")
    value.add_argument("--reports-directory", default=".reports")
    value.add_argument("--observatory-snapshot", default="")
    value.add_argument("--observatory-comparison", default="")
    value.add_argument("--default-branch", default="")
    value.add_argument("--activity-since", default="1 year ago")
    value.add_argument("--max-depth", default="10")
    value.add_argument("--artifact-retention-days", default="30")
    value.add_argument("--hardening-outcome", default="skipped")
    value.add_argument("--preflight-outcome", default="skipped")
    value.add_argument("--checkout-outcome", default="skipped")
    value.add_argument("--generation-outcome", default="skipped")
    value.add_argument("--provenance-outcome", default="skipped")
    value.add_argument("--site-upload-outcome", default="skipped")
    value.add_argument("--site-artifact-digest", default="")
    return value


def main() -> int:
    """Run the requested operation with stable, non-reflective diagnostics."""

    try:
        arguments = parser().parse_args()
        action_path = Path(arguments.action_path).resolve(strict=True)
        if arguments.operation == "prepare":
            prepare(arguments)
        else:
            finalize(arguments, action_path)
    except ContractError as error:
        print(f"repository-intelligence-workflow-evidence: {error.code}")
        return 2
    except (OSError, ValueError, json.JSONDecodeError):
        print("repository-intelligence-workflow-evidence: RIW-INTERNAL-ERROR")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
