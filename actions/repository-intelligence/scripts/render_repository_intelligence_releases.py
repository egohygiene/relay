# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Render the Repository Intelligence Releases route from Observatory evidence."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any


class ReleasesViewError(ValueError):
    """Raised when a projected Releases view cannot be rendered safely."""


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
    """Parse the bounded Releases-route rendering interface."""

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
        raise ReleasesViewError(f"{label} must be a non-empty string")
    return value


def validate_entity(
    value: Any,
    label: str,
    *,
    expected_kind: str | None = None,
) -> dict[str, Any]:
    """Validate the compact entity fields consumed by the Releases presentation."""

    entity = site.require_object(value)
    if not entity:
        raise ReleasesViewError(f"{label} must be an object")
    for member in ("id", "key", "kind", "state", "canonical_url"):
        require_string(entity.get(member), f"{label}.{member}")
    kind = site.normalize_state(entity["kind"])
    if expected_kind is not None and kind != expected_kind:
        raise ReleasesViewError(f"{label} must describe {expected_kind}")
    if not site.safe_href(entity["canonical_url"]):
        raise ReleasesViewError(f"{label}.canonical_url must be a credential-free HTTPS URL")
    for optional in ("assertion", "confidence", "freshness", "repository", "visibility"):
        if optional in entity and entity[optional] is not None:
            require_string(entity[optional], f"{label}.{optional}")
    title = entity.get("title")
    if title is not None and (not isinstance(title, str) or not title):
        raise ReleasesViewError(f"{label}.title must be null or a non-empty string")
    return entity


def validate_published_at(value: Any, label: str) -> str:
    """Require the release publication boundary to be a timezone-aware instant."""

    published_at = require_string(value, label)
    try:
        site.parse_rfc3339(published_at, label)
    except site.SiteInputError as error:
        raise ReleasesViewError(str(error)) from error
    return published_at


def validate_release_record(value: Any, label: str) -> dict[str, Any]:
    """Validate one accepted Observatory Releases record without extending it."""

    record = site.require_object(value)
    if not record:
        raise ReleasesViewError(f"{label} must be an object")
    validate_entity(record.get("entity"), f"{label}.entity", expected_kind="release")
    validate_published_at(record.get("published_at"), f"{label}.published_at")

    includes = record.get("includes")
    if not isinstance(includes, list):
        raise ReleasesViewError(f"{label}.includes must be an array")
    included_ids: set[str] = set()
    for index, candidate in enumerate(includes):
        entity = validate_entity(candidate, f"{label}.includes[{index}]")
        if entity["id"] in included_ids:
            raise ReleasesViewError(f"{label}.includes IDs must be unique")
        included_ids.add(entity["id"])

    deployments = record.get("deployments")
    if not isinstance(deployments, list):
        raise ReleasesViewError(f"{label}.deployments must be an array")
    deployment_ids: set[str] = set()
    for index, candidate in enumerate(deployments):
        entity = validate_entity(
            candidate,
            f"{label}.deployments[{index}]",
            expected_kind="deployment",
        )
        if entity["id"] in deployment_ids:
            raise ReleasesViewError(f"{label}.deployments IDs must be unique")
        deployment_ids.add(entity["id"])

    boundary_event_ids = record.get("boundary_event_ids")
    if not isinstance(boundary_event_ids, list):
        raise ReleasesViewError(f"{label}.boundary_event_ids must be an array")
    seen_events: set[str] = set()
    for index, event_id in enumerate(boundary_event_ids):
        require_string(event_id, f"{label}.boundary_event_ids[{index}]")
        if event_id in seen_events:
            raise ReleasesViewError(f"{label}.boundary_event_ids must be unique")
        seen_events.add(event_id)
    return record


def validate_releases_view(value: Any) -> dict[str, Any]:
    """Validate only Observatory's accepted Releases query shape consumed by Relay."""

    releases_view = site.require_object(value)
    if not releases_view:
        raise ReleasesViewError("snapshot views.releases must be an object")
    records = releases_view.get("releases")
    if not isinstance(records, list):
        raise ReleasesViewError("snapshot views.releases.releases must be an array")
    release_ids: set[str] = set()
    for index, candidate in enumerate(records):
        record = validate_release_record(candidate, f"snapshot views.releases.releases[{index}]")
        release_id = site.require_object(record["entity"])["id"]
        if release_id in release_ids:
            raise ReleasesViewError("snapshot views.releases release IDs must be unique")
        release_ids.add(release_id)
    return releases_view


def evidence_label(entity: dict[str, Any], field: str) -> str:
    """Keep optional evidence metadata explicit rather than manufacturing it."""

    return site.state_label(entity.get(field) or "unknown")


def render_evidence_record(entity: dict[str, Any], *, eyebrow: str) -> str:
    """Render one normalized included/deployment entity without adding semantics."""

    state = site.normalize_state(entity.get("state"))
    kind = site.normalize_state(entity.get("kind"))
    title = entity.get("title") or entity.get("key") or entity.get("id")
    return f'''<article class="ri-record"{site.source_repository_attribute(entity)}>
      <div class="ri-record__top"><span class="ri-eyebrow">{site.escaped(eyebrow)}</span><span>{site.status_pill(state)}</span></div>
      <h4>{site.escaped(title)}</h4>
      <p>{site.escaped(site.state_label(kind))} · {site.escaped(entity.get("key") or "No identifier")}</p>
      <dl class="ri-provenance"><div><dt>Assertion</dt><dd>{site.escaped(evidence_label(entity, "assertion"))}</dd></div><div><dt>Freshness</dt><dd>{site.escaped(evidence_label(entity, "freshness"))}</dd></div></dl>
      <p>{site.source_link(entity, "Open canonical evidence")}</p>
    </article>'''


def render_entity_details(
    *,
    label: str,
    records: list[dict[str, Any]],
    eyebrow: str,
    empty_message: str,
) -> str:
    """Render bounded normalized evidence behind progressive disclosure."""

    count = len(records)
    content = (
        '<div class="ri-record-list">'
        + "".join(render_evidence_record(record, eyebrow=eyebrow) for record in records)
        + "</div>"
        if records
        else site.empty_state(label, empty_message, "empty")
    )
    return f'''<details class="ri-evidence"><summary><span><strong>{site.escaped(label)}</strong><small>{count} projected</small></span><span aria-hidden="true">+</span></summary><div class="ri-evidence-viewport">{content}</div></details>'''


def render_boundary_events(event_ids: list[str]) -> str:
    """Expose normalized boundary IDs without claiming they explain causality."""

    if not event_ids:
        content = site.empty_state(
            "No boundary events projected",
            "The normalized release record contains no release-boundary event identifiers.",
            "empty",
        )
    else:
        items = "".join(f"<li><code>{site.escaped(event_id)}</code></li>" for event_id in event_ids)
        content = f'<ul class="ri-source-list">{items}</ul>'
    return f'''<details class="ri-evidence"><summary><span><strong>Boundary evidence</strong><small>{len(event_ids)} event IDs</small></span><span aria-hidden="true">+</span></summary><div class="ri-evidence-viewport"><p>These identifiers mark the normalized release boundary. Relay does not infer causality from them.</p>{content}</div></details>'''


def release_search_text(record: dict[str, Any]) -> str:
    """Build browser-search text only from already projected public-safe fields."""

    release = site.require_object(record.get("entity"))
    nested = [
        *[site.require_object(value) for value in site.require_list(record.get("includes"))],
        *[site.require_object(value) for value in site.require_list(record.get("deployments"))],
    ]
    values: list[str] = [
        str(release.get("title") or ""),
        str(release.get("key") or ""),
        str(release.get("state") or ""),
        str(record.get("published_at") or ""),
        str(release.get("assertion") or ""),
        str(release.get("freshness") or ""),
    ]
    for entity in nested:
        values.extend(
            [
                str(entity.get("title") or ""),
                str(entity.get("key") or ""),
                str(entity.get("kind") or ""),
                str(entity.get("state") or ""),
            ]
        )
    values.extend(str(value) for value in site.require_list(record.get("boundary_event_ids")))
    return " ".join(values).lower()


def render_release(record: dict[str, Any], *, latest_release_id: str) -> str:
    """Render one release boundary with publication and deployment kept distinct."""

    release = site.require_object(record["entity"])
    includes = [site.require_object(value) for value in site.require_list(record["includes"])]
    deployments = [site.require_object(value) for value in site.require_list(record["deployments"])]
    event_ids = [str(value) for value in site.require_list(record["boundary_event_ids"])]
    state = site.normalize_state(release.get("state"))
    title = release.get("title") or release.get("key") or release.get("id")
    latest = release.get("id") == latest_release_id
    latest_label = '<span class="ri-eyebrow">Latest projected release</span>' if latest else '<span class="ri-eyebrow">Projected release</span>'
    return f'''<li><article class="ri-record" data-filter-item{site.source_repository_attribute(release)} data-state="{site.escaped(state)}" data-kind="release" data-search="{site.escaped(release_search_text(record))}">
      <div class="ri-record__top">{latest_label}<span>{site.status_pill(state)}</span></div>
      <h3>{site.escaped(title)}</h3>
      <p><strong>Published:</strong> {site.escaped(site.format_date(record["published_at"]))}</p>
      <dl class="ri-provenance"><div><dt>Assertion</dt><dd>{site.escaped(evidence_label(release, "assertion"))}</dd></div><div><dt>Freshness</dt><dd>{site.escaped(evidence_label(release, "freshness"))}</dd></div></dl>
      <div class="ri-roadmap-metrics" aria-label="Release evidence summary"><article><strong>{len(includes)}</strong><span>included entities</span></article><article><strong>{len(deployments)}</strong><span>deployments</span></article><article><strong>{len(event_ids)}</strong><span>boundary events</span></article></div>
      <p>{site.source_link(release, "Open canonical release")}</p>
      {render_entity_details(label="Included evidence", records=includes, eyebrow="Included by release", empty_message="The normalized release record contains no included entities.")}
      {render_entity_details(label="Deployment evidence", records=deployments, eyebrow="Deployment evidence", empty_message="The normalized release record contains no associated deployments. Release publication is not treated as deployment success.")}
      {render_boundary_events(event_ids)}
    </article></li>'''


def latest_release_id(records: list[dict[str, Any]]) -> str:
    """Select the latest projected publication instant without changing record order."""

    if not records:
        return ""
    latest = max(
        records,
        key=lambda record: site.parse_rfc3339(
            site.require_object(record).get("published_at"),
            "snapshot views.releases.releases[].published_at",
        ),
    )
    return str(site.require_object(site.require_object(latest).get("entity")).get("id") or "")


def releases_body(snapshot: dict[str, Any] | None) -> str:
    """Render shipped evidence without conflating release, deployment, or distribution."""

    if snapshot is None:
        return f'''<section class="ri-section ri-section--lead" aria-labelledby="releases-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Delivery evidence</span><h2 id="releases-heading">What has actually shipped?</h2></div><p>Only normalized Observatory Releases evidence is rendered here.</p></div>{site.empty_state("Release evidence unavailable", "Supply a repository- and commit-matched Observatory read model to inspect projected releases, included evidence, deployments, and release boundaries.", "partial")}</section>'''

    views = site.require_object(snapshot.get("views"))
    if "releases" not in views:
        return f'''<section class="ri-section ri-section--lead" aria-labelledby="releases-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Delivery evidence</span><h2 id="releases-heading">What has actually shipped?</h2></div><p>This snapshot predates or omits the normalized Releases query.</p></div>{site.empty_state("Releases view not projected", "The represented snapshot is available, but it does not contain views.releases. Relay will not reconstruct release membership from Journey, Git history, or raw GitHub activity.", "partial")}</section>'''

    releases_view = validate_releases_view(views.get("releases"))
    records = [site.require_object(value) for value in site.require_list(releases_view["releases"])]
    if not records:
        return f'''<section class="ri-section ri-section--lead" aria-labelledby="releases-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Delivery evidence</span><h2 id="releases-heading">What has actually shipped?</h2></div><p>The normalized Releases query is present and contains no release records.</p></div>{site.empty_state("No releases projected", "This query is empty for the represented snapshot; it does not prove that historical, private, external, or otherwise unprojected releases do not exist.", "not_applicable")}</section>'''

    latest_id = latest_release_id(records)
    total_includes = sum(len(site.require_list(record.get("includes"))) for record in records)
    total_deployments = sum(len(site.require_list(record.get("deployments"))) for record in records)
    latest = next(record for record in records if site.require_object(record.get("entity")).get("id") == latest_id)
    latest_entity = site.require_object(latest["entity"])
    latest_title = latest_entity.get("title") or latest_entity.get("key") or latest_entity.get("id")
    releases_html = "".join(render_release(record, latest_release_id=latest_id) for record in records)
    return f'''<section class="ri-section ri-section--lead" aria-labelledby="releases-heading">
      <div class="ri-section-heading"><div><span class="ri-eyebrow">Delivery evidence</span><h2 id="releases-heading">What has actually shipped?</h2></div><p>Release publication, included work, and deployment evidence stay separate and traceable.</p></div>
      <div class="ri-roadmap-metrics" aria-label="Release summary"><article><strong>{len(records)}</strong><span>projected releases</span></article><article><strong>{total_includes}</strong><span>included entities</span></article><article><strong>{total_deployments}</strong><span>deployments</span></article></div>
      <p><strong>Latest projected release:</strong> {site.escaped(latest_title)} · {site.escaped(site.format_date(latest["published_at"]))}</p>
      <details class="ri-progress-rules"><summary>What this view does and does not claim</summary><p>Observatory supplies release membership, publication time, deployments, and boundary-event identifiers. Relay presents that evidence without inferring package-manager availability, installability, rollback support, release quality, delivery velocity, or unreleased work.</p></details>
    </section>
    <section class="ri-section" aria-labelledby="release-history-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Shipped history</span><h2 id="release-history-heading">Projected release boundaries</h2></div><p>The normalized record order is preserved; the latest publication is highlighted independently.</p></div><ol class="ri-record-list" aria-label="Projected releases">{releases_html}</ol></section>'''


def render_page(
    *,
    snapshot: dict[str, Any] | None,
    summary: dict[str, Any],
    repository: str,
    source_commit: str,
) -> str:
    """Compose Releases through Relay's canonical shared shell."""

    observed_at = str(
        snapshot.get("observed_at") if snapshot else summary.get("generated_at") or ""
    )
    freshness = site.normalize_state(
        site.require_object(snapshot.get("coverage")).get("status") if snapshot else "unknown"
    )
    return site.shell_document(
        route="releases",
        route_label="Releases",
        repository=repository,
        source_commit=source_commit,
        observed_at=observed_at,
        freshness=freshness,
        summary=summary,
        body=releases_body(snapshot),
        prefix="../",
        snapshot_available=snapshot is not None,
    )


def main() -> int:
    """Validate shared inputs and replace only the generated Releases route."""

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
        output_root / "releases/index.html",
        render_page(
            snapshot=snapshot,
            summary=summary,
            repository=args.repository,
            source_commit=args.source_commit,
        ),
    )
    print(
        "Rendered Repository Intelligence Releases at "
        f"{output_root / 'releases/index.html'} for {args.repository}@{args.source_commit[:12]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
