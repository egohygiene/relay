# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Render the bounded Repository Intelligence Health route from Observatory evidence."""

from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

ASSERTION_STATES = {"authoritative", "inferred", "unknown"}
FRESHNESS_STATES = {"current", "not_applicable", "stale", "unknown"}


class HealthViewError(ValueError):
    """Raised when a projected Health view cannot be rendered safely."""


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
    """Parse the bounded Health-route rendering interface."""

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
        raise HealthViewError(f"{label} must be a non-empty string")
    return value


def validate_distribution(
    value: Any,
    label: str,
    *,
    allowed_keys: set[str] | None = None,
) -> dict[str, int]:
    """Validate one normalized count distribution without manufacturing categories."""

    if not isinstance(value, dict):
        raise HealthViewError(f"{label} must be an object")
    result: dict[str, int] = {}
    for key, count in value.items():
        if not isinstance(key, str) or not key or site.normalize_state(key) != key:
            raise HealthViewError(f"{label} keys must be normalized non-empty strings")
        if allowed_keys is not None and key not in allowed_keys:
            raise HealthViewError(f"{label} uses unsupported state {key}")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise HealthViewError(f"{label}.{key} must be a non-negative integer")
        result[key] = count
    return result


def validate_identifier_list(value: Any, label: str) -> list[str]:
    """Validate one ordered list of stable evidence identifiers."""

    if not isinstance(value, list):
        raise HealthViewError(f"{label} must be an array")
    result: list[str] = []
    for index, identifier in enumerate(value):
        if not isinstance(identifier, str) or not identifier:
            raise HealthViewError(f"{label}[{index}] must be a non-empty string")
        result.append(identifier)
    if len(result) != len(set(result)):
        raise HealthViewError(f"{label} must not contain duplicate IDs")
    return result


def validate_health_check(value: Any, label: str) -> dict[str, Any]:
    """Validate the exact compact check fields consumed by Relay."""

    record = site.require_object(value)
    if not record:
        raise HealthViewError(f"{label} must be an object")
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
    ):
        require_string(record.get(member), f"{label}.{member}")
    if site.normalize_state(record["kind"]) != "check":
        raise HealthViewError(f"{label}.kind must be check")
    if record["assertion"] not in ASSERTION_STATES:
        raise HealthViewError(f"{label}.assertion uses unsupported state {record['assertion']}")
    if record["freshness"] not in FRESHNESS_STATES:
        raise HealthViewError(f"{label}.freshness uses unsupported state {record['freshness']}")
    if not site.safe_href(record["canonical_url"]):
        raise HealthViewError(
            f"{label}.canonical_url must be a credential-free HTTPS URL"
        )
    title = record.get("title")
    if title is not None and (not isinstance(title, str) or not title):
        raise HealthViewError(f"{label}.title must be null or a non-empty string")
    return record


def validate_health_view(value: Any) -> dict[str, Any]:
    """Validate Observatory's accepted core Health projection without extending it."""

    if not isinstance(value, dict) or not value:
        raise HealthViewError("snapshot views.health must be an object")

    assertions = validate_distribution(
        value.get("assertions"),
        "snapshot views.health.assertions",
        allowed_keys=ASSERTION_STATES,
    )
    check_states = validate_distribution(
        value.get("check_states"),
        "snapshot views.health.check_states",
    )
    freshness = validate_distribution(
        value.get("freshness"),
        "snapshot views.health.freshness",
        allowed_keys=FRESHNESS_STATES,
    )

    raw_checks = value.get("checks")
    if not isinstance(raw_checks, list):
        raise HealthViewError("snapshot views.health.checks must be an array")
    checks: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for index, candidate in enumerate(raw_checks):
        check = validate_health_check(candidate, f"snapshot views.health.checks[{index}]")
        if check["id"] in identifiers:
            raise HealthViewError("snapshot views.health check IDs must be unique")
        identifiers.add(check["id"])
        checks.append(check)

    expected_states = Counter(site.normalize_state(check["state"]) for check in checks)
    supplied_states = Counter(
        {state: count for state, count in check_states.items() if count > 0}
    )
    if expected_states != supplied_states:
        raise HealthViewError(
            "snapshot views.health.check_states must exactly describe projected checks"
        )

    stale_ids = validate_identifier_list(
        value.get("stale_ids"), "snapshot views.health.stale_ids"
    )
    unknown_ids = validate_identifier_list(
        value.get("unknown_ids"), "snapshot views.health.unknown_ids"
    )
    overlap = sorted(set(stale_ids) & set(unknown_ids))
    if overlap:
        raise HealthViewError(
            "snapshot views.health stale_ids and unknown_ids must be disjoint"
        )
    if freshness.get("stale", 0) != len(stale_ids):
        raise HealthViewError(
            "snapshot views.health.freshness.stale must match stale_ids"
        )
    if freshness.get("unknown", 0) != len(unknown_ids):
        raise HealthViewError(
            "snapshot views.health.freshness.unknown must match unknown_ids"
        )

    if "score" not in value or value["score"] is not None:
        raise HealthViewError("snapshot views.health.score must be null")
    require_string(value.get("score_reason"), "snapshot views.health.score_reason")

    # Keep local names live so malformed empty objects cannot bypass validation above.
    _ = assertions
    return value


def render_distribution(
    title: str,
    values: dict[str, int],
    *,
    order: tuple[str, ...] = (),
) -> str:
    """Render one compact normalized distribution without deriving a roll-up."""

    ordered_keys = [key for key in order if key in values]
    ordered_keys.extend(sorted(key for key in values if key not in ordered_keys))
    items = "".join(
        f'<article><strong>{values[key]}</strong><span>{site.escaped(site.state_label(key))}</span></article>'
        for key in ordered_keys
    )
    if not items:
        items = '<article><strong>0</strong><span>No projected categories</span></article>'
    return f'''<section class="ri-panel" aria-label="{site.escaped(title)}"><h3>{site.escaped(title)}</h3><div class="ri-roadmap-metrics">{items}</div></section>'''


def render_check_filters(
    checks: list[dict[str, Any]],
    check_states: dict[str, int],
) -> str:
    """Expose exact check-state and freshness facets without changing evidence."""

    freshness_counts = Counter(site.normalize_state(check["freshness"]) for check in checks)
    state_options = "".join(
        f'<option value="{site.escaped(state)}">{site.escaped(site.state_label(state))} ({count})</option>'
        for state, count in check_states.items()
        if count > 0
    )
    freshness_options = "".join(
        f'<option value="{site.escaped(state)}">{site.escaped(site.state_label(state))} ({freshness_counts[state]})</option>'
        for state in ("current", "stale", "unknown", "not_applicable")
        if freshness_counts[state]
    )
    return f'''<details class="ri-decision-filters" open><summary>Check evidence facets</summary><div><label><span>Check state</span><select data-filter-extra="check-state"><option value="all">All check states</option>{state_options}</select></label><label><span>Freshness</span><select data-filter-extra="freshness"><option value="all">All freshness</option>{freshness_options}</select></label></div><p>These controls only hide or show supplied check records. They do not recalculate repository health.</p></details>'''


def render_check(record: dict[str, Any]) -> str:
    """Render one normalized check and its canonical evidence link."""

    state = site.normalize_state(record["state"])
    freshness = site.normalize_state(record["freshness"])
    assertion = site.normalize_state(record["assertion"])
    title = record.get("title") or record["key"]
    search_text = " ".join(
        str(record.get(field) or "")
        for field in ("title", "key", "repository", "state", "assertion", "freshness")
    ).casefold()
    return f'''<li><article class="ri-record" data-entity-id="{site.escaped(record.get("id"))}" data-filter-item{site.source_repository_attribute(record)} data-state="{site.escaped(state)}" data-kind="check" data-filter-check-state="{site.escaped(state)}" data-filter-freshness="{site.escaped(freshness)}" data-search="{site.escaped(search_text)}">
      <div class="ri-record__top"><span class="ri-eyebrow">Normalized check</span><span>{site.status_pill(state)} {site.status_pill(freshness, f"Freshness: {site.state_label(freshness)}")}</span></div>
      <h3>{site.escaped(title)}</h3>
      <p>{site.escaped(record["repository"])} · {site.escaped(record["key"])}</p>
      <dl class="ri-provenance"><div><dt>Assertion</dt><dd>{site.escaped(site.state_label(assertion))}</dd></div><div><dt>Freshness</dt><dd>{site.escaped(site.state_label(freshness))}</dd></div><div><dt>Confidence</dt><dd>{site.escaped(site.state_label(record["confidence"]))}</dd></div></dl>
      <p>{site.source_link(record, "Open canonical check evidence")}</p>
    </article></li>'''


def render_identifier_inventory(
    *,
    title: str,
    identifiers: list[str],
    state: str,
    empty_message: str,
) -> str:
    """Render Observatory-owned stale/unknown IDs without inventing entity meaning."""

    if identifiers:
        contents = "".join(f"<li><code>{site.escaped(identifier)}</code></li>" for identifier in identifiers)
        body = f'<ol class="ri-record-list" aria-label="{site.escaped(title)}">{contents}</ol>'
    else:
        body = site.empty_state(title, empty_message, "not_applicable")
    return f'''<details class="ri-progress-rules" data-state="{site.escaped(state)}"><summary>{site.escaped(title)} ({len(identifiers)})</summary><p>These are stable IDs projected by Observatory. Relay does not infer titles, severity, or conformance meaning from the identifiers.</p>{body}</details>'''


def health_body(snapshot: dict[str, Any] | None) -> str:
    """Render the accepted core Health query without claiming fleet conformance."""

    if snapshot is None:
        return f'''<section class="ri-section ri-section--lead" aria-labelledby="health-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Core check evidence</span><h2 id="health-heading">What does the current evidence say?</h2></div><p>Health evidence is unavailable until a commit-matched Observatory snapshot is supplied.</p></div>{site.empty_state("Health evidence unavailable", "Supply a repository- and commit-matched Observatory read model. Missing evidence is never treated as passing.", "partial")}</section>'''

    views = site.require_object(snapshot.get("views"))
    if "health" not in views:
        return f'''<section class="ri-section ri-section--lead" aria-labelledby="health-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Core check evidence</span><h2 id="health-heading">What does the current evidence say?</h2></div><p>The represented snapshot is available, but its core Health query is not projected.</p></div>{site.empty_state("Health view not projected", "Relay will not rebuild health semantics from Now, Journey, provider data, or unfinished fleet-conformance evidence.", "partial")}</section>'''

    health = validate_health_view(views.get("health"))
    checks = [site.require_object(value) for value in site.require_list(health["checks"])]
    check_states = validate_distribution(
        health["check_states"], "snapshot views.health.check_states"
    )
    assertions = validate_distribution(
        health["assertions"],
        "snapshot views.health.assertions",
        allowed_keys=ASSERTION_STATES,
    )
    freshness = validate_distribution(
        health["freshness"],
        "snapshot views.health.freshness",
        allowed_keys=FRESHNESS_STATES,
    )
    stale_ids = validate_identifier_list(
        health["stale_ids"], "snapshot views.health.stale_ids"
    )
    unknown_ids = validate_identifier_list(
        health["unknown_ids"], "snapshot views.health.unknown_ids"
    )

    state_metrics = "".join(
        f'<article><strong>{count}</strong><span>{site.escaped(site.state_label(state))}</span></article>'
        for state, count in check_states.items()
    )
    if not state_metrics:
        state_metrics = '<article><strong>0</strong><span>check states</span></article>'

    checks_body = (
        f'''{render_check_filters(checks, check_states)}<ol class="ri-record-list" aria-label="Normalized Repository Intelligence health checks">{"".join(render_check(check) for check in checks)}</ol>'''
        if checks
        else site.empty_state(
            "No check records projected",
            "The core Health query is present but contains no normalized checks. Absence of check evidence is not a passing state.",
            "not_applicable",
        )
    )

    return f'''<section class="ri-section ri-section--lead" aria-labelledby="health-heading">
      <div class="ri-section-heading"><div><span class="ri-eyebrow">Core check evidence</span><h2 id="health-heading">What does the current evidence say?</h2></div><p>This view reports Observatory-normalized check and freshness evidence only. It is not complete Hygiene conformance.</p></div>
      <div class="ri-roadmap-metrics" aria-label="Core check posture"><article><strong>{len(checks)}</strong><span>normalized checks</span></article>{state_metrics}</div>
      <div class="ri-panel"><h3>No roll-up score</h3><p>{site.escaped(health["score_reason"])}</p><p>Relay preserves the upstream <code>score: null</code> contract and does not manufacture a percentage, grade, maturity rating, or security posture.</p></div>
    </section>
    <section class="ri-section" aria-labelledby="coverage-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Evidence coverage</span><h2 id="coverage-heading">Assertion and freshness distribution</h2></div><p>Counts are copied from the accepted Health projection; they are not recalculated into a score.</p></div><div class="ri-now-grid">{render_distribution("Assertion distribution", assertions, order=("authoritative", "inferred", "unknown"))}{render_distribution("Freshness distribution", freshness, order=("current", "stale", "unknown", "not_applicable"))}</div></section>
    <section class="ri-section" aria-labelledby="checks-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Checks</span><h2 id="checks-heading">Normalized check records</h2></div><p>Each material claim links back to its canonical check evidence.</p></div>{checks_body}</section>
    <section class="ri-section" aria-labelledby="exceptions-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Freshness exceptions</span><h2 id="exceptions-heading">Stale and unknown evidence stays explicit</h2></div><p>Stable IDs remain separate so missing or aging evidence cannot silently become a pass.</p></div>{render_identifier_inventory(title="Stale evidence IDs", identifiers=stale_ids, state="stale", empty_message="The Health projection contains no stale IDs. This does not assert complete conformance.")}{render_identifier_inventory(title="Unknown evidence IDs", identifiers=unknown_ids, state="unknown", empty_message="The Health projection contains no unknown IDs. This does not assert evidence outside the normalized snapshot.")}</section>'''


def render_page(
    *,
    snapshot: dict[str, Any] | None,
    summary: dict[str, Any],
    repository: str,
    source_commit: str,
) -> str:
    """Compose Health through Relay's canonical shared shell."""

    observed_at = str(
        snapshot.get("observed_at") if snapshot else summary.get("generated_at") or ""
    )
    freshness = site.projection_freshness(snapshot, "health")
    return site.shell_document(
        route="health",
        route_label="Health",
        repository=repository,
        source_commit=source_commit,
        observed_at=observed_at,
        freshness=freshness,
        summary=summary,
        body=health_body(snapshot),
        prefix="../",
        snapshot_available=snapshot is not None,
    )


def main() -> int:
    """Validate shared inputs and replace only the generated Health route."""

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
        output_root / "health/index.html",
        render_page(
            snapshot=snapshot,
            summary=summary,
            repository=args.repository,
            source_commit=args.source_commit,
        ),
    )
    print(
        "Rendered Repository Intelligence Health at "
        f"{output_root / 'health/index.html'} for {args.repository}@{args.source_commit[:12]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
