#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Pure proposed architecture-coherence governance admission and evaluation.

No network, checkout inspection, provider requests, clock reads, decision writes
or AI assessment occur here. Callers supply authenticated public admission and
explicitly sourced material-change observations. Validation checks source shape
and bindings; it cannot establish that a declaration really came from a human.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from urllib.parse import urlsplit

SCHEMA = "egohygiene.architecture-coherence-governance/v1"
CHANGE_SCHEMA = "egohygiene.architecture-coherence-material-change/v1"
VERSION = "1.0.0-alpha.1"
POLICY = "egohygiene.architecture-coherence-policy/v1"
APPLICABILITY = ("unknown", "required", "recommended", "optional", "not-applicable", "deferred")
PROGRESS = ("not-started", "due", "in-progress", "complete")
DISPOSITIONS = ("ratified", "ratified-with-notes", "revision-required", "rejected", "deferred", "not-applicable")
MATERIAL_KINDS = ("architecture-milestone", "ownership-change", "accepted-adr-topology-change",
    "cross-repository-dependency", "persistence-boundary", "trust-boundary", "runtime-replacement",
    "repository-split-merge-extraction", "organization-architecture-change", "audit-architecture-drift",
    "material-architecture-document-change", "explicit-human-invalidation")
RECOMMENDED_KINDS = ("repeated-ownership-confusion", "maintainer-request")
NONMATERIAL_KINDS = ("routine-implementation",)
REPOSITORY = re.compile(r"egohygiene/(?:\.github|[a-z0-9][a-z0-9.-]*)")
SHA = re.compile(r"[0-9a-f]{40}")
HASH = re.compile(r"[0-9a-f]{64}")
SENSITIVE = re.compile(r"(?:github_pat_|gh[pousr]_|(?:token|password|secret)\s*[:=]|[\w.+-]+@[\w.-]+\.[a-z]{2,}|/(?:home|Users|workspace|tmp)/|[A-Za-z]:\\|\\\\)", re.I)


class CoherenceError(ValueError):
    """Closed diagnostic: rejected identities and input prose never escape."""


class TrustedHumanEvidence:
    """Explicit immutable context supplied by a trusted human-source adapter.

    Construct only AFTER independently verifying authentic human provenance and
    the exact statement. This type performs no such verification. It has no JSON
    decoder: review JSON, AI output, merge events and actor labels cannot create
    trusted context. capture_sha256 stays operational and is never published.
    """

    __slots__ = ("statement_sha256", "capture_sha256")

    def __init__(self, statement_sha256, capture_sha256):
        require(isinstance(statement_sha256, str) and HASH.fullmatch(statement_sha256)
            and isinstance(capture_sha256, str) and HASH.fullmatch(capture_sha256))
        object.__setattr__(self, "statement_sha256", statement_sha256)
        object.__setattr__(self, "capture_sha256", capture_sha256)

    def __setattr__(self, name, value):
        raise AttributeError("Human evidence context is immutable")


def require(condition):
    if not condition:
        raise CoherenceError("Architecture coherence governance is incompatible")


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def plain(value):
    require(isinstance(value, dict) and not getattr(value, "duplicate_keys", set()))
    return value


def closed(value, keys):
    require(set(plain(value)) == set(keys))
    return value


def unambiguous(value):
    if isinstance(value, dict):
        plain(value)
        for item in value.values():
            unambiguous(item)
    elif isinstance(value, list):
        for item in value:
            unambiguous(item)


def text(value, maximum=2048):
    require(isinstance(value, str) and 0 < len(value) <= maximum
        and not any(ord(char) < 32 or ord(char) == 127 or 0xD800 <= ord(char) <= 0xDFFF for char in value)
        and not SENSITIVE.search(value))
    return value


def instant(value):
    require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value))
    try:
        result = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        raise CoherenceError("Architecture coherence timestamp is incompatible") from None
    require(result.strftime("%Y-%m-%dT%H:%M:%SZ") == value)
    return result


def allowlist(values):
    require(isinstance(values, (list, tuple, set, frozenset))
        and all(isinstance(name, str) and REPOSITORY.fullmatch(name) for name in values))
    return frozenset(values)


def url(value, allowed):
    value = text(value)
    try:
        parsed = urlsplit(value)
        require(parsed.scheme == "https" and parsed.netloc == "github.com"
            and not parsed.query and "%" not in value and "\\" not in parsed.path
            and re.fullmatch(r"[A-Za-z0-9._-]*", parsed.fragment)
            and not any(part in (".", "..") for part in parsed.path.split("/")))
    except ValueError:
        raise CoherenceError("Architecture coherence evidence is incompatible") from None
    parts = parsed.path.strip("/").split("/")
    require(len(parts) >= 3 and "/".join(parts[:2]) in allowed)
    return value


def authority(value, allowed):
    closed(value, {"kind", "reference", "evidence_url", "decided_at"})
    require(value["kind"] == "human" and isinstance(value["reference"], str)
        and re.fullmatch(r"https://github\.com/[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", value["reference"]))
    url(value["evidence_url"], allowed)
    instant(value["decided_at"])
    return value


def revisions(value, repositories):
    require(isinstance(value, list) and len(value) == len(repositories))
    names = []
    for item in value:
        closed(item, {"repository", "revision"})
        require(isinstance(item["repository"], str) and item["repository"] in repositories
            and isinstance(item["revision"], str) and SHA.fullmatch(item["revision"]))
        names.append(item["repository"])
    require(names == sorted(repositories))
    return value


def _admitted(value, allowed):
    # Excluded records are not validated, counted, identified or hashed. An
    # organization review containing any protected scope cannot be partially
    # relabelled as the same public review or yield a protected placeholder.
    if (not isinstance(value, dict) or value.get("visibility") != "public"
            or "visibility" in getattr(value, "duplicate_keys", set())):
        return False
    scope = value.get("scope")
    if not isinstance(scope, dict) or "repositories" in getattr(scope, "duplicate_keys", set()):
        return False
    repositories = scope.get("repositories")
    return isinstance(repositories, list) and bool(repositories) and all(
        isinstance(name, str) and name in allowed for name in repositories)


def admit_governance(value, *, public_repositories):
    """Return a validated public governance source, or None for an exclusion."""
    allowed = allowlist(public_repositories)
    if not _admitted(value, allowed):
        return None
    unambiguous(value)
    closed(value, {"schema", "contract_version", "visibility", "scope", "represented_revisions",
        "applicability", "progress", "review_ref", "human_decision", "valid_until"})
    require(value["schema"] == SCHEMA and value["contract_version"] == VERSION)
    scope = closed(value["scope"], {"kind", "key", "repositories"})
    require(scope["kind"] in ("repository", "subsystem", "organization"))
    text(scope["key"], 256)
    repositories = scope["repositories"]
    require(1 <= len(repositories) <= 256 and repositories == sorted(set(repositories))
        and (scope["kind"] == "organization" or len(repositories) == 1)
        and (scope["kind"] != "repository" or scope["key"] == repositories[0])
        and (scope["kind"] != "organization" or scope["key"] == "egohygiene")
        and (scope["kind"] != "subsystem" or re.fullmatch(re.escape(repositories[0]) + r":[a-z0-9][a-z0-9.-]*", scope["key"])))
    revisions(value["represented_revisions"], repositories)
    application = closed(value["applicability"], {"status", "declared_at", "evidence", "reason", "deferred_until", "authority"})
    require(application["status"] in APPLICABILITY and isinstance(application["evidence"], list)
        and len(application["evidence"]) <= 32)
    for evidence in application["evidence"]:
        url(evidence, allowed)
    require(application["evidence"] == sorted(set(application["evidence"])))
    if application["status"] == "unknown":
        require(all(application[field] is None for field in ("declared_at", "reason", "deferred_until", "authority"))
            and not application["evidence"])
    else:
        instant(application["declared_at"])
        text(application["reason"])
        require(bool(application["evidence"]))
    if application["status"] in ("deferred", "not-applicable"):
        proof = authority(application["authority"], allowed)
        require(proof["decided_at"] <= application["declared_at"])
        if application["status"] == "deferred":
            require(instant(application["deferred_until"]) > instant(application["declared_at"]))
        else:
            require(application["deferred_until"] is None)
    else:
        require(application["authority"] is None and application["deferred_until"] is None)
    require(value["progress"] in PROGRESS)
    review = value["review_ref"]
    if review is not None:
        closed(review, {"id", "url", "assessment_sha256", "completed_at"})
        text(review["id"], 256); url(review["url"], allowed)
        require(isinstance(review["assessment_sha256"], str) and HASH.fullmatch(review["assessment_sha256"]))
        instant(review["completed_at"])
    require((value["progress"] == "complete") == (review is not None))
    decision = value["human_decision"]
    if decision is not None:
        closed(decision, {"disposition", "authority", "review_id", "assessment_sha256", "scope_key",
            "represented_revisions", "notes", "follow_up"})
        require(review is not None and decision["disposition"] in DISPOSITIONS)
        proof = authority(decision["authority"], allowed)
        require(proof["decided_at"] >= review["completed_at"] and decision["review_id"] == review["id"]
            and decision["assessment_sha256"] == review["assessment_sha256"] and decision["scope_key"] == scope["key"]
            and encoded(decision["represented_revisions"]) == encoded(value["represented_revisions"]))
        require(isinstance(decision["notes"], list) and len(decision["notes"]) <= 32
            and isinstance(decision["follow_up"], list) and len(decision["follow_up"]) <= 32)
        for note in decision["notes"]:
            text(note)
        for reference in decision["follow_up"]:
            url(reference, allowed)
        require(decision["follow_up"] == sorted(set(decision["follow_up"])))
        if decision["disposition"] == "ratified-with-notes":
            require(bool(decision["notes"]))
    if value["valid_until"] is not None:
        require(review is not None and instant(value["valid_until"]) > instant(review["completed_at"]))
    return value


validate_governance = admit_governance


def human_statement(governance, *, public_repositories, kind="decision"):
    """Public statement subject for a separate authentic human-source verifier.

    The canonical subject includes scope and exact represented revisions. Its
    digest is not evidence that the human authored, understood or approved it.
    """
    value = admit_governance(governance, public_repositories=public_repositories)
    require(value is not None and kind in ("decision", "applicability"))
    claim = value["human_decision"] if kind == "decision" else value["applicability"]
    require(claim is not None and (kind == "decision" or claim["authority"] is not None))
    return {"schema": SCHEMA, "contract_version": VERSION, "visibility": value["visibility"],
        "kind": kind, "scope": value["scope"], "represented_revisions": value["represented_revisions"],
        "review_ref": value["review_ref"] if kind == "decision" else None,
        "valid_until": value["valid_until"] if kind == "decision" else None, "claim": claim}


def statement_sha256(statement):
    return hashlib.sha256(encoded(statement)).hexdigest()


def _trusted(value, kind, public_repositories, evidence):
    claim = value["human_decision"] if kind == "decision" else value["applicability"]["authority"]
    if claim is None:
        return False
    subject = statement_sha256(human_statement(value, kind=kind, public_repositories=public_repositories))
    return any(type(item) is TrustedHumanEvidence and item.statement_sha256 == subject for item in evidence)


def admit_material_change(value, *, public_repositories, scope_key, review_id):
    allowed = allowlist(public_repositories)
    if not _admitted(value, allowed):
        return None
    # Nonselected public scopes/reviews are equally irrelevant to this query.
    if value["scope"].get("key") != scope_key or value.get("review_id") != review_id:
        return None
    unambiguous(value)
    closed(value, {"schema", "contract_version", "visibility", "scope", "review_id", "id", "kind", "observed_at", "evidence_url", "authority"})
    require(value["schema"] == CHANGE_SCHEMA and value["contract_version"] == VERSION)
    scope = closed(value["scope"], {"kind", "key", "repositories"})
    text(scope["key"], 256)
    repositories = scope["repositories"]
    require(scope["kind"] in ("repository", "subsystem", "organization")
        and 1 <= len(repositories) <= 256 and repositories == sorted(set(repositories))
        and (scope["kind"] == "organization" or len(repositories) == 1)
        and (scope["kind"] != "repository" or scope["key"] == repositories[0])
        and (scope["kind"] != "organization" or scope["key"] == "egohygiene")
        and (scope["kind"] != "subsystem" or re.fullmatch(re.escape(repositories[0]) + r":[a-z0-9][a-z0-9.-]*", scope["key"])))
    text(value["id"], 256)
    require(value["review_id"] is None or isinstance(value["review_id"], str) and 0 < len(value["review_id"]) <= 256)
    require(value["kind"] in (*MATERIAL_KINDS, *RECOMMENDED_KINDS, *NONMATERIAL_KINDS))
    instant(value["observed_at"]); url(value["evidence_url"], allowed)
    if value["kind"] == "explicit-human-invalidation":
        require(authority(value["authority"], allowed)["decided_at"] <= value["observed_at"])
    else:
        require(value["authority"] is None)
    return value


def material_change_statement(change, *, public_repositories):
    """Subject for separately verified explicit-human-invalidation evidence."""
    require(isinstance(change, dict) and isinstance(change.get("scope"), dict))
    value = admit_material_change(change, public_repositories=public_repositories,
        scope_key=change["scope"].get("key"), review_id=change.get("review_id"))
    require(value is not None and value["kind"] == "explicit-human-invalidation")
    return {"schema": CHANGE_SCHEMA, "contract_version": VERSION, "claim": value}


def evaluate(governance, *, as_of, public_repositories, material_changes=(), change_inventory="unknown",
             current_revisions=None, availability="unavailable", trusted_human_evidence=()):
    """Evaluate source posture without changing historical human disposition.

    change_inventory is explicit capture scope, not inferred from an empty list.
    Current Git revision differences are shown independently and never classify
    architecture materiality. Unknown inventory cannot establish freshness.
    """
    observed = instant(as_of)
    require(change_inventory in ("unknown", "partial", "complete", "unavailable")
        and availability in ("missing", "unavailable", "present"))
    value = admit_governance(governance, public_repositories=public_repositories)
    empty = {"state": "unavailable", "applicability": "unknown", "progress": "not-started",
        "claimed_applicability": "unknown", "human_disposition": None, "claimed_human_disposition": None,
        "human_evidence": "absent", "applicability_evidence": "absent", "freshness": "unknown", "revision_match": "unknown",
        "material_change_ids": [], "unverified_change_ids": [], "due_trigger_ids": [], "change_inventory": change_inventory}
    if value is None:
        # A filtered protected source cannot become an absence placeholder.
        if governance is None and availability == "missing":
            return {**empty, "state": "not-reviewed"}
        return empty
    application, review, decision = value["applicability"], value["review_ref"], value["human_decision"]
    require(isinstance(trusted_human_evidence, (list, tuple)) and isinstance(material_changes, (list, tuple)))
    decision_verified = _trusted(value, "decision", public_repositories, trusted_human_evidence)
    exceptional = application["status"] in ("not-applicable", "deferred")
    application_verified = exceptional and _trusted(value, "applicability", public_repositories, trusted_human_evidence)
    effective_applicability = application["status"] if not exceptional or application_verified else "unknown"
    for timestamp in (application["declared_at"], review["completed_at"] if review else None,
            decision["authority"]["decided_at"] if decision else None):
        require(timestamp is None or instant(timestamp) <= observed)
    selected, unverified_changes = [], []
    for item in material_changes:
        change = admit_material_change(item, public_repositories=public_repositories,
            scope_key=value["scope"]["key"], review_id=review["id"] if review else None)
        if change is None:
            continue
        require(instant(change["observed_at"]) <= observed)
        # Same key/review ID does not authorize a different represented scope.
        require(encoded(change["scope"]) == encoded(value["scope"]))
        if review is None or change["observed_at"] > review["completed_at"]:
            if change["kind"] == "explicit-human-invalidation":
                subject = statement_sha256(material_change_statement(change, public_repositories=public_repositories))
                if not any(type(item) is TrustedHumanEvidence and item.statement_sha256 == subject
                           for item in trusted_human_evidence):
                    unverified_changes.append(change["id"])
                    require(len(unverified_changes) <= 1024)
                    continue
            selected.append(change)
            require(len(selected) <= 1024)
    require(len({item["id"] for item in selected}) == len(selected)
        and len(set(unverified_changes)) == len(unverified_changes)
        and not {item["id"] for item in selected}.intersection(unverified_changes))
    material = sorted(item["id"] for item in selected if item["kind"] in MATERIAL_KINDS)
    recommended = sorted(item["id"] for item in selected if item["kind"] in RECOMMENDED_KINDS)
    expired = value["valid_until"] is not None and instant(value["valid_until"]) < observed
    freshness = ("stale" if review is not None and (material or expired) else "current" if review is not None
                 and change_inventory == "complete" and not unverified_changes else "unknown")
    revision_match = "unknown"
    if current_revisions is not None:
        revisions(current_revisions, value["scope"]["repositories"])
        revision_match = "matched" if encoded(current_revisions) == encoded(value["represented_revisions"]) else "different"
    state = {"not-started": "not-reviewed", "due": "review-due", "in-progress": "review-in-progress",
             "complete": "review-in-progress"}[value["progress"]]
    if decision is not None and decision_verified:
        state = decision["disposition"]
        if freshness == "stale":
            state = "stale"
        elif freshness == "unknown":
            state = "unavailable"
    elif material or recommended or effective_applicability == "required" and value["progress"] == "not-started":
        state = "review-due"
    exception_invalidated = application_verified and any(item["kind"] in MATERIAL_KINDS
        and item["observed_at"] > application["declared_at"] for item in selected)
    if exception_invalidated:
        effective_applicability, state = "unknown", "review-due"
    elif exceptional and not application_verified:
        state = "unavailable"
    elif effective_applicability == "not-applicable":
        state = "not-applicable"
    elif effective_applicability == "deferred":
        state = "deferred" if instant(application["deferred_until"]) >= observed else "review-due"
    return {"state": state, "applicability": effective_applicability, "claimed_applicability": application["status"],
        "progress": value["progress"], "human_disposition": decision["disposition"] if decision_verified else None,
        "claimed_human_disposition": decision["disposition"] if decision else None,
        "human_evidence": "verified" if decision_verified else "unverified" if decision else "absent",
        "applicability_evidence": "verified" if application_verified else "unverified" if exceptional else "not-required",
        "freshness": freshness,
        "revision_match": revision_match, "material_change_ids": material,
        "unverified_change_ids": sorted(unverified_changes), "due_trigger_ids": recommended, "change_inventory": change_inventory}
