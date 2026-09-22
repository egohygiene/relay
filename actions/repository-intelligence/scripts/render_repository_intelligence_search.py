# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Render the Repository Intelligence Search route from Observatory evidence."""

from __future__ import annotations

import argparse
import importlib.util
from collections import Counter
from pathlib import Path
from types import ModuleType
from typing import Any


class SearchViewError(ValueError):
    """Raised when a projected Search view cannot be rendered safely."""


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
    """Parse the bounded Search-route rendering interface."""

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
        raise SearchViewError(f"{label} must be a non-empty string")
    return value


def validate_search_record(value: Any, label: str) -> dict[str, Any]:
    """Validate the exact compact entity/search fields consumed by Relay."""

    record = site.require_object(value)
    if not record:
        raise SearchViewError(f"{label} must be an object")
    for member in (
        "id",
        "key",
        "kind",
        "repository",
        "state",
        "assertion",
        "confidence",
        "freshness",
        "visibility",
        "canonical_url",
        "search_text",
    ):
        require_string(record.get(member), f"{label}.{member}")
    if not site.safe_href(record["canonical_url"]):
        raise SearchViewError(
            f"{label}.canonical_url must be a credential-free HTTPS URL"
        )
    title = record.get("title")
    if title is not None and (not isinstance(title, str) or not title):
        raise SearchViewError(f"{label}.title must be null or a non-empty string")
    return record


def validate_search_view(value: Any) -> dict[str, Any]:
    """Validate Observatory's accepted Search projection without extending it."""

    search_view = site.require_object(value)
    if not search_view:
        raise SearchViewError("snapshot views.search must be an object")
    records = search_view.get("records")
    if not isinstance(records, list):
        raise SearchViewError("snapshot views.search.records must be an array")
    identifiers: set[str] = set()
    for index, candidate in enumerate(records):
        record = validate_search_record(
            candidate, f"snapshot views.search.records[{index}]"
        )
        if record["id"] in identifiers:
            raise SearchViewError("snapshot views.search record IDs must be unique")
        identifiers.add(record["id"])
    return search_view


def render_freshness_filter(records: list[dict[str, Any]]) -> str:
    """Expose evidence freshness without turning it into a relevance score."""

    counts = Counter(site.normalize_state(record.get("freshness")) for record in records)
    order = ("current", "stale", "unknown", "not_applicable")
    options = "".join(
        f'<option value="{site.escaped(value)}">{site.escaped(site.state_label(value))} ({counts[value]})</option>'
        for value in order
        if counts[value]
    )
    return f'''<details class="ri-decision-filters" open><summary>Search evidence facets</summary><div><label><span>Freshness</span><select data-filter-extra="freshness"><option value="all">All freshness</option>{options}</select></label></div><p>The shared text, state, and kind controls filter these normalized records. Freshness remains an evidence state, not result quality.</p></details>'''


def render_kind_summary(records: list[dict[str, Any]]) -> str:
    """Render compact record counts by projected entity kind."""

    counts = Counter(site.normalize_state(record.get("kind")) for record in records)
    return "".join(
        f'<article><strong>{count}</strong><span>{site.escaped(site.state_label(kind))}</span></article>'
        for kind, count in sorted(counts.items())
    )


def render_search_record(record: dict[str, Any]) -> str:
    """Render one normalized searchable entity without local ranking semantics."""

    state = site.normalize_state(record.get("state"))
    kind = site.normalize_state(record.get("kind"))
    freshness = site.normalize_state(record.get("freshness"))
    title = record.get("title") or record.get("key") or record.get("id")
    return f'''<li><article class="ri-record" data-entity-id="{site.escaped(record.get("id"))}" data-filter-item{site.source_repository_attribute(record)} data-state="{site.escaped(state)}" data-kind="{site.escaped(kind)}" data-filter-freshness="{site.escaped(freshness)}" data-search="{site.escaped(record["search_text"])}">
      <div class="ri-record__top"><span class="ri-eyebrow">{site.escaped(site.state_label(kind))}</span><span>{site.status_pill(state)} {site.status_pill(freshness, f"Freshness: {site.state_label(freshness)}")}</span></div>
      <h3>{site.escaped(title)}</h3>
      <p>{site.escaped(record.get("repository"))} · {site.escaped(record.get("key"))}</p>
      <dl class="ri-provenance"><div><dt>Assertion</dt><dd>{site.escaped(site.state_label(record.get("assertion")))}</dd></div><div><dt>Freshness</dt><dd>{site.escaped(site.state_label(record.get("freshness")))}</dd></div></dl>
      <p>{site.source_link(record, "Open canonical source")}</p>
    </article></li>'''


def search_body(snapshot: dict[str, Any] | None) -> str:
    """Render normalized entity discovery without provider or semantic search."""

    if snapshot is None:
        return f'''<section class="ri-section ri-section--lead" aria-labelledby="search-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Evidence discovery</span><h2 id="search-heading">Find a normalized repository object</h2></div><p>Only Observatory's public-safe Search projection is searchable here.</p></div>{site.empty_state("Search evidence unavailable", "Supply a repository- and commit-matched Observatory read model to search normalized Repository Intelligence entities.", "partial")}</section>'''

    views = site.require_object(snapshot.get("views"))
    if "search" not in views:
        return f'''<section class="ri-section ri-section--lead" aria-labelledby="search-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Evidence discovery</span><h2 id="search-heading">Find a normalized repository object</h2></div><p>This snapshot predates or omits the normalized Search query.</p></div>{site.empty_state("Search view not projected", "The represented snapshot is available, but it does not contain views.search. Relay will not rebuild a search index from other views, canonical URLs, or provider data.", "partial")}</section>'''

    search_view = validate_search_view(views.get("search"))
    records = [site.require_object(value) for value in site.require_list(search_view["records"])]
    if not records:
        return f'''<section class="ri-section ri-section--lead" aria-labelledby="search-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Evidence discovery</span><h2 id="search-heading">Find a normalized repository object</h2></div><p>The normalized Search query is present and contains no records.</p></div>{site.empty_state("No searchable records projected", "This empty projection is distinct from a browser query that happens to match zero records and does not prove that private or unprojected repository objects do not exist.", "not_applicable")}</section>'''

    return f'''<section class="ri-section ri-section--lead" aria-labelledby="search-heading">
      <div class="ri-section-heading"><div><span class="ri-eyebrow">Evidence discovery</span><h2 id="search-heading">Find a normalized repository object</h2></div><p>Search the accepted Repository Intelligence entity index, then follow the canonical source to inspect or act.</p></div>
      <div class="ri-roadmap-metrics" aria-label="Search index summary"><article><strong>{len(records)}</strong><span>searchable records</span></article>{render_kind_summary(records)}</div>
      <details class="ri-progress-rules"><summary>What this search can match</summary><p>Observatory supplies each record's normalized <code>search_text</code> from title, key, kind, state, and repository. Relay filters that supplied string exactly; it does not search issue bodies, commit diffs, source files, ADR prose, or external providers, and the current contract does not identify which individual field matched.</p></details>
      {render_freshness_filter(records)}
    </section>
    <section class="ri-section" aria-labelledby="search-results-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Normalized index</span><h2 id="search-results-heading">Searchable evidence</h2></div><p>Result order is the deterministic Observatory projection order; Relay does not rank by activity or inferred relevance.</p></div><ol class="ri-record-list" aria-label="Normalized Repository Intelligence search records">{"".join(render_search_record(record) for record in records)}</ol></section>'''


def render_page(
    *,
    snapshot: dict[str, Any] | None,
    summary: dict[str, Any],
    repository: str,
    source_commit: str,
) -> str:
    """Compose Search through Relay's canonical shared shell."""

    observed_at = str(
        snapshot.get("observed_at") if snapshot else summary.get("generated_at") or ""
    )
    freshness = site.normalize_state(
        site.require_object(snapshot.get("coverage")).get("status")
        if snapshot
        else "unknown"
    )
    return site.shell_document(
        route="search",
        route_label="Search",
        repository=repository,
        source_commit=source_commit,
        observed_at=observed_at,
        freshness=freshness,
        summary=summary,
        body=search_body(snapshot),
        prefix="../",
        snapshot_available=snapshot is not None,
    )


def main() -> int:
    """Validate shared inputs and replace only the generated Search route."""

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
        output_root / "search/index.html",
        render_page(
            snapshot=snapshot,
            summary=summary,
            repository=args.repository,
            source_commit=args.source_commit,
        ),
    )
    print(
        "Rendered Repository Intelligence Search at "
        f"{output_root / 'search/index.html'} for {args.repository}@{args.source_commit[:12]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
