"""Standalone public Sanity metadata contract; Hygiene owns governance meaning."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("observatory_sanity_public_reviews", Path(__file__).with_name("public_reviews.py"))
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)

SCHEMA = "egohygiene.observatory.repository-sanity/v1"
FLEET_SCHEMA = "egohygiene.observatory.fleet-sanity/v1"
VERSION = "1.0.0-alpha.1"
LOCK = "aether.architecture-coherence.v1.lock.json"
LOCK_SHA256 = "a5ea406128a8ef50b9a7cd2bdaeb02dde52e6137474b5f6f2aac272acbe8d73e"
HELPER = "library/organization/skills/architecture/review-architecture-coherence/scripts/architecture_coherence.py"
DEFAULT_ROOT = shared.DEFAULT_ROOT
parse, digest, instant, admission = shared.parse, shared.digest, shared.instant, shared.admission
canonical, require, closed, plain = shared.canonical, shared.require, shared.closed, shared.plain
ASSESSMENT_FIELDS = ("components", "relationships", "dimensions", "assumptions", "strengths", "concerns", "questions", "alternatives", "recommendation")
HUMAN_STATES = ("not-reviewed", "review-due", "review-in-progress", "ratified", "ratified-with-notes", "revision-required",
                "rejected", "deferred", "stale", "not-applicable", "unavailable", "mixed")


def owners(root=DEFAULT_ROOT):
    lock, files = shared.owner_resources(root, LOCK, LOCK_SHA256)
    require(lock["owner"] == "egohygiene/aether")
    native = shared.load_owner(files[HELPER]["local"], "observatory_aether_sanity_owner")
    policy = native.governance_contract()
    return native, policy, {"owner": lock["owner"], "revision": lock["revision"], "lock_sha256": LOCK_SHA256,
        "schema": native.SCHEMA, "contract_version": native.CONTRACT_VERSION,
        "governance": {"owner": "egohygiene/hygiene", "revision": policy.__owner_revision__,
            "schema": policy.SCHEMA, "contract_version": policy.VERSION, "policy": policy.POLICY}}


def _governance(value, *, policy, allowed, scope, revisions, subject, as_of, changes, inventory, repository, represented_commit):
    if value is not None:
        require(policy.admit_governance(value, public_repositories=allowed) is not None)
        require(canonical(value["scope"]) == canonical(scope) and canonical(value["represented_revisions"]) == canonical(revisions))
        if value["review_ref"] is not None:
            require(subject is not None and all(value["review_ref"][key] == subject[key]
                for key in ("id", "assessment_sha256", "completed_at")))
    require(isinstance(changes, list) and len(changes) <= 1024)
    review_id = value["review_ref"]["id"] if value is not None and value["review_ref"] is not None else None
    identifiers = []
    for change in changes:
        require(policy.admit_material_change(change, public_repositories=allowed,
            scope_key=scope["key"], review_id=review_id) is not None)
        require(canonical(change["scope"]) == canonical(scope) and instant(change["observed_at"]) <= instant(as_of))
        identifiers.append(change["id"])
    require(identifiers == sorted(set(identifiers)))
    # This serializable owner query deliberately supplies no trusted authority.
    # Raw source fields or a serialized "verified" marker cannot create it.
    current = [{"repository": repository, "revision": represented_commit}] if len(scope["repositories"]) == 1 else None
    return policy.evaluate(value, as_of=as_of, public_repositories=allowed, material_changes=changes,
        change_inventory=inventory, current_revisions=current, availability="missing" if value is None else "present",
        trusted_human_evidence=())


def assessment(review):
    result = {name: deepcopy(review[name]) for name in ASSESSMENT_FIELDS}
    result["explanation_summary"] = review["explanation"]["summary"]
    result["concerns"] = [{key: deepcopy(value) for key, value in concern.items() if key != "detail"}
                          for concern in review["concerns"]]
    for name in ASSESSMENT_FIELDS:
        if isinstance(result[name], list):
            result[name].sort(key=lambda item: item["id"])
    return result


def _assessment_shape(value, native):
    """Use pinned owner rules for the preserved field projection only.

    Omitted narrative fields are substituted solely to exercise owner shape and
    reference checks. This is NOT original-assessment replay, source validation
    or a recomputation of the original assessment digest. No reconstructed value
    is returned or published; the original digest remains a named source claim.
    """
    item = value["assessment"]
    closed(item, {"explanation_summary", *ASSESSMENT_FIELDS})
    summary_text = item["explanation_summary"]
    native._text(summary_text, "EXPLANATION_SUMMARY")
    for concern in item["concerns"]:
        require(isinstance(concern, dict) and "detail" not in concern)
    reconstructed = {"schema": native.SCHEMA, "contract_version": native.CONTRACT_VERSION,
        "id": value["id"], "visibility": "public", "scope": value["scope"],
        "represented_revisions": value["represented_revisions"], "generated_at": value["generated_at"],
        "reviewer": value["reviewer"], "execution": value["execution"], "sources": value["sources"],
        "explanation": {**{name: "." for name in ("system", "boundaries", "flows", "rationale")}, "summary": summary_text},
        **{name: item[name] for name in ASSESSMENT_FIELDS}, "governance": None}
    reconstructed["concerns"] = [{**concern, "detail": "."} for concern in item["concerns"]]
    native.validate_review(reconstructed)
    for name in ASSESSMENT_FIELDS:
        if isinstance(item[name], list):
            require([record["id"] for record in item[name]] == sorted(record["id"] for record in item[name]))


def _review(value, *, repository, represented_commit, as_of, native, policy, allowed):
    closed(value, {"id", "scope", "represented_revisions", "generated_at", "completed_at", "execution", "reviewer",
        "sources", "revision_status", "assessment", "governance_source", "governance", "material_changes", "change_inventory", "source"})
    require(shared.scope_admitted({"visibility": "public", "scope": value["scope"]}, allowed)
        and repository in value["scope"]["repositories"])
    require(shared.ownership_preflight(value, allowed))
    native._scope(value["scope"], value["represented_revisions"])
    _assessment_shape(value, native)
    require(instant(value["generated_at"]) <= as_of and value["completed_at"] == value["execution"]["completed_at"])
    revision = next(item["revision"] for item in value["represented_revisions"] if item["repository"] == repository)
    require(value["revision_status"] == ("matched" if revision == represented_commit else "different"))
    source = closed(value["source"], {"review_schema", "contract_version", "assessment_sha256", "input"})
    require(source["review_schema"] == native.SCHEMA and source["contract_version"] == native.CONTRACT_VERSION
        and isinstance(source["assessment_sha256"], str) and shared.base.HASH.fullmatch(source["assessment_sha256"]))
    shared.input_metadata(source["input"], allowed)
    subject = {"id": value["id"], "assessment_sha256": source["assessment_sha256"], "completed_at": value["completed_at"]}
    expected = _governance(value["governance_source"], policy=policy, allowed=allowed, scope=value["scope"],
        revisions=value["represented_revisions"], subject=subject, as_of=as_of.strftime("%Y-%m-%dT%H:%M:%SZ"),
        changes=value["material_changes"], inventory=value["change_inventory"], repository=repository, represented_commit=represented_commit)
    require(canonical(value["governance"]) == canonical(expected))


def _independent(value, *, repository, represented_commit, as_of, policy, allowed):
    closed(value, {"id", "revision_status", "governance_source", "governance", "material_changes", "change_inventory", "source"})
    raw = value["governance_source"]
    require(policy.admit_governance(raw, public_repositories=allowed) is not None and raw["review_ref"] is None
        and repository in raw["scope"]["repositories"])
    require(shared.ownership_preflight(value, allowed))
    require(value["id"] == "governance-" + digest(raw)[:24])
    revision = next(item["revision"] for item in raw["represented_revisions"] if item["repository"] == repository)
    require(value["revision_status"] == ("matched" if revision == represented_commit else "different"))
    shared.input_metadata(value["source"], allowed)
    expected = _governance(raw, policy=policy, allowed=allowed, scope=raw["scope"], revisions=raw["represented_revisions"],
        subject=None, as_of=as_of.strftime("%Y-%m-%dT%H:%M:%SZ"), changes=value["material_changes"], inventory=value["change_inventory"],
        repository=repository, represented_commit=represented_commit)
    require(canonical(value["governance"]) == canonical(expected))


def posture(reviews, records):
    current = [item for item in [*reviews, *records] if item["revision_status"] == "matched"]
    states = {item["governance"]["state"] for item in current}
    return (next(iter(states)) if len(states) == 1 else "mixed" if states else "unavailable",
        "unverified" if any(item["governance"]["human_evidence"] == "unverified"
            or item["governance"]["applicability_evidence"] == "unverified"
            or bool(item["governance"]["unverified_change_ids"]) for item in current) else "absent")


def summary(reviews, records):
    return {"counting_unit": "repository-review-projection", "review_count": len(reviews), "governance_record_count": len(records),
        "execution": dict(sorted(Counter(item["execution"]["status"] for item in reviews).items())),
        "current_review_count": sum(item["revision_status"] == "matched" for item in reviews),
        "other_revision_review_count": sum(item["revision_status"] == "different" for item in reviews),
        "strength_count": sum(len(item["assessment"]["strengths"]) for item in reviews),
        "concern_count": sum(len(item["assessment"]["concerns"]) for item in reviews),
        "question_count": sum(len(item["assessment"]["questions"]) for item in reviews),
        "human_state_counts": dict(sorted(Counter(item["governance"]["state"] for item in [*reviews, *records]).items())),
        "assessment": "reviewer-assessment-is-not-human-ratification-or-conformance"}


def queries(reviews, records):
    latest = max((item["completed_at"] or item["generated_at"] for item in reviews), default=None)
    return {"latest_review_ids": [item["id"] for item in reviews if (item["completed_at"] or item["generated_at"]) == latest],
        "review_due_ids": [item["id"] for item in [*reviews, *records] if item["governance"]["state"] == "review-due"],
        "stale_ids": [item["id"] for item in [*reviews, *records] if item["governance"]["freshness"] == "stale"],
        "unverified_human_claim_ids": [item["id"] for item in [*reviews, *records]
            if item["governance"]["human_evidence"] == "unverified"
            or item["governance"]["applicability_evidence"] == "unverified"
            or bool(item["governance"]["unverified_change_ids"])],
        "material_changes": "explicit-hygiene-classifications-only-no-commit-volume-proxy"}


def evidence(reviews, records):
    return {"state": "supplied" if reviews or records else "unavailable", "record_count": len(reviews) + len(records),
        "canonical_inputs_sha256": digest([item["source"]["input"]["canonical_input_sha256"] for item in reviews]
            + [item["source"]["canonical_input_sha256"] for item in records]),
        "human_verification": "unavailable-no-authenticated-human-source-context"}


def validate(value, *, admission_root=DEFAULT_ROOT):
    require(isinstance(value, dict) and value.get("visibility") == "public")
    if value.get("schema") == FLEET_SCHEMA:
        return validate_fleet(value, admission_root=admission_root)
    shared.base.unambiguous(value)
    closed(value, {"schema", "contract_version", "visibility", "repository", "represented_commit", "as_of", "admission",
        "source_owner", "reviews", "governance_records", "summary", "queries", "evidence", "human_state", "human_evidence", "digest"})
    require(value["schema"] == SCHEMA and value["contract_version"] == VERSION)
    identity = closed(value["repository"], {"full_name", "repository_id", "visibility", "source_url"})
    row, proof, allowed = admission(identity["full_name"], admission_root=admission_root)
    require(identity == shared.repository_identity(row) and value["admission"] == proof)
    require(isinstance(value["represented_commit"], str) and shared.base.SHA.fullmatch(value["represented_commit"]))
    native, policy, owner = owners(admission_root)
    require(value["source_owner"] == owner)
    observed = instant(value["as_of"])
    for field, validator in (("reviews", _review), ("governance_records", _independent)):
        require(isinstance(value[field], list) and len(value[field]) <= shared.MAX_RECORDS)
        identifiers = []
        for item in value[field]:
            options = {"repository": row["full_name"], "represented_commit": value["represented_commit"], "as_of": observed,
                "policy": policy, "allowed": allowed}
            if field == "reviews": options["native"] = native
            validator(item, **options)
            identifiers.append(item["id"])
        require(identifiers == sorted(set(identifiers)))
    require(canonical(value["summary"]) == canonical(summary(value["reviews"], value["governance_records"]))
        and canonical(value["queries"]) == canonical(queries(value["reviews"], value["governance_records"]))
        and canonical(value["evidence"]) == canonical(evidence(value["reviews"], value["governance_records"])))
    require((value["human_state"], value["human_evidence"]) == posture(value["reviews"], value["governance_records"]))
    shared.verify_seal(value)
    return value


def validate_fleet(value, *, admission_root=DEFAULT_ROOT):
    closed(value, {"schema", "contract_version", "visibility", "as_of", "admission", "repositories", "summary", "evidence", "digest"})
    require(value["schema"] == FLEET_SCHEMA and value["contract_version"] == VERSION and value["visibility"] == "public")
    instant(value["as_of"])
    rows, _allowed = shared.public_catalog(admission_root)
    require(isinstance(value["repositories"], list) and len(value["repositories"]) <= shared.MAX_TARGETS)
    names, reviews, records = [], [], []
    for item in value["repositories"]:
        validate(item, admission_root=admission_root)
        require(item["as_of"] == value["as_of"])
        names.append(item["repository"]["full_name"]); reviews.extend(item["reviews"]); records.extend(item["governance_records"])
    require(names == sorted(set(names)) and value["admission"] == shared.fleet_admission(names, rows, admission_root))
    require(canonical(value["summary"]) == canonical(summary(reviews, records)))
    require(canonical(value["evidence"]) == canonical({"state": "supplied" if reviews or records else "unavailable", "repository_count": len(names),
        "with_evidence_count": sum(bool(item["reviews"] or item["governance_records"]) for item in value["repositories"]),
        "canonical_inputs_sha256": digest([item["digest"] for item in value["repositories"]])}))
    shared.verify_seal(value)
    return value
