# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT
"""Validate Relay workflow classes and durable report policy."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import Any

EXPECTED_CLASSES = {
    "supersedable-check": (True, "no-repository-mutation"),
    "evidence-preserving-check": (False, "no-repository-mutation"),
    "serialized-write": (False, "purpose-bound-write"),
    "immutable-publication": (False, "purpose-bound-write"),
}
WRITE_LEVEL = "write"


def load_object(path: Path) -> dict[str, Any]:
    """Read one JSON object."""

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate(repository_root: Path) -> list[str]:
    """Return every lifecycle contract error."""

    errors: list[str] = []
    try:
        lifecycle = load_object(repository_root / "catalog/ci-run-lifecycle.json")
        workflow_catalog = load_object(repository_root / "workflow-catalog.json")
    except (OSError, json.JSONDecodeError, ValueError) as error:
        return [f"invalid CI run lifecycle input: {error}"]

    if lifecycle.get("schema") != "egohygiene.relay.ci-run-lifecycle/v1":
        errors.append("CI run lifecycle uses an unsupported schema")
    if (
        lifecycle.get("schema_version") != 1
        or lifecycle.get("owner") != "egohygiene/relay"
    ):
        errors.append("CI run lifecycle version or owner is invalid")

    classes = lifecycle.get("workflow_classes")
    if not isinstance(classes, dict) or set(classes) != set(EXPECTED_CLASSES):
        errors.append("CI run lifecycle workflow classes are incomplete")
        classes = {}
    for name, (cancel, authority) in EXPECTED_CLASSES.items():
        value = classes.get(name)
        if not isinstance(value, dict):
            continue
        if value.get("cancel_in_progress") is not cancel:
            errors.append(f"workflow class {name} has the wrong cancellation policy")
        if value.get("authority") != authority:
            errors.append(f"workflow class {name} has the wrong authority ceiling")
        if (
            not isinstance(value.get("description"), str)
            or not value["description"].strip()
        ):
            errors.append(f"workflow class {name} needs a description")

    expected_report_policy = {
        "root": ".reports",
        "producer_directory": ".reports/<producer>",
        "producer_pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$",
        "artifact_name": "relay-report-<producer>-<run-id>-<run-attempt>",
        "default_retention_days": 30,
        "minimum_retention_days": 1,
        "maximum_retention_days": 90,
        "default_maximum_files": 100,
        "default_maximum_bytes": 104857600,
        "failure_upload_condition": "always",
        "missing_failure_evidence": "unavailable-not-success",
    }
    if lifecycle.get("report_policy") != expected_report_policy:
        errors.append("CI run lifecycle report policy is incomplete or unsupported")

    catalog_entries = {
        entry.get("path"): entry
        for entry in workflow_catalog.get("workflows", [])
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    }
    lifecycle_entries = lifecycle.get("workflows")
    if not isinstance(lifecycle_entries, list):
        return [*errors, "CI run lifecycle workflows must be an array"]
    lifecycle_paths: set[str] = set()
    for index, entry in enumerate(lifecycle_entries):
        label = f"ci-run-lifecycle.workflows[{index}]"
        if not isinstance(entry, dict) or set(entry) != {"id", "path", "class"}:
            errors.append(f"{label} has an unsupported shape")
            continue
        path = entry["path"]
        workflow_class = entry["class"]
        catalog_entry = catalog_entries.get(path)
        if catalog_entry is None:
            errors.append(f"{label} does not match a workflow catalog path: {path}")
            continue
        lifecycle_paths.add(path)
        if entry["id"] != catalog_entry.get("id"):
            errors.append(f"{label} id does not match the workflow catalog")
        class_contract = classes.get(workflow_class)
        if not isinstance(class_contract, dict):
            errors.append(f"{label} names an unknown workflow class")
            continue
        concurrency = catalog_entry.get("concurrency")
        if not isinstance(concurrency, dict):
            errors.append(f"{label} has no cataloged concurrency")
            continue
        if concurrency.get("cancel_in_progress") is not class_contract.get(
            "cancel_in_progress"
        ):
            errors.append(f"{label} cancellation disagrees with {workflow_class}")
        group = concurrency.get("group")
        if workflow_class in {
            "supersedable-check",
            "evidence-preserving-check",
        } and not any(
            token in str(group)
            for token in (
                "github.ref",
                "github.event.pull_request.number",
                "github.event.workflow_run.id",
            )
        ):
            errors.append(f"{label} does not identify the replaceable work item")
        if workflow_class == "immutable-publication" and not any(
            token in str(group)
            for token in ("inputs.version", "inputs.release-version")
        ):
            errors.append(f"{label} does not serialize by immutable release identity")
        permissions = catalog_entry.get("permissions")
        repository_writes = (
            {
                scope
                for scope, level in permissions.items()
                if level == WRITE_LEVEL and scope != "copilot-requests"
            }
            if isinstance(permissions, dict)
            else set()
        )
        has_repository_write = bool(repository_writes)
        if (
            has_repository_write
            and class_contract.get("authority") != "purpose-bound-write"
        ):
            errors.append(f"{label} places write authority in a read-only class")
        if not has_repository_write and workflow_class in {
            "serialized-write",
            "immutable-publication",
        }:
            errors.append(f"{label} places a read-only workflow in a write class")
        if workflow_class == "immutable-publication":
            failure = catalog_entry.get("failure_semantics")
            if (
                not isinstance(failure, dict)
                or failure.get("mode") != "resume-verified-release"
            ):
                errors.append(f"{label} immutable publication is not safely resumable")

    if lifecycle_paths != set(catalog_entries):
        missing = sorted(set(catalog_entries) - lifecycle_paths)
        stale = sorted(lifecycle_paths - set(catalog_entries))
        if missing:
            errors.append(f"workflow lifecycle classes missing: {', '.join(missing)}")
        if stale:
            errors.append(f"stale workflow lifecycle classes: {', '.join(stale)}")

    action = (
        repository_root / "actions/preserve-ci-report/action.yml"
    ).read_text(encoding="utf-8")
    for required in (
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
        'default: "30"',
        'path: "${{ steps.prepare.outputs.report-directory }}"',
        "if-no-files-found: error",
        "include-hidden-files: true",
    ):
        if required not in action:
            errors.append(f"preserve-ci-report action lacks required contract: {required}")

    adoption = lifecycle.get("adoption_evidence")
    if not isinstance(adoption, list):
        errors.append("CI run lifecycle adoption evidence must be an array")
        return errors
    evidence = {
        item.get("id"): item for item in adoption if isinstance(item, dict)
    }
    empathy = evidence.get("empathy-osv-scan")
    if not isinstance(empathy, dict) or empathy != {
        "id": "empathy-osv-scan",
        "kind": "reviewed-consumer",
        "repository": "egohygiene/empathy",
        "revision": "98778e8442d3be3ea7a3d1f62b71f33969346ecc",
        "path": ".github/workflows/osv-scan.yml",
        "class": "supersedable-check",
        "report_directory": ".reports/osv",
        "retention_days": 30,
        "failure_upload_condition": "always",
        "proof_run_url": "https://github.com/egohygiene/empathy/actions/runs/35354888576",
        "proof_snapshot_revision": "c9800ed19293e7c1b1d4a70c3bea006c1f2b64f5",
    }:
        errors.append("Empathy OSV adoption evidence is incomplete")

    fixture = evidence.get("relay-disposable-failure-smoke")
    validation = (repository_root / ".github/workflows/validate.yml").read_text(
        encoding="utf-8"
    )
    if not isinstance(fixture, dict):
        errors.append("disposable failure smoke evidence is missing")
    for required in (
        "id: ci-report-lifecycle-check",
        "continue-on-error: true",
        "uses: ./actions/preserve-ci-report",
        'producer: "ci-report-lifecycle-smoke"',
        'retention-days: "1"',
        "CI_REPORT_CHECK_OUTCOME",
    ):
        if required not in validation:
            errors.append(f"disposable failure smoke lacks required contract: {required}")
    preservation_step = re.search(
        r"- name: Preserve disposable failure evidence\n"
        r"(?:.*\n){0,5}?\s+if: \"\$\{\{ always\(\) \}\}\"\n"
        r"(?:.*\n){0,5}?\s+uses: \./actions/preserve-ci-report",
        validation,
    )
    if preservation_step is None:
        errors.append(
            'disposable failure smoke lacks required contract: if: "${{ always() }}"'
        )

    return errors


def main() -> int:
    """Validate the repository contract."""

    repository_root = Path(__file__).resolve().parents[1]
    errors = validate(repository_root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    count = len(
        load_object(repository_root / "catalog/ci-run-lifecycle.json")["workflows"]
    )
    print(f"Validated {count} workflow lifecycle classes and durable report policy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
