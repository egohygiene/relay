# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Compose the routed Repository Intelligence shell and operational Now view."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import html
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any
from urllib.parse import urlsplit

SNAPSHOT_SCHEMA = "egohygiene.observatory.repository-intelligence-read-model/v1"
ROUTES = (
    ("now", "Now"),
    ("roadmap", "Roadmap"),
    ("decisions", "Decisions"),
    ("journey", "Journey"),
    ("dependencies", "Dependencies"),
    ("health", "Health"),
    ("releases", "Releases"),
    ("work", "Work"),
    ("search", "Search"),
    ("compare", "Compare"),
)
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
EMAIL = re.compile(r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SECRET = re.compile(r"(?i)(?:github_pat_|gh[pousr]_|(?:token|password|secret)\s*[:=])")
BROKEN_STATES = {"error", "failed", "failure", "timed_out"}
PENDING_DECISION_STATES = {"draft", "pending", "proposed"}


class SiteInputError(ValueError):
    """Raised when the shell receives an incompatible or unsafe contract."""


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--provenance", required=True)
    parser.add_argument("--snapshot", default="")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--stylesheet-source", required=True)
    parser.add_argument("--script-source", required=True)
    return parser.parse_args()


def load_object(path: Path, label: str) -> dict[str, Any]:
    def reject_nonstandard_number(value: str) -> None:
        raise ValueError(f"non-standard JSON number: {value}")

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=reject_nonstandard_number,
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        raise SiteInputError(f"{label} must contain valid UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise SiteInputError(f"{label} must be an object")
    return value


def require_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def require_object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def escaped(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def normalize_state(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        return "unknown"
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_") or "unknown"


def state_label(value: Any) -> str:
    return " ".join(part.capitalize() for part in normalize_state(value).split("_"))


def format_date(value: Any) -> str:
    if not isinstance(value, str) or not value:
        return "Unknown time"
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return value
    return parsed.astimezone(UTC).strftime("%b %d, %Y · %H:%M UTC")


def safe_href(value: Any) -> str:
    """Accept credential-free HTTPS evidence links only."""

    if not isinstance(value, str) or not value or EMAIL.search(value) or SECRET.search(value):
        return ""
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return ""
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or port not in {None, 443}
        or parsed.username is not None
        or parsed.password is not None
    ):
        return ""
    return value


def entity(record: Any) -> dict[str, Any]:
    item = require_object(record)
    nested = item.get("entity")
    return require_object(nested) if isinstance(nested, dict) else item


def validate_snapshot(
    snapshot: dict[str, Any], repository: str, source_commit: str
) -> dict[str, Any]:
    if snapshot.get("schema") != SNAPSHOT_SCHEMA:
        raise SiteInputError(f"snapshot schema must be {SNAPSHOT_SCHEMA}")
    if snapshot.get("represented_commit") != source_commit:
        raise SiteInputError("snapshot must represent the generated dashboard commit")
    snapshot_repository = require_object(snapshot.get("repository"))
    if snapshot_repository.get("key") != repository:
        raise SiteInputError("snapshot repository must match the generated dashboard")
    for key in ("id", "key", "title", "state"):
        if not isinstance(snapshot_repository.get(key), str) or not snapshot_repository[key]:
            raise SiteInputError(f"snapshot repository.{key} must be a non-empty string")
    observed_at = snapshot.get("observed_at")
    normalized_observed_at = (
        observed_at[:-1] + "+00:00"
        if isinstance(observed_at, str) and observed_at.endswith("Z")
        else observed_at
    )
    try:
        parsed_observed_at = datetime.fromisoformat(normalized_observed_at)
    except (TypeError, ValueError) as error:
        raise SiteInputError("snapshot observed_at must be an RFC 3339 timestamp") from error
    if parsed_observed_at.tzinfo is None:
        raise SiteInputError("snapshot observed_at must be an RFC 3339 timestamp")
    coverage_status = normalize_state(require_object(snapshot.get("coverage")).get("status"))
    if coverage_status not in {
        "current",
        "error",
        "not_applicable",
        "partial",
        "stale",
        "unknown",
    }:
        raise SiteInputError("snapshot coverage.status uses an unsupported state")
    views = require_object(snapshot.get("views"))
    for name in ("now", "roadmap", "decisions", "health", "work"):
        if not isinstance(views.get(name), dict):
            raise SiteInputError(f"snapshot views.{name} must be an object")
    required_arrays = {
        "now": ("blockers", "current_focus", "next_ready", "recent_events"),
        "roadmap": ("roots", "steps"),
        "decisions": ("decisions",),
        "health": ("checks",),
        "work": ("open_issues", "open_pull_requests"),
    }
    for view_name, members in required_arrays.items():
        view = views[view_name]
        for member in members:
            if not isinstance(view.get(member), list):
                raise SiteInputError(
                    f"snapshot views.{view_name}.{member} must be an array"
                )
    if not isinstance(views["work"].get("roadmap_queues"), dict):
        raise SiteInputError("snapshot views.work.roadmap_queues must be an object")
    return snapshot


def validate_site_contracts(
    summary: dict[str, Any],
    provenance: dict[str, Any],
    repository: str,
    source_commit: str,
) -> None:
    """Require the shell inputs to describe one repository source boundary."""

    summary_repository = require_object(summary.get("repository"))
    if summary_repository.get("name") != repository or summary_repository.get(
        "source_commit"
    ) != source_commit:
        raise SiteInputError("dashboard summary does not match the requested source")
    consumer = require_object(provenance.get("consumer"))
    if (
        consumer.get("repository") != repository
        or consumer.get("source_commit") != source_commit
    ):
        raise SiteInputError("bundle provenance does not match the requested source")


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def validate_repository_path(repository_root: Path, path: Path, label: str) -> None:
    """Keep action reads inside the checkout without following input symlinks."""

    try:
        relative = path.relative_to(repository_root)
    except ValueError as error:
        raise SiteInputError(f"{label} must remain inside the repository") from error
    current = repository_root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise SiteInputError(f"{label} must not use symbolic-link components")


def status_pill(state: Any, label: str | None = None) -> str:
    normalized = normalize_state(state)
    return (
        f'<span class="ri-status" data-state="{escaped(normalized)}">'
        f'<span aria-hidden="true"></span>{escaped(label or state_label(normalized))}</span>'
    )


def source_link(item: dict[str, Any], label: str = "Open source") -> str:
    href = safe_href(item.get("canonical_url"))
    if not href:
        return ""
    return f'<a class="ri-source-link" href="{escaped(href)}">{escaped(label)} <span aria-hidden="true">↗</span></a>'


def empty_state(title: str, message: str, state: str = "unknown") -> str:
    return f'''<div class="ri-empty" data-state="{escaped(normalize_state(state))}" role="status">
      <span class="ri-empty__mark" aria-hidden="true"></span>
      <div><h3>{escaped(title)}</h3><p>{escaped(message)}</p></div>
    </div>'''


def record_card(item: Any, *, eyebrow: str = "Evidence") -> str:
    value = entity(item)
    title = value.get("title") or value.get("key") or "Untitled record"
    kind = state_label(value.get("kind"))
    state = normalize_state(value.get("state"))
    search = " ".join(str(value.get(key, "")) for key in ("title", "key", "kind", "state"))
    return f'''<article class="ri-record" data-filter-item data-state="{escaped(state)}" data-kind="{escaped(normalize_state(value.get("kind")))}" data-search="{escaped(search.lower())}">
      <div class="ri-record__top"><span class="ri-eyebrow">{escaped(eyebrow)}</span>{status_pill(state)}</div>
      <h3>{escaped(title)}</h3>
      <p>{escaped(kind)} · {escaped(value.get("key") or "No identifier")}</p>
      {source_link(value)}
    </article>'''


def render_recent_change(now: dict[str, Any]) -> str:
    events = require_list(now.get("recent_events"))
    if not events:
        return empty_state(
            "No recent meaningful change projected",
            "The snapshot does not assert a recent event. This is unknown, not inactivity.",
        )
    event = require_object(events[0])
    subject = entity(event.get("subject_entity"))
    event_type = str(event.get("type") or "recorded").replace("_", " ").replace(".", " · ")
    return f'''<article class="ri-change" data-filter-item data-state="{escaped(normalize_state(subject.get("state")))}" data-kind="{escaped(normalize_state(subject.get("kind")))}" data-search="{escaped((str(subject.get("title", "")) + " " + event_type).lower())}">
      <div class="ri-change__rail" aria-hidden="true"><span></span></div>
      <div><div class="ri-record__top"><span class="ri-eyebrow">{escaped(event_type)}</span>{status_pill(subject.get("state"))}</div>
      <h3>{escaped(subject.get("title") or "Recorded change")}</h3>
      <p><time datetime="{escaped(event.get("occurred_at"))}">{escaped(format_date(event.get("occurred_at")))}</time></p>
      {source_link(subject, "Inspect change")}</div>
    </article>'''


def render_collection(
    items: list[Any], *, empty_title: str, empty_message: str, eyebrow: str
) -> str:
    if not items:
        return empty_state(empty_title, empty_message, "empty")
    return '<div class="ri-record-list">' + "".join(
        record_card(item, eyebrow=eyebrow) for item in items
    ) + "</div>"


def newly_broken(now: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for candidate in require_list(now.get("recent_events")):
        event = require_object(candidate)
        subject = entity(event.get("subject_entity"))
        if normalize_state(subject.get("kind")) != "check":
            continue
        changes = require_list(event.get("changes"))
        transitioned = any(
            normalize_state(require_object(change).get("to")) in BROKEN_STATES
            and normalize_state(require_object(change).get("from")) not in BROKEN_STATES
            for change in changes
        )
        if transitioned and normalize_state(subject.get("state")) in BROKEN_STATES:
            results.append(subject)
    return results


def pending_decisions(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    decisions = require_list(
        require_object(require_object(snapshot.get("views")).get("decisions")).get("decisions")
    )
    return [
        candidate
        for candidate in decisions
        if normalize_state(entity(candidate).get("state")) in PENDING_DECISION_STATES
    ]


def render_next_actions(snapshot: dict[str, Any]) -> str:
    views = require_object(snapshot.get("views"))
    ready = require_list(require_object(views.get("now")).get("next_ready"))[:3]
    roadmap = require_list(require_object(views.get("roadmap")).get("steps"))
    roadmap_by_id = {
        str(entity(step).get("id")): require_object(step)
        for step in roadmap
        if entity(step).get("id")
    }
    if not ready:
        return empty_state(
            "No ready action asserted",
            "Observatory has not projected a ready quest. Planned and incomplete work are not silently promoted.",
            "empty",
        )
    cards = []
    for index, candidate in enumerate(ready, start=1):
        action_entity = entity(candidate)
        step = roadmap_by_id.get(str(action_entity.get("id")), require_object(candidate))
        readiness = require_object(step.get("readiness"))
        reasons = [str(reason) for reason in require_list(readiness.get("reasons")) if reason]
        rationale = "; ".join(reasons) or str(step.get("outcome") or "Observatory marks this quest ready.")
        dependencies = [entity(value) for value in require_list(step.get("dependencies"))]
        prerequisites = (
            "".join(
                f'<li>{status_pill(dep.get("state"))}<span>{escaped(dep.get("title") or dep.get("key"))}</span>{source_link(dep, "Open")}</li>'
                for dep in dependencies
            )
            if dependencies
            else '<li><span class="ri-muted">No prerequisites asserted.</span></li>'
        )
        cards.append(f'''<li class="ri-action" data-filter-item data-state="ready" data-kind="roadmap_step" data-search="{escaped((str(action_entity.get("title", "")) + " " + rationale).lower())}">
          <div class="ri-action__number" aria-hidden="true">{index:02d}</div>
          <article><div class="ri-record__top"><span class="ri-eyebrow">Ready action</span>{status_pill("ready")}</div>
          <h3>{escaped(action_entity.get("title") or action_entity.get("key") or "Untitled action")}</h3>
          <p><strong>Why now:</strong> {escaped(rationale)}</p>
          <details><summary>Prerequisites</summary><ul>{prerequisites}</ul></details>
          {source_link(action_entity, "Open canonical work")}</article>
        </li>''')
    return '<ol class="ri-action-list">' + "".join(cards) + "</ol>"


def build_status(summary: dict[str, Any]) -> tuple[str, str]:
    execution = require_object(require_object(summary.get("states")).get("execution"))
    if int(execution.get("failure", 0) or 0) > 0:
        return "failure", "Build signals failing"
    if int(execution.get("success", 0) or 0) > 0 and int(execution.get("unknown", 0) or 0) == 0:
        return "success", "Build signals passing"
    return "unknown", "Build status partial"


def navigation(current: str, prefix: str) -> str:
    links = []
    for route, label in ROUTES:
        current_attribute = ' aria-current="page"' if current == route else ""
        links.append(
            f'<a href="{escaped(prefix + route + "/")}"{current_attribute}>{escaped(label)}</a>'
        )
    links.append(f'<a href="{escaped(prefix + "dashboard/")}">Dashboard</a>')
    return "".join(links)


def shell_document(
    *,
    route: str,
    route_label: str,
    repository: str,
    source_commit: str,
    observed_at: str,
    freshness: str,
    summary: dict[str, Any],
    body: str,
    prefix: str,
    snapshot_available: bool,
) -> str:
    state, build_label = build_status(summary)
    repository_url = f"https://github.com/{repository}"
    commit_url = f"{repository_url}/commit/{source_commit}"
    snapshot_label = "Observatory snapshot loaded" if snapshot_available else "Snapshot unavailable"
    return f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="Repository Intelligence {escaped(route_label)} view for {escaped(repository)}.">
    <title>{escaped(route_label)} · {escaped(repository)} · Repository Intelligence</title>
    <link rel="stylesheet" href="{escaped(prefix)}site.css">
  </head>
  <body data-ri-route="{escaped(route)}" data-ri-repository="{escaped(repository)}" data-ri-commit="{escaped(source_commit)}">
    <a class="ri-skip" href="#main-content">Skip to current repository state</a>
    <header class="ri-global-header">
      <a class="ri-brand" href="{escaped(prefix)}"><span aria-hidden="true">EH</span><strong>Repository Intelligence</strong></a>
      <nav aria-label="Global navigation"><a href="https://github.com/egohygiene">Ego Hygiene</a><a href="{escaped(repository_url)}">Repository source</a></nav>
    </header>
    <div class="ri-layout">
      <aside class="ri-sidebar" aria-label="Repository Intelligence navigation">
        <div class="ri-repository"><span class="ri-eyebrow">Repository</span><strong>{escaped(repository)}</strong><span>{status_pill(freshness)}</span></div>
        <nav class="ri-route-nav">{navigation(route, prefix)}</nav>
        <div class="ri-local-resume" data-local-resume>
          <span class="ri-eyebrow">This device</span>
          <p>Resume data stays in this browser. It never becomes canonical repository evidence.</p>
          <a class="ri-button ri-button--quiet" data-resume-link hidden href="{escaped(prefix + "now/")}">Resume last view</a>
          <button class="ri-text-button" type="button" data-clear-resume>Forget local position</button>
        </div>
      </aside>
      <div class="ri-page">
        <header class="ri-hero">
          <div><span class="ri-kicker"><i aria-hidden="true"></i>{escaped(route_label)} view</span><h1>{escaped(repository.split("/", 1)[-1])}</h1><p>See what changed, what needs attention, and the next grounded moves without flattening uncertainty.</p></div>
          <div class="ri-orbit" data-state="{escaped(freshness)}" role="img" aria-label="Evidence freshness: {escaped(state_label(freshness))}"><span></span><strong>{escaped(state_label(freshness))}</strong><small>evidence</small></div>
        </header>
        <section class="ri-context" aria-label="Represented source and build context">
          <a href="{escaped(commit_url)}"><span>Represented commit</span><code>{escaped(source_commit[:12])}</code></a>
          <div><span>Observed</span><strong>{escaped(format_date(observed_at))}</strong></div>
          <div><span>Collection</span>{status_pill(freshness, snapshot_label)}</div>
          <a href="{escaped(prefix)}dashboard/"><span>Build evidence</span>{status_pill(state, build_label)}</a>
          <a href="{escaped(prefix)}provenance.json"><span>Generator</span><strong>View provenance ↗</strong></a>
        </section>
        <div class="ri-command-bar" data-filters>
          <label class="ri-search"><span class="ri-visually-hidden">Search this view</span><span aria-hidden="true">⌕</span><input type="search" data-filter-query placeholder="Search this view…" autocomplete="off"></label>
          <label><span>State</span><select data-filter-state><option value="all">All states</option><option value="active">Active</option><option value="blocked">Blocked</option><option value="ready">Ready</option><option value="failure">Failure</option><option value="proposed">Proposed</option><option value="unknown">Unknown</option></select></label>
          <label><span>Kind</span><select data-filter-kind><option value="all">All evidence</option><option value="roadmap_step">Quest</option><option value="architecture_decision">Decision</option><option value="check">Check</option><option value="commit">Commit</option><option value="issue">Issue</option><option value="pull_request">Pull request</option><option value="release">Release</option><option value="deployment">Deployment</option></select></label>
          <button class="ri-button ri-button--quiet" type="button" data-filter-reset>Reset</button>
          <output data-filter-results aria-live="polite">Showing the full view</output>
        </div>
        <main id="main-content" tabindex="-1">{body}<div class="ri-no-results" data-no-results hidden>{empty_state("No matching evidence", "Clear a filter or broaden the search to continue.", "empty")}</div></main>
        <footer><span>Operational state is rendered only from <code>{escaped(SNAPSHOT_SCHEMA)}</code>.</span><a href="#main-content">Back to top ↑</a></footer>
      </div>
    </div>
    <script src="{escaped(prefix)}site.js" defer></script>
  </body>
</html>
'''


def now_body(snapshot: dict[str, Any] | None) -> str:
    if snapshot is None:
        unavailable = empty_state(
            "Observatory snapshot unavailable",
            "The shell is healthy, but active work, blockers, decisions, and next actions cannot be asserted from the dashboard aggregate alone.",
            "partial",
        )
        return f'''<section class="ri-section ri-section--lead" aria-labelledby="now-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Operational entry</span><h2 id="now-heading">Where things stand</h2></div><p>Unknown remains visible until a commit-matched Observatory read model is supplied.</p></div>{unavailable}</section>'''
    views = require_object(snapshot.get("views"))
    now = require_object(views.get("now"))
    focus = require_list(now.get("current_focus"))
    blockers = require_list(now.get("blockers"))
    broken = newly_broken(now)
    pending = pending_decisions(snapshot)
    return f'''<section class="ri-section ri-section--lead" aria-labelledby="now-heading">
      <div class="ri-section-heading"><div><span class="ri-eyebrow">Operational entry</span><h2 id="now-heading">Where things stand</h2></div><p>Blocked, broken, incomplete, stale, and unknown remain distinct evidence states.</p></div>
      <div class="ri-now-grid">
        <section class="ri-panel ri-panel--wide" aria-labelledby="changed-heading"><div class="ri-panel-heading"><span class="ri-panel-icon" aria-hidden="true">⌁</span><div><span class="ri-eyebrow">Changed</span><h2 id="changed-heading">Most recent meaningful change</h2></div></div>{render_recent_change(now)}</section>
        <section class="ri-panel" aria-labelledby="focus-heading"><div class="ri-panel-heading"><span class="ri-panel-icon" aria-hidden="true">◎</span><div><span class="ri-eyebrow">Active</span><h2 id="focus-heading">Current quests</h2></div></div>{render_collection(focus, empty_title="No active quest asserted", empty_message="No current focus is projected. Incomplete work is not automatically called active.", eyebrow="Active quest")}</section>
        <section class="ri-panel" data-severity="blocked" aria-labelledby="blockers-heading"><div class="ri-panel-heading"><span class="ri-panel-icon" aria-hidden="true">!</span><div><span class="ri-eyebrow">Blocked</span><h2 id="blockers-heading">Blockers</h2></div></div>{render_collection(blockers, empty_title="No blocker asserted", empty_message="The snapshot contains no explicit blocked-by evidence.", eyebrow="Blocker")}</section>
        <section class="ri-panel" data-severity="failure" aria-labelledby="broken-heading"><div class="ri-panel-heading"><span class="ri-panel-icon" aria-hidden="true">×</span><div><span class="ri-eyebrow">Newly broken</span><h2 id="broken-heading">Checks that regressed</h2></div></div>{render_collection(broken, empty_title="No newly broken check", empty_message="No recent check transition into a failing state is projected.", eyebrow="Broken check")}</section>
        <section class="ri-panel" aria-labelledby="decisions-heading"><div class="ri-panel-heading"><span class="ri-panel-icon" aria-hidden="true">◇</span><div><span class="ri-eyebrow">Pending</span><h2 id="decisions-heading">Decisions awaiting closure</h2></div></div>{render_collection(pending, empty_title="No pending decision", empty_message="No draft, pending, or proposed ADR is projected.", eyebrow="Pending decision")}</section>
      </div>
    </section>
    <section class="ri-section" aria-labelledby="actions-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Ready queue</span><h2 id="actions-heading">The next three grounded moves</h2></div><p>Each action retains its rationale, prerequisites, and canonical source.</p></div>{render_next_actions(snapshot)}</section>'''


def placeholder_body(route: str, label: str, prefix: str) -> str:
    issue_routes = {
        "roadmap": 31,
        "decisions": 30,
        "journey": 32,
        "dependencies": 29,
        "health": 29,
        "releases": 33,
        "work": 33,
        "search": 33,
        "compare": 33,
    }
    issue = issue_routes.get(route, 27)
    return f'''<section class="ri-section ri-section--lead" aria-labelledby="placeholder-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Shared shell ready</span><h2 id="placeholder-heading">{escaped(label)} is the next layer</h2></div><p>This route is reserved now so navigation, deep links, and page composition stay stable as the experience grows.</p></div>
      <div class="ri-panel">{empty_state("View intentionally not materialized yet", "The shell is live; this evidence projection remains owned by its focused Relay issue.", "not_applicable")}<p><a class="ri-button" href="https://github.com/egohygiene/relay/issues/{issue}">Track Relay #{issue} <span aria-hidden="true">↗</span></a> <a class="ri-button ri-button--quiet" href="{escaped(prefix)}now/">Return to Now</a></p></div></section>'''


def write_site(
    *,
    output_root: Path,
    summary: dict[str, Any],
    provenance: dict[str, Any],
    snapshot: dict[str, Any] | None,
    repository: str,
    source_commit: str,
    stylesheet_source: Path,
    script_source: Path,
) -> None:
    observed_at = str(
        snapshot.get("observed_at") if snapshot else summary.get("generated_at") or ""
    )
    freshness = normalize_state(
        require_object(snapshot.get("coverage")).get("status") if snapshot else "unknown"
    )
    current = now_body(snapshot)
    shared = {
        "repository": repository,
        "source_commit": source_commit,
        "observed_at": observed_at,
        "freshness": freshness,
        "summary": summary,
        "snapshot_available": snapshot is not None,
    }
    atomic_write(
        output_root / "index.html",
        shell_document(route="now", route_label="Now", body=current, prefix="", **shared),
    )
    atomic_write(
        output_root / "now/index.html",
        shell_document(route="now", route_label="Now", body=current, prefix="../", **shared),
    )
    for route, label in ROUTES[1:]:
        atomic_write(
            output_root / route / "index.html",
            shell_document(
                route=route,
                route_label=label,
                body=placeholder_body(route, label, "../"),
                prefix="../",
                **shared,
            ),
        )
    atomic_write(output_root / "site.css", stylesheet_source.read_text(encoding="utf-8"))
    atomic_write(output_root / "site.js", script_source.read_text(encoding="utf-8"))


def main() -> int:
    args = parse_arguments()
    repository_root = Path(args.repository_root).resolve(strict=True)
    output_root = Path(args.output_root).resolve()
    summary_path = Path(args.summary).resolve()
    provenance_path = Path(args.provenance).resolve()
    snapshot_path = Path(args.snapshot).absolute() if args.snapshot else None
    stylesheet_source = Path(args.stylesheet_source).resolve()
    script_source = Path(args.script_source).resolve()
    if not FULL_SHA.fullmatch(args.source_commit):
        raise SystemExit("source-commit must be a full lowercase Git SHA")
    for path, label in (
        (output_root, "output root"),
        (summary_path, "dashboard summary"),
        (provenance_path, "bundle provenance"),
        *(((snapshot_path, "Observatory snapshot"),) if snapshot_path is not None else ()),
    ):
        validate_repository_path(repository_root, path, label)
    summary = load_object(summary_path, "dashboard summary")
    provenance = load_object(provenance_path, "bundle provenance")
    validate_site_contracts(summary, provenance, args.repository, args.source_commit)
    snapshot = None
    if snapshot_path is not None:
        if not snapshot_path.is_file():
            raise SystemExit(f"Observatory snapshot is unavailable: {snapshot_path}")
        snapshot = validate_snapshot(
            load_object(snapshot_path, "Observatory snapshot"),
            args.repository,
            args.source_commit,
        )
    write_site(
        output_root=output_root,
        summary=summary,
        provenance=provenance,
        snapshot=snapshot,
        repository=args.repository,
        source_commit=args.source_commit,
        stylesheet_source=stylesheet_source,
        script_source=script_source,
    )
    print(
        f"Generated Repository Intelligence shell at {output_root} "
        f"for {args.repository}@{args.source_commit[:12]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
