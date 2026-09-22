# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Render the Repository Intelligence Work route from Observatory evidence."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

READINESS_QUEUES = ("active", "ready", "waiting", "blocked", "unknown")
WORK_KINDS = {"issue", "pull_request", "roadmap_step"}


class WorkViewError(ValueError):
    """Raised when a projected Work view cannot be rendered safely."""


def load_site_module() -> ModuleType:
    """Load Relay's canonical shared shell without duplicating its contract."""

    path = Path(__file__).with_name("generate_repository_intelligence_site.py")
    spec = importlib.util.spec_from_file_location("relay_repository_intelligence_site", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Repository Intelligence shell module could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


site = load_site_module()


def parse_arguments() -> argparse.Namespace:
    """Parse the bounded Work-route rendering interface."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--provenance", required=True)
    parser.add_argument("--snapshot", default="")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--source-commit", required=True)
    return parser.parse_args()


def require_string(value: Any, label: str) -> str:
    """Return one non-empty string or reject the incompatible projection."""

    if not isinstance(value, str) or not value:
        raise WorkViewError(f"{label} must be a non-empty string")
    return value


def validate_work_entity(value: Any, label: str, *, expected_kind: str) -> dict[str, Any]:
    """Validate the compact entity fields needed by the Work presentation."""

    entity = site.require_object(value)
    if not entity:
        raise WorkViewError(f"{label} must be an object")
    for member in ("id", "key", "kind", "state", "canonical_url"):
        require_string(entity.get(member), f"{label}.{member}")
    if site.normalize_state(entity["kind"]) != expected_kind:
        raise WorkViewError(f"{label} must describe {expected_kind}")
    if not site.safe_href(entity["canonical_url"]):
        raise WorkViewError(f"{label}.canonical_url must be a credential-free HTTPS URL")
    for optional in ("assertion", "confidence", "freshness", "repository", "visibility"):
        if optional in entity and entity[optional] is not None:
            require_string(entity[optional], f"{label}.{optional}")
    title = entity.get("title")
    if title is not None and (not isinstance(title, str) or not title):
        raise WorkViewError(f"{label}.title must be null or a non-empty string")
    return entity


def validate_work_view(value: Any) -> dict[str, Any]:
    """Validate only Observatory's accepted Work query shape consumed by Relay."""

    work = site.require_object(value)
    if not work:
        raise WorkViewError("snapshot views.work must be an object")
    for collection_name, expected_kind in (
        ("open_issues", "issue"),
        ("open_pull_requests", "pull_request"),
    ):
        collection = work.get(collection_name)
        if not isinstance(collection, list):
            raise WorkViewError(f"snapshot views.work.{collection_name} must be an array")
        identifiers: set[str] = set()
        for index, candidate in enumerate(collection):
            entity = validate_work_entity(
                candidate,
                f"snapshot views.work.{collection_name}[{index}]",
                expected_kind=expected_kind,
            )
            if entity["id"] in identifiers:
                raise WorkViewError(f"snapshot views.work.{collection_name} IDs must be unique")
            identifiers.add(entity["id"])

    queues = work.get("roadmap_queues")
    if not isinstance(queues, dict):
        raise WorkViewError("snapshot views.work.roadmap_queues must be an object")
    for queue_name in READINESS_QUEUES:
        queue = queues.get(queue_name)
        if not isinstance(queue, list):
            raise WorkViewError(
                f"snapshot views.work.roadmap_queues.{queue_name} must be an array"
            )
        identifiers: set[str] = set()
        for index, candidate in enumerate(queue):
            entity = validate_work_entity(
                candidate,
                f"snapshot views.work.roadmap_queues.{queue_name}[{index}]",
                expected_kind="roadmap_step",
            )
            if entity["id"] in identifiers:
                raise WorkViewError(
                    f"snapshot views.work.roadmap_queues.{queue_name} IDs must be unique"
                )
            identifiers.add(entity["id"])
    return work


def evidence_label(entity: dict[str, Any], field: str) -> str:
    """Keep missing optional evidence metadata explicit rather than inventing it."""

    return site.state_label(entity.get(field) or "unknown")


def render_work_record(
    entity: dict[str, Any],
    *,
    eyebrow: str,
    readiness: str = "",
    local_roadmap: bool = False,
) -> str:
    """Render one actionable or strategic Work record as complete static HTML."""

    state = site.normalize_state(entity.get("state"))
    kind = site.normalize_state(entity.get("kind"))
    title = entity.get("title") or entity.get("key") or entity.get("id")
    search = " ".join(
        str(value or "")
        for value in (
            title,
            entity.get("key"),
            kind,
            state,
            readiness,
            entity.get("repository"),
            entity.get("assertion"),
            entity.get("freshness"),
        )
    ).lower()
    readiness_attribute = (
        f' data-filter-readiness="{site.escaped(readiness)}"' if readiness else ""
    )
    source_attributes = site.source_repository_attribute(entity)
    action = site.source_link(
        entity,
        "Open in GitHub" if kind in {"issue", "pull_request"} else "Open canonical roadmap step",
    )
    roadmap_link = ""
    if local_roadmap and kind == "roadmap_step":
        anchor = site.stable_fragment("quest", entity.get("id"))
        roadmap_link = (
            f'<a class="ri-button ri-button--quiet" data-preserve-context href="../roadmap/#{site.escaped(anchor)}">'
            'View in roadmap</a>'
        )
    readiness_pill = site.status_pill(readiness, f"Readiness: {site.state_label(readiness)}") if readiness else ""
    return f'''<article class="ri-record" data-entity-id="{site.escaped(entity.get("id"))}" data-filter-item{source_attributes} data-state="{site.escaped(state)}" data-kind="{site.escaped(kind)}"{readiness_attribute} data-search="{site.escaped(search)}">
      <div class="ri-record__top"><span class="ri-eyebrow">{site.escaped(eyebrow)}</span><span>{site.status_pill(state)} {readiness_pill}</span></div>
      <h3>{site.escaped(title)}</h3>
      <p>{site.escaped(site.state_label(kind))} · {site.escaped(entity.get("key") or "No identifier")}</p>
      <dl class="ri-provenance"><div><dt>Assertion</dt><dd>{site.escaped(evidence_label(entity, "assertion"))}</dd></div><div><dt>Freshness</dt><dd>{site.escaped(evidence_label(entity, "freshness"))}</dd></div></dl>
      <p>{action} {roadmap_link}</p>
    </article>'''


def render_queue(name: str, records: list[dict[str, Any]]) -> str:
    """Render one roadmap-readiness queue without collapsing empty into unavailable."""

    label = site.state_label(name)
    if not records:
        return site.empty_state(
            f"No {label.lower()} roadmap work projected",
            f"The normalized Work query contains no roadmap step in the {label.lower()} queue.",
            "empty",
        )
    return '<div class="ri-record-list">' + "".join(
        render_work_record(
            record,
            eyebrow=f"{label} roadmap work",
            readiness=name,
            local_roadmap=True,
        )
        for record in records
    ) + "</div>"


def render_execution_details(label: str, records: list[dict[str, Any]], *, kind: str) -> str:
    """Keep GitHub execution records available without making backlog the default view."""

    count = len(records)
    noun = label.lower() if count != 1 else label.lower().rstrip("s")
    content = (
        '<div class="ri-record-list">'
        + "".join(
            render_work_record(record, eyebrow="GitHub execution") for record in records
        )
        + "</div>"
        if records
        else site.empty_state(
            f"No open {noun} projected",
            "The normalized Work query contains no matching open GitHub execution records.",
            "empty",
        )
    )
    return f'''<details class="ri-evidence"><summary><span><strong>{site.escaped(label)}</strong><small>{count} open</small></span><span aria-hidden="true">+</span></summary><div class="ri-evidence-viewport">{content}</div></details>'''


def render_readiness_filter(work: dict[str, Any]) -> str:
    """Expose the five accepted readiness queues through the shared URL filter layer."""

    queues = site.require_object(work.get("roadmap_queues"))
    options = "".join(
        f'<option value="{site.escaped(name)}">{site.escaped(site.state_label(name))} ({len(site.require_list(queues.get(name)))})</option>'
        for name in READINESS_QUEUES
    )
    return f'''<details class="ri-decision-filters" open><summary>Work facets</summary><div><label><span>Readiness</span><select data-filter-extra="readiness"><option value="all">All readiness</option>{options}</select></label></div><p>Readiness comes from Observatory's normalized Work query. GitHub issue and pull-request state remain separate execution evidence.</p></details>'''


def work_body(snapshot: dict[str, Any] | None) -> str:
    """Render active execution orientation without rebuilding GitHub as a task manager."""

    if snapshot is None:
        return f'''<section class="ri-section ri-section--lead" aria-labelledby="work-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Execution orientation</span><h2 id="work-heading">What work needs attention?</h2></div><p>Only normalized Observatory Work evidence is rendered here.</p></div>{site.empty_state("Work evidence unavailable", "Supply a repository- and commit-matched Observatory read model to inspect open execution records and roadmap readiness queues.", "partial")}</section>'''

    views = site.require_object(snapshot.get("views"))
    if "work" not in views:
        return f'''<section class="ri-section ri-section--lead" aria-labelledby="work-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Execution orientation</span><h2 id="work-heading">What work needs attention?</h2></div><p>This snapshot predates or omits the normalized Work query.</p></div>{site.empty_state("Work view not projected", "The represented snapshot is available, but it does not contain views.work. Relay will not reconstruct work state from issues, roadmap, or activity in other views.", "partial")}</section>'''

    work = validate_work_view(views.get("work"))
    issues = [site.require_object(value) for value in work["open_issues"]]
    pull_requests = [site.require_object(value) for value in work["open_pull_requests"]]
    queues = site.require_object(work["roadmap_queues"])
    queue_records = {
        name: [site.require_object(value) for value in site.require_list(queues.get(name))]
        for name in READINESS_QUEUES
    }
    total_queue_records = sum(len(values) for values in queue_records.values())
    if not issues and not pull_requests and total_queue_records == 0:
        return f'''<section class="ri-section ri-section--lead" aria-labelledby="work-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Execution orientation</span><h2 id="work-heading">What work needs attention?</h2></div><p>The normalized Work query is present and contains no open execution or roadmap queue records.</p></div>{site.empty_state("No work records projected", "This query is empty for the represented snapshot; it does not prove the repository has no historical, private, or otherwise unprojected work.", "not_applicable")}</section>'''

    return f'''<section class="ri-section ri-section--lead" aria-labelledby="work-heading">
      <div class="ri-section-heading"><div><span class="ri-eyebrow">Execution orientation</span><h2 id="work-heading">What work needs attention?</h2></div><p>Resume from active, blocked, waiting, or ready roadmap work, then jump to GitHub for execution.</p></div>
      <div class="ri-roadmap-metrics" aria-label="Work summary"><article><strong>{len(issues)}</strong><span>open issues</span></article><article><strong>{len(pull_requests)}</strong><span>open pull requests</span></article><article><strong>{len(queue_records["active"])}</strong><span>active quests</span></article><article><strong>{len(queue_records["ready"])}</strong><span>ready quests</span></article></div>
      <details class="ri-progress-rules"><summary>How this view decides what to show</summary><p>Relay does not prioritize GitHub work. Observatory supplies open issue and pull-request records plus active, ready, waiting, blocked, and unknown roadmap queues. Queue membership is displayed as evidence, never converted into a productivity score.</p></details>
      {render_readiness_filter(work)}
    </section>
    <section class="ri-section" aria-labelledby="active-work-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Current focus</span><h2 id="active-work-heading">Active roadmap work</h2></div><p>Canonical active intent stays distinct from issue activity.</p></div>{render_queue("active", queue_records["active"])}</section>
    <section class="ri-section" aria-labelledby="attention-work-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Attention</span><h2 id="attention-work-heading">Blocked, waiting, and unknown</h2></div><p>Uncertainty and prerequisites stay visible instead of becoming generic backlog.</p></div><div class="ri-now-grid"><section class="ri-panel" data-severity="blocked"><h3>Blocked</h3>{render_queue("blocked", queue_records["blocked"])}</section><section class="ri-panel"><h3>Waiting</h3>{render_queue("waiting", queue_records["waiting"])}</section><section class="ri-panel"><h3>Unknown</h3>{render_queue("unknown", queue_records["unknown"])}</section></div></section>
    <section class="ri-section" aria-labelledby="ready-work-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Next grounded moves</span><h2 id="ready-work-heading">Ready roadmap work</h2></div><p>Ready means the normalized readiness query says ready; Relay does not promote planned work itself.</p></div>{render_queue("ready", queue_records["ready"])}</section>
    <section class="ri-section" aria-labelledby="github-work-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Execution layer</span><h2 id="github-work-heading">Open GitHub work</h2></div><p>Inspect here, act in GitHub. Editing remains outside Intelligence.</p></div>{render_execution_details("Issues", issues, kind="issue")}{render_execution_details("Pull requests", pull_requests, kind="pull_request")}</section>'''


def render_page(
    *,
    snapshot: dict[str, Any] | None,
    summary: dict[str, Any],
    repository: str,
    source_commit: str,
) -> str:
    """Compose Work through Relay's canonical shared shell."""

    observed_at = str(
        snapshot.get("observed_at") if snapshot else summary.get("generated_at") or ""
    )
    freshness = site.normalize_state(
        site.require_object(snapshot.get("coverage")).get("status") if snapshot else "unknown"
    )
    return site.shell_document(
        route="work",
        route_label="Work",
        repository=repository,
        source_commit=source_commit,
        observed_at=observed_at,
        freshness=freshness,
        summary=summary,
        body=work_body(snapshot),
        prefix="../",
        snapshot_available=snapshot is not None,
    )


def main() -> int:
    """Validate shared inputs and replace only the generated Work route."""

    args = parse_arguments()
    repository_root = Path(args.repository_root).resolve(strict=True)
    output_root = Path(args.output_root).resolve()
    summary_path = Path(args.summary).resolve()
    provenance_path = Path(args.provenance).resolve()
    snapshot_path = Path(args.snapshot).absolute() if args.snapshot else None
    if not site.FULL_SHA.fullmatch(args.source_commit):
        raise SystemExit("source-commit must be a full lowercase Git SHA")
    for path, label in (
        (output_root, "output root"),
        (summary_path, "dashboard summary"),
        (provenance_path, "bundle provenance"),
        *(((snapshot_path, "Observatory snapshot"),) if snapshot_path is not None else ()),
    ):
        site.validate_repository_path(repository_root, path, label)
    summary = site.load_object(summary_path, "dashboard summary")
    provenance = site.load_object(provenance_path, "bundle provenance")
    site.validate_site_contracts(summary, provenance, args.repository, args.source_commit)
    snapshot = None
    if snapshot_path is not None:
        if not snapshot_path.is_file():
            raise SystemExit(f"Observatory snapshot is unavailable: {snapshot_path}")
        snapshot = site.validate_snapshot(
            site.load_object(snapshot_path, "Observatory snapshot"),
            args.repository,
            args.source_commit,
        )
    site.atomic_write(
        output_root / "work/index.html",
        render_page(
            snapshot=snapshot,
            summary=summary,
            repository=args.repository,
            source_commit=args.source_commit,
        ),
    )
    print(
        "Rendered Repository Intelligence Work at "
        f"{output_root / 'work/index.html'} for {args.repository}@{args.source_commit[:12]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
