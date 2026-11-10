#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT
"""Portable closed audit profile/report contract; no collection or mutation.

Structural admission and authored evidence labels never establish that a command,
condition, policy violation, resolution, approval or host execution actually ran.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import PurePosixPath
import re
from urllib.parse import urlsplit

SCHEMA = "aether.repository-audit-report/v1"
REGISTRY_SCHEMA = "aether.audit-profile-registry/v1"
VERSION = "1.0.0"
MAX_BYTES = 8 * 1024 * 1024
MAX_FINDINGS = 1000
MAX_EVIDENCE = 10000
LABELS = ("observed", "inferred", "recommended", "unverified")
COMPLETION_STATES = ("complete", "partial", "blocked", "failed", "unsupported", "not_applicable", "unknown")
CLASSIFICATIONS = ("confirmed-defect", "probable-issue", "architectural-concern", "maintainability-risk",
    "optimization-opportunity", "documentation-gap", "future-enhancement", "intentional-trade-off",
    "needs-human-clarification", "positive-observation")
NATURES = ("defect", "opportunity", "experimental-opportunity", "policy-conformance", "risk", "clarification", "positive-observation")
SEVERITIES = ("critical", "high", "medium", "low", "informational")
STATUSES = ("confirmed", "probable", "needs-validation", "intentional-trade-off", "needs-clarification", "not-applicable")
DELTAS = ("new", "unchanged", "improved", "regressed", "resolved", "unverified", "not-compared")
HASH = re.compile(r"[0-9a-f]{64}")
SHA = re.compile(r"[0-9a-f]{40}")
REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
ID = re.compile(r"[a-z0-9][a-z0-9._:-]{0,127}")
PROFILE_ID = re.compile(r"[a-z][a-z0-9-]{0,63}")
SEMVER = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
FINDING_ID = re.compile(r"AUDIT-[0-9]{3}")
EVIDENCE_ID = re.compile(r"EVIDENCE-[0-9]{1,5}")
SENSITIVE = re.compile(r"(?i)(?:github_pat_|gh[pousr]_|\b(?:password|token|secret)\s*[:=]\s*[^\s]+|[\w.+-]+@[\w.-]+\.[a-z]{2,}|/(?:home|Users|workspace|tmp)/|[A-Za-z]:\\)")


class AuditContractError(ValueError):
    """A bounded contract failure; never includes source text or credentials."""


def require(condition):
    if not condition:
        raise AuditContractError("Audit profile/report input is incompatible")


def parse(content):
    """Read a bounded JSON object without duplicate keys or nonfinite numbers."""
    try:
        require(isinstance(content, (str, bytes)))
        raw = content.encode("utf-8") if isinstance(content, str) else content
        require(0 < len(raw) <= MAX_BYTES)
        def unique(pairs):
            value = {}
            for key, item in pairs:
                require(key not in value)
                value[key] = item
            return value
        value = json.loads(raw, object_pairs_hook=unique, parse_constant=lambda _value: require(False))
        require(isinstance(value, dict))
        return value
    except (ValueError, UnicodeError, TypeError, RecursionError):
        raise AuditContractError("Audit JSON input is incompatible") from None


def canonical_bytes(value):
    try:
        content = (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
        require(len(content) <= MAX_BYTES)
        return content
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise AuditContractError("Audit canonical encoding is incompatible") from None


def digest(value):
    """Canonical semantic JSON digest, distinct from original file/ZIP hashes."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def closed(value, keys):
    require(isinstance(value, dict) and set(value) == set(keys))
    return value


def text(value, maximum=4096, *, nullable=False):
    if value is None and nullable:
        return value
    require(isinstance(value, str) and 0 < len(value) <= maximum
        and not any(ord(char) < 32 and char not in "\n\t" or ord(char) == 127 for char in value))
    return value


def strings(value, maximum=256, *, item_maximum=1024, nonempty=False):
    require(isinstance(value, list) and int(nonempty) <= len(value) <= maximum)
    for item in value:
        text(item, item_maximum)
    require(len(value) == len(set(value)))
    return value


def instant(value):
    require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value))
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        raise AuditContractError("Audit timestamp is incompatible") from None


def identifier(value, pattern=ID):
    require(isinstance(value, str) and pattern.fullmatch(value))
    return value


def repository(value):
    identifier(value, REPOSITORY)
    require(all(part not in {".", ".."} for part in value.split("/")))
    return value


def relative(value):
    text(value, 512)
    path = PurePosixPath(value)
    require(not path.is_absolute() and path.as_posix() == value and "\\" not in value
        and all(part not in {"", ".", "..", ".git"} for part in value.split("/")))
    return value


def uri(value, *, nullable=False):
    if value is None and nullable:
        return value
    text(value, 2048)
    try:
        parsed = urlsplit(value)
        require(parsed.scheme == "https" and bool(parsed.hostname) and parsed.username is None
            and parsed.password is None and parsed.port in {None, 443} and not parsed.query
            and not any(char.isspace() for char in value) and "\\" not in value and "%" not in value
            and (not parsed.fragment or re.fullmatch(r"[A-Za-z0-9._:-]+", parsed.fragment))
            and not any(part in {".", ".."} for part in parsed.path.split("/")))
    except ValueError:
        raise AuditContractError("Audit evidence URI is incompatible") from None
    return value


def profile_ref(value):
    closed(value, ("id", "version"))
    identifier(value["id"], PROFILE_ID); identifier(value["version"], SEMVER)
    return value


def validate_registry(value):
    closed(value, ("schema", "contract_version", "status", "profiles"))
    require(value["schema"] == REGISTRY_SCHEMA and value["contract_version"] == VERSION and value["status"] == "draft")
    require(isinstance(value["profiles"], list) and 1 <= len(value["profiles"]) <= 128)
    profiles = {}
    for item in value["profiles"]:
        closed(item, ("id", "version", "kind", "stability", "title", "focus", "applicability", "required_evidence", "exclusions", "includes", "finding_natures"))
        identifier(item["id"], PROFILE_ID); identifier(item["version"], SEMVER)
        require(item["id"] not in profiles and item["kind"] in {"leaf", "composite"}
            and item["stability"] in {"stable", "experimental"})
        text(item["title"], 256); text(item["applicability"], 2048)
        strings(item["focus"], 64, item_maximum=128)
        strings(item["required_evidence"], 32, item_maximum=128, nonempty=True)
        strings(item["exclusions"], 32, item_maximum=512)
        strings(item["finding_natures"], len(NATURES), item_maximum=64)
        require(set(item["finding_natures"]) <= set(NATURES) and isinstance(item["includes"], list) and len(item["includes"]) <= 128)
        for ref in item["includes"]:
            profile_ref(ref)
        require(len({ref["id"] for ref in item["includes"]}) == len(item["includes"]))
        require((item["kind"] == "leaf" and not item["includes"] and bool(item["finding_natures"]))
            or (item["kind"] == "composite" and bool(item["includes"]) and not item["finding_natures"]))
        if item["stability"] == "experimental" and item["kind"] == "leaf":
            require(item["finding_natures"] == ["experimental-opportunity"])
        elif item["kind"] == "leaf":
            require("experimental-opportunity" not in item["finding_natures"])
        profiles[item["id"]] = item
    require([item["id"] for item in value["profiles"]] == sorted(profiles))
    visited = set()
    def visit(name, seen):
        require(name not in seen)
        if name in visited:
            return
        parent = profiles[name]
        for ref in parent["includes"]:
            child = profiles.get(ref["id"])
            require(child is not None and child["version"] == ref["version"]
                and (parent["stability"] == "experimental" or child["stability"] == "stable"))
            visit(child["id"], seen | {name})
        visited.add(name)
    for name in profiles:
        visit(name, set())
    require({"feature-opportunity", "experimental-opportunity", "implementation-quality", "contract-drift", "holistic"} <= set(profiles))
    holistic = profiles["holistic"]
    require(holistic["kind"] == "composite" and holistic["stability"] == "stable")
    leaves = set()
    collected = set()
    def collect(name):
        if name in collected:
            return
        collected.add(name)
        item = profiles[name]
        if item["kind"] == "leaf":
            leaves.add(name)
        else:
            for child in item["includes"]:
                collect(child["id"])
    collect("holistic")
    require(leaves == {name for name, item in profiles.items() if item["kind"] == "leaf" and item["stability"] == "stable"})
    return value


def resolve_profiles(requested, registry):
    """Resolve exact leaf profiles deterministically; never infer applicability."""
    validate_registry(registry)
    require(isinstance(requested, list) and 1 <= len(requested) <= 128)
    profiles = {item["id"]: item for item in registry["profiles"]}
    chosen = {}
    for value in requested:
        ref = {"id": value, "version": profiles[value]["version"]} if isinstance(value, str) and value in profiles else value
        profile_ref(ref)
        require(ref["id"] in profiles and ref["version"] == profiles[ref["id"]]["version"] and ref["id"] not in chosen)
        chosen[ref["id"]] = dict(ref)
    resolved = {}
    included = set()
    def include(ref):
        if ref["id"] in included:
            return
        included.add(ref["id"])
        item = profiles[ref["id"]]
        if item["kind"] == "leaf":
            resolved[item["id"]] = dict(ref)
        else:
            for child in item["includes"]:
                include(child)
    for ref in chosen.values():
        include(ref)
    return {"registry_version": registry["contract_version"], "registry_sha256": digest(registry),
        "requested": [chosen[name] for name in sorted(chosen)], "resolved": [resolved[name] for name in sorted(resolved)]}


def completion_state(profile_states):
    """Scope completion only; complete never means pass, conformant or ratified."""
    states = {item["state"] for item in profile_states}
    require(bool(states) and states <= set(COMPLETION_STATES))
    if "failed" in states:
        return "failed"
    applicable = states - {"not_applicable"}
    if not applicable:
        return "not_applicable"
    if len(applicable) == 1:
        return next(iter(applicable))
    return "partial"


def _refs(value, evidence, *, nonempty=False):
    strings(value, 64, item_maximum=32, nonempty=nonempty)
    require(set(value) <= set(evidence))


def _privacy(value, public):
    if isinstance(value, str):
        require(not public or not SENSITIVE.search(value))
    elif isinstance(value, list):
        for item in value:
            _privacy(item, public)
    elif isinstance(value, dict):
        for item in value.values():
            _privacy(item, public)


def referenced_repositories(report):
    """Extract declared public structured owners before any report ID/hash use.

    This performs no roster lookup or provider authentication. A consumer must
    admit every returned identity through its actual public owner roster before
    invoking report_summary or hashing report bytes. Narrative text remains
    untrusted and requires the consumer's independent namespace/privacy policy.
    """
    require(isinstance(report, dict) and report.get("visibility") == "public")
    scope = report.get("scope")
    require(isinstance(scope, dict) and isinstance(scope.get("repositories"), list)
        and len(scope["repositories"]) <= 128)
    owners = set()
    for item in scope["repositories"]:
        require(isinstance(item, dict) and item.get("visibility") == "public")
        owners.add(repository(item.get("full_name")))
    findings, evidence = report.get("findings"), report.get("evidence")
    require(isinstance(findings, list) and len(findings) <= MAX_FINDINGS
        and isinstance(evidence, list) and len(evidence) <= MAX_EVIDENCE)
    for item in findings:
        require(isinstance(item, dict) and item.get("visibility") == "public")
        owners.add(repository(item.get("repository")))
    urls = []
    for item in evidence:
        require(isinstance(item, dict))
        if item.get("repository") is not None:
            owners.add(repository(item["repository"]))
        urls.append(item.get("uri"))
    prior = report.get("prior_audits")
    require(isinstance(prior, list) and len(prior) <= 128)
    for item in prior:
        require(isinstance(item, dict)); urls.append(item.get("uri"))
    canonical = report.get("canonical_report")
    provenance = report.get("provenance")
    require(isinstance(canonical, dict) and isinstance(provenance, dict)
        and isinstance(provenance.get("producer"), dict))
    urls.extend((canonical.get("uri"), provenance["producer"].get("uri")))
    for value in urls:
        if value is None:
            continue
        uri(value)
        parsed = urlsplit(value)
        if parsed.hostname not in {"github.com", "api.github.com", "raw.githubusercontent.com"}:
            continue
        parts = parsed.path.strip("/").split("/")
        if parsed.hostname == "api.github.com":
            require(len(parts) >= 3 and parts[0] == "repos")
            parts = parts[1:]
        require(len(parts) >= 2)
        owners.add(repository("/".join(parts[:2])))
    return sorted(owners)


def validate_report(value, registry):
    """Validate a self-contained authored sidecar, not the truth of its claims."""
    closed(value, ("schema", "contract_version", "audit_id", "visibility", "scope", "profiles", "started_at", "completed_at",
        "completion", "findings", "evidence", "positive_observations", "candidate_issues", "prior_audits", "provenance", "canonical_report"))
    require(value["schema"] == SCHEMA and value["contract_version"] == VERSION and value["visibility"] in {"public", "private", "internal"})
    scope = closed(value["scope"], ("kind", "repositories", "include", "exclude", "inspected", "uninspected"))
    require(scope["kind"] in {"repository", "organization"} and isinstance(scope["repositories"], list)
        and 1 <= len(scope["repositories"]) <= 128)
    targets = {}
    # Declared public visibility precedes audit/finding identities and hashes.
    # Authenticating roster membership remains the consumer admission boundary.
    for target in scope["repositories"]:
        closed(target, ("full_name", "revision", "visibility"))
        require(target["visibility"] in {"public", "private", "internal"}
            and (value["visibility"] != "public" or target["visibility"] == "public"))
        repository(target["full_name"]); identifier(target["revision"], SHA)
        require(target["full_name"] not in targets)
        targets[target["full_name"]] = target["revision"]
    require(scope["kind"] != "repository" or len(targets) == 1)
    require([target["full_name"] for target in scope["repositories"]] == sorted(targets))
    identifier(value["audit_id"])
    for key in ("include", "exclude", "inspected", "uninspected"):
        strings(scope[key], 256, item_maximum=1024, nonempty=key == "include")
    profiles = closed(value["profiles"], ("registry_version", "registry_sha256", "requested", "resolved"))
    require(profiles == resolve_profiles(profiles["requested"], registry))
    selected = {ref["id"]: ref for ref in profiles["resolved"]}
    definitions = {item["id"]: item for item in registry["profiles"]}
    started = instant(value["started_at"])
    if value["completed_at"] is not None:
        require(instant(value["completed_at"]) >= started)
    completion = closed(value["completion"], ("state", "reason", "continuation", "profiles"))
    require(completion["state"] in COMPLETION_STATES and isinstance(completion["profiles"], list)
        and len(completion["profiles"]) == len(selected))
    profile_ids = []
    for item in completion["profiles"]:
        closed(item, ("profile", "state", "reason")); profile_ref(item["profile"])
        require(item["profile"] == selected.get(item["profile"]["id"]) and item["state"] in COMPLETION_STATES)
        text(item["reason"], 2048, nullable=item["state"] == "complete")
        profile_ids.append(item["profile"]["id"])
    require(profile_ids == sorted(selected) and completion["state"] == completion_state(completion["profiles"]))
    profile_states = {item["profile"]["id"]: item["state"] for item in completion["profiles"]}
    text(completion["reason"], 4096, nullable=completion["state"] == "complete")
    strings(completion["continuation"], 64, item_maximum=1024)
    require(completion["state"] == "unknown" or value["completed_at"] is not None)
    require(completion["state"] != "complete" or not scope["uninspected"])
    evidence = {}
    require(isinstance(value["evidence"], list) and len(value["evidence"]) <= MAX_EVIDENCE)
    for item in value["evidence"]:
        closed(item, ("id", "classification", "kind", "repository", "revision", "uri", "path", "sha256", "observed_at", "summary"))
        identifier(item["id"], EVIDENCE_ID)
        require(item["id"] not in evidence and item["classification"] in LABELS
            and item["kind"] in {"source", "command", "artifact", "provider", "policy", "prior-audit", "manual"})
        if item["repository"] is not None:
            repository(item["repository"])
        if item["revision"] is not None:
            identifier(item["revision"], SHA); require(item["repository"] is not None)
        uri(item["uri"], nullable=True)
        if item["path"] is not None:
            relative(item["path"])
        if item["sha256"] is not None:
            identifier(item["sha256"], HASH)
        if item["observed_at"] is not None:
            require(instant(item["observed_at"]) <= (instant(value["completed_at"]) if value["completed_at"] else started))
        if item["classification"] == "observed":
            require((item["uri"] is not None or item["path"] is not None) and item["observed_at"] is not None)
        if item["kind"] == "source":
            require(item["repository"] is not None and item["revision"] is not None)
        text(item["summary"])
        evidence[item["id"]] = item
    prior = {}
    require(isinstance(value["prior_audits"], list) and len(value["prior_audits"]) <= 128)
    for item in value["prior_audits"]:
        closed(item, ("audit_id", "uri", "sha256", "relationship", "evidence_classification"))
        identifier(item["audit_id"]); require(item["audit_id"] != value["audit_id"] and item["audit_id"] not in prior)
        uri(item["uri"], nullable=True); identifier(item["sha256"], HASH)
        require(item["relationship"] in {"predecessor", "related"} and item["evidence_classification"] in LABELS)
        prior[item["audit_id"]] = item
    findings = {}
    require(isinstance(value["findings"], list) and len(value["findings"]) <= MAX_FINDINGS)
    for finding in value["findings"]:
        # Finding visibility is checked before identity or text.
        require(isinstance(finding, dict) and finding.get("visibility") in {"public", "private", "internal"}
            and (value["visibility"] != "public" or finding["visibility"] == "public"))
        closed(finding, ("id", "visibility", "repository", "title", "classification", "nature", "severity", "confidence", "status", "area",
            "effort", "impact", "observation", "why_it_matters", "recommendation", "suggested_validation", "dependencies",
            "evidence_classification", "evidence_refs", "source_profile", "missing_evidence", "history"))
        identifier(finding["id"], FINDING_ID); require(finding["id"] not in findings)
        repository(finding["repository"]); require(finding["repository"] in targets)
        profile_ref(finding["source_profile"])
        require(finding["source_profile"] == selected.get(finding["source_profile"]["id"])
            and profile_states[finding["source_profile"]["id"]] != "not_applicable")
        definition = definitions[finding["source_profile"]["id"]]
        require(finding["classification"] in CLASSIFICATIONS and finding["nature"] in definition["finding_natures"]
            and finding["severity"] in SEVERITIES and finding["confidence"] in {"high", "medium", "low"}
            and finding["status"] in STATUSES and finding["effort"] in {"small", "medium", "large", "unknown"}
            and finding["impact"] in {"low", "medium", "high", "critical"} and finding["evidence_classification"] in LABELS)
        for key in ("title", "area", "observation", "why_it_matters", "recommendation"):
            text(finding[key], 8192 if key in {"observation", "why_it_matters", "recommendation"} else 512)
        for key in ("suggested_validation", "dependencies", "missing_evidence"):
            strings(finding[key], 64, item_maximum=2048)
        _refs(finding["evidence_refs"], evidence)
        if finding["confidence"] == "low" or finding["evidence_classification"] in {"recommended", "unverified"}:
            require(bool(finding["missing_evidence"]))
        observed = [evidence[name] for name in finding["evidence_refs"] if evidence[name]["classification"] == "observed"]
        if finding["status"] == "confirmed" or finding["classification"] == "confirmed-defect":
            require(finding["evidence_classification"] == "observed" and bool(observed))
        if finding["classification"] == "confirmed-defect":
            require(finding["nature"] in {"defect", "policy-conformance"} and finding["status"] == "confirmed")
        if finding["nature"] in {"opportunity", "experimental-opportunity"}:
            require(finding["classification"] in {"optimization-opportunity", "future-enhancement", "needs-human-clarification"}
                and finding["status"] in {"probable", "needs-validation", "needs-clarification"})
        if finding["classification"] in {"optimization-opportunity", "future-enhancement"}:
            require(finding["nature"] in {"opportunity", "experimental-opportunity"})
        if finding["classification"] == "probable-issue":
            require(finding["nature"] in {"defect", "risk", "policy-conformance"}
                and finding["status"] in {"probable", "needs-validation"})
        if finding["classification"] == "intentional-trade-off":
            require(finding["nature"] == "risk" and finding["status"] == "intentional-trade-off")
        require((finding["nature"] == "experimental-opportunity") == (definition["stability"] == "experimental"))
        if finding["nature"] == "experimental-opportunity":
            require(finding["severity"] == "informational" and finding["evidence_classification"] in {"recommended", "unverified"})
        if finding["nature"] == "policy-conformance":
            require(any(item["kind"] == "policy" for item in observed))
        if finding["nature"] == "positive-observation":
            require(finding["classification"] == "positive-observation")
        require((finding["classification"] == "positive-observation") == (finding["nature"] == "positive-observation"))
        history = closed(finding["history"], ("delta", "prior_audit_id", "prior_finding_id", "evidence_classification", "evidence_refs"))
        require(history["delta"] in DELTAS and history["evidence_classification"] in LABELS)
        _refs(history["evidence_refs"], evidence)
        if history["prior_audit_id"] is not None:
            require(history["prior_audit_id"] in prior)
        if history["prior_finding_id"] is not None:
            identifier(history["prior_finding_id"], FINDING_ID); require(history["prior_audit_id"] is not None)
        if history["delta"] in {"unchanged", "improved", "regressed", "resolved"}:
            require(history["prior_audit_id"] is not None and history["prior_finding_id"] is not None and bool(history["evidence_refs"]))
        if history["delta"] == "resolved":
            selected_prior = prior[history["prior_audit_id"]]
            proof = [evidence[name] for name in history["evidence_refs"] if evidence[name]["classification"] == "observed"]
            require(history["evidence_classification"] == "observed"
                and selected_prior["evidence_classification"] == "observed"
                and any(item["kind"] == "prior-audit" and item["sha256"] == selected_prior["sha256"]
                    and (item["uri"] == selected_prior["uri"] if selected_prior["uri"] is not None else item["path"] is not None)
                    for item in proof)
                and any(item["kind"] in {"source", "command", "artifact", "provider", "manual"}
                    and item["repository"] == finding["repository"] and item["revision"] == targets[finding["repository"]]
                    for item in proof))
        if history["delta"] == "not-compared":
            require(history["prior_audit_id"] is None and history["prior_finding_id"] is None
                and history["evidence_classification"] == "unverified" and not history["evidence_refs"])
        findings[finding["id"]] = finding
    require([item["id"] for item in value["findings"]] == sorted(findings))
    require(completion["state"] != "not_applicable" or not findings)
    positives = closed(value["positive_observations"], ("finding_ids", "absence_reason"))
    strings(positives["finding_ids"], MAX_FINDINGS, item_maximum=16)
    require(positives["finding_ids"] == sorted(key for key, finding in findings.items() if finding["nature"] == "positive-observation"))
    text(positives["absence_reason"], 2048, nullable=bool(positives["finding_ids"]))
    require(isinstance(value["candidate_issues"], list) and len(value["candidate_issues"]) <= 256)
    candidates = set()
    for item in value["candidate_issues"]:
        closed(item, ("id", "status", "finding_ids", "priority", "outcome", "acceptance_criteria", "dependencies"))
        require(isinstance(item["id"], str) and re.fullmatch(r"CANDIDATE-[0-9]{3}", item["id"]) and item["id"] not in candidates
            and item["status"] == "suggested" and item["priority"] in {"low", "medium", "high", "critical"})
        strings(item["finding_ids"], 64, item_maximum=16, nonempty=True); require(set(item["finding_ids"]) <= set(findings))
        text(item["outcome"], 4096); strings(item["acceptance_criteria"], 64, item_maximum=2048, nonempty=True)
        strings(item["dependencies"], 64, item_maximum=2048); candidates.add(item["id"])
    provenance = closed(value["provenance"], ("producer", "tools", "commands", "limitations", "privacy", "execution"))
    producer = closed(provenance["producer"], ("name", "version", "uri"))
    text(producer["name"], 256); text(producer["version"], 128); uri(producer["uri"], nullable=True)
    require(provenance["execution"] == "read-only" and isinstance(provenance["tools"], list) and len(provenance["tools"]) <= 128)
    for tool in provenance["tools"]:
        closed(tool, ("name", "version")); text(tool["name"], 128); text(tool["version"], 128, nullable=True)
    strings(provenance["limitations"], 128, item_maximum=2048)
    privacy = closed(provenance["privacy"], ("contains_sensitive_data", "redactions"))
    require(privacy["contains_sensitive_data"] is False); strings(privacy["redactions"], 64, item_maximum=256)
    require(isinstance(provenance["commands"], list) and len(provenance["commands"]) <= 256)
    for command in provenance["commands"]:
        closed(command, ("command", "state", "exit_code", "evidence_refs", "reason"))
        text(command["command"], 2048)
        require(command["state"] in {"success", "failure", "not_run", "unavailable", "unsupported"})
        _refs(command["evidence_refs"], evidence)
        require(command["exit_code"] is None or type(command["exit_code"]) is int and -255 <= command["exit_code"] <= 255)
        text(command["reason"], 2048, nullable=command["state"] == "success")
        if command["state"] in {"success", "failure"}:
            require(any(evidence[name]["classification"] == "observed"
                and evidence[name]["kind"] in {"command", "artifact", "provider", "manual"}
                for name in command["evidence_refs"]))
        if command["state"] == "success":
            require(command["exit_code"] == 0 and bool(command["evidence_refs"]))
        elif command["state"] in {"not_run", "unavailable", "unsupported"}:
            require(command["exit_code"] is None)
        else:
            require(type(command["exit_code"]) is int and command["exit_code"] != 0)
    report = closed(value["canonical_report"], ("path", "uri", "sha256"))
    relative(report["path"]); require(re.fullmatch(r"audits/[A-Za-z0-9][A-Za-z0-9._-]*-[0-9]{8}T[0-9]{6}Z\.md", report["path"]))
    try:
        datetime.strptime(report["path"][-19:-3], "%Y%m%dT%H%M%SZ")
    except ValueError:
        raise AuditContractError("Audit report filename timestamp is incompatible") from None
    uri(report["uri"], nullable=True); identifier(report["sha256"], HASH)
    _privacy(value, True)
    canonical_bytes(value)
    return value


def report_summary(report, registry):
    """Return typed manifest metadata only, without observations or raw evidence."""
    validate_report(report, registry)
    return {"schema": SCHEMA, "contract_version": VERSION, "audit_id": report["audit_id"],
        "visibility": report["visibility"], "scope": {"kind": report["scope"]["kind"], "repositories": report["scope"]["repositories"]},
        "profiles": report["profiles"], "started_at": report["started_at"], "completed_at": report["completed_at"],
        "completion": {"state": report["completion"]["state"],
            "profiles": [{"profile": item["profile"], "state": item["state"]} for item in report["completion"]["profiles"]]},
        "findings": [{key: finding[key] for key in ("id", "repository", "visibility", "classification", "nature", "severity",
            "confidence", "status", "effort", "impact", "source_profile", "evidence_classification", "history")}
            for finding in report["findings"]], "canonical_report": report["canonical_report"], "report_sha256": digest(report)}
