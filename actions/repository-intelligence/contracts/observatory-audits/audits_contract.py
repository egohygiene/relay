"""Standalone, standard-library public repository/fleet Audits owner contract."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("observatory_audits_public_reviews", Path(__file__).with_name("public_reviews.py"))
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)

SCHEMA = "egohygiene.observatory.repository-audits/v1"
FLEET_SCHEMA = "egohygiene.observatory.fleet-audits/v1"
VERSION = "1.0.0-alpha.1"
LOCK = "aether.audit-report.v1.lock.json"
LOCK_SHA256 = "951fc63ac3fc30918b4de3ac6def6da286046901a51b5cb8ffed3e3692614194"
HELPER = "library/organization/skills/quality/audit-repository/scripts/audit_contract.py"
REGISTRY = "library/organization/skills/quality/audit-repository/references/audit-profiles.v1.json"
MAX_AGE = 31536000
DEFAULT_AGE = 2592000
DEFAULT_ROOT = shared.DEFAULT_ROOT
parse = shared.parse
digest = shared.digest
instant = shared.instant
admission = shared.admission
canonical = shared.canonical
require = shared.require
closed = shared.closed
plain = shared.plain


def owners(root=DEFAULT_ROOT):
    lock, files = shared.owner_resources(root, LOCK, LOCK_SHA256)
    require(lock["owner"] == "egohygiene/aether")
    native = shared.load_owner(files[HELPER]["local"], "observatory_aether_audit_owner")
    registry = native.validate_registry(shared.native_value(parse(files[REGISTRY]["bytes"])))
    return native, registry, {"owner": lock["owner"], "revision": lock["revision"], "lock_sha256": LOCK_SHA256,
        "schema": native.SCHEMA, "contract_version": native.VERSION, "registry_sha256": native.digest(registry)}


input_metadata = shared.input_metadata


def _counts(values, choices):
    counts = Counter(values)
    require(set(counts) <= set(choices))
    return {name: counts[name] for name in choices}


def summary(runs, native):
    findings = [item for run in runs for item in run["findings"]]
    return {"completion": _counts((run["completion"]["state"] for run in runs), native.COMPLETION_STATES),
        "counting_unit": "repository-report-projection",
        "freshness": _counts((run["freshness"] for run in runs), ("current", "stale", "unknown")),
        "revision": _counts((run["revision_status"] for run in runs), ("matched", "different")),
        "findings": {"classification": _counts((item["classification"] for item in findings), native.CLASSIFICATIONS),
            "nature": _counts((item["nature"] for item in findings), native.NATURES),
            "severity": _counts((item["severity"] for item in findings), native.SEVERITIES),
            "confidence": _counts((item["confidence"] for item in findings), ("high", "medium", "low")),
            "status": _counts((item["status"] for item in findings), native.STATUSES),
            "evidence_classification": _counts((item["evidence_classification"] for item in findings), native.LABELS),
            "history_delta": _counts((item["history"]["delta"] for item in findings), native.DELTAS)},
        "candidate_issues": {"suggested": sum(len(run["candidate_issues"]) for run in runs), "materialization": "unavailable"},
        "assessment": "authored-audit-evidence-only-no-conformance-or-sanity-score"}


def queries(runs):
    latest = {}
    for run in runs:
        boundary = run["completed_at"] or run["started_at"]
        for profile in run["profiles"]["resolved"]:
            key = (profile["id"], profile["version"])
            selected = latest.setdefault(key, {"profile": deepcopy(profile), "boundary": boundary, "audit_ids": []})
            if boundary > selected["boundary"]:
                selected.update(boundary=boundary, audit_ids=[])
            if boundary == selected["boundary"]:
                selected["audit_ids"].append(run["id"])
    return {"latest_by_profile": [{**latest[key], "audit_ids": sorted(latest[key]["audit_ids"])} for key in sorted(latest)],
        "recurrence_claims": [item["key"] for run in runs for item in run["findings"]
            if item["history"]["delta"] in {"unchanged", "improved", "regressed"}],
        "resolution_claims": [item["key"] for run in runs for item in run["findings"] if item["history"]["delta"] == "resolved"],
        "comparison": "explicit-source-history-only-no-disappearance-inference"}


def evidence(runs):
    return {"state": "supplied" if runs else "unavailable", "record_count": len(runs),
        "canonical_inputs_sha256": digest([run["source"]["input"]["canonical_input_sha256"] for run in runs]),
        "current_revision_run_count": sum(run["revision_status"] == "matched" for run in runs),
        "other_revision_run_count": sum(run["revision_status"] == "different" for run in runs)}


def _run(value, *, repository, represented_commit, as_of, maximum_age, native, registry, allowed):
    closed(value, {"id", "scope", "profiles", "started_at", "completed_at", "completion", "revision_status", "freshness",
        "source", "findings", "candidate_issues", "prior_audits", "producer", "limitations", "command_states"})
    native.identifier(value["id"])
    scope = closed(value["scope"], {"kind", "repositories", "include", "exclude", "inspected", "uninspected"})
    require(scope["kind"] in {"repository", "organization"} and isinstance(scope["repositories"], list)
            and 1 <= len(scope["repositories"]) <= 128)
    represented = {}
    for item in scope["repositories"]:
        closed(item, {"full_name", "revision", "visibility"})
        require(item["visibility"] == "public" and item["full_name"] in allowed and item["full_name"] not in represented
                and isinstance(item["revision"], str) and shared.base.SHA.fullmatch(item["revision"]))
        represented[item["full_name"]] = item["revision"]
    require(repository in represented and [item["full_name"] for item in scope["repositories"]] == sorted(represented))
    require(scope["kind"] != "repository" or len(represented) == 1)
    for name in ("include", "exclude", "inspected", "uninspected"):
        native.strings(scope[name], 256, nonempty=name == "include")
    require(value["profiles"] == native.resolve_profiles(value["profiles"]["requested"], registry))
    started = instant(value["started_at"])
    completed = instant(value["completed_at"]) if value["completed_at"] is not None else None
    require(started <= as_of and (completed is None or started <= completed <= as_of))
    completion = closed(value["completion"], {"state", "reason", "continuation", "profiles"})
    require(completion["state"] == native.completion_state(completion["profiles"]))
    require(completion["state"] == "unknown" or completed is not None)
    require(completion["state"] != "complete" or not scope["uninspected"])
    selected = {item["id"]: item for item in value["profiles"]["resolved"]}
    require([item["profile"]["id"] for item in completion["profiles"]] == sorted(selected))
    for item in completion["profiles"]:
        closed(item, {"profile", "state", "reason"})
        require(item["profile"] == selected[item["profile"]["id"]])
        native.text(item["reason"], 2048, nullable=item["state"] == "complete")
    native.text(completion["reason"], nullable=completion["state"] == "complete")
    native.strings(completion["continuation"], 64)
    expected_freshness = "unknown" if completed is None else "stale" if (as_of - completed).total_seconds() > maximum_age else "current"
    require(value["freshness"] == expected_freshness and value["revision_status"] == (
        "matched" if represented[repository] == represented_commit else "different"))
    source = closed(value["source"], {"report_schema", "contract_version", "owner_report_sha256", "canonical_report", "input"})
    require(source["report_schema"] == native.SCHEMA and source["contract_version"] == native.VERSION
            and isinstance(source["owner_report_sha256"], str) and shared.base.HASH.fullmatch(source["owner_report_sha256"]))
    artifact = closed(source["canonical_report"], {"path", "uri", "sha256"})
    native.relative(artifact["path"])
    require(isinstance(artifact["sha256"], str) and shared.base.HASH.fullmatch(artifact["sha256"]))
    if artifact["uri"] is not None:
        shared.public_url(artifact["uri"], allowed)
    input_metadata(source["input"], allowed)
    require(isinstance(value["findings"], list) and len(value["findings"]) <= shared.MAX_FINDINGS)
    keys = []
    finding_ids = []
    for item in value["findings"]:
        closed(item, {"id", "key", "repository", "title", "classification", "nature", "severity", "confidence", "status", "area",
            "effort", "impact", "source_profile", "evidence_classification", "evidence", "history", "history_evidence", "missing_evidence"})
        native.identifier(item["id"], native.FINDING_ID)
        require(item["repository"] == repository and item["key"] == f"{repository}:{value['id']}:{item['id']}")
        native.text(item["title"], 512); native.text(item["area"], 512)
        require(item["classification"] in native.CLASSIFICATIONS and item["nature"] in native.NATURES
            and item["severity"] in native.SEVERITIES and item["confidence"] in {"high", "medium", "low"}
            and item["status"] in native.STATUSES and item["effort"] in {"small", "medium", "large", "unknown"}
            and item["impact"] in {"low", "medium", "high", "critical"} and item["evidence_classification"] in native.LABELS)
        require(item["source_profile"] == selected.get(item["source_profile"]["id"]))
        profile_state = next(row["state"] for row in completion["profiles"] if row["profile"] == item["source_profile"])
        require(profile_state != "not_applicable")
        native.strings(item["missing_evidence"], 64, item_maximum=2048)
        require(not (item["confidence"] == "low" or item["evidence_classification"] in {"recommended", "unverified"})
                or bool(item["missing_evidence"]))
        definition = next(profile for profile in registry["profiles"] if profile["id"] == item["source_profile"]["id"])
        require(item["nature"] in definition["finding_natures"])
        require(isinstance(item["evidence"], list) and len(item["evidence"]) <= 64)
        require(isinstance(item["history_evidence"], list) and len(item["history_evidence"]) <= 64)
        evidence_ids, history_ids = [], []
        for ref in [*item["evidence"], *item["history_evidence"]]:
            closed(ref, {"id", "classification", "kind", "repository", "revision", "uri", "path", "sha256", "observed_at"})
            native.identifier(ref["id"], native.EVIDENCE_ID)
            require(ref["classification"] in native.LABELS and ref["kind"] in {"source", "command", "artifact", "provider", "policy", "prior-audit", "manual"})
            require(ref["repository"] is None or ref["repository"] in allowed)
            require(ref["revision"] is None or isinstance(ref["revision"], str) and shared.base.SHA.fullmatch(ref["revision"]))
            require(ref["revision"] is None or ref["repository"] is not None)
            require(ref["kind"] != "source" or ref["repository"] is not None and ref["revision"] is not None)
            require(ref["sha256"] is None or isinstance(ref["sha256"], str) and shared.base.HASH.fullmatch(ref["sha256"]))
            if ref["uri"] is not None:
                shared.public_url(ref["uri"], allowed)
            if ref["path"] is not None:
                native.relative(ref["path"])
            require(ref["observed_at"] is None or instant(ref["observed_at"]) <= (completed or started))
            require(ref["classification"] != "observed" or (
                (ref["uri"] is not None or ref["path"] is not None) and ref["observed_at"] is not None))
        evidence_ids = [ref["id"] for ref in item["evidence"]]
        history_ids = [ref["id"] for ref in item["history_evidence"]]
        require(evidence_ids == sorted(set(evidence_ids)))
        require(history_ids == sorted(set(history_ids)))
        observed = [ref for ref in item["evidence"] if ref["classification"] == "observed"]
        if item["status"] == "confirmed" or item["classification"] == "confirmed-defect":
            require(item["evidence_classification"] == "observed" and bool(observed))
        if item["classification"] == "confirmed-defect":
            require(item["nature"] in {"defect", "policy-conformance"} and item["status"] == "confirmed")
        if item["nature"] in {"opportunity", "experimental-opportunity"}:
            require(item["classification"] in {"optimization-opportunity", "future-enhancement", "needs-human-clarification"}
                    and item["status"] in {"probable", "needs-validation", "needs-clarification"})
        if item["classification"] in {"optimization-opportunity", "future-enhancement"}:
            require(item["nature"] in {"opportunity", "experimental-opportunity"})
        if item["classification"] == "probable-issue":
            require(item["nature"] in {"defect", "risk", "policy-conformance"}
                    and item["status"] in {"probable", "needs-validation"})
        if item["classification"] == "intentional-trade-off":
            require(item["nature"] == "risk" and item["status"] == "intentional-trade-off")
        require((item["nature"] == "experimental-opportunity") == (definition["stability"] == "experimental"))
        if item["nature"] == "experimental-opportunity":
            require(item["severity"] == "informational" and item["evidence_classification"] in {"recommended", "unverified"})
        if item["nature"] == "policy-conformance":
            require(any(ref["kind"] == "policy" for ref in observed))
        require((item["classification"] == "positive-observation") == (item["nature"] == "positive-observation"))
        history = closed(item["history"], {"delta", "prior_audit_id", "prior_finding_id", "evidence_classification", "evidence_refs"})
        require(history["delta"] in native.DELTAS and history["evidence_classification"] in native.LABELS)
        native.strings(history["evidence_refs"], 64)
        require(sorted(history["evidence_refs"]) == history_ids)
        if history["delta"] == "not-compared":
            require(history["prior_audit_id"] is None and history["prior_finding_id"] is None
                and history["evidence_classification"] == "unverified" and not history["evidence_refs"])
        elif history["delta"] in {"unchanged", "improved", "regressed", "resolved"}:
            require(history["prior_audit_id"] is not None and history["prior_finding_id"] is not None and bool(history["evidence_refs"]))
        if history["prior_finding_id"] is not None:
            native.identifier(history["prior_finding_id"], native.FINDING_ID)
        if history["delta"] == "resolved":
            require(history["evidence_classification"] == "observed"
                    and any(ref["classification"] == "observed" for ref in item["history_evidence"]))
        keys.append(item["key"]); finding_ids.append(item["id"])
    require(keys == sorted(set(keys)))
    require(isinstance(value["candidate_issues"], list) and len(value["candidate_issues"]) <= 256)
    candidate_ids = []
    for item in value["candidate_issues"]:
        closed(item, {"id", "status", "priority", "finding_ids", "projection", "materialization"})
        require(isinstance(item["id"], str) and __import__("re").fullmatch(r"CANDIDATE-[0-9]{3}", item["id"])
            and item["status"] == "suggested" and item["priority"] in {"low", "medium", "high", "critical"}
            and item["projection"] in {"complete", "repository-subset"} and item["materialization"] == "unavailable")
        require(isinstance(item["finding_ids"], list) and item["finding_ids"] and set(item["finding_ids"]) <= set(finding_ids))
        candidate_ids.append(item["id"])
    require(candidate_ids == sorted(set(candidate_ids)))
    require(isinstance(value["prior_audits"], list) and len(value["prior_audits"]) <= 128)
    prior_ids = []
    for item in value["prior_audits"]:
        closed(item, {"audit_id", "uri", "sha256", "relationship", "evidence_classification"})
        native.identifier(item["audit_id"])
        require(item["audit_id"] != value["id"] and item["relationship"] in {"predecessor", "related"}
                and item["evidence_classification"] in native.LABELS and isinstance(item["sha256"], str)
                and shared.base.HASH.fullmatch(item["sha256"]))
        if item["uri"] is not None:
            shared.public_url(item["uri"], allowed)
        prior_ids.append(item["audit_id"])
    require(prior_ids == sorted(set(prior_ids)))
    for item in value["findings"]:
        require(item["history"]["prior_audit_id"] is None or item["history"]["prior_audit_id"] in prior_ids)
        if item["history"]["delta"] == "resolved":
            prior = next(row for row in value["prior_audits"] if row["audit_id"] == item["history"]["prior_audit_id"])
            proof = [row for row in item["history_evidence"] if row["classification"] == "observed"]
            require(prior["evidence_classification"] == "observed" and any(
                ref["kind"] == "prior-audit" and ref["sha256"] == prior["sha256"] and (
                    ref["uri"] == prior["uri"] if prior["uri"] is not None else ref["path"] is not None) for ref in proof)
                and any(ref["kind"] in {"source", "command", "artifact", "provider", "manual"}
                    and ref["repository"] == repository and ref["revision"] == represented[repository] for ref in proof))
    producer = closed(value["producer"], {"name", "version", "uri"})
    native.text(producer["name"], 256); native.text(producer["version"], 128)
    if producer["uri"] is not None:
        shared.public_url(producer["uri"], allowed)
    native.strings(value["limitations"], 128, item_maximum=2048)
    closed(value["command_states"], {"success", "failure", "not_run", "unavailable", "unsupported"})
    require(all(type(item) is int and item >= 0 for item in value["command_states"].values()))
    require(sum(value["command_states"].values()) <= 256)


def validate(value, *, admission_root=DEFAULT_ROOT):
    require(isinstance(value, dict) and value.get("visibility") == "public")
    shared.base.unambiguous(value)
    native, registry, source_owner = owners(admission_root)
    if value.get("schema") == FLEET_SCHEMA:
        return validate_fleet(value, admission_root=admission_root)
    closed(value, {"schema", "contract_version", "visibility", "repository", "represented_commit", "as_of", "admission",
        "source_owner", "freshness_policy", "runs", "summary", "queries", "campaigns", "evidence", "digest"})
    require(value["schema"] == SCHEMA and value["contract_version"] == VERSION)
    repository = closed(value["repository"], {"full_name", "repository_id", "visibility", "source_url"})
    row, proof, allowed = admission(repository["full_name"], admission_root=admission_root)
    require(shared.ownership_preflight(value, allowed))
    native._privacy(value, True)
    require(repository == shared.repository_identity(row) and value["admission"] == proof and value["source_owner"] == source_owner)
    require(isinstance(value["represented_commit"], str) and shared.base.SHA.fullmatch(value["represented_commit"]))
    evaluated = instant(value["as_of"])
    policy = closed(value["freshness_policy"], {"maximum_age_seconds", "anchor"})
    require(type(policy["maximum_age_seconds"]) is int and 1 <= policy["maximum_age_seconds"] <= MAX_AGE
            and policy["anchor"] == "original-completed-at")
    require(isinstance(value["runs"], list) and len(value["runs"]) <= shared.MAX_RECORDS)
    identifiers = []
    for run in value["runs"]:
        _run(run, repository=row["full_name"], represented_commit=value["represented_commit"], as_of=evaluated,
            maximum_age=policy["maximum_age_seconds"], native=native, registry=registry, allowed=allowed)
        identifiers.append(run["id"])
    require(identifiers == sorted(set(identifiers)))
    require(sum(len(run["findings"]) for run in value["runs"]) <= shared.MAX_FINDINGS)
    require(value["summary"] == summary(value["runs"], native) and value["queries"] == queries(value["runs"])
            and value["evidence"] == evidence(value["runs"]))
    require(value["campaigns"] == {"state": "unavailable", "references": [], "reason": "No compatible orchestration manifests supplied."})
    shared.verify_seal(value)
    return value


def validate_fleet(value, *, admission_root=DEFAULT_ROOT):
    closed(value, {"schema", "contract_version", "visibility", "as_of", "admission", "repositories", "summary", "evidence", "digest"})
    require(value["schema"] == FLEET_SCHEMA and value["contract_version"] == VERSION and value["visibility"] == "public")
    instant(value["as_of"])
    rows, _allowed = shared.public_catalog(admission_root)
    require(isinstance(value["repositories"], list) and len(value["repositories"]) <= shared.MAX_TARGETS)
    names, runs = [], []
    for item in value["repositories"]:
        validate(item, admission_root=admission_root)
        require(item["as_of"] == value["as_of"])
        names.append(item["repository"]["full_name"])
        runs.extend(item["runs"])
    require(names == sorted(set(names)) and value["admission"] == shared.fleet_admission(names, rows, admission_root))
    native, _registry, _owner = owners(admission_root)
    require(value["summary"] == summary(runs, native))
    require(value["evidence"] == {"state": "supplied" if any(item["runs"] for item in value["repositories"]) else "unavailable",
        "repository_count": len(names), "with_evidence_count": sum(bool(item["runs"]) for item in value["repositories"]),
        "canonical_inputs_sha256": digest([item["digest"] for item in value["repositories"]])})
    shared.verify_seal(value)
    return value
