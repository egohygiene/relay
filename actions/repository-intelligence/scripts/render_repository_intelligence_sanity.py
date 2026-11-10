#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Present architecture assessment separately from owner-evaluated human posture."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("relay_sanity_view_support", Path(__file__).with_name("repository_review_view_support.py"))
support = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(support)
SCHEMA = "egohygiene.relay.architecture-coherence-receipt/v1"
LOCK = ROOT / "contracts/repository-sanity.v1.lock.json"
OWNER_FILES = {
    "src/observatory/sanity_contract.py": "sanity_contract.py",
    "src/observatory/public_reviews.py": "public_reviews.py",
    "src/observatory/conformance_contract.py": "conformance_contract.py",
    "src/observatory/data/hygiene.public-repositories.v1.json": "hygiene.public-repositories.v1.json",
    "contracts/hygiene.public-conformance.v1.lock.json": "hygiene.public-conformance.v1.lock.json",
    "schemas/repository-sanity.v1.schema.json": "repository-sanity.v1.schema.json",
    "src/observatory/data/aether.architecture-coherence.v1.lock.json": "aether.architecture-coherence.v1.lock.json",
    "src/observatory/data/sanity-owner/architecture_coherence.py": "sanity-owner/architecture_coherence.py",
    "src/observatory/data/sanity-owner/architecture_coherence_governance.py": "sanity-owner/architecture_coherence_governance.py",
    "src/observatory/data/sanity-owner/governance.lock.json": "sanity-owner/governance.lock.json",
    "src/observatory/data/sanity-owner/aether.architecture-coherence-review.v1.schema.json": "sanity-owner/aether.architecture-coherence-review.v1.schema.json",
}
VIEW = support.Boundary(route="sanity", renderer=__file__, lock=LOCK,
    owner_module="sanity_contract.py", files=OWNER_FILES, schema=SCHEMA)
require = support.require
# This exact owner profile receives no separately authenticated human context.
# A future verified-disposition transport needs a separately reviewed profile.
HUMAN_STATES = {"not-reviewed", "review-due", "review-in-progress", "unavailable", "stale", "mixed"}


def _summary(value):
    reviews = value["reviews"]
    records = value["governance_records"]
    current_reviews = [review for review in reviews if review["revision_status"] == "matched"]
    current_records = [record for record in records if record["revision_status"] == "matched"]
    current = [*current_reviews, *current_records]
    clocks = {name: sum(record["governance"]["freshness"] == name for record in current) for name in ("current", "stale", "unknown")}
    return {"freshness": "stale" if clocks["stale"] else "current" if current and not clocks["unknown"] else "unknown",
        "human_state": value["human_state"], "human_evidence": value["human_evidence"],
        "counts": {"review": len(reviews), "governance": len(records),
            "change": sum(len(record["material_changes"]) for record in [*reviews, *records])},
        "current_reviews": len(current_reviews), "other_revision_reviews": len(reviews) - len(current_reviews),
        "current_governance_records": len(current_records), "other_revision_governance_records": len(records) - len(current_records),
        "current_freshness": clocks}


def validate_input(path, repository, source_commit, as_of):
    try:
        _contract, value, receipt = VIEW.admit(path, repository, source_commit, as_of)
        receipt.update(_summary(value))
        validate_receipt(receipt, repository, source_commit, as_of)
        return value, receipt
    except Exception:
        raise support.ReviewViewError("Sanity input denied; inspect exact public owner evidence") from None


def validate_receipt(receipt, repository, source_commit, as_of):
    contract = VIEW.validate_core(receipt, repository, source_commit, as_of,
        {"freshness", "human_state", "human_evidence", "counts", "current_reviews", "other_revision_reviews",
            "current_governance_records", "other_revision_governance_records", "current_freshness"})
    counts, clocks = receipt["counts"], receipt["current_freshness"]
    require(isinstance(counts, dict) and set(counts) == {"review", "governance", "change"}
        and all(type(item) is int and item >= 0 for item in counts.values())
        and counts["review"] <= contract.shared.MAX_RECORDS and counts["governance"] <= contract.shared.MAX_RECORDS
        and counts["change"] <= (counts["review"] + counts["governance"]) * 1024
        and all(type(receipt[name]) is int and 0 <= receipt[name] <= counts["review"]
                for name in ("current_reviews", "other_revision_reviews"))
        and receipt["current_reviews"] + receipt["other_revision_reviews"] == counts["review"]
        and all(type(receipt[name]) is int and 0 <= receipt[name] <= counts["governance"]
                for name in ("current_governance_records", "other_revision_governance_records"))
        and receipt["current_governance_records"] + receipt["other_revision_governance_records"] == counts["governance"])
    current_count = receipt["current_reviews"] + receipt["current_governance_records"]
    require(
        isinstance(clocks, dict) and set(clocks) == {"current", "stale", "unknown"}
        and all(type(item) is int and 0 <= item <= current_count for item in clocks.values())
        and sum(clocks.values()) == current_count
        and receipt["human_state"] in HUMAN_STATES and receipt["human_evidence"] in {"absent", "unverified"})
    require(receipt["freshness"] == ("stale" if clocks["stale"] else
        "current" if current_count and not clocks["unknown"] else "unknown"))
    require(current_count > 0 or receipt["human_state"] == "unavailable" and receipt["human_evidence"] == "absent")
    require(receipt["human_state"] != "mixed" or current_count >= 2)
    return receipt


def validate_page(document, receipt):
    VIEW.validate_page(document, receipt)

    class HumanState(support.HTMLParser):
        def __init__(self):
            super().__init__(); self.active = False; self.text = []; self.records = []

        def handle_starttag(self, tag, attrs):
            require(not self.active)
            if "data-sanity-primary-human-state" in dict(attrs):
                require(tag == "strong" and len(attrs) == 1
                    and dict(attrs)["data-sanity-primary-human-state"] == receipt["human_state"])
                self.active = True; self.text = []

        def handle_endtag(self, tag):
            if self.active:
                require(tag == "strong")
                self.records.append("".join(self.text)); self.active = False

        def handle_data(self, data):
            if self.active: self.text.append(data)

    state = HumanState(); state.feed(document); state.close()
    require(not state.active and state.records == [receipt["human_state"]])
    return document


def _governance_claim(value):
    """Display claimed-source metadata, never copy notes or a human identity."""
    if value is None: return {"supplied": False}
    decision, application = value["human_decision"], value["applicability"]
    result = {"supplied": True, "claimed_applicability": application["status"],
        "claimed_progress": value["progress"], "represented_revisions": value["represented_revisions"],
        "review_ref": value["review_ref"], "valid_until": value["valid_until"], "human_decision": None}
    if application.get("authority") is not None:
        result["claimed_applicability_evidence"] = application["authority"]["evidence_url"]
    if decision is not None:
        result["human_decision"] = {"claimed_disposition": decision["disposition"], "notes_present": bool(decision["notes"]),
            "claimed_authority_evidence": decision["authority"]["evidence_url"], "claimed_decided_at": decision["authority"]["decided_at"]}
    return result


def render_body(value, receipt=None):
    contract, lock = VIEW.owner()
    contract.validate(value, admission_root=VIEW.vendor)
    if receipt is None:
        receipt = {"model_sha256": contract.digest(value), "owner": {"schema": contract.SCHEMA, "revision": lock["revision"]},
            "repository": value["repository"]["full_name"], "source_commit": value["represented_commit"],
            "as_of": value["as_of"], **_summary(value)}
    else:
        validate_receipt(receipt, value["repository"]["full_name"], value["represented_commit"], value["as_of"])
        require(all(receipt[name] == item for name, item in _summary(value).items()))
    require(contract.digest(value) == receipt["model_sha256"])
    display = support.Display(VIEW, value, receipt); esc = display.esc
    attrs = " ".join(f'{name}="{esc(item)}"' for name, item in VIEW.bindings(receipt).items())
    reviews, governance_records = value["reviews"], value["governance_records"]
    all_records = [*reviews, *governance_records]
    current = [review for review in reviews if review["revision_status"] == "matched"]
    facets = [display.facet("sanity-review", "Review", [review["id"] for review in reviews]),
        display.facet("sanity-revision", "Revision context", [record["revision_status"] for record in all_records]),
        display.facet("sanity-governance", "Effective governance", [record["governance"]["state"] for record in all_records]),
        display.facet("sanity-dimension", "Assessment dimension state", [item["status"] for review in reviews for item in review["assessment"]["dimensions"]])]
    explanations = []
    for review in current:
        source_note = ("Full explanation and rationale remain in the source review identified below."
            if review["source"]["input"]["artifact"] is not None else
            "Full explanation document unavailable: no source artifact locator was supplied.")
        explanations.append('<article class="ri-panel"><h4>' + esc(review["id"]) + '</h4><p>'
            + esc(review["assessment"]["explanation_summary"]) + '</p><p>' + esc(source_note) + '</p>'
            + display.detail(review["source"]) + '</article>')
    if not explanations:
        explanations.append(display.site.empty_state("Current architecture explanation unavailable",
            "No admitted current-revision reviewer explanation was supplied. Historical review text does not establish the current architecture.", "unknown"))
    cards = []
    for review in reviews:
        fields = {key: item for key, item in review.items() if key != "governance_source"}
        fields["governance_source_metadata"] = _governance_claim(review["governance_source"])
        cards.append(display.record(group="review", identifier=review["id"], title=review["id"] + " — reviewer assessment",
            state=review["execution"]["status"], fields=fields,
            facets=(("sanity-review", review["id"]), ("sanity-revision", review["revision_status"]),
                ("sanity-governance", review["governance"]["state"]),
                ("sanity-dimension", [item["status"] for item in review["assessment"]["dimensions"]])),
            intro={"Reviewer": review["reviewer"], "Assessment execution (not human approval)": review["execution"],
                "Reviewer recommendation (not a human disposition)": review["assessment"]["recommendation"],
                "Effective governance from owner policy": review["governance"], "Revision context": review["revision_status"]}))
    governance_cards = [display.record(group="governance", identifier=record["id"], title=record["id"] + " — independent governance record",
        state=record["governance"]["state"], fields={**{key: item for key, item in record.items() if key != "governance_source"},
            "governance_source_metadata": _governance_claim(record["governance_source"])},
        facets=(("sanity-revision", record["revision_status"]), ("sanity-governance", record["governance"]["state"])),
        intro={"Effective governance from owner policy": record["governance"], "Revision context": record["revision_status"],
            "Source context": "Supplied before or independently of an architecture assessment; no human approval is authenticated."})
        for record in governance_records]
    changes = [display.record(group="change", identifier=record["id"] + ":" + item["id"], title=item["id"] + " — supplied change occurrence",
        state="unknown", fields={"context_id": record["id"], "revision_status": record["revision_status"], **item},
        facets=(("sanity-revision", record["revision_status"]),))
        for record in all_records for item in record["material_changes"]]
    judgments = []
    for review in current:
        assessment = review["assessment"]
        judgments.append('<article class="ri-panel"><h4>' + esc(review["id"]) + '</h4><h5>Components and reviewer-declared connections</h5>'
            + display.detail({"components": assessment["components"], "relationships": assessment["relationships"]})
            + '<h5>Strengths, concerns and independent dimensions</h5>'
            + display.detail({"dimensions": assessment["dimensions"], "strengths": assessment["strengths"], "concerns": assessment["concerns"]})
            + '<h5>Questions requiring human judgment</h5>' + display.detail(assessment["questions"])
            + '<h5>Assumptions and alternatives</h5>' + display.detail({"assumptions": assessment["assumptions"], "alternatives": assessment["alternatives"]}) + '</article>')
    return f'''<section id="sanity-evidence" class="ri-section ri-section--lead" {attrs}>
      <div class="ri-section-heading"><div><span class="ri-eyebrow">Human architecture alignment</span><h2 id="sanity-heading">Architecture sanity</h2></div><p>Reviewer assessment and explicit human authority remain separate.</p></div>
      <div class="ri-panel"><h3>Effective human governance</h3><p><strong data-sanity-primary-human-state="{esc(receipt['human_state'])}">{esc(receipt['human_state'])}</strong> · human evidence {esc(receipt['human_evidence'])}</p>
        <p>This JSON foundation supplies no authenticated human approval. An AI/reviewer recommendation, successful execution, source claim or merged implementation cannot ratify architecture. The effective state above comes unchanged from the owner evaluation.</p>
        <p>Supplied reviews {receipt['counts']['review']} · current-revision reviews {receipt['current_reviews']} · historical reviews {receipt['other_revision_reviews']} · independent governance records {receipt['counts']['governance']}. No opaque score or conformance claim is produced.</p>{display.detail(value['summary'])}</div>
      <section class="ri-section"><h3>Architecture in plain English</h3>{''.join(explanations)}</section>
      <section class="ri-section"><h3>Ownership, connections and human review queue</h3><p>These are reviewer assertions with source evidence and uncertainty, not a new canonical dependency graph. Missing questions or relationships do not prove completeness; questions never auto-resolve.</p>{''.join(judgments) if judgments else display.site.empty_state('Reviewer assessment unavailable', 'No admitted current-revision assessment metadata was supplied.', 'unknown')}</section>
      <div class="ri-command-bar">{''.join(facets)}</div>
      {display.section('Reviewer assessments and governance evidence', cards, 'No admitted review was supplied. Human ratification remains unavailable, regardless of build or AI status.')}
      {display.section('Independent governance evidence', governance_cards, 'No independent governance record was supplied. An absent review does not establish an exemption or approval.')}
      <section class="ri-section"><h3>Owner queries and input availability</h3>{display.detail({'queries': value['queries'], 'evidence': value['evidence']})}</section>
      {display.section('Supplied architecture change occurrences', changes, 'No admitted change observations were supplied. An empty or incomplete inventory cannot prove architecture freshness.')}
      <p>Change counts describe occurrences within supplied review or governance contexts. Repeated references do not establish additional distinct changes.</p>
      <p>Materiality and freshness come from explicit owner-scoped observations, not ordinary commit volume. Human claims and notes remain in their canonical sources; notes presence and claim-evidence links are shown without copying their prose.</p>
      <p>{display.link(value['repository']['source_url'], 'Repository source')} · Contract <code>{esc(contract.SCHEMA)}</code> {esc(contract.VERSION)}</p>
    </section>'''


def render_page(*, value, receipt, summary, repository, source_commit):
    return support.site().shell_document(route="sanity", route_label="Sanity", repository=repository, source_commit=source_commit,
        observed_at=value["as_of"], freshness=receipt["freshness"], summary=summary, body=render_body(value, receipt),
        prefix="../", snapshot_available=True, supported_views=("sanity",), source_schema=receipt["owner"]["schema"])
