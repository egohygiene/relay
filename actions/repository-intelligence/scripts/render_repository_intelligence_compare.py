# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Render the Repository Intelligence Compare route from Observatory evidence."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import re
from types import ModuleType
from typing import Any


COMPARE_SCHEMA = "egohygiene.observatory.repository-intelligence-compare/v1"
COMPARE_CONTRACT_VERSION = "1.0.0-alpha.1"
COMPARE_VIEW_NAMES = (
    "roadmap",
    "decisions",
    "journey",
    "now",
    "dependencies",
    "health",
    "releases",
    "work",
    "search",
)
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


class CompareViewError(ValueError):
    """Raised when normalized comparison evidence cannot be rendered safely."""


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
    """Parse the bounded Compare-route rendering interface."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--provenance", required=True)
    parser.add_argument("--snapshot", default="")
    parser.add_argument("--comparison", default="")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--source-commit", required=True)
    return parser.parse_args()


def require_string(value: Any, label: str) -> str:
    """Return one non-empty string or reject incompatible comparison evidence."""

    if not isinstance(value, str) or not value:
        raise CompareViewError(f"{label} must be a non-empty string")
    return value


def require_exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    """Fail closed on alpha comparison-shape drift."""

    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        details = []
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected {', '.join(unexpected)}")
        raise CompareViewError(f"{label} has incompatible fields: {'; '.join(details)}")


def validate_boundary(value: Any, label: str) -> dict[str, Any]:
    """Validate one Observatory before/after comparison boundary."""

    boundary = site.require_object(value)
    if not boundary:
        raise CompareViewError(f"{label} must be an object")
    require_exact_keys(
        boundary,
        {"snapshot_id", "represented_commit", "observed_at"},
        label,
    )
    require_string(boundary.get("snapshot_id"), f"{label}.snapshot_id")
    represented_commit = require_string(
        boundary.get("represented_commit"), f"{label}.represented_commit"
    )
    if not site.FULL_SHA.fullmatch(represented_commit):
        raise CompareViewError(f"{label}.represented_commit must be a full lowercase Git SHA")
    observed_at = require_string(boundary.get("observed_at"), f"{label}.observed_at")
    try:
        site.parse_rfc3339(observed_at, f"{label}.observed_at")
    except site.SiteInputError as error:
        raise CompareViewError(str(error)) from error
    return boundary


def validate_identifier_list(value: Any, label: str) -> list[str]:
    """Validate one deterministic list of stable graph IDs."""

    if not isinstance(value, list):
        raise CompareViewError(f"{label} must be an array")
    identifiers = [require_string(item, f"{label}[{index}]") for index, item in enumerate(value)]
    if len(identifiers) != len(set(identifiers)):
        raise CompareViewError(f"{label} must not contain duplicate IDs")
    return identifiers


def validate_changed_records(value: Any, label: str) -> list[dict[str, Any]]:
    """Validate IDs and exact structural field paths emitted by Observatory."""

    if not isinstance(value, list):
        raise CompareViewError(f"{label} must be an array")
    records: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for index, candidate in enumerate(value):
        record_label = f"{label}[{index}]"
        record = site.require_object(candidate)
        if not record:
            raise CompareViewError(f"{record_label} must be an object")
        require_exact_keys(record, {"id", "fields"}, record_label)
        identifier = require_string(record.get("id"), f"{record_label}.id")
        if identifier in identifiers:
            raise CompareViewError(f"{label} must not contain duplicate IDs")
        identifiers.add(identifier)
        fields = record.get("fields")
        if not isinstance(fields, list) or not fields:
            raise CompareViewError(f"{record_label}.fields must be a non-empty array")
        normalized_fields = [
            require_string(field, f"{record_label}.fields[{field_index}]")
            for field_index, field in enumerate(fields)
        ]
        if len(normalized_fields) != len(set(normalized_fields)):
            raise CompareViewError(f"{record_label}.fields must not contain duplicates")
        records.append(record)
    return records


def validate_delta(value: Any, label: str) -> dict[str, Any]:
    """Validate one Observatory collection delta without adding semantics."""

    delta = site.require_object(value)
    if not delta:
        raise CompareViewError(f"{label} must be an object")
    require_exact_keys(delta, {"added", "removed", "changed"}, label)
    added = validate_identifier_list(delta.get("added"), f"{label}.added")
    removed = validate_identifier_list(delta.get("removed"), f"{label}.removed")
    changed = validate_changed_records(delta.get("changed"), f"{label}.changed")
    changed_ids = {record["id"] for record in changed}
    overlaps = (set(added) & set(removed)) | (set(added) & changed_ids) | (set(removed) & changed_ids)
    if overlaps:
        raise CompareViewError(
            f"{label} categories must be disjoint; repeated IDs: {', '.join(sorted(overlaps))}"
        )
    return delta


def validate_view_deltas(value: Any) -> list[dict[str, Any]]:
    """Validate deterministic per-view digests and their changed flags."""

    if not isinstance(value, list):
        raise CompareViewError("comparison.views must be an array")
    records: list[dict[str, Any]] = []
    names: list[str] = []
    for index, candidate in enumerate(value):
        label = f"comparison.views[{index}]"
        record = site.require_object(candidate)
        if not record:
            raise CompareViewError(f"{label} must be an object")
        require_exact_keys(
            record,
            {"view", "changed", "before_digest", "after_digest"},
            label,
        )
        name = require_string(record.get("view"), f"{label}.view")
        names.append(name)
        changed = record.get("changed")
        if type(changed) is not bool:
            raise CompareViewError(f"{label}.changed must be a boolean")
        before_digest = require_string(record.get("before_digest"), f"{label}.before_digest")
        after_digest = require_string(record.get("after_digest"), f"{label}.after_digest")
        if not DIGEST_PATTERN.fullmatch(before_digest) or not DIGEST_PATTERN.fullmatch(after_digest):
            raise CompareViewError(f"{label} digests must be lowercase SHA-256 identifiers")
        if changed != (before_digest != after_digest):
            raise CompareViewError(f"{label}.changed contradicts its before/after digests")
        records.append(record)
    if tuple(names) != COMPARE_VIEW_NAMES:
        raise CompareViewError(
            "comparison.views must preserve Observatory's canonical view order: "
            + ", ".join(COMPARE_VIEW_NAMES)
        )
    return records


def current_entity_index(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index current compact entity refs only from the accepted Search view."""

    views = site.require_object(snapshot.get("views"))
    if "search" not in views:
        return {}
    search = site.require_object(views.get("search"))
    if not search:
        raise CompareViewError(
            "snapshot views.search must be an object when projected"
        )
    records = search.get("records")
    if not isinstance(records, list):
        raise CompareViewError(
            "the matching after snapshot must contain views.search.records for stable current-entity resolution"
        )
    index: dict[str, dict[str, Any]] = {}
    for position, candidate in enumerate(records):
        label = f"snapshot views.search.records[{position}]"
        record = site.require_object(candidate)
        identifier = require_string(record.get("id"), f"{label}.id")
        if identifier in index:
            raise CompareViewError("snapshot views.search record IDs must be unique")
        canonical_url = require_string(record.get("canonical_url"), f"{label}.canonical_url")
        if not site.safe_href(canonical_url):
            raise CompareViewError(
                f"{label}.canonical_url must be a credential-free HTTPS URL"
            )
        index[identifier] = record
    return index


def validate_entity_delta_against_snapshot(
    delta: dict[str, Any],
    entity_index: dict[str, dict[str, Any]],
) -> None:
    """Bind entity deltas to the supplied Observatory `after` snapshot."""

    added = set(site.require_list(delta.get("added")))
    removed = set(site.require_list(delta.get("removed")))
    changed = {
        site.require_object(record).get("id")
        for record in site.require_list(delta.get("changed"))
    }
    current_ids = set(entity_index)
    missing_current = sorted((added | changed) - current_ids)
    still_present = sorted(removed & current_ids)
    if missing_current:
        raise CompareViewError(
            "comparison entity additions/changes are missing from the matching after snapshot: "
            + ", ".join(missing_current)
        )
    if still_present:
        raise CompareViewError(
            "comparison removed entities are still present in the matching after snapshot: "
            + ", ".join(still_present)
        )


def validate_comparison(
    value: Any,
    *,
    repository: str,
    source_commit: str,
    snapshot: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Validate Observatory comparison evidence and bind it to the current snapshot."""

    comparison = site.require_object(value)
    if not comparison:
        raise CompareViewError("Observatory comparison must be an object")
    require_exact_keys(
        comparison,
        {
            "schema",
            "contract_version",
            "repository",
            "before",
            "after",
            "entities",
            "relationships",
            "events",
            "views",
        },
        "comparison",
    )
    if comparison.get("schema") != COMPARE_SCHEMA:
        raise CompareViewError(
            f"unsupported comparison schema: {comparison.get('schema')!r}; expected {COMPARE_SCHEMA!r}"
        )
    if comparison.get("contract_version") != COMPARE_CONTRACT_VERSION:
        raise CompareViewError(
            "unsupported comparison contract version: "
            f"{comparison.get('contract_version')!r}; expected {COMPARE_CONTRACT_VERSION!r}"
        )
    if comparison.get("repository") != repository:
        raise CompareViewError("comparison repository must match the rendered repository")
    before = validate_boundary(comparison.get("before"), "comparison.before")
    after = validate_boundary(comparison.get("after"), "comparison.after")
    if after["represented_commit"] != source_commit:
        raise CompareViewError(
            "comparison after.represented_commit must match the rendered source commit"
        )
    entities = validate_delta(comparison.get("entities"), "comparison.entities")
    validate_delta(comparison.get("relationships"), "comparison.relationships")
    validate_delta(comparison.get("events"), "comparison.events")
    validate_view_deltas(comparison.get("views"))
    if snapshot is None:
        raise CompareViewError(
            "a normalized comparison requires the matching Observatory after snapshot"
        )
    if snapshot.get("represented_commit") != source_commit:
        raise CompareViewError("after snapshot represented_commit must match source commit")
    if after["snapshot_id"] != snapshot.get("snapshot_id"):
        raise CompareViewError(
            "comparison after.snapshot_id must match the supplied Observatory snapshot"
        )
    search_projected = "search" in site.require_object(snapshot.get("views"))
    entity_index = current_entity_index(snapshot)
    if search_projected:
        validate_entity_delta_against_snapshot(entities, entity_index)
    return comparison, entity_index


def render_boundary(label: str, boundary: dict[str, Any], repository: str) -> str:
    """Render one normalized snapshot boundary without claiming causality."""

    commit = boundary["represented_commit"]
    commit_url = f"https://github.com/{repository}/commit/{commit}"
    return f'''<article class="ri-panel"><span class="ri-eyebrow">{site.escaped(label)}</span><h3><a href="{site.escaped(commit_url)}"><code>{site.escaped(commit[:12])}</code></a></h3><p>{site.escaped(site.format_date(boundary["observed_at"]))}</p><p><small>{site.escaped(boundary["snapshot_id"])}</small></p></article>'''


def current_source_link(identifier: str, entity_index: dict[str, dict[str, Any]]) -> str:
    """Link only stable IDs that exist in the validated matching after snapshot."""

    record = entity_index.get(identifier)
    if record is None:
        return ""
    return f'<p>{site.source_link(record, "Open current canonical source")}</p>'


def comparison_record_search_text(identifier: str, fields: list[str]) -> str:
    """Build local text filtering only from comparison evidence already displayed."""

    return " ".join([identifier, *fields]).lower()


def render_identifier_record(
    identifier: str,
    *,
    category: str,
    collection: str,
    entity_index: dict[str, dict[str, Any]],
) -> str:
    """Render one structural added/removed ID without inventing historical metadata."""

    current = entity_index.get(identifier) if collection == "Entities" and category != "Removed" else None
    title = current.get("title") or current.get("key") if current else None
    state = site.normalize_state(current.get("state")) if current else "unknown"
    kind = site.normalize_state(current.get("kind")) if current else "unknown"
    heading = f"<h4>{site.escaped(title)}</h4>" if title else ""
    return f'''<li><article class="ri-record" data-entity-id="{site.escaped(identifier)}" data-filter-item data-state="{site.escaped(state)}" data-kind="{site.escaped(kind)}" data-search="{site.escaped(identifier.lower())}"><div class="ri-record__top"><span class="ri-eyebrow">{site.escaped(category)} {site.escaped(collection[:-1].lower())}</span><span>{site.status_pill(category.lower(), category)}</span></div>{heading}<p><code>{site.escaped(identifier)}</code></p>{current_source_link(identifier, entity_index) if current else ""}</article></li>'''


def render_changed_record(
    record: dict[str, Any],
    *,
    collection: str,
    entity_index: dict[str, dict[str, Any]],
) -> str:
    """Render one field-changed structural record exactly as Observatory reported it."""

    identifier = record["id"]
    fields = [str(field) for field in site.require_list(record["fields"])]
    current = entity_index.get(identifier) if collection == "Entities" else None
    title = current.get("title") or current.get("key") if current else None
    state = site.normalize_state(current.get("state")) if current else "unknown"
    kind = site.normalize_state(current.get("kind")) if current else "unknown"
    heading = f"<h4>{site.escaped(title)}</h4>" if title else ""
    field_items = "".join(f"<li><code>{site.escaped(field)}</code></li>" for field in fields)
    return f'''<li><article class="ri-record" data-entity-id="{site.escaped(identifier)}" data-filter-item data-state="{site.escaped(state)}" data-kind="{site.escaped(kind)}" data-search="{site.escaped(comparison_record_search_text(identifier, fields))}"><div class="ri-record__top"><span class="ri-eyebrow">Changed {site.escaped(collection[:-1].lower())}</span><span>{site.status_pill("changed", "Changed")}</span></div>{heading}<p><code>{site.escaped(identifier)}</code></p><details class="ri-evidence" open><summary><span><strong>Changed field paths</strong><small>{len(fields)} projected</small></span><span aria-hidden="true">+</span></summary><ul class="ri-source-list">{field_items}</ul></details>{current_source_link(identifier, entity_index) if current else ""}</article></li>'''


def render_delta_group(
    label: str,
    identifiers: list[str],
    *,
    collection: str,
    entity_index: dict[str, dict[str, Any]],
) -> str:
    """Render one added/removed category with progressive disclosure."""

    if not identifiers:
        return site.empty_state(
            f"No {label.lower()} {collection.lower()}",
            "The normalized comparison reports none in this category.",
            "empty",
        )
    records = "".join(
        render_identifier_record(
            identifier,
            category=label,
            collection=collection,
            entity_index=entity_index,
        )
        for identifier in identifiers
    )
    return f'<ol class="ri-record-list" aria-label="{site.escaped(label)} {site.escaped(collection.lower())}">{records}</ol>'


def render_changed_group(
    records: list[dict[str, Any]],
    *,
    collection: str,
    entity_index: dict[str, dict[str, Any]],
) -> str:
    """Render field-changed records without attaching causal meaning."""

    if not records:
        return site.empty_state(
            f"No field-changed {collection.lower()}",
            "The normalized comparison reports none in this category.",
            "empty",
        )
    rendered = "".join(
        render_changed_record(
            record,
            collection=collection,
            entity_index=entity_index,
        )
        for record in records
    )
    return f'<ol class="ri-record-list" aria-label="Field-changed {site.escaped(collection.lower())}">{rendered}</ol>'


def render_delta_section(
    collection: str,
    delta: dict[str, Any],
    entity_index: dict[str, dict[str, Any]],
) -> str:
    """Render one normalized collection delta with separate structural categories."""

    added = [str(value) for value in site.require_list(delta["added"])]
    removed = [str(value) for value in site.require_list(delta["removed"])]
    changed = [site.require_object(value) for value in site.require_list(delta["changed"])]
    section_id = f"compare-{collection.lower()}"
    return f'''<section class="ri-section" aria-labelledby="{site.escaped(section_id)}-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Structural delta</span><h2 id="{site.escaped(section_id)}-heading">{site.escaped(collection)}</h2></div><p>Addition, removal, and field change are distinct facts; none implies improvement, regression, or resolution.</p></div><div class="ri-roadmap-metrics" aria-label="{site.escaped(collection)} comparison summary"><article><strong>{len(added)}</strong><span>added</span></article><article><strong>{len(removed)}</strong><span>removed</span></article><article><strong>{len(changed)}</strong><span>field-changed</span></article></div><details class="ri-evidence"><summary><span><strong>Added</strong><small>{len(added)} IDs</small></span><span aria-hidden="true">+</span></summary>{render_delta_group("Added", added, collection=collection, entity_index=entity_index)}</details><details class="ri-evidence"><summary><span><strong>Removed</strong><small>{len(removed)} IDs</small></span><span aria-hidden="true">+</span></summary>{render_delta_group("Removed", removed, collection=collection, entity_index=entity_index)}</details><details class="ri-evidence"><summary><span><strong>Field-changed</strong><small>{len(changed)} IDs</small></span><span aria-hidden="true">+</span></summary>{render_changed_group(changed, collection=collection, entity_index=entity_index)}</details></section>'''


def render_view_comparison(records: list[dict[str, Any]]) -> str:
    """Render per-view digest change without explaining why a view changed."""

    cards = []
    for record in records:
        changed = bool(record["changed"])
        state = "changed" if changed else "unchanged"
        before_digest = str(record["before_digest"])
        after_digest = str(record["after_digest"])
        cards.append(
            f'''<li><article class="ri-record" data-filter-item data-state="unknown" data-kind="unknown" data-search="{site.escaped(str(record["view"]).lower())}"><div class="ri-record__top"><span class="ri-eyebrow">{site.escaped(site.state_label(record["view"]))} view</span><span>{site.status_pill(state, site.state_label(state))}</span></div><h3>{site.escaped(site.state_label(record["view"]))}</h3><details class="ri-evidence"><summary><span><strong>Content digests</strong><small>{"different" if changed else "identical"}</small></span><span aria-hidden="true">+</span></summary><dl class="ri-provenance"><div><dt>Before</dt><dd><code>{site.escaped(before_digest)}</code></dd></div><div><dt>After</dt><dd><code>{site.escaped(after_digest)}</code></dd></div></dl></details></article></li>'''
        )
    return f'''<section class="ri-section" aria-labelledby="compare-views-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Derived views</span><h2 id="compare-views-heading">Which normalized views changed?</h2></div><p>Digest differences report changed content only. They do not explain cause, quality, or significance.</p></div><ol class="ri-record-list" aria-label="Repository Intelligence view digest comparison">{"".join(cards)}</ol></section>'''


def has_structural_changes(comparison: dict[str, Any]) -> bool:
    """Return whether Observatory reported any collection or view change."""

    for collection in ("entities", "relationships", "events"):
        delta = site.require_object(comparison[collection])
        if any(site.require_list(delta.get(category)) for category in ("added", "removed", "changed")):
            return True
    return any(bool(site.require_object(record).get("changed")) for record in site.require_list(comparison["views"]))


def comparison_body(
    comparison: dict[str, Any] | None,
    *,
    snapshot: dict[str, Any] | None,
    repository: str,
    source_commit: str,
) -> str:
    """Render Observatory structural change without manufacturing causality."""

    if comparison is None:
        return f'''<section class="ri-section ri-section--lead" aria-labelledby="compare-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Snapshot difference</span><h2 id="compare-heading">What structurally changed?</h2></div><p>Compare requires Observatory's separate two-snapshot comparison artifact.</p></div>{site.empty_state("Comparison evidence unavailable", "Supply a public-safe Observatory comparison plus its matching current after snapshot. Relay will not reconstruct historical evidence from Git, Journey, or provider APIs.", "partial")}</section>'''

    validated, entity_index = validate_comparison(
        comparison,
        repository=repository,
        source_commit=source_commit,
        snapshot=snapshot,
    )
    before = site.require_object(validated["before"])
    after = site.require_object(validated["after"])
    changed_views = sum(
        1 for record in site.require_list(validated["views"]) if site.require_object(record).get("changed") is True
    )
    entity_delta = site.require_object(validated["entities"])
    relationship_delta = site.require_object(validated["relationships"])
    event_delta = site.require_object(validated["events"])
    total_changes = sum(
        len(site.require_list(delta[category]))
        for delta in (entity_delta, relationship_delta, event_delta)
        for category in ("added", "removed", "changed")
    )
    no_change = ""
    if not has_structural_changes(validated):
        no_change = site.empty_state(
            "No normalized structural differences",
            "Observatory reports identical entity, relationship, event, and view structure across these two snapshots. This is not a claim that raw repository bytes are identical.",
            "not_applicable",
        )
    return f'''<section class="ri-section ri-section--lead" aria-labelledby="compare-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Snapshot difference</span><h2 id="compare-heading">What structurally changed?</h2></div><p>Read a deterministic normalized before/after delta without turning structural change into a causal story.</p></div><div class="ri-now-grid">{render_boundary("Before", before, repository)}{render_boundary("After", after, repository)}</div><div class="ri-roadmap-metrics" aria-label="Comparison orientation"><article><strong>{total_changes}</strong><span>collection delta records</span></article><article><strong>{changed_views}</strong><span>changed views</span></article><article><strong>{len(COMPARE_VIEW_NAMES) - changed_views}</strong><span>unchanged views</span></article></div><details class="ri-progress-rules"><summary>What this comparison means</summary><p>Observatory reports stable IDs that were added or removed, exact field paths whose normalized values changed, and per-view content digest differences. Relay does not claim which commit, person, decision, or event caused those differences; a removal is not automatically a resolution, and an addition is not automatically an improvement.</p></details>{no_change}</section>{render_delta_section("Entities", entity_delta, entity_index)}{render_delta_section("Relationships", relationship_delta, entity_index)}{render_delta_section("Events", event_delta, entity_index)}{render_view_comparison([site.require_object(record) for record in site.require_list(validated["views"])])}'''


def render_page(
    *,
    comparison: dict[str, Any] | None,
    snapshot: dict[str, Any] | None,
    summary: dict[str, Any],
    repository: str,
    source_commit: str,
) -> str:
    """Compose Compare through Relay's canonical shared shell."""

    observed_at = str(
        snapshot.get("observed_at") if snapshot else summary.get("generated_at") or ""
    )
    freshness = site.projection_freshness(
        snapshot,
        "compare",
        projected=comparison is not None,
    )
    return site.shell_document(
        route="compare",
        route_label="Compare",
        repository=repository,
        source_commit=source_commit,
        observed_at=observed_at,
        freshness=freshness,
        summary=summary,
        body=comparison_body(
            comparison,
            snapshot=snapshot,
            repository=repository,
            source_commit=source_commit,
        ),
        prefix="../",
        snapshot_available=snapshot is not None,
    )


def main() -> int:
    """Validate shared inputs and replace only the generated Compare route."""

    args = parse_arguments()
    repository_root = Path(args.repository_root).resolve(strict=True)
    output_root = Path(args.output_root).resolve()
    summary_path = Path(args.summary).resolve()
    provenance_path = Path(args.provenance).resolve()
    snapshot_path = Path(args.snapshot).absolute() if args.snapshot else None
    comparison_path = Path(args.comparison).absolute() if args.comparison else None
    if not site.FULL_SHA.fullmatch(args.source_commit):
        raise SystemExit("source-commit must be a full lowercase Git SHA")
    for path, label in (
        (output_root, "output root"),
        (summary_path, "dashboard summary"),
        (provenance_path, "bundle provenance"),
        *(((snapshot_path, "Observatory snapshot"),) if snapshot_path is not None else ()),
        *(((comparison_path, "Observatory comparison"),) if comparison_path is not None else ()),
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
    comparison = None
    if comparison_path is not None:
        if snapshot is None:
            raise SystemExit(
                "observatory-comparison requires the matching observatory-snapshot"
            )
        if not comparison_path.is_file():
            raise SystemExit(f"Observatory comparison is unavailable: {comparison_path}")
        comparison = site.load_object(comparison_path, "Observatory comparison")
        validate_comparison(
            comparison,
            repository=args.repository,
            source_commit=args.source_commit,
            snapshot=snapshot,
        )
    site.atomic_write(
        output_root / "compare/index.html",
        render_page(
            comparison=comparison,
            snapshot=snapshot,
            summary=summary,
            repository=args.repository,
            source_commit=args.source_commit,
        ),
    )
    print(
        "Rendered Repository Intelligence Compare at "
        f"{output_root / 'compare/index.html'} for {args.repository}@{args.source_commit[:12]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
