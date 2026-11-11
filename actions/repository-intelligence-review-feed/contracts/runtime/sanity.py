"""Pure public repository and explicit-roster Sanity metadata queries."""

from __future__ import annotations

from copy import deepcopy

from . import sanity_contract as contract

shared = contract.shared


def _public_source(value, allowed, repository, *, review):
    if not shared.scope_admitted(value, allowed) or repository not in value["scope"]["repositories"]:
        return False
    if review:
        for source in value.get("sources", []):
            if (not isinstance(source, dict) or source.get("visibility") != "public"
                    or source.get("repository") not in allowed or not shared.url_scope_admitted(source.get("url"), allowed)):
                return False
    return shared.ownership_preflight(value, allowed)


def _changes(values, *, scope, reference, policy, allowed):
    selected = []
    for value in values:
        if not shared.scope_admitted(value, allowed):
            continue
        if value["scope"].get("key") != scope["key"] or value.get("review_id") != reference:
            continue
        if not shared.ownership_preflight(value, allowed):
            continue
        admitted = policy.admit_material_change(value, public_repositories=allowed,
            scope_key=scope["key"], review_id=reference)
        shared.require(admitted is not None and shared.canonical(admitted["scope"]) == shared.canonical(scope))
        selected.append(deepcopy(admitted))
        shared.require(len(selected) <= 1024)
    selected.sort(key=lambda item: item["id"])
    shared.require(len({item["id"] for item in selected}) == len(selected))
    return selected


def build_repository_sanity(evidence_wrappers, *, repository, represented_commit, as_of,
        admission_root=contract.DEFAULT_ROOT, admission=None, governance_wrappers=(), material_changes=(), change_inventory="unknown"):
    row, proof, allowed = shared.admission(repository, admission_root=admission_root)
    shared.require(admission is None or admission == proof)
    shared.require(isinstance(represented_commit, str) and shared.base.SHA.fullmatch(represented_commit)
        and change_inventory in ("unknown", "partial", "complete", "unavailable"))
    evaluated = shared.instant(as_of)
    native, policy, owner = contract.owners(admission_root)
    changes = list(material_changes)
    reviews, records = [], []
    identifiers = set()
    for raw, transport in shared.wrappers(evidence_wrappers, repository, allowed):
        if not _public_source(raw, allowed, repository, review=True):
            continue
        shared.require(len(reviews) < shared.MAX_RECORDS)
        review = native.validate_review(shared.native_value(raw), public_repositories=allowed)
        shared.require(shared.instant(review["generated_at"]) <= evaluated and review["id"] not in identifiers)
        identifiers.add(review["id"])
        subject = native.review_subject(review)
        source = shared.source_input(transport, raw)
        ref = review["governance"]["review_ref"] if review["governance"] is not None else None
        selected_changes = _changes(changes, scope=review["scope"], reference=ref["id"] if ref else None, policy=policy, allowed=allowed)
        governance = contract._governance(review["governance"], policy=policy, allowed=allowed, scope=review["scope"],
            revisions=review["represented_revisions"], subject=subject, as_of=as_of, changes=selected_changes,
            inventory=change_inventory, repository=repository, represented_commit=represented_commit)
        revision = next(item["revision"] for item in review["represented_revisions"] if item["repository"] == repository)
        reviews.append({"id": review["id"], "scope": deepcopy(review["scope"]),
            "represented_revisions": deepcopy(review["represented_revisions"]), "generated_at": review["generated_at"],
            "completed_at": subject["completed_at"], "execution": deepcopy(review["execution"]),
            "reviewer": deepcopy(review["reviewer"]), "sources": deepcopy(review["sources"]),
            "revision_status": "matched" if revision == represented_commit else "different",
            "assessment": contract.assessment(review), "governance_source": deepcopy(review["governance"]), "governance": governance,
            "material_changes": selected_changes, "change_inventory": change_inventory,
            "source": {"review_schema": native.SCHEMA, "contract_version": native.CONTRACT_VERSION,
                "assessment_sha256": subject["assessment_sha256"], "input": source}})
    identifiers = set()
    for raw, transport in shared.wrappers(governance_wrappers, repository, allowed):
        if not _public_source(raw, allowed, repository, review=False):
            continue
        shared.require(len(records) < shared.MAX_RECORDS)
        value = policy.admit_governance(shared.native_value(raw), public_repositories=allowed)
        shared.require(value is not None and value["review_ref"] is None)
        identifier = "governance-" + shared.digest(value)[:24]
        shared.require(identifier not in identifiers)
        identifiers.add(identifier)
        source = shared.source_input(transport, raw)
        selected_changes = _changes(changes, scope=value["scope"], reference=None, policy=policy, allowed=allowed)
        governance = contract._governance(value, policy=policy, allowed=allowed, scope=value["scope"],
            revisions=value["represented_revisions"], subject=None, as_of=as_of, changes=selected_changes,
            inventory=change_inventory, repository=repository, represented_commit=represented_commit)
        revision = next(item["revision"] for item in value["represented_revisions"] if item["repository"] == repository)
        records.append({"id": identifier, "revision_status": "matched" if revision == represented_commit else "different",
            "governance_source": deepcopy(value), "governance": governance, "material_changes": selected_changes,
            "change_inventory": change_inventory, "source": source})
    reviews.sort(key=lambda item: item["id"]); records.sort(key=lambda item: item["id"])
    state, human_evidence = contract.posture(reviews, records)
    value = {"schema": contract.SCHEMA, "contract_version": contract.VERSION, "visibility": "public",
        "repository": shared.repository_identity(row), "represented_commit": represented_commit, "as_of": as_of,
        "admission": proof, "source_owner": owner, "reviews": reviews, "governance_records": records,
        "summary": contract.summary(reviews, records), "queries": contract.queries(reviews, records),
        "evidence": contract.evidence(reviews, records), "human_state": state, "human_evidence": human_evidence}
    return contract.validate(shared.seal(value), admission_root=admission_root)


def build_fleet_sanity(evidence_wrappers, *, repositories, as_of, admission_root=contract.DEFAULT_ROOT,
        governance_wrappers=(), material_changes=(), change_inventory="unknown"):
    selected, rows, _allowed = shared.targets(repositories, admission_root)
    shared.instant(as_of)
    wrappers, declarations, changes = list(evidence_wrappers), list(governance_wrappers), list(material_changes)
    entries, size = [], 0
    for name, revision in selected.items():
        entry = build_repository_sanity(wrappers, repository=name, represented_commit=revision, as_of=as_of,
            admission_root=admission_root, governance_wrappers=declarations, material_changes=changes, change_inventory=change_inventory)
        size += len(contract.canonical(entry)); shared.require(size <= shared.base.MAX_BYTES)
        entries.append(entry)
    reviews = [review for entry in entries for review in entry["reviews"]]
    records = [record for entry in entries for record in entry["governance_records"]]
    value = {"schema": contract.FLEET_SCHEMA, "contract_version": contract.VERSION, "visibility": "public", "as_of": as_of,
        "admission": shared.fleet_admission(selected, rows, admission_root), "repositories": entries,
        "summary": contract.summary(reviews, records), "evidence": {"state": "supplied" if reviews or records else "unavailable",
            "repository_count": len(entries), "with_evidence_count": sum(bool(item["reviews"] or item["governance_records"]) for item in entries),
            "canonical_inputs_sha256": contract.digest([item["digest"] for item in entries])}}
    return contract.validate_fleet(shared.seal(value), admission_root=admission_root)
