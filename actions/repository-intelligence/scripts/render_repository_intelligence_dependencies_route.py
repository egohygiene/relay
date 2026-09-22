# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Render the Repository Intelligence dependency-impact route from Observatory evidence."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import re
from types import ModuleType
from typing import Any

DEPENDENCY_RELATIONSHIP_TYPES = {"blocks", "depends-on"}
ASSERTION_STATES = {"authoritative", "inferred", "unknown"}
FRESHNESS_STATES = {"current", "not_applicable", "stale", "unknown"}
REPOSITORY_PATTERN = re.compile(
    r"^(?!\.{1,2}/)(?![^/]+/\.{1,2}$)[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
)


class DependencyViewError(ValueError):
    """Raised when a projected Dependencies view cannot be rendered safely."""


def load_site_module() -> ModuleType:
    """Load Relay's canonical shared shell without duplicating its presentation contract."""

    path = Path(__file__).with_name("generate_repository_intelligence_site.py")
    spec = importlib.util.spec_from_file_location("relay_repository_intelligence_site", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Repository Intelligence shell module could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


site = load_site_module()


def parse_arguments() -> argparse.Namespace:
    """Parse the bounded dependency-route rendering interface."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--provenance", required=True)
    parser.add_argument("--snapshot", default="")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--source-commit", required=True)
    return parser.parse_args()


def require_non_empty_string(value: Any, label: str) -> str:
    """Return one non-empty string or reject the incompatible projection."""

    if not isinstance(value, str) or not value:
        raise DependencyViewError(f"{label} must be a non-empty string")
    return value


def validate_endpoint(value: Any, label: str) -> dict[str, Any]:
    """Validate the compact entity fields needed for dependency presentation."""

    endpoint = site.require_object(value)
    if not endpoint:
        raise DependencyViewError(f"{label} must be an object")
    for member in (
        "assertion",
        "canonical_url",
        "confidence",
        "freshness",
        "id",
        "key",
        "kind",
        "repository",
        "state",
        "visibility",
    ):
        require_non_empty_string(endpoint.get(member), f"{label}.{member}")
    if endpoint["assertion"] not in ASSERTION_STATES:
        raise DependencyViewError(f"{label}.assertion uses an unsupported state")
    if endpoint["confidence"] not in ASSERTION_STATES:
        raise DependencyViewError(f"{label}.confidence uses an unsupported state")
    if endpoint["freshness"] not in FRESHNESS_STATES:
        raise DependencyViewError(f"{label}.freshness uses an unsupported state")
    if not REPOSITORY_PATTERN.fullmatch(endpoint["repository"]):
        raise DependencyViewError(f"{label}.repository must use owner/name form")
    if not site.safe_href(endpoint["canonical_url"]):
        raise DependencyViewError(
            f"{label}.canonical_url must be a credential-free HTTPS URL"
        )
    title = endpoint.get("title")
    if title is not None and (not isinstance(title, str) or not title):
        raise DependencyViewError(f"{label}.title must be null or a non-empty string")
    return endpoint


def validate_dependencies_view(value: Any) -> dict[str, Any]:
    """Validate only the accepted Observatory Dependencies query shape used by Relay."""

    dependencies = site.require_object(value)
    if not dependencies:
        raise DependencyViewError("snapshot views.dependencies must be an object")
    external = dependencies.get("external_repositories")
    relationships = dependencies.get("relationships")
    if not isinstance(external, list) or any(
        not isinstance(repository, str) or not REPOSITORY_PATTERN.fullmatch(repository)
        for repository in external
    ):
        raise DependencyViewError(
            "snapshot views.dependencies.external_repositories must contain repository names"
        )
    if len(external) != len(set(external)):
        raise DependencyViewError(
            "snapshot views.dependencies.external_repositories must be unique"
        )
    if not isinstance(relationships, list):
        raise DependencyViewError(
            "snapshot views.dependencies.relationships must be an array"
        )

    identifiers: set[str] = set()
    for index, candidate in enumerate(relationships):
        relationship = site.require_object(candidate)
        if not relationship:
            raise DependencyViewError(
                f"snapshot views.dependencies.relationships[{index}] must be an object"
            )
        identifier = require_non_empty_string(
            relationship.get("id"),
            f"snapshot views.dependencies.relationships[{index}].id",
        )
        if identifier in identifiers:
            raise DependencyViewError("dependency relationship IDs must be unique")
        identifiers.add(identifier)
        relationship_type = require_non_empty_string(
            relationship.get("type"),
            f"snapshot views.dependencies.relationships[{index}].type",
        )
        if relationship_type not in DEPENDENCY_RELATIONSHIP_TYPES:
            raise DependencyViewError(
                f"snapshot views.dependencies.relationships[{index}] uses unsupported type "
                f"{relationship_type}"
            )
        assertion = require_non_empty_string(
            relationship.get("assertion"),
            f"snapshot views.dependencies.relationships[{index}].assertion",
        )
        confidence = require_non_empty_string(
            relationship.get("confidence"),
            f"snapshot views.dependencies.relationships[{index}].confidence",
        )
        freshness = require_non_empty_string(
            relationship.get("freshness"),
            f"snapshot views.dependencies.relationships[{index}].freshness",
        )
        if assertion not in ASSERTION_STATES or confidence not in ASSERTION_STATES:
            raise DependencyViewError(
                f"snapshot views.dependencies.relationships[{index}] uses unsupported assertion"
            )
        if freshness not in FRESHNESS_STATES:
            raise DependencyViewError(
                f"snapshot views.dependencies.relationships[{index}] uses unsupported freshness"
            )
        provenance = relationship.get("provenance")
        if (
            not isinstance(provenance, list)
            or not provenance
            or any(
                not isinstance(identifier, str) or not identifier
                for identifier in provenance
            )
        ):
            raise DependencyViewError(
                f"snapshot views.dependencies.relationships[{index}].provenance "
                "must contain source IDs"
            )
        validate_endpoint(
            relationship.get("source"),
            f"snapshot views.dependencies.relationships[{index}].source",
        )
        validate_endpoint(
            relationship.get("target"),
            f"snapshot views.dependencies.relationships[{index}].target",
        )
    return dependencies


def source_index(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index already-public graph sources for provenance expansion without live lookups."""

    graph = site.require_object(snapshot.get("graph"))
    index: dict[str, dict[str, Any]] = {}
    for candidate in site.require_list(graph.get("sources")):
        source = site.require_object(candidate)
        identifier = source.get("id")
        if isinstance(identifier, str) and identifier:
            index[identifier] = source
    return index


def relationship_scope(relationship: dict[str, Any]) -> str:
    """Classify only whether normalized endpoints cross repository identity."""

    source = site.require_object(relationship.get("source"))
    target = site.require_object(relationship.get("target"))
    return (
        "repository-local"
        if source.get("repository") == target.get("repository")
        else "cross-repository"
    )


def endpoint_label(endpoint: dict[str, Any]) -> str:
    """Choose one stable human label without inventing missing titles."""

    return str(endpoint.get("title") or endpoint.get("key") or endpoint.get("id"))


def render_endpoint(endpoint: dict[str, Any], *, label: str, repository: str) -> str:
    """Render one endpoint, preserving canonical identity and safe source boundaries."""

    href = site.safe_href(endpoint.get("canonical_url"))
    text = endpoint_label(endpoint)
    kind = site.state_label(endpoint.get("kind"))
    state = site.state_label(endpoint.get("state"))
    repository_name = str(endpoint.get("repository"))
    attributes = site.source_repository_attribute(endpoint)
    repository_root = f"https://github.com/{repository_name}"
    link_allowed = bool(href) and not (
        repository_name != repository and href.rstrip("/") == repository_root
    )
    canonical_note = ""
    if link_allowed:
        identity = (
            f'<a class="ri-link-chip"{attributes} href="{site.escaped(href)}">'
            f'<strong>{site.escaped(text)}</strong><small>{site.escaped(kind)} · '
            f'{site.escaped(state)}</small></a>'
        )
    else:
        identity = (
            f'<span class="ri-link-chip"{attributes}><strong>{site.escaped(text)}</strong>'
            f'<small>{site.escaped(kind)} · {site.escaped(state)}</small></span>'
        )
        if href:
            canonical_note = (
                '<small>Canonical identity: '
                f'<code>{site.escaped(href)}</code></small>'
            )
    return (
        f'<div><strong>{site.escaped(label)}</strong>{identity}'
        f'<small>{site.escaped(repository_name)}</small>{canonical_note}</div>'
    )


def render_provenance(
    relationship: dict[str, Any], sources: dict[str, dict[str, Any]]
) -> str:
    """Render normalized provenance IDs and any already-authorized canonical links."""

    records: list[str] = []
    for identifier in relationship["provenance"]:
        source = sources.get(identifier, {})
        href = site.safe_href(source.get("url"))
        repository_attribute = site.source_repository_attribute(source)
        if href:
            records.append(
                f'<li><a class="ri-link-chip"{repository_attribute} '
                f'href="{site.escaped(href)}">{site.escaped(identifier)} '
                '<span aria-hidden="true">↗</span></a></li>'
            )
        else:
            records.append(f'<li><code>{site.escaped(identifier)}</code></li>')
    source_label = "source" if len(records) == 1 else "sources"
    return (
        '<details class="ri-evidence"><summary><span><strong>Canonical evidence</strong>'
        f'<small>{len(records)} provenance {source_label}</small>'
        '</span><span aria-hidden="true">+</span></summary>'
        '<div class="ri-evidence__summary"><span>Relationship evidence is normalized by '
        'Observatory; linked sources remain canonical.</span></div>'
        '<div class="ri-evidence-viewport"><ol class="ri-evidence-list">'
        f'{"".join(records)}</ol></div></details>'
    )


def render_relationship(
    relationship: dict[str, Any],
    *,
    repository: str,
    sources: dict[str, dict[str, Any]],
) -> str:
    """Render one static relationship record with explicit direction and evidence state."""

    source = site.require_object(relationship.get("source"))
    target = site.require_object(relationship.get("target"))
    relationship_type = str(relationship["type"])
    assertion = str(relationship["assertion"])
    freshness = str(relationship["freshness"])
    confidence = str(relationship["confidence"])
    scope = relationship_scope(relationship)
    endpoint_states = {
        site.normalize_state(source.get("state")),
        site.normalize_state(target.get("state")),
    }
    endpoint_kinds = {
        site.normalize_state(source.get("kind")),
        site.normalize_state(target.get("kind")),
    }
    search = " ".join(
        str(value or "")
        for value in (
            relationship.get("id"),
            relationship_type,
            assertion,
            confidence,
            freshness,
            scope,
            source.get("title"),
            source.get("key"),
            source.get("kind"),
            source.get("state"),
            source.get("repository"),
            target.get("title"),
            target.get("key"),
            target.get("kind"),
            target.get("state"),
            target.get("repository"),
            *relationship["provenance"],
        )
    ).lower()
    readable_type = "depends on" if relationship_type == "depends-on" else "blocks"
    direction_label = (
        f"{endpoint_label(source)} {readable_type} {endpoint_label(target)}"
    )
    fragment = site.stable_fragment("dependency", relationship.get("id"))
    return f'''<li class="ri-evidence-record" id="{site.escaped(fragment)}" data-entity-id="{site.escaped(relationship.get("id"))}" data-filter-item data-states="{site.escaped(" ".join(sorted(endpoint_states)))}" data-kinds="{site.escaped(" ".join(sorted(endpoint_kinds)))}" data-filter-relationship="{site.escaped(relationship_type)}" data-filter-assertion="{site.escaped(assertion)}" data-filter-freshness="{site.escaped(freshness)}" data-filter-scope="{site.escaped(scope)}" data-search="{site.escaped(search)}">
      <div class="ri-evidence-record__top"><span class="ri-evidence-kind">{site.escaped(site.state_label(relationship_type))}</span><span>{site.status_pill(assertion, f"Assertion: {site.state_label(assertion)}")} {site.status_pill(freshness, f"Freshness: {site.state_label(freshness)}")}</span></div>
      <strong>{site.escaped(direction_label)}</strong>
      <p>Directed relationship · Confidence: {site.escaped(site.state_label(confidence))} · Scope: {site.escaped(site.state_label(scope))}</p>
      <div class="ri-relationship-grid" role="group" aria-label="{site.escaped(direction_label)}">
        {render_endpoint(source, label="Source", repository=repository)}
        {render_endpoint(target, label="Target", repository=repository)}
      </div>
      <dl class="ri-provenance"><div><dt>Relationship ID</dt><dd>{site.escaped(relationship.get("id"))}</dd></div><div><dt>Direction</dt><dd>Source → target</dd></div><div><dt>Assertion</dt><dd>{site.escaped(site.state_label(assertion))}</dd></div><div><dt>Freshness</dt><dd>{site.escaped(site.state_label(freshness))}</dd></div></dl>
      {render_provenance(relationship, sources)}
    </li>'''


def render_filter_controls(relationships: list[dict[str, Any]]) -> str:
    """Render URL-backed relationship facets from only values present in the snapshot."""

    assertions = sorted({str(value["assertion"]) for value in relationships})
    freshness = sorted({str(value["freshness"]) for value in relationships})
    scopes = sorted({relationship_scope(value) for value in relationships})

    def options(values: list[str]) -> str:
        return "".join(
            f'<option value="{site.escaped(value)}">'
            f'{site.escaped(site.state_label(value))}</option>'
            for value in values
        )

    return f'''<details class="ri-decision-filters" open>
      <summary>Dependency facets</summary>
      <div>
        <label><span>Relationship</span><select data-filter-extra="relationship"><option value="all">All relationships</option><option value="depends-on">Depends on</option><option value="blocks">Blocks</option></select></label>
        <label><span>Assertion</span><select data-filter-extra="assertion"><option value="all">All assertions</option>{options(assertions)}</select></label>
        <label><span>Freshness</span><select data-filter-extra="freshness"><option value="all">All freshness states</option>{options(freshness)}</select></label>
        <label><span>Scope</span><select data-filter-extra="scope"><option value="all">All scopes</option>{options(scopes)}</select></label>
      </div>
      <p>The shared State and Kind filters apply to relationship endpoints. These facets apply to the normalized relationship itself.</p>
    </details>'''


def dependencies_body(snapshot: dict[str, Any] | None, *, repository: str) -> str:
    """Render one dependency-impact view without reconstructing graph semantics locally."""

    if snapshot is None:
        return f'''<section class="ri-section ri-section--lead" aria-labelledby="dependencies-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Dependency impact</span><h2 id="dependencies-heading">What depends on what?</h2></div><p>Only normalized Observatory relationships are rendered here.</p></div>{site.empty_state("Dependency evidence unavailable", "Supply a repository- and commit-matched Observatory read model to inspect dependency and blocking relationships.", "partial")}</section>'''

    views = site.require_object(snapshot.get("views"))
    if "dependencies" not in views:
        return f'''<section class="ri-section ri-section--lead" aria-labelledby="dependencies-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Dependency impact</span><h2 id="dependencies-heading">What depends on what?</h2></div><p>This snapshot predates or omits the normalized Dependencies query.</p></div>{site.empty_state("Dependencies view not projected", "The represented snapshot is available, but it does not contain views.dependencies. Relay will not infer dependency truth from other views.", "partial")}</section>'''

    dependencies = validate_dependencies_view(views.get("dependencies"))
    relationships = [
        site.require_object(value) for value in dependencies["relationships"]
    ]
    external_repositories = list(dependencies["external_repositories"])
    if not relationships:
        return f'''<section class="ri-section ri-section--lead" aria-labelledby="dependencies-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Dependency impact</span><h2 id="dependencies-heading">What depends on what?</h2></div><p>The normalized Dependencies query is present and contains no directed relationships.</p></div>{site.empty_state("No dependency relationships projected", "This means this Observatory query is empty for the represented snapshot; it does not prove the wider ecosystem has no dependencies.", "not_applicable")}</section>'''

    depends_on = sum(
        1 for value in relationships if value["type"] == "depends-on"
    )
    blocks = sum(1 for value in relationships if value["type"] == "blocks")
    inferred_or_unknown = sum(
        1
        for value in relationships
        if value["assertion"] in {"inferred", "unknown"}
    )
    evidence = source_index(snapshot)
    external = (
        '<div class="ri-relationship-row"><strong>External repositories</strong><div>'
        + "".join(
            f'<span class="ri-link-chip">{site.escaped(value)}</span>'
            for value in external_repositories
        )
        + "</div></div>"
        if external_repositories
        else '<div class="ri-relationship-row"><strong>External repositories</strong><div><span class="ri-link-chip">None projected</span></div></div>'
    )
    records = "".join(
        render_relationship(value, repository=repository, sources=evidence)
        for value in relationships
    )
    relationship_verb = "is" if inferred_or_unknown == 1 else "are"
    return f'''<section class="ri-section ri-section--lead" aria-labelledby="dependencies-heading">
      <div class="ri-section-heading"><div><span class="ri-eyebrow">Dependency impact</span><h2 id="dependencies-heading">What depends on what?</h2></div><p>Follow directed dependency and blocking evidence without turning inferred relationships into authoritative truth.</p></div>
      <div class="ri-roadmap-metrics" aria-label="Dependency relationship summary"><article><strong>{len(relationships)}</strong><span>directed relationships</span></article><article><strong>{depends_on}</strong><span>depends-on edges</span></article><article><strong>{blocks}</strong><span>blocking edges</span></article><article><strong>{len(external_repositories)}</strong><span>external repositories</span></article></div>
      <details class="ri-progress-rules"><summary>How to read this view</summary><p>Direction, assertion, freshness, and provenance come from the normalized Observatory query. Relay derives only presentation grouping such as repository-local versus cross-repository scope. {inferred_or_unknown} relationship {relationship_verb} inferred or unknown and therefore remain labelled rather than promoted.</p></details>
      <div class="ri-relationship-grid">{external}</div>
      {render_filter_controls(relationships)}
    </section>
    <section class="ri-section" aria-labelledby="dependency-records-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Directed evidence</span><h2 id="dependency-records-heading">Relationship records</h2></div><p>Every record keeps its source, target, assertion, freshness, and provenance visible in static HTML.</p></div><ol class="ri-evidence-list">{records}</ol></section>'''


def render_page(
    *,
    snapshot: dict[str, Any] | None,
    summary: dict[str, Any],
    repository: str,
    source_commit: str,
) -> str:
    """Compose Dependencies through Relay's canonical shared shell."""

    observed_at = str(
        snapshot.get("observed_at")
        if snapshot
        else summary.get("generated_at") or ""
    )
    freshness = site.projection_freshness(snapshot, "dependencies")
    return site.shell_document(
        route="dependencies",
        route_label="Dependencies",
        repository=repository,
        source_commit=source_commit,
        observed_at=observed_at,
        freshness=freshness,
        summary=summary,
        body=dependencies_body(snapshot, repository=repository),
        prefix="../",
        snapshot_available=snapshot is not None,
    )


def main() -> int:
    """Validate the shared inputs and replace only the generated Dependencies route."""

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
    site.validate_site_contracts(
        summary,
        provenance,
        args.repository,
        args.source_commit,
    )
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
        output_root / "dependencies/index.html",
        render_page(
            snapshot=snapshot,
            summary=summary,
            repository=args.repository,
            source_commit=args.source_commit,
        ),
    )
    print(
        "Rendered Repository Intelligence Dependencies at "
        f"{output_root / 'dependencies/index.html'} for "
        f"{args.repository}@{args.source_commit[:12]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
