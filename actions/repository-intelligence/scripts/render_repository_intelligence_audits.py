#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Render admitted authored audit evidence without inferring an audit outcome."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("relay_audits_view_support", Path(__file__).with_name("repository_review_view_support.py"))
support = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(support)
SCHEMA = "egohygiene.relay.audit-evidence-receipt/v1"
LOCK = ROOT / "contracts/repository-audits.v1.lock.json"
OWNER_FILES = {
    "src/observatory/audits_contract.py": "audits_contract.py",
    "src/observatory/public_reviews.py": "public_reviews.py",
    "src/observatory/conformance_contract.py": "conformance_contract.py",
    "src/observatory/data/hygiene.public-repositories.v1.json": "hygiene.public-repositories.v1.json",
    "contracts/hygiene.public-conformance.v1.lock.json": "hygiene.public-conformance.v1.lock.json",
    "schemas/repository-audits.v1.schema.json": "repository-audits.v1.schema.json",
    "src/observatory/data/aether.audit-report.v1.lock.json": "aether.audit-report.v1.lock.json",
    "src/observatory/data/audit-owner/audit_contract.py": "audit-owner/audit_contract.py",
    "src/observatory/data/audit-owner/audit-profiles.v1.json": "audit-owner/audit-profiles.v1.json",
    "src/observatory/data/audit-owner/aether.audit-profile-registry.v1.schema.json": "audit-owner/aether.audit-profile-registry.v1.schema.json",
    "src/observatory/data/audit-owner/aether.repository-audit-report.v1.schema.json": "audit-owner/aether.repository-audit-report.v1.schema.json",
}
VIEW = support.Boundary(route="audits", renderer=__file__, lock=LOCK,
    owner_module="audits_contract.py", files=OWNER_FILES, schema=SCHEMA)
require = support.require


def _summary(value):
    runs = value["runs"]
    current = [run for run in runs if run["revision_status"] == "matched"]
    clocks = {name: sum(run["freshness"] == name for run in current) for name in ("current", "stale", "unknown")}
    return {"freshness": "stale" if clocks["stale"] else "current" if current and not clocks["unknown"] else "unknown",
        "counts": {"run": len(runs), "finding": sum(len(run["findings"]) for run in runs),
            "candidate": sum(len(run["candidate_issues"]) for run in runs)},
        "current_runs": len(current), "other_revision_runs": len(runs) - len(current), "current_freshness": clocks}


def validate_input(path, repository, source_commit, as_of):
    try:
        _contract, value, receipt = VIEW.admit(path, repository, source_commit, as_of)
        receipt.update(_summary(value))
        validate_receipt(receipt, repository, source_commit, as_of)
        return value, receipt
    except Exception:
        raise support.ReviewViewError("Audits input denied; inspect exact public owner evidence") from None


def validate_receipt(receipt, repository, source_commit, as_of):
    contract = VIEW.validate_core(receipt, repository, source_commit, as_of,
        {"freshness", "counts", "current_runs", "other_revision_runs", "current_freshness"})
    counts, clocks = receipt["counts"], receipt["current_freshness"]
    require(isinstance(counts, dict) and set(counts) == {"run", "finding", "candidate"}
        and all(type(item) is int and item >= 0 for item in counts.values())
        and counts["run"] <= contract.shared.MAX_RECORDS
        and counts["finding"] <= counts["run"] * contract.shared.MAX_FINDINGS
        and counts["candidate"] <= counts["run"] * 256
        and all(type(receipt[name]) is int and 0 <= receipt[name] <= counts["run"]
                for name in ("current_runs", "other_revision_runs"))
        and receipt["current_runs"] + receipt["other_revision_runs"] == counts["run"]
        and isinstance(clocks, dict) and set(clocks) == {"current", "stale", "unknown"}
        and all(type(item) is int and 0 <= item <= receipt["current_runs"] for item in clocks.values())
        and sum(clocks.values()) == receipt["current_runs"])
    require(receipt["freshness"] == ("stale" if clocks["stale"] else
        "current" if receipt["current_runs"] and not clocks["unknown"] else "unknown"))
    return receipt


def validate_page(document, receipt):
    return VIEW.validate_page(document, receipt)


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
    runs = value["runs"]
    findings = [(run, finding) for run in runs for finding in run["findings"]]
    facets = []
    for field, label in (("classification", "Classification"), ("nature", "Finding nature"), ("severity", "Severity"),
            ("confidence", "Confidence"), ("status", "Finding status"), ("area", "Area"),
            ("effort", "Effort"), ("impact", "Impact")):
        facets.append(display.facet("audit-" + field, label, [item[field] for _run, item in findings]))
    facets.append(display.facet("audit-run", "Audit", [run["id"] for run in runs]))
    facets.append(display.facet("audit-profile", "Profile", [profile["id"] for run in runs for profile in run["profiles"]["resolved"]]))
    facets.append(display.facet("audit-revision", "Revision context", [run["revision_status"] for run in runs]))
    facets.append(display.facet("audit-history", "Authored change claim", [item["history"]["delta"] for _run, item in findings]))
    sections = []
    # Nature is an owner field, not a Relay severity/priority calculation.
    for nature in sorted({item["nature"] for _run, item in findings}):
        cards = []
        for run, item in findings:
            if item["nature"] != nature: continue
            extra = [("audit-" + key, item[key]) for key in ("classification", "nature", "severity", "confidence", "status", "area", "effort", "impact")]
            extra += [("audit-run", run["id"]), ("audit-profile", item["source_profile"]["id"]),
                ("audit-revision", run["revision_status"]), ("audit-history", item["history"]["delta"])]
            cards.append(display.record(group="finding", identifier=item["key"], title=item["title"], state=item["status"],
                fields={"audit_id": run["id"], "revision_status": run["revision_status"], "freshness": run["freshness"], **item},
                facets=extra, intro={"Classification": item["classification"], "Severity": item["severity"],
                    "Confidence": item["confidence"], "Evidence classification": item["evidence_classification"],
                    "Profile": item["source_profile"], "Authored change claim": item["history"]["delta"],
                    "Revision context": run["revision_status"], "Canonical audit report": run["source"]["canonical_report"]}))
        sections.append(display.section(nature.replace("-", " ").capitalize(), cards, "No admitted findings in this owner category."))
    if not findings:
        sections.append(display.site.empty_state("Finding evidence unavailable", "No findings were supplied in the admitted audit projection. This is not a clean-audit or conformance claim.", "unknown"))
    history = []
    for run in runs:
        fields = {key: item for key, item in run.items() if key not in {"findings", "candidate_issues"}}
        history.append(display.record(group="run", identifier=run["id"], title=run["id"], state=run["completion"]["state"],
            fields=fields, facets=(("audit-run", run["id"]), ("audit-revision", run["revision_status"]),
                ("audit-profile", [item["id"] for item in run["profiles"]["resolved"]])),
            intro={"Run completion (not audit outcome)": run["completion"]["state"], "Completed": run["completed_at"],
                "Freshness": run["freshness"], "Revision context": run["revision_status"],
                "Inspected scope": run["scope"]["inspected"], "Uninspected scope": run["scope"]["uninspected"],
                "Profiles": run["profiles"]["resolved"], "Canonical report": run["source"]["canonical_report"]}))
    candidates = []
    for run in runs:
        for item in run["candidate_issues"]:
            candidates.append(display.record(group="candidate", identifier=run["id"] + ":" + item["id"],
                title=item["id"] + " — suggested issue", state=item["status"], fields={"audit_id": run["id"], **item},
                facets=(("audit-run", run["id"]), ("audit-revision", run["revision_status"])),
                intro={"Proposal status": item["status"], "Priority (authored)": item["priority"],
                    "GitHub issue materialization": item["materialization"], "Projection scope": item["projection"],
                    "Canonical audit report": run["source"]["canonical_report"]}))
    claims = []
    for key, title in (("recurrence_claims", "Explicit recurrence claims"), ("resolution_claims", "Explicit resolution claims")):
        links = ''.join(f'<li><a href="#{display.fragment("finding", identifier)}">{esc(identifier)}</a></li>' for identifier in value["queries"][key])
        claims.append('<h4>' + esc(title) + '</h4>' + ('<ul>' + links + '</ul>' if links else '<p>None supplied.</p>'))
    return f'''<section id="audits-evidence" class="ri-section ri-section--lead" {attrs}>
      <div class="ri-section-heading"><div><span class="ri-eyebrow">Authored audit evidence</span><h2 id="audits-heading">Audits</h2></div><p>Run coverage, findings and issue proposals retain independent meanings.</p></div>
      <div class="ri-panel"><p>Supplied runs {receipt['counts']['run']} · current-revision runs {receipt['current_runs']} · other-revision context {receipt['other_revision_runs']} · findings {receipt['counts']['finding']} · suggested issues {receipt['counts']['candidate']}</p>
        <p>Run completion is not an audit pass. Missing evidence is unknown; historical rows are context. No score, conformance, issue creation or resolution from silence is inferred.</p>{display.detail(value['evidence'])}</div>
      <details class="ri-evidence"><summary>Owner counts and latest supplied runs by profile</summary>{display.detail(value['summary'])}{display.detail(value['queries']['latest_by_profile'])}{display.detail(value['freshness_policy'])}</details>
      <div class="ri-command-bar">{''.join(facets)}</div>{''.join(sections)}
      {display.section('Audit history and scope', history, 'No admitted authored audit run was supplied; this does not establish that the repository has never been audited.')}
      {display.section('Candidate backlog — proposals only', candidates, 'No admitted candidate issue proposals were supplied. GitHub issue materialization is unavailable in this owner contract.')}
      <section class="ri-section"><h3>Comparison and recurring findings</h3><p>Only explicit authored source history is projected. An absent later finding never proves resolution.</p>{''.join(claims)}{display.detail(value['queries'])}</section>
      <section class="ri-section"><h3>Orchestration coverage</h3>{display.detail(value['campaigns'])}</section>
      <p>{display.link(value['repository']['source_url'], 'Repository source')} · Contract <code>{esc(contract.SCHEMA)}</code> {esc(contract.VERSION)}</p>
    </section>'''


def render_page(*, value, receipt, summary, repository, source_commit):
    return support.site().shell_document(route="audits", route_label="Audits", repository=repository, source_commit=source_commit,
        observed_at=value["as_of"], freshness=receipt["freshness"], summary=summary, body=render_body(value, receipt),
        prefix="../", snapshot_available=True, supported_views=("audits",), source_schema=receipt["owner"]["schema"])
