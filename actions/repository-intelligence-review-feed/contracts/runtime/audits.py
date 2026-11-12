"""Deterministic Audits metadata queries from exact authored Aether sidecars."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any, Iterable

from . import audits_contract as contract

shared = contract.shared


def _public_source(report, allowed, repository):
    if not shared.scope_admitted(report, allowed, objects=True):
        return False
    targets = report["scope"]["repositories"]
    if not any(item["full_name"] == repository for item in targets):
        return False
    # Source references are scope headers too; their text and identities do not
    # become public merely because the enclosing report declared visibility.
    for ref in report.get("evidence", []):
        if isinstance(ref, dict):
            if ref.get("repository") is not None and ref.get("repository") not in allowed:
                return False
            if not shared.url_scope_admitted(ref.get("uri"), allowed):
                return False
    for finding in report.get("findings", []):
        if isinstance(finding, dict) and (finding.get("visibility") != "public" or finding.get("repository") not in allowed):
            return False
    for prior in report.get("prior_audits", []):
        if isinstance(prior, dict) and not shared.url_scope_admitted(prior.get("uri"), allowed):
            return False
    canonical = report.get("canonical_report", {})
    producer = report.get("provenance", {}).get("producer", {}) if isinstance(report.get("provenance"), dict) else {}
    if isinstance(canonical, dict) and not shared.url_scope_admitted(canonical.get("uri"), allowed):
        return False
    if isinstance(producer, dict) and not shared.url_scope_admitted(producer.get("uri"), allowed):
        return False
    return shared.ownership_preflight(report, allowed)


def _normalize(report, input_metadata, repository, represented_commit, as_of, maximum_age, native):
    evidence = {item["id"]: item for item in report["evidence"]}
    findings = []
    for finding in report["findings"]:
        if finding["repository"] != repository:
            continue
        fields = ("id", "repository", "title", "classification", "nature", "severity", "confidence", "status", "area",
                  "effort", "impact", "source_profile", "evidence_classification", "history", "missing_evidence")
        evidence_fields = ("id", "classification", "kind", "repository", "revision", "uri", "path", "sha256", "observed_at")
        findings.append({**{name: deepcopy(finding[name]) for name in fields},
            "key": f"{repository}:{report['audit_id']}:{finding['id']}",
            "evidence": [{name: deepcopy(evidence[ref][name]) for name in evidence_fields} for ref in sorted(finding["evidence_refs"])],
            "history_evidence": [{name: deepcopy(evidence[ref][name]) for name in evidence_fields}
                for ref in sorted(finding["history"]["evidence_refs"])]})
    finding_ids = {item["id"] for item in findings}
    candidates = []
    for item in report["candidate_issues"]:
        selected = sorted(set(item["finding_ids"]) & finding_ids)
        if selected:
            candidates.append({"id": item["id"], "status": item["status"], "priority": item["priority"],
                "finding_ids": selected, "projection": "complete" if len(selected) == len(item["finding_ids"]) else "repository-subset",
                "materialization": "unavailable"})
    completed = shared.instant(report["completed_at"]) if report["completed_at"] is not None else None
    revision = next(item["revision"] for item in report["scope"]["repositories"] if item["full_name"] == repository)
    command_counts = Counter(item["state"] for item in report["provenance"]["commands"])
    return {"id": report["audit_id"], "scope": deepcopy(report["scope"]), "profiles": deepcopy(report["profiles"]),
        "started_at": report["started_at"], "completed_at": report["completed_at"], "completion": deepcopy(report["completion"]),
        "revision_status": "matched" if revision == represented_commit else "different",
        "freshness": "unknown" if completed is None else "stale" if (shared.instant(as_of) - completed).total_seconds() > maximum_age else "current",
        "source": {"report_schema": native.SCHEMA, "contract_version": native.VERSION, "owner_report_sha256": native.digest(report),
            "canonical_report": deepcopy(report["canonical_report"]), "input": input_metadata},
        "findings": sorted(findings, key=lambda item: item["key"]), "candidate_issues": sorted(candidates, key=lambda item: item["id"]),
        "prior_audits": sorted(deepcopy(report["prior_audits"]), key=lambda item: item["audit_id"]),
        "producer": deepcopy(report["provenance"]["producer"]), "limitations": deepcopy(report["provenance"]["limitations"]),
        "command_states": {name: command_counts[name] for name in ("success", "failure", "not_run", "unavailable", "unsupported")}}


def build_repository_audits(evidence_wrappers: Iterable[Any], *, repository: str, represented_commit: str,
        as_of: str, admission_root=contract.DEFAULT_ROOT, admission: dict | None = None,
        maximum_age_seconds: int = contract.DEFAULT_AGE) -> dict:
    row, proof, allowed = shared.admission(repository, admission_root=admission_root)
    require = shared.require
    require(admission is None or admission == proof)
    require(isinstance(represented_commit, str) and shared.base.SHA.fullmatch(represented_commit)
            and type(maximum_age_seconds) is int and 1 <= maximum_age_seconds <= contract.MAX_AGE)
    evaluated = shared.instant(as_of)
    native, registry, owner = contract.owners(admission_root)
    runs = []
    identifiers = set()
    finding_count = 0
    for raw, transport in shared.wrappers(evidence_wrappers, repository, allowed):
        if not _public_source(raw, allowed, repository):
            continue
        if not set(native.referenced_repositories(raw)) <= allowed:
            continue
        require(len(runs) < shared.MAX_RECORDS)
        report = native.validate_report(shared.native_value(raw), registry)
        metadata = shared.source_input(transport, raw)
        require(report["audit_id"] not in identifiers)
        require(shared.instant(report["started_at"]) <= evaluated and (report["completed_at"] is None
                or shared.instant(report["completed_at"]) <= evaluated))
        identifiers.add(report["audit_id"])
        normalized = _normalize(report, metadata, repository, represented_commit, as_of, maximum_age_seconds, native)
        finding_count += len(normalized["findings"])
        require(finding_count <= shared.MAX_FINDINGS)
        runs.append(normalized)
    runs.sort(key=lambda item: item["id"])
    value = {"schema": contract.SCHEMA, "contract_version": contract.VERSION, "visibility": "public",
        "repository": shared.repository_identity(row), "represented_commit": represented_commit, "as_of": as_of,
        "admission": proof, "source_owner": owner, "freshness_policy": {"maximum_age_seconds": maximum_age_seconds, "anchor": "original-completed-at"},
        "runs": runs, "summary": contract.summary(runs, native), "queries": contract.queries(runs),
        "campaigns": {"state": "unavailable", "references": [], "reason": "No compatible orchestration manifests supplied."},
        "evidence": contract.evidence(runs)}
    return contract.validate(shared.seal(value), admission_root=admission_root)


def build_fleet_audits(evidence_wrappers: Iterable[Any], *, repositories: Iterable[Any], as_of: str,
        admission_root=contract.DEFAULT_ROOT, maximum_age_seconds: int = contract.DEFAULT_AGE) -> dict:
    selected, rows, _allowed = shared.targets(repositories, admission_root)
    shared.instant(as_of)
    # Materialize data only; no lookup, inspection or digest of excluded wrappers.
    wrappers = list(evidence_wrappers)
    entries, size = [], 0
    for name, revision in selected.items():
        entry = build_repository_audits(wrappers, repository=name, represented_commit=revision, as_of=as_of,
            admission_root=admission_root, maximum_age_seconds=maximum_age_seconds)
        size += len(contract.canonical(entry))
        shared.require(size <= shared.base.MAX_BYTES)
        entries.append(entry)
    native, _registry, _owner = contract.owners(admission_root)
    runs = [run for item in entries for run in item["runs"]]
    value = {"schema": contract.FLEET_SCHEMA, "contract_version": contract.VERSION, "visibility": "public", "as_of": as_of,
        "admission": shared.fleet_admission(selected, rows, admission_root), "repositories": entries,
        "summary": contract.summary(runs, native), "evidence": {"state": "supplied" if runs else "unavailable",
            "repository_count": len(entries), "with_evidence_count": sum(bool(item["runs"]) for item in entries),
            "canonical_inputs_sha256": contract.digest([item["digest"] for item in entries])}}
    return contract.validate_fleet(shared.seal(value), admission_root=admission_root)
