# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Compose the routed Repository Intelligence shell and operational Now view."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
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
ROADMAP_STATES = {
    "active",
    "blocked",
    "cancelled",
    "complete",
    "deferred",
    "planned",
    "ready",
    "superseded",
}
ROADMAP_EVIDENCE_FIELDS = (
    ("blocked_by", "blocked by"),
    ("dependencies", "depends on"),
    ("informed_by", "informed by"),
    ("tracked_by", "tracked by"),
    ("verified_by", "verified by"),
    ("evidence", "evidence"),
    ("releases", "released by"),
    ("deployments", "deployed by"),
    ("changed_files", "changed file"),
    ("files", "changed file"),
    ("supersedes", "supersedes"),
    ("superseded_by", "superseded by"),
)


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


def stable_fragment(prefix: str, value: Any) -> str:
    """Build a readable fragment whose identity does not depend on display order."""

    identity = str(value or "record")
    slug = re.sub(r"[^a-z0-9]+", "-", identity.casefold()).strip("-") or "record"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{slug[:72]}-{digest}"


def validate_roadmap_view(roadmap: dict[str, Any]) -> None:
    """Validate the display boundary needed for durable quest-line rendering."""

    roots = require_list(roadmap.get("roots"))
    if any(not isinstance(root, str) or not root for root in roots):
        raise SiteInputError("snapshot views.roadmap.roots must contain stable IDs")
    if len(roots) != len(set(roots)):
        raise SiteInputError("snapshot views.roadmap.roots must be unique")
    identifiers: set[str] = set()
    keys: set[str] = set()
    fragments: set[str] = set()
    for index, candidate in enumerate(require_list(roadmap.get("steps"))):
        step = require_object(candidate)
        if not step:
            raise SiteInputError(f"snapshot views.roadmap.steps[{index}] must be an object")
        step_entity = entity(step)
        for member in ("id", "key", "title", "kind", "state"):
            if not isinstance(step_entity.get(member), str) or not step_entity[member]:
                raise SiteInputError(
                    f"snapshot views.roadmap.steps[{index}].entity.{member} "
                    "must be a non-empty string"
                )
        if normalize_state(step_entity.get("kind")) != "roadmap_step":
            raise SiteInputError(
                f"snapshot views.roadmap.steps[{index}] must describe a roadmap_step"
            )
        state = normalize_state(step_entity.get("state"))
        if state not in ROADMAP_STATES:
            raise SiteInputError(
                f"snapshot views.roadmap.steps[{index}] uses unsupported state {state}"
            )
        identifier = str(step_entity["id"])
        key = str(step_entity["key"])
        fragment = stable_fragment("quest", identifier)
        if identifier in identifiers or key in keys or fragment in fragments:
            raise SiteInputError("roadmap step IDs, keys, and fragments must be unique")
        identifiers.add(identifier)
        keys.add(key)
        fragments.add(fragment)
        for field, _ in ROADMAP_EVIDENCE_FIELDS:
            if field in step and not isinstance(step[field], list):
                raise SiteInputError(
                    f"snapshot views.roadmap.steps[{index}].{field} must be an array"
                )
        criteria = require_list(step.get("exit_criteria"))
        for criterion_index, criterion_value in enumerate(criteria):
            criterion = require_object(criterion_value)
            if (
                not isinstance(criterion.get("text"), str)
                or not criterion["text"]
                or not isinstance(criterion.get("complete"), bool)
            ):
                raise SiteInputError(
                    "snapshot views.roadmap.steps"
                    f"[{index}].exit_criteria[{criterion_index}] is invalid"
                )
    missing_roots = sorted(set(roots) - identifiers)
    if missing_roots:
        raise SiteInputError(
            "snapshot views.roadmap.roots contain unresolved step IDs: "
            + ", ".join(missing_roots)
        )


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
    validate_roadmap_view(require_object(views.get("roadmap")))
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


def roadmap_index(
    snapshot: dict[str, Any],
) -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, str],
    dict[str, list[dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
]:
    """Index roadmap steps and derive inverse display links without changing truth."""

    roadmap = require_object(require_object(snapshot.get("views")).get("roadmap"))
    steps = [require_object(step) for step in require_list(roadmap.get("steps"))]
    by_id = {str(entity(step).get("id")): step for step in steps}
    by_key = {str(entity(step).get("key")): step for step in steps}
    anchors: dict[str, str] = {}
    for step in steps:
        step_entity = entity(step)
        anchor = stable_fragment("quest", step_entity.get("id"))
        anchors[str(step_entity.get("id"))] = anchor
        anchors[str(step_entity.get("key"))] = anchor
    dependents: dict[str, list[dict[str, Any]]] = {identifier: [] for identifier in by_id}
    blocks: dict[str, list[dict[str, Any]]] = {identifier: [] for identifier in by_id}
    for step in steps:
        step_entity = entity(step)
        for dependency_value in require_list(step.get("dependencies")):
            dependency = entity(dependency_value)
            dependency_id = str(dependency.get("id") or "")
            dependency_step = by_id.get(dependency_id) or by_key.get(
                str(dependency.get("key") or "")
            )
            if dependency_step is not None:
                dependents[str(entity(dependency_step).get("id"))].append(step_entity)
        for blocker_value in require_list(step.get("blocked_by")):
            blocker = entity(blocker_value)
            blocker_id = str(blocker.get("id") or "")
            blocker_step = by_id.get(blocker_id) or by_key.get(str(blocker.get("key") or ""))
            if blocker_step is not None:
                blocks[str(entity(blocker_step).get("id"))].append(step_entity)
    return steps, by_id, anchors, dependents, blocks


def roadmap_chapters(
    snapshot: dict[str, Any], steps: list[dict[str, Any]], by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Group the dependency forest by declared roots while retaining source order."""

    roadmap = require_object(require_object(snapshot.get("views")).get("roadmap"))
    order = {str(entity(step).get("id")): index for index, step in enumerate(steps)}
    children: dict[str, list[str]] = {identifier: [] for identifier in by_id}
    for step in steps:
        step_id = str(entity(step).get("id"))
        for dependency_value in require_list(step.get("dependencies")):
            dependency = entity(dependency_value)
            dependency_id = str(dependency.get("id") or "")
            if dependency_id in children:
                children[dependency_id].append(step_id)
    for values in children.values():
        values.sort(key=lambda identifier: order.get(identifier, len(order)))
    declared_roots = [
        str(identifier)
        for identifier in require_list(roadmap.get("roots"))
        if str(identifier) in by_id
    ]
    if not declared_roots and steps:
        declared_roots = [str(entity(steps[0]).get("id"))]
    assigned: set[str] = set()
    chapters: list[dict[str, Any]] = []
    for root_id in declared_roots:
        queue = [root_id]
        members: list[dict[str, Any]] = []
        while queue:
            identifier = queue.pop(0)
            if identifier in assigned or identifier not in by_id:
                continue
            assigned.add(identifier)
            members.append(by_id[identifier])
            queue.extend(children.get(identifier, []))
        if members:
            members.sort(key=lambda step: order[str(entity(step).get("id"))])
            chapters.append({"root": by_id[root_id], "steps": members})
    remaining = [step for step in steps if str(entity(step).get("id")) not in assigned]
    if remaining:
        chapters.append({"root": remaining[0], "steps": remaining, "supplemental": True})
    return chapters


def roadmap_evidence(step: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Flatten the normalized, relationship-labelled evidence attached to one quest."""

    records: list[tuple[str, dict[str, Any]]] = []
    seen: set[tuple[str, str]] = set()
    for field, relationship in ROADMAP_EVIDENCE_FIELDS:
        for candidate in require_list(step.get(field)):
            value = entity(candidate)
            identifier = str(value.get("id") or value.get("canonical_url") or "")
            marker = (relationship, identifier)
            if not value or not identifier or marker in seen:
                continue
            seen.add(marker)
            records.append((relationship, value))
    return records


def roadmap_reference_href(value: dict[str, Any], anchors: dict[str, str]) -> str:
    internal = anchors.get(str(value.get("id") or "")) or anchors.get(
        str(value.get("key") or "")
    )
    if internal:
        return f"#{internal}"
    return safe_href(value.get("canonical_url"))


def render_roadmap_reference(
    value: dict[str, Any], anchors: dict[str, str], relationship: str
) -> str:
    href = roadmap_reference_href(value, anchors)
    label = value.get("title") or value.get("key") or "Untitled evidence"
    content = (
        f'<span class="ri-link-chip__relationship">{escaped(relationship)}</span>'
        f'<span>{escaped(label)}</span>'
    )
    if href:
        return f'<a class="ri-link-chip" href="{escaped(href)}">{content}</a>'
    return f'<span class="ri-link-chip">{content}</span>'


def render_roadmap_evidence_record(
    relationship: str,
    value: dict[str, Any],
    anchors: dict[str, str],
    index: int,
    total: int,
) -> str:
    kind = normalize_state(value.get("kind"))
    state = normalize_state(value.get("state"))
    href = roadmap_reference_href(value, anchors)
    title = value.get("title") or value.get("key") or "Untitled evidence"
    search = " ".join(
        str(item or "")
        for item in (
            relationship,
            value.get("title"),
            value.get("key"),
            value.get("kind"),
            value.get("state"),
            value.get("repository"),
        )
    ).lower()
    heading = (
        f'<a href="{escaped(href)}">{escaped(title)} <span aria-hidden="true">↗</span></a>'
        if href
        else f"<span>{escaped(title)}</span>"
    )
    return f'''<li class="ri-evidence-record" data-evidence-item data-kind="{escaped(kind)}" data-state="{escaped(state)}" data-search="{escaped(search)}" aria-posinset="{index + 1}" aria-setsize="{total}">
      <div class="ri-evidence-record__top"><span class="ri-evidence-kind">{escaped(state_label(kind))}</span>{status_pill(state)}</div>
      <strong>{heading}</strong>
      <p>{escaped(relationship.capitalize())} · {escaped(value.get("key") or "No identifier")}</p>
      <dl class="ri-provenance"><div><dt>Assertion</dt><dd>{escaped(state_label(value.get("assertion")))}</dd></div><div><dt>Confidence</dt><dd>{escaped(state_label(value.get("confidence")))}</dd></div><div><dt>Freshness</dt><dd>{escaped(state_label(value.get("freshness")))}</dd></div><div><dt>Owner</dt><dd>{escaped(value.get("repository") or "Unknown")}</dd></div></dl>
    </li>'''


def render_exit_criteria(criteria: list[Any]) -> str:
    if not criteria:
        return '<p class="ri-muted">No exit criteria are projected for this quest.</p>'
    items = []
    for candidate in criteria:
        criterion = require_object(candidate)
        complete = bool(criterion.get("complete"))
        items.append(
            f'<li data-complete="{str(complete).lower()}"><span aria-hidden="true">'
            f'{"✓" if complete else ""}</span><span>{escaped(criterion.get("text"))}</span></li>'
        )
    return '<ul class="ri-criteria" aria-label="Exit criteria">' + "".join(items) + "</ul>"


def render_relationship_row(
    label: str, values: list[Any], anchors: dict[str, str]
) -> str:
    records = [entity(value) for value in values if entity(value)]
    if not records:
        return ""
    return (
        f'<div class="ri-relationship-row"><strong>{escaped(label)}</strong><div>'
        + "".join(render_roadmap_reference(value, anchors, label.casefold()) for value in records)
        + "</div></div>"
    )


def render_quest_step(
    step: dict[str, Any],
    *,
    index: int,
    total: int,
    anchors: dict[str, str],
    dependents: dict[str, list[dict[str, Any]]],
    blocks: dict[str, list[dict[str, Any]]],
) -> str:
    step_entity = entity(step)
    step_id = str(step_entity.get("id"))
    anchor = anchors[step_id]
    state = normalize_state(step_entity.get("state"))
    criteria = require_list(step.get("exit_criteria"))
    complete_criteria = sum(
        1 for candidate in criteria if require_object(candidate).get("complete") is True
    )
    percentage = (
        round(complete_criteria * 100 / len(criteria))
        if criteria
        else (100 if state == "complete" else 0)
    )
    evidence_records = roadmap_evidence(step)
    evidence_kinds = [normalize_state(value.get("kind")) for _, value in evidence_records]
    evidence_states = [normalize_state(value.get("state")) for _, value in evidence_records]
    kinds = sorted({"roadmap_step", *evidence_kinds})
    states = sorted({state, *evidence_states})
    search = " ".join(
        [
            str(step_entity.get("key") or ""),
            str(step_entity.get("title") or ""),
            str(step.get("outcome") or ""),
            state,
            *[
                " ".join(
                    str(item or "")
                    for item in (
                        relationship,
                        value.get("title"),
                        value.get("key"),
                        value.get("kind"),
                        value.get("state"),
                    )
                )
                for relationship, value in evidence_records
            ],
        ]
    ).lower()
    kind_counts: dict[str, int] = {}
    for kind in evidence_kinds:
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
    evidence_summary = "".join(
        f'<span><strong>{count}</strong> {escaped(state_label(kind))}</span>'
        for kind, count in sorted(kind_counts.items())
    ) or "<span>No linked evidence yet</span>"
    evidence_items = "".join(
        render_roadmap_evidence_record(relationship, value, anchors, evidence_index, len(evidence_records))
        for evidence_index, (relationship, value) in enumerate(evidence_records)
    )
    canonical = source_link(step_entity, "Open canonical ROADMAP.md step")
    return f'''<li class="ri-quest" id="{escaped(anchor)}" data-filter-item data-roadmap-quest data-state="{escaped(state)}" data-states="{escaped(" ".join(states))}" data-kind="roadmap_step" data-kinds="{escaped(" ".join(kinds))}" data-search="{escaped(search)}">
      <div class="ri-quest__node" aria-hidden="true"><span>{index + 1:02d}</span></div>
      <article class="ri-quest__card" tabindex="-1">
        <header><div><a class="ri-quest__permalink" data-quest-link href="#{escaped(anchor)}">Quest {index + 1} of {total} · {escaped(step_entity.get("key"))}</a><h3>{escaped(step_entity.get("title"))}</h3></div>{status_pill(state)}</header>
        <p class="ri-quest__outcome">{escaped(step.get("outcome") or "Outcome not yet described.")}</p>
        <div class="ri-progress"><div role="progressbar" aria-label="Exit-criteria progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{percentage}"><span style="--ri-progress: {percentage}%"></span></div><strong>{complete_criteria}/{len(criteria)} criteria · {percentage}%</strong></div>
        {render_exit_criteria(criteria)}
        <div class="ri-relationship-grid">
          {render_relationship_row("Depends on", require_list(step.get("dependencies")), anchors)}
          {render_relationship_row("Unlocks", dependents.get(step_id, []), anchors)}
          {render_relationship_row("Blocked by", require_list(step.get("blocked_by")), anchors)}
          {render_relationship_row("Blocks", blocks.get(step_id, []), anchors)}
        </div>
        <div class="ri-quest__source">{canonical}<span>Assertion: {escaped(state_label(step_entity.get("assertion")))} · Freshness: {escaped(state_label(step_entity.get("freshness")))}</span></div>
        <details class="ri-evidence" data-quest-evidence>
          <summary><span><strong>Quest evidence</strong><small>{len(evidence_records)} linked {"record" if len(evidence_records) == 1 else "records"}</small></span><span aria-hidden="true">+</span></summary>
          <div class="ri-evidence__summary">{evidence_summary}</div>
          <div class="ri-evidence-viewport" data-evidence-viewport data-evidence-total="{len(evidence_records)}" data-row-height="150">
            <ol class="ri-evidence-list">{evidence_items}</ol>
          </div>
        </details>
      </article>
    </li>'''


def roadmap_body(snapshot: dict[str, Any] | None) -> str:
    """Render a static-first, dependency-aware quest line from Observatory output."""

    if snapshot is None:
        return f'''<section class="ri-section ri-section--lead" aria-labelledby="roadmap-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Canonical intent</span><h2 id="roadmap-heading">The quest line</h2></div><p>The page never infers roadmap state from repository activity.</p></div>{empty_state("Observatory roadmap unavailable", "Supply a repository- and commit-matched read model to render stable quests, progress, dependencies, and delivery evidence.", "partial")}</section>'''
    steps, by_id, anchors, dependents, blocks = roadmap_index(snapshot)
    if not steps:
        return f'''<section class="ri-section ri-section--lead" aria-labelledby="roadmap-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Canonical intent</span><h2 id="roadmap-heading">The quest line</h2></div><p>The supplied read model contains no roadmap steps.</p></div>{empty_state("No roadmap quests projected", "ROADMAP.md remains canonical. Add contract-valid stable steps there before expecting a generated path.", "empty")}</section>'''
    chapters = roadmap_chapters(snapshot, steps, by_id)
    complete = sum(1 for step in steps if normalize_state(entity(step).get("state")) == "complete")
    active = sum(1 for step in steps if normalize_state(entity(step).get("state")) == "active")
    blocked = sum(1 for step in steps if normalize_state(entity(step).get("state")) == "blocked")
    completed_criteria = sum(
        1
        for step in steps
        for criterion in require_list(step.get("exit_criteria"))
        if require_object(criterion).get("complete") is True
    )
    total_criteria = sum(len(require_list(step.get("exit_criteria"))) for step in steps)
    repository = str(require_object(snapshot.get("repository")).get("key"))
    source_commit = str(snapshot.get("represented_commit"))
    roadmap_url = f"https://github.com/{repository}/blob/{source_commit}/ROADMAP.md"
    minimap = []
    rendered_chapters = []
    sequence = 0
    for chapter_index, chapter in enumerate(chapters, start=1):
        root_entity = entity(chapter["root"])
        chapter_anchor = stable_fragment("chapter", root_entity.get("id"))
        chapter_steps = chapter["steps"]
        chapter_complete = sum(
            1
            for step in chapter_steps
            if normalize_state(entity(step).get("state")) == "complete"
        )
        minimap_quests = "".join(
            f'<li><a data-minimap-quest href="#{escaped(anchors[str(entity(step).get("id"))])}" data-state="{escaped(normalize_state(entity(step).get("state")))}"><span>{escaped(entity(step).get("key"))}</span><small>{escaped(entity(step).get("title"))}</small></a></li>'
            for step in chapter_steps
        )
        minimap.append(
            f'<li><a class="ri-map__chapter" href="#{escaped(chapter_anchor)}">Chapter {chapter_index:02d} · {escaped(root_entity.get("title"))}</a><ol>{minimap_quests}</ol></li>'
        )
        quest_html = []
        for step in chapter_steps:
            quest_html.append(
                render_quest_step(
                    step,
                    index=sequence,
                    total=len(steps),
                    anchors=anchors,
                    dependents=dependents,
                    blocks=blocks,
                )
            )
            sequence += 1
        rendered_chapters.append(
            f'''<section class="ri-roadmap-chapter" id="{escaped(chapter_anchor)}" aria-labelledby="{escaped(chapter_anchor)}-title">
              <header class="ri-chapter-heading"><div><span>Chapter {chapter_index:02d}</span><h2 id="{escaped(chapter_anchor)}-title">{escaped(root_entity.get("title"))}</h2></div><p><strong>{chapter_complete}/{len(chapter_steps)}</strong> quests complete</p></header>
              <ol class="ri-quest-line">{"".join(quest_html)}</ol>
            </section>'''
        )
    return f'''<section class="ri-section ri-section--lead ri-roadmap-intro" aria-labelledby="roadmap-heading">
      <div class="ri-section-heading"><div><span class="ri-eyebrow">Canonical intent</span><h2 id="roadmap-heading">The quest line</h2></div><p>Follow the dependency path, inspect delivery evidence, and return to the exact step in <a href="{escaped(roadmap_url)}">ROADMAP.md</a>.</p></div>
      <div class="ri-roadmap-metrics" aria-label="Roadmap progress summary"><article><strong>{complete}/{len(steps)}</strong><span>verified complete</span></article><article><strong>{active}</strong><span>active now</span></article><article><strong>{blocked}</strong><span>explicitly blocked</span></article><article><strong>{completed_criteria}/{total_criteria}</strong><span>exit criteria met</span></article></div>
      <details class="ri-progress-rules"><summary>How progress is determined</summary><p>Quest state comes from canonical roadmap declarations normalized by Observatory. Exit-criteria completion is the only percentage denominator. Commits and other linked records are evidence, never progress units. Missing, stale, inferred, and unknown evidence remain labelled.</p></details>
    </section>
    <div class="ri-roadmap-layout">
      <nav class="ri-map" aria-label="Roadmap chapters and quests"><span class="ri-eyebrow">Quest map</span><p>{len(chapters)} {"chapter" if len(chapters) == 1 else "chapters"} · {len(steps)} quests</p><ol>{"".join(minimap)}</ol></nav>
      <div class="ri-roadmap-story">{"".join(rendered_chapters)}</div>
    </div>'''


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
    route_descriptions = {
        "now": "See what changed, what needs attention, and the next grounded moves without flattening uncertainty.",
        "roadmap": "Traverse canonical intent as a quest line, then open the evidence that makes each step true.",
    }
    route_description = route_descriptions.get(
        route,
        "Explore one commit-matched projection without replacing its canonical repository sources.",
    )
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
          <div><span class="ri-kicker"><i aria-hidden="true"></i>{escaped(route_label)} view</span><h1>{escaped(repository.split("/", 1)[-1])}</h1><p>{escaped(route_description)}</p></div>
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
          <label><span>State</span><select data-filter-state><option value="all">All states</option><option value="active">Active</option><option value="blocked">Blocked</option><option value="ready">Ready</option><option value="planned">Planned</option><option value="complete">Complete</option><option value="deferred">Deferred</option><option value="superseded">Superseded</option><option value="failure">Failure</option><option value="proposed">Proposed</option><option value="unknown">Unknown</option></select></label>
          <label><span>Kind</span><select data-filter-kind><option value="all">All evidence</option><option value="roadmap_step">Quest</option><option value="architecture_decision">Decision</option><option value="check">Check</option><option value="commit">Commit</option><option value="issue">Issue</option><option value="pull_request">Pull request</option><option value="release">Release</option><option value="deployment">Deployment</option><option value="file">Changed file</option></select></label>
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
        body = (
            roadmap_body(snapshot)
            if route == "roadmap"
            else placeholder_body(route, label, "../")
        )
        atomic_write(
            output_root / route / "index.html",
            shell_document(
                route=route,
                route_label=label,
                body=body,
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
