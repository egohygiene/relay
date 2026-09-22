# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Compose routed operational, roadmap, decision, and journey intelligence."""

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
ROUTE_QUESTIONS = {
    "now": "What changed, what needs attention, and which grounded moves come next?",
    "roadmap": "What should happen next, what is blocked, and which evidence proves progress?",
    "decisions": "Why did the architecture change, and what authority does each decision retain?",
    "journey": "How did intent become work, code, proof, and delivery over time?",
    "dependencies": "What depends on what, and where can a change or blocker propagate?",
    "health": "What do normalized checks and freshness evidence say right now?",
    "releases": "What actually shipped, when, and with which included evidence?",
    "work": "Which execution records and roadmap queues need attention?",
    "search": "Where is a normalized repository object and its canonical source?",
    "compare": "What structurally changed between two accepted snapshots?",
}
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
DECISION_STATES = {"accepted", "deprecated", "proposed", "rejected", "superseded"}
DECISION_IMPLEMENTATION_STATES = {
    "implemented",
    "in_progress",
    "not_applicable",
    "not_started",
    "unknown",
    "verified",
}
DECISION_RELATIONSHIP_FIELDS = (
    ("informs", "affects roadmap"),
    ("tracked_by", "tracked by"),
    ("evidence", "evidenced by"),
    ("verified_by", "verified by"),
    ("implemented_by", "implemented by"),
    ("releases", "released by"),
    ("deployments", "deployed by"),
    ("changed_files", "changed file"),
    ("related", "related to"),
    ("supersedes", "supersedes"),
    ("superseded_by", "superseded by"),
)
JOURNEY_EVENT_TYPES = {
    "architecture_decision.accepted",
    "architecture_decision.deprecated",
    "architecture_decision.proposed",
    "architecture_decision.superseded",
    "check.completed",
    "commit.created",
    "deployment.completed",
    "issue.closed",
    "issue.opened",
    "issue.reopened",
    "pull_request.closed",
    "pull_request.merged",
    "pull_request.opened",
    "release.published",
    "repository.observed",
    "roadmap_step.created",
    "roadmap_step.status_changed",
}
JOURNEY_LANES = (
    ("intent", "Intent", {"architecture_decision", "roadmap_step"}),
    ("work", "Work", {"issue", "pull_request"}),
    ("code", "Code", {"commit"}),
    ("proof", "Proof", {"check"}),
    ("delivery", "Delivery", {"deployment", "release", "repository"}),
)
JOURNEY_ASSERTIONS = {"authoritative", "inferred", "unknown"}
JOURNEY_FRESHNESS = {"current", "not_applicable", "stale", "unknown"}
JOURNEY_VISIBILITIES = {"internal", "private", "public"}


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


def format_calendar_date(value: Any) -> str:
    """Render one ADR date without implying a timestamp that was not projected."""

    if not isinstance(value, str) or not value:
        return "Not projected"
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%b %d, %Y")
    except ValueError:
        return value


def parse_rfc3339(value: Any, label: str) -> datetime:
    """Parse a timezone-aware contract timestamp or fail at the display boundary."""

    normalized = value[:-1] + "+00:00" if isinstance(value, str) and value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except (TypeError, ValueError) as error:
        raise SiteInputError(f"{label} must be an RFC 3339 timestamp") from error
    if parsed.tzinfo is None:
        raise SiteInputError(f"{label} must be an RFC 3339 timestamp")
    return parsed


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


def filter_token(value: Any) -> str:
    """Return a whitespace-safe, deterministic token for an exact filter value."""

    text = str(value or "unknown")
    slug = re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-") or "unknown"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
    return f"{slug[:48]}-{digest}"


def string_values(value: Any) -> list[str]:
    """Normalize optional scalar-or-array display metadata without inventing values."""

    if isinstance(value, str) and value:
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item]
    return []


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


def validate_decisions_view(decisions_view: dict[str, Any]) -> None:
    """Validate the display boundary required for a durable ADR ledger."""

    identifiers: set[str] = set()
    keys: set[str] = set()
    fragments: set[str] = set()
    required_relationships = {
        "evidence",
        "informs",
        "superseded_by",
        "supersedes",
        "tracked_by",
        "verified_by",
    }
    for index, candidate in enumerate(require_list(decisions_view.get("decisions"))):
        decision = require_object(candidate)
        if not decision:
            raise SiteInputError(
                f"snapshot views.decisions.decisions[{index}] must be an object"
            )
        decision_entity = entity(decision)
        for member in (
            "assertion",
            "canonical_url",
            "freshness",
            "id",
            "key",
            "kind",
            "repository",
            "state",
            "title",
        ):
            if (
                not isinstance(decision_entity.get(member), str)
                or not decision_entity[member]
            ):
                raise SiteInputError(
                    "snapshot views.decisions.decisions"
                    f"[{index}].entity.{member} must be a non-empty string"
                )
        if normalize_state(decision_entity.get("kind")) != "architecture_decision":
            raise SiteInputError(
                "snapshot views.decisions.decisions"
                f"[{index}] must describe an architecture_decision"
            )
        status = normalize_state(decision_entity.get("state"))
        if status not in DECISION_STATES:
            raise SiteInputError(
                "snapshot views.decisions.decisions"
                f"[{index}] uses unsupported status {status}"
            )
        implementation = normalize_state(decision.get("implementation_status"))
        if implementation not in DECISION_IMPLEMENTATION_STATES:
            raise SiteInputError(
                "snapshot views.decisions.decisions"
                f"[{index}] uses unsupported implementation status {implementation}"
            )
        scope = normalize_state(decision.get("decision_scope"))
        if scope not in {"organization", "repository"}:
            raise SiteInputError(
                "snapshot views.decisions.decisions"
                f"[{index}] uses unsupported decision scope {scope}"
            )
        identifier = str(decision_entity["id"])
        key = str(decision_entity["key"])
        fragment = stable_fragment("decision", identifier)
        if identifier in identifiers or key in keys or fragment in fragments:
            raise SiteInputError("decision IDs, keys, and fragments must be unique")
        identifiers.add(identifier)
        keys.add(key)
        fragments.add(fragment)
        for field in required_relationships:
            if not isinstance(decision.get(field), list):
                raise SiteInputError(
                    "snapshot views.decisions.decisions"
                    f"[{index}].{field} must be an array"
                )
        decision_date = decision.get("date")
        if decision_date is not None:
            try:
                datetime.strptime(str(decision_date), "%Y-%m-%d")
            except ValueError as error:
                raise SiteInputError(
                    "snapshot views.decisions.decisions"
                    f"[{index}].date must use YYYY-MM-DD"
                ) from error


def validate_journey_view(journey: dict[str, Any]) -> None:
    """Validate chronological events and their deterministic release chapters."""

    events = require_list(journey.get("events"))
    chapters = require_list(journey.get("chapters"))
    event_ids: set[str] = set()
    fragments: set[str] = set()
    event_index: dict[str, dict[str, Any]] = {}
    chronological: list[tuple[datetime, str]] = []
    for index, candidate in enumerate(events):
        event = require_object(candidate)
        if not event:
            raise SiteInputError(f"snapshot views.journey.events[{index}] must be an object")
        for member in ("id", "type", "subject", "occurred_at", "recorded_at"):
            if not isinstance(event.get(member), str) or not event[member]:
                raise SiteInputError(
                    f"snapshot views.journey.events[{index}].{member} must be a non-empty string"
                )
        identifier = str(event["id"])
        fragment = stable_fragment("event", identifier)
        if identifier in event_ids or fragment in fragments:
            raise SiteInputError("journey event IDs and fragments must be unique")
        event_ids.add(identifier)
        fragments.add(fragment)
        event_index[identifier] = event
        event_type = str(event.get("type"))
        if event_type not in JOURNEY_EVENT_TYPES:
            raise SiteInputError(
                f"snapshot views.journey.events[{index}] uses unsupported type {event_type}"
            )
        occurred_at = parse_rfc3339(
            event.get("occurred_at"),
            f"snapshot views.journey.events[{index}].occurred_at",
        )
        parse_rfc3339(
            event.get("recorded_at"),
            f"snapshot views.journey.events[{index}].recorded_at",
        )
        chronological.append((occurred_at, identifier))
        for member in ("changes", "provenance"):
            if not isinstance(event.get(member), list):
                raise SiteInputError(
                    f"snapshot views.journey.events[{index}].{member} must be an array"
                )
        for change_index, candidate_change in enumerate(event["changes"]):
            change = require_object(candidate_change)
            if (
                not change
                or not isinstance(change.get("field"), str)
                or not change["field"]
                or "from" not in change
                or "to" not in change
                or (change["from"] is None and change["to"] is None)
            ):
                raise SiteInputError(
                    "snapshot views.journey.events"
                    f"[{index}].changes[{change_index}] is invalid"
                )
        provenance = event["provenance"]
        if (
            not provenance
            or any(not isinstance(value, str) or not value for value in provenance)
            or len(provenance) != len(set(provenance))
        ):
            raise SiteInputError(
                f"snapshot views.journey.events[{index}].provenance must contain unique source IDs"
            )
        if not isinstance(event.get("extensions"), dict):
            raise SiteInputError(
                f"snapshot views.journey.events[{index}].extensions must be an object"
            )
        if event.get("actor") is not None:
            actor = require_object(event.get("actor"))
            if not actor:
                raise SiteInputError(
                    f"snapshot views.journey.events[{index}].actor must be an object or null"
                )
            for member in ("assertion", "id", "kind", "url"):
                if not isinstance(actor.get(member), str) or not actor[member]:
                    raise SiteInputError(
                        "snapshot views.journey.events"
                        f"[{index}].actor.{member} must be a non-empty string"
                    )
            if actor.get("assertion") not in JOURNEY_ASSERTIONS:
                raise SiteInputError(
                    f"snapshot views.journey.events[{index}].actor.assertion is unsupported"
                )
        if event.get("assertion") not in JOURNEY_ASSERTIONS:
            raise SiteInputError(
                f"snapshot views.journey.events[{index}].assertion is unsupported"
            )
        if event.get("freshness") not in JOURNEY_FRESHNESS:
            raise SiteInputError(
                f"snapshot views.journey.events[{index}].freshness is unsupported"
            )
        if event.get("visibility") not in JOURNEY_VISIBILITIES:
            raise SiteInputError(
                f"snapshot views.journey.events[{index}].visibility is unsupported"
            )
        subject = require_object(event.get("subject_entity"))
        for member in (
            "assertion",
            "canonical_url",
            "freshness",
            "id",
            "key",
            "kind",
            "repository",
            "state",
            "visibility",
        ):
            if not isinstance(subject.get(member), str) or not subject[member]:
                raise SiteInputError(
                    "snapshot views.journey.events"
                    f"[{index}].subject_entity.{member} must be a non-empty string"
                )
        if subject.get("title") is not None and (
            not isinstance(subject.get("title"), str) or not subject["title"]
        ):
            raise SiteInputError(
                f"snapshot views.journey.events[{index}].subject_entity.title is invalid"
            )
        if subject.get("assertion") not in JOURNEY_ASSERTIONS:
            raise SiteInputError(
                f"snapshot views.journey.events[{index}].subject_entity.assertion is unsupported"
            )
        if subject.get("freshness") not in JOURNEY_FRESHNESS:
            raise SiteInputError(
                f"snapshot views.journey.events[{index}].subject_entity.freshness is unsupported"
            )
        if subject.get("visibility") not in JOURNEY_VISIBILITIES:
            raise SiteInputError(
                f"snapshot views.journey.events[{index}].subject_entity.visibility is unsupported"
            )
        if event["subject"] != subject.get("id"):
            raise SiteInputError(
                f"snapshot views.journey.events[{index}] subject does not match subject_entity"
            )
    if chronological != sorted(chronological):
        raise SiteInputError("snapshot views.journey.events must be ordered by occurred_at then id")

    chapter_ids: set[str] = set()
    flattened_event_ids: list[str] = []
    for index, candidate in enumerate(chapters):
        chapter = require_object(candidate)
        if not chapter:
            raise SiteInputError(f"snapshot views.journey.chapters[{index}] must be an object")
        for member in ("id", "title", "start_at", "end_at"):
            if not isinstance(chapter.get(member), str) or not chapter[member]:
                raise SiteInputError(
                    f"snapshot views.journey.chapters[{index}].{member} must be a non-empty string"
                )
        chapter_id = str(chapter["id"])
        if chapter_id in chapter_ids:
            raise SiteInputError("journey chapter IDs must be unique")
        chapter_ids.add(chapter_id)
        members = chapter.get("event_ids")
        if (
            not isinstance(members, list)
            or not members
            or any(not isinstance(value, str) or not value for value in members)
            or len(members) != len(set(members))
        ):
            raise SiteInputError(
                f"snapshot views.journey.chapters[{index}].event_ids must contain unique event IDs"
            )
        unresolved = [value for value in members if value not in event_index]
        if unresolved:
            raise SiteInputError(
                "snapshot views.journey.chapters contain unresolved event IDs: "
                + ", ".join(unresolved)
            )
        selected = [event_index[value] for value in members]
        if chapter["start_at"] != selected[0]["occurred_at"] or chapter["end_at"] != selected[-1]["occurred_at"]:
            raise SiteInputError("journey chapter boundaries must match their first and last events")
        parse_rfc3339(
            chapter.get("start_at"),
            f"snapshot views.journey.chapters[{index}].start_at",
        )
        parse_rfc3339(
            chapter.get("end_at"),
            f"snapshot views.journey.chapters[{index}].end_at",
        )
        boundary = chapter.get("boundary")
        if boundary is None:
            if index != len(chapters) - 1:
                raise SiteInputError("only the final journey chapter may be open")
            if any(event["type"] == "release.published" for event in selected):
                raise SiteInputError("an open journey chapter cannot contain a release boundary")
        else:
            boundary_entity = require_object(boundary)
            if normalize_state(boundary_entity.get("kind")) != "release":
                raise SiteInputError("journey chapter boundary must describe a release")
            last_event = selected[-1]
            if (
                last_event["type"] != "release.published"
                or last_event["subject"] != boundary_entity.get("id")
            ):
                raise SiteInputError("journey release chapter must close on its boundary event")
            boundary_subject = entity(last_event.get("subject_entity"))
            for member in (
                "assertion",
                "canonical_url",
                "freshness",
                "id",
                "key",
                "kind",
                "repository",
                "state",
                "title",
                "visibility",
            ):
                if boundary_entity.get(member) != boundary_subject.get(member):
                    raise SiteInputError(
                        "journey release chapter boundary must match its release event entity"
                    )
        flattened_event_ids.extend(members)
    expected_event_ids = [str(event["id"]) for event in events]
    if flattened_event_ids != expected_event_ids:
        raise SiteInputError("journey chapters must partition every event in canonical order")
    if bool(events) != bool(chapters):
        raise SiteInputError("journey chapters and events must either both be empty or both be present")


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
    for name in ("now", "roadmap", "decisions", "journey"):
        if not isinstance(views.get(name), dict):
            raise SiteInputError(f"snapshot views.{name} must be an object")
    required_arrays = {
        "now": ("blockers", "current_focus", "next_ready", "recent_events"),
        "roadmap": ("roots", "steps"),
        "decisions": ("decisions",),
        "journey": ("chapters", "events"),
    }
    for view_name, members in required_arrays.items():
        view = views[view_name]
        for member in members:
            if not isinstance(view.get(member), list):
                raise SiteInputError(
                    f"snapshot views.{view_name}.{member} must be an array"
                )
    if "health" in views:
        health = views["health"]
        if not isinstance(health, dict):
            raise SiteInputError("snapshot views.health must be an object")
        if not isinstance(health.get("checks"), list):
            raise SiteInputError("snapshot views.health.checks must be an array")
    if "work" in views:
        work = views["work"]
        if not isinstance(work, dict):
            raise SiteInputError("snapshot views.work must be an object")
        for member in ("open_issues", "open_pull_requests"):
            if not isinstance(work.get(member), list):
                raise SiteInputError(f"snapshot views.work.{member} must be an array")
        if not isinstance(work.get("roadmap_queues"), dict):
            raise SiteInputError("snapshot views.work.roadmap_queues must be an object")
    validate_roadmap_view(require_object(views.get("roadmap")))
    validate_decisions_view(require_object(views.get("decisions")))
    validate_journey_view(require_object(views.get("journey")))
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


def source_repository_attribute(item: dict[str, Any]) -> str:
    """Declare an exact cross-repository source boundary for bundle validation."""

    repository = item.get("repository")
    if not isinstance(repository, str) or not repository:
        return ""
    return f' data-source-repository="{escaped(repository)}"'


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
    return f'''<article class="ri-record" data-entity-id="{escaped(value.get("id"))}" data-filter-item{source_repository_attribute(value)} data-state="{escaped(state)}" data-kind="{escaped(normalize_state(value.get("kind")))}" data-search="{escaped(search.lower())}">
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
    return f'''<article class="ri-change" data-entity-id="{escaped(subject.get("id"))}" data-filter-item{source_repository_attribute(subject)} data-state="{escaped(normalize_state(subject.get("state")))}" data-kind="{escaped(normalize_state(subject.get("kind")))}" data-search="{escaped((str(subject.get("title", "")) + " " + event_type).lower())}">
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
        cards.append(f'''<li class="ri-action" data-entity-id="{escaped(action_entity.get("id"))}" data-filter-item data-state="ready" data-kind="roadmap_step" data-search="{escaped((str(action_entity.get("title", "")) + " " + rationale).lower())}">
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
        return f'<a class="ri-link-chip" data-preserve-context href="{escaped(href)}">{content}</a>'
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
        f'<a data-preserve-context href="{escaped(href)}">{escaped(title)} <span aria-hidden="true">↗</span></a>'
        if href
        else f"<span>{escaped(title)}</span>"
    )
    return f'''<li class="ri-evidence-record" data-evidence-item{source_repository_attribute(value)} data-kind="{escaped(kind)}" data-state="{escaped(state)}" data-assertion="{escaped(normalize_state(value.get("assertion")))}" data-search="{escaped(search)}" aria-posinset="{index + 1}" aria-setsize="{total}">
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
    return f'''<li class="ri-quest" id="{escaped(anchor)}" data-entity-id="{escaped(step_id)}" data-filter-item data-roadmap-quest data-state="{escaped(state)}" data-states="{escaped(" ".join(states))}" data-kind="roadmap_step" data-kinds="{escaped(" ".join(kinds))}" data-search="{escaped(search)}">
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


def decision_metadata(decision: dict[str, Any]) -> dict[str, Any]:
    """Extract optional ADR facets while keeping absent contract data explicit."""

    decision_entity = entity(decision)
    owners = string_values(decision.get("owners")) or string_values(
        decision_entity.get("repository")
    )
    domains = string_values(decision.get("domains")) or string_values(
        decision.get("domain")
    )
    components = [
        *string_values(decision.get("affected_components")),
        *string_values(decision.get("affected_contracts")),
        *string_values(decision.get("affected_repositories")),
    ]
    components = list(dict.fromkeys(components))
    roadmap = [
        entity(value)
        for value in require_list(decision.get("informs"))
        if normalize_state(entity(value).get("kind")) == "roadmap_step"
    ]
    date = decision.get("date") if isinstance(decision.get("date"), str) else ""
    return {
        "scope": normalize_state(decision.get("decision_scope")),
        "implementation": normalize_state(decision.get("implementation_status")),
        "owners": owners,
        "domains": domains,
        "components": components,
        "roadmap": roadmap,
        "date": date,
    }


def decision_filter_facets(decision: dict[str, Any]) -> dict[str, list[tuple[str, str]]]:
    """Build exact display/filter pairs for every requested ADR facet."""

    metadata = decision_metadata(decision)

    def tokenized(values: list[str], *, unknown_label: str = "Not projected") -> list[tuple[str, str]]:
        return (
            [(filter_token(value), value) for value in values]
            if values
            else [("unknown", unknown_label)]
        )

    roadmap_labels = [
        str(value.get("key") or value.get("title") or value.get("id"))
        for value in metadata["roadmap"]
    ]
    year = metadata["date"][:4] if metadata["date"] else ""
    return {
        "scope": [
            (
                metadata["scope"],
                "Organization / inherited"
                if metadata["scope"] == "organization"
                else "Repository-local",
            )
        ],
        "implementation": [
            (metadata["implementation"], state_label(metadata["implementation"]))
        ],
        "owner": tokenized(metadata["owners"]),
        "date": [(f"year-{year}", year)] if year else [("unknown", "Not projected")],
        "domain": tokenized(metadata["domains"]),
        "component": tokenized(metadata["components"]),
        "roadmap": tokenized(
            roadmap_labels,
            unknown_label="No affected quest projected",
        ),
    }


def render_decision_filter_controls(decisions: list[dict[str, Any]]) -> str:
    """Render route-specific, URL-backed ADR filters from observed facet values."""

    definitions = (
        ("scope", "Authority"),
        ("implementation", "Implementation"),
        ("owner", "Owner"),
        ("date", "Date"),
        ("domain", "Domain"),
        ("component", "Affected component"),
        ("roadmap", "Roadmap"),
    )
    choices: dict[str, dict[str, str]] = {name: {} for name, _ in definitions}
    for decision in decisions:
        for name, values in decision_filter_facets(decision).items():
            for token, label in values:
                choices[name][token] = label
    controls = []
    for name, label in definitions:
        options = "".join(
            f'<option value="{escaped(token)}">{escaped(option_label)}</option>'
            for token, option_label in sorted(
                choices[name].items(),
                key=lambda item: (item[0] == "unknown", item[1].casefold()),
            )
        )
        controls.append(
            f'<label><span>{escaped(label)}</span><select data-filter-extra="{escaped(name)}">'
            f'<option value="all">All {escaped(label.casefold())}</option>{options}</select></label>'
        )
    return f'''<details class="ri-decision-filters" data-decision-filters open>
      <summary>Decision facets</summary>
      <div>{"".join(controls)}</div>
      <p>Date, domain, and affected-component values remain “Not projected” when the pinned Observatory contract does not supply them.</p>
    </details>'''


def decision_index(
    snapshot: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, str], dict[str, str]]:
    """Return deterministic chronological decisions and cross-view deep links."""

    decisions_view = require_object(require_object(snapshot.get("views")).get("decisions"))
    decisions = [
        require_object(value) for value in require_list(decisions_view.get("decisions"))
    ]
    decisions.sort(
        key=lambda value: (
            str(value.get("date") or "9999-12-31"),
            str(entity(value).get("key") or "").casefold(),
            str(entity(value).get("id") or ""),
        )
    )
    decision_anchors: dict[str, str] = {}
    for decision in decisions:
        decision_entity = entity(decision)
        anchor = stable_fragment("decision", decision_entity.get("id"))
        decision_anchors[str(decision_entity.get("id"))] = anchor
        decision_anchors[str(decision_entity.get("key"))] = anchor
    roadmap_anchors: dict[str, str] = {}
    roadmap = require_object(require_object(snapshot.get("views")).get("roadmap"))
    for step in require_list(roadmap.get("steps")):
        step_entity = entity(step)
        anchor = stable_fragment("quest", step_entity.get("id"))
        roadmap_anchors[str(step_entity.get("id"))] = anchor
        roadmap_anchors[str(step_entity.get("key"))] = anchor
    return decisions, decision_anchors, roadmap_anchors


def decision_reference_href(
    value: dict[str, Any],
    decision_anchors: dict[str, str],
    roadmap_anchors: dict[str, str],
) -> str:
    """Prefer stable local lineage and quest links, then canonical evidence."""

    identifiers = (str(value.get("id") or ""), str(value.get("key") or ""))
    for identifier in identifiers:
        if identifier in decision_anchors:
            return f"#{decision_anchors[identifier]}"
        if identifier in roadmap_anchors:
            return f"../roadmap/#{roadmap_anchors[identifier]}"
    return safe_href(value.get("canonical_url"))


def render_decision_reference(
    value: dict[str, Any],
    decision_anchors: dict[str, str],
    roadmap_anchors: dict[str, str],
    relationship: str,
) -> str:
    href = decision_reference_href(value, decision_anchors, roadmap_anchors)
    title = value.get("title") or value.get("key") or "Untitled record"
    assertion = normalize_state(value.get("assertion"))
    content = (
        f'<span class="ri-link-chip__relationship">{escaped(relationship)}</span>'
        f'<span>{escaped(title)}</span>'
        f'<small data-assertion="{escaped(assertion)}">{escaped(state_label(assertion))}</small>'
    )
    if href:
        return f'<a class="ri-link-chip" data-preserve-context href="{escaped(href)}">{content}</a>'
    return f'<span class="ri-link-chip">{content}</span>'


def render_decision_relationship_row(
    label: str,
    values: list[Any],
    decision_anchors: dict[str, str],
    roadmap_anchors: dict[str, str],
) -> str:
    records = [entity(value) for value in values if entity(value)]
    if not records:
        return ""
    return (
        f'<div class="ri-relationship-row"><strong>{escaped(label)}</strong><div>'
        + "".join(
            render_decision_reference(
                value,
                decision_anchors,
                roadmap_anchors,
                label.casefold(),
            )
            for value in records
        )
        + "</div></div>"
    )


def decision_evidence(decision: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Flatten every projected ADR relationship without losing its label."""

    records: list[tuple[str, dict[str, Any]]] = []
    seen: set[tuple[str, str]] = set()
    for field, relationship in DECISION_RELATIONSHIP_FIELDS:
        for candidate in require_list(decision.get(field)):
            value = entity(candidate)
            identifier = str(value.get("id") or value.get("canonical_url") or "")
            marker = (relationship, identifier)
            if not value or not identifier or marker in seen:
                continue
            seen.add(marker)
            records.append((relationship, value))
    return records


def render_decision_evidence_record(
    relationship: str,
    value: dict[str, Any],
    decision_anchors: dict[str, str],
    roadmap_anchors: dict[str, str],
    index: int,
    total: int,
) -> str:
    kind = normalize_state(value.get("kind"))
    state = normalize_state(value.get("state"))
    href = decision_reference_href(value, decision_anchors, roadmap_anchors)
    title = value.get("title") or value.get("key") or "Untitled evidence"
    heading = (
        f'<a data-preserve-context href="{escaped(href)}">{escaped(title)} <span aria-hidden="true">↗</span></a>'
        if href
        else f"<span>{escaped(title)}</span>"
    )
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
    return f'''<li class="ri-evidence-record" data-evidence-item{source_repository_attribute(value)} data-kind="{escaped(kind)}" data-state="{escaped(state)}" data-assertion="{escaped(normalize_state(value.get("assertion")))}" data-search="{escaped(search)}" aria-posinset="{index + 1}" aria-setsize="{total}">
      <div class="ri-evidence-record__top"><span class="ri-evidence-kind">{escaped(state_label(kind))}</span>{status_pill(state)}</div>
      <strong>{heading}</strong>
      <p>{escaped(relationship.capitalize())} · {escaped(value.get("key") or "No identifier")}</p>
      <dl class="ri-provenance"><div><dt>Assertion</dt><dd>{escaped(state_label(value.get("assertion")))}</dd></div><div><dt>Confidence</dt><dd>{escaped(state_label(value.get("confidence")))}</dd></div><div><dt>Freshness</dt><dd>{escaped(state_label(value.get("freshness")))}</dd></div><div><dt>Owner</dt><dd>{escaped(value.get("repository") or "Unknown")}</dd></div></dl>
    </li>'''


def render_decision_narrative(decision: dict[str, Any]) -> str:
    """Render optional summaries, otherwise keep the canonical ADR boundary obvious."""

    sections = []
    for field, label in (
        ("context", "Context"),
        ("alternatives", "Alternatives"),
        ("consequences", "Consequences"),
    ):
        values = string_values(decision.get(field))
        if values:
            sections.append(
                f'<section><h4>{escaped(label)}</h4><p>{escaped(" · ".join(values))}</p></section>'
            )
    if sections:
        return '<div class="ri-decision-narrative">' + "".join(sections) + "</div>"
    return '<p class="ri-decision-narrative-note">Context, alternatives, and consequences remain in the canonical ADR; this projection does not duplicate or rewrite them.</p>'


def render_decision_card(
    decision: dict[str, Any],
    *,
    index: int,
    total: int,
    repository: str,
    source_commit: str,
    decision_anchors: dict[str, str],
    roadmap_anchors: dict[str, str],
) -> str:
    decision_entity = entity(decision)
    identifier = str(decision_entity.get("id"))
    anchor = decision_anchors[identifier]
    status = normalize_state(decision_entity.get("state"))
    metadata = decision_metadata(decision)
    facets = decision_filter_facets(decision)
    evidence_records = decision_evidence(decision)
    evidence_kinds = [normalize_state(value.get("kind")) for _, value in evidence_records]
    evidence_states = [normalize_state(value.get("state")) for _, value in evidence_records]
    kinds = sorted({"architecture_decision", *evidence_kinds})
    states = sorted({status, *evidence_states})
    origin = (
        "Inherited organization decision"
        if metadata["scope"] == "organization"
        or decision_entity.get("repository") != repository
        else "Repository-local decision"
    )
    date_label = format_calendar_date(metadata["date"])
    owner_label = ", ".join(metadata["owners"]) or "Not projected"
    domain_label = ", ".join(metadata["domains"]) or "Not projected"
    component_label = ", ".join(metadata["components"]) or "Not projected"
    roadmap_label = ", ".join(
        str(value.get("key") or value.get("title")) for value in metadata["roadmap"]
    ) or "No affected quest projected"
    search = " ".join(
        [
            str(decision_entity.get("key") or ""),
            str(decision_entity.get("title") or ""),
            status,
            metadata["implementation"],
            metadata["scope"],
            owner_label,
            domain_label,
            component_label,
            roadmap_label,
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
    facet_attributes = " ".join(
        f'data-filter-{name}="{escaped(" ".join(token for token, _ in values))}"'
        for name, values in facets.items()
    )
    evidence_items = "".join(
        render_decision_evidence_record(
            relationship,
            value,
            decision_anchors,
            roadmap_anchors,
            evidence_index,
            len(evidence_records),
        )
        for evidence_index, (relationship, value) in enumerate(evidence_records)
    )
    kind_counts: dict[str, int] = {}
    for kind in evidence_kinds:
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
    evidence_summary = "".join(
        f'<span><strong>{count}</strong> {escaped(state_label(kind))}</span>'
        for kind, count in sorted(kind_counts.items())
    ) or "<span>No linked evidence yet</span>"
    successor_note = (
        '<p class="ri-lineage-warning">This record is superseded, but its successor is not projected in this snapshot.</p>'
        if status == "superseded" and not require_list(decision.get("superseded_by"))
        else ""
    )
    return f'''<li class="ri-decision" id="{escaped(anchor)}" data-entity-id="{escaped(identifier)}" data-filter-item data-decision-record data-source-repository="{escaped(decision_entity.get("repository"))}" data-state="{escaped(status)}" data-states="{escaped(" ".join(states))}" data-kind="architecture_decision" data-kinds="{escaped(" ".join(kinds))}" data-search="{escaped(search)}" {facet_attributes} data-decision-id="{escaped(identifier)}" data-decision-title="{escaped(decision_entity.get("title"))}" data-decision-status="{escaped(state_label(status))}" data-decision-implementation="{escaped(state_label(metadata["implementation"]))}" data-decision-scope="{escaped(state_label(metadata["scope"]))}" data-decision-date-label="{escaped(date_label)}" data-decision-owner-label="{escaped(owner_label)}" data-decision-domain-label="{escaped(domain_label)}" data-decision-component-label="{escaped(component_label)}" data-decision-roadmap-label="{escaped(roadmap_label)}">
      <div class="ri-decision__node" aria-hidden="true"><span>{index + 1:02d}</span></div>
      <article class="ri-decision__card" tabindex="-1">
        <header><div><a class="ri-decision__permalink" data-decision-link href="#{escaped(anchor)}">Decision {index + 1} of {total} · {escaped(decision_entity.get("key"))}</a><h3>{escaped(decision_entity.get("title"))}</h3><p>{escaped(origin)}</p></div>{status_pill(status)}</header>
        <div class="ri-decision-states"><div><span>Decision lifecycle</span>{status_pill(status)}</div><div><span>Implementation</span>{status_pill(metadata["implementation"])}</div></div>
        <dl class="ri-decision-metadata"><div><dt>Date</dt><dd>{escaped(date_label)}</dd></div><div><dt>Owner</dt><dd>{escaped(owner_label)}</dd></div><div><dt>Scope</dt><dd>{escaped(state_label(metadata["scope"]))}</dd></div><div><dt>Domain</dt><dd>{escaped(domain_label)}</dd></div><div><dt>Affected component</dt><dd>{escaped(component_label)}</dd></div><div><dt>Affected roadmap</dt><dd>{escaped(roadmap_label)}</dd></div></dl>
        {render_decision_narrative(decision)}
        <div class="ri-relationship-grid">
          {render_decision_relationship_row("Supersedes", require_list(decision.get("supersedes")), decision_anchors, roadmap_anchors)}
          {render_decision_relationship_row("Superseded by", require_list(decision.get("superseded_by")), decision_anchors, roadmap_anchors)}
          {render_decision_relationship_row("Affects roadmap", require_list(decision.get("informs")), decision_anchors, roadmap_anchors)}
        </div>
        {successor_note}
        <div class="ri-decision__source">{source_link(decision_entity, "Open canonical ADR")}<span>Represented revision: <code>{escaped(source_commit[:12])}</code> · Assertion: {escaped(state_label(decision_entity.get("assertion")))} · Freshness: {escaped(state_label(decision_entity.get("freshness")))}</span></div>
        <details class="ri-evidence" data-decision-evidence>
          <summary><span><strong>Decision evidence and lineage</strong><small>{len(evidence_records)} linked {"record" if len(evidence_records) == 1 else "records"}</small></span><span aria-hidden="true">+</span></summary>
          <div class="ri-evidence__summary">{evidence_summary}</div>
          <div class="ri-evidence-viewport" data-evidence-viewport data-evidence-total="{len(evidence_records)}" data-row-height="150">
            <ol class="ri-evidence-list">{evidence_items}</ol>
          </div>
        </details>
      </article>
    </li>'''


def render_decision_compare(decisions: list[dict[str, Any]]) -> str:
    """Render a browser-enhanced compare control without hiding static records."""

    options = "".join(
        f'<option value="{escaped(entity(decision).get("id"))}">{escaped(entity(decision).get("key"))} · {escaped(entity(decision).get("title"))}</option>'
        for decision in decisions
    )
    return f'''<section class="ri-decision-compare" aria-labelledby="decision-compare-heading" data-decision-compare>
      <div><span class="ri-eyebrow">Compare</span><h2 id="decision-compare-heading">Place two decisions side by side</h2><p>Compare reports projected fields; it does not infer causality or rewrite the ADRs.</p></div>
      <div class="ri-decision-compare__controls"><label><span>First decision</span><select data-compare-left><option value="">Choose a decision</option>{options}</select></label><button class="ri-button ri-button--quiet" type="button" data-compare-swap>Swap</button><label><span>Second decision</span><select data-compare-right><option value="">Choose a decision</option>{options}</select></label></div>
      <div class="ri-decision-compare__output" data-compare-output role="status" aria-live="polite"><p>Choose two different decisions to compare their projected lifecycle, authority, implementation, and impact.</p></div>
      <noscript><p>The complete ledger remains available below; interactive comparison requires JavaScript.</p></noscript>
    </section>'''


def decisions_body(snapshot: dict[str, Any] | None) -> str:
    """Render ADR history as a static-first, authority-aware decision ledger."""

    if snapshot is None:
        return f'''<section class="ri-section ri-section--lead" aria-labelledby="decision-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Canonical decisions</span><h2 id="decision-heading">The decision ledger</h2></div><p>The page never reconstructs architectural intent from Git activity.</p></div>{empty_state("Observatory decision history unavailable", "Supply a repository- and commit-matched read model to render ADR lifecycle, implementation, lineage, and evidence.", "partial")}</section>'''
    decisions, decision_anchors, roadmap_anchors = decision_index(snapshot)
    if not decisions:
        return f'''<section class="ri-section ri-section--lead" aria-labelledby="decision-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Canonical decisions</span><h2 id="decision-heading">The decision ledger</h2></div><p>The supplied read model contains no architecture decisions.</p></div>{empty_state("No ADRs projected", "Canonical ADR Markdown remains authoritative. An empty projection is not evidence that no decisions exist.", "empty")}</section>'''
    repository = str(require_object(snapshot.get("repository")).get("key"))
    source_commit = str(snapshot.get("represented_commit"))
    decision_index_url = (
        f"https://github.com/{repository}/blob/{source_commit}/DECISIONS.md"
    )
    inherited = [
        decision
        for decision in decisions
        if decision_metadata(decision)["scope"] == "organization"
        or entity(decision).get("repository") != repository
    ]
    local = [decision for decision in decisions if decision not in inherited]
    groups = [
        (
            "Inherited organization decisions",
            "Organization-scoped records remain owned by their canonical source repository.",
            inherited,
        ),
        (
            "Repository-local decisions",
            "This repository owns these records and their implementation evidence.",
            local,
        ),
    ]
    rendered_groups = []
    index_groups = []
    sequence = 0
    for group_title, group_description, group_decisions in groups:
        if not group_decisions:
            continue
        group_anchor = stable_fragment("decision-scope", group_title)
        index_links = []
        cards = []
        for decision in group_decisions:
            decision_entity = entity(decision)
            anchor = decision_anchors[str(decision_entity.get("id"))]
            index_links.append(
                f'<li><a data-decision-index href="#{escaped(anchor)}" data-state="{escaped(normalize_state(decision_entity.get("state")))}"><span>{escaped(decision_entity.get("key"))}</span><small>{escaped(decision_entity.get("title"))}</small></a></li>'
            )
            cards.append(
                render_decision_card(
                    decision,
                    index=sequence,
                    total=len(decisions),
                    repository=repository,
                    source_commit=source_commit,
                    decision_anchors=decision_anchors,
                    roadmap_anchors=roadmap_anchors,
                )
            )
            sequence += 1
        index_groups.append(
            f'<li data-decision-index-group><a class="ri-map__chapter" href="#{escaped(group_anchor)}">{escaped(group_title)}</a><ol>{"".join(index_links)}</ol></li>'
        )
        rendered_groups.append(
            f'''<section class="ri-decision-group" id="{escaped(group_anchor)}" data-decision-group aria-labelledby="{escaped(group_anchor)}-title"><header class="ri-chapter-heading"><div><span>Authority boundary</span><h2 id="{escaped(group_anchor)}-title">{escaped(group_title)}</h2></div><p>{escaped(group_description)}</p></header><ol class="ri-decision-line">{"".join(cards)}</ol></section>'''
        )
    accepted = sum(
        1 for decision in decisions if normalize_state(entity(decision).get("state")) == "accepted"
    )
    proposed = sum(
        1 for decision in decisions if normalize_state(entity(decision).get("state")) == "proposed"
    )
    terminal = sum(
        1
        for decision in decisions
        if normalize_state(entity(decision).get("state"))
        in {"deprecated", "rejected", "superseded"}
    )
    return f'''<section class="ri-section ri-section--lead ri-decision-intro" aria-labelledby="decision-heading">
      <div class="ri-section-heading"><div><span class="ri-eyebrow">Canonical decisions</span><h2 id="decision-heading">The decision ledger</h2></div><p>Read the historical chain, inspect evidence, and return to the authoritative record in <a href="{escaped(decision_index_url)}">DECISIONS.md</a>.</p></div>
      <div class="ri-roadmap-metrics" aria-label="Decision history summary"><article><strong>{len(decisions)}</strong><span>historical records</span></article><article><strong>{accepted}</strong><span>accepted</span></article><article><strong>{proposed}</strong><span>awaiting disposition</span></article><article><strong>{terminal}</strong><span>preserved terminal records</span></article></div>
      <div class="ri-decision-boundaries"><article><span class="ri-eyebrow">Inherited</span><strong>Organization authority</strong><p>Shown for context; ownership stays with the source repository.</p></article><article><span class="ri-eyebrow">Local</span><strong>Repository authority</strong><p>Owned here, with lifecycle and implementation tracked separately.</p></article><article><span class="ri-eyebrow">Assertion</span><strong>Authority stays visible</strong><p>Inferred and unknown references are labelled instead of presented as fact.</p></article></div>
      {render_decision_filter_controls(decisions)}
    </section>
    {render_decision_compare(decisions)}
    <div class="ri-decision-layout">
      <nav class="ri-map ri-decision-map" aria-label="Decision history index"><span class="ri-eyebrow">Decision index</span><p>{len(decisions)} records · chronological where dates are projected; stable key order otherwise</p><ol>{"".join(index_groups)}</ol></nav>
      <div class="ri-decision-story">{"".join(rendered_groups)}</div>
    </div>'''


def journey_lane(kind: Any) -> tuple[str, str]:
    """Map one projected entity kind to a deterministic semantic delivery lane."""

    normalized = normalize_state(kind)
    for lane, label, kinds in JOURNEY_LANES:
        if normalized in kinds:
            return lane, label
    return "other", "Other"


def journey_event_label(event: dict[str, Any]) -> str:
    event_type = event.get("type")
    if event_type == "check.completed":
        transitions = [require_object(change) for change in require_list(event.get("changes"))]
        if any(normalize_state(change.get("to")) in BROKEN_STATES for change in transitions):
            return "Check regressed"
        if any(
            normalize_state(change.get("from")) in BROKEN_STATES
            and normalize_state(change.get("to")) == "success"
            for change in transitions
        ):
            return "Check recovered"
    labels = {
        "architecture_decision.accepted": "Decision accepted",
        "architecture_decision.deprecated": "Decision deprecated",
        "architecture_decision.proposed": "Decision proposed",
        "architecture_decision.superseded": "Decision superseded",
        "check.completed": "Check completed",
        "commit.created": "Commit recorded",
        "deployment.completed": "Deployment completed",
        "issue.closed": "Issue closed",
        "issue.opened": "Issue opened",
        "issue.reopened": "Issue reopened",
        "pull_request.closed": "Pull request closed",
        "pull_request.merged": "Pull request merged",
        "pull_request.opened": "Pull request opened",
        "release.published": "Release published",
        "repository.observed": "Repository observed",
        "roadmap_step.created": "Quest created",
        "roadmap_step.status_changed": "Quest state changed",
    }
    return labels.get(str(event_type), state_label(event_type))


def journey_context_index(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Reverse explicit roadmap and ADR relationships for journey drill-down."""

    index: dict[str, dict[str, Any]] = {}

    def add_context(
        subject_id: Any,
        context_kind: str,
        context_entity: dict[str, Any],
        *,
        changed_files: list[Any] | None = None,
    ) -> None:
        if not isinstance(subject_id, str) or not subject_id:
            return
        record = index.setdefault(
            subject_id,
            {"roadmap": {}, "decisions": {}, "changed_files": {}},
        )
        context_id = str(context_entity.get("id") or "")
        if context_id:
            record[context_kind][context_id] = context_entity
        for file_reference in changed_files or []:
            file_entity = entity(file_reference)
            file_id = str(file_entity.get("id") or "")
            if file_id:
                record["changed_files"][file_id] = file_entity

    views = require_object(snapshot.get("views"))
    roadmap = require_object(views.get("roadmap"))
    for step in require_list(roadmap.get("steps")):
        step_record = require_object(step)
        step_entity = entity(step_record)
        changed_files = require_list(step_record.get("changed_files")) + require_list(
            step_record.get("files")
        )
        related_ids = {str(step_entity.get("id") or "")}
        for field, _ in ROADMAP_EVIDENCE_FIELDS:
            related_ids.update(
                str(entity(reference).get("id") or "")
                for reference in require_list(step_record.get(field))
            )
        for related_id in sorted(related_ids):
            add_context(
                related_id,
                "roadmap",
                step_entity,
                changed_files=changed_files,
            )
    decisions = require_object(views.get("decisions"))
    for decision in require_list(decisions.get("decisions")):
        decision_record = require_object(decision)
        decision_entity = entity(decision_record)
        related_ids = {str(decision_entity.get("id") or "")}
        for field, _ in DECISION_RELATIONSHIP_FIELDS:
            related_ids.update(
                str(entity(reference).get("id") or "")
                for reference in require_list(decision_record.get(field))
            )
        for related_id in sorted(related_ids):
            add_context(related_id, "decisions", decision_entity)
    return index


def journey_select(
    label: str,
    parameter: str,
    options: list[tuple[str, str]],
) -> str:
    rendered_options = ['<option value="all">All</option>']
    rendered_options.extend(
        f'<option value="{escaped(value)}">{escaped(option_label)}</option>'
        for value, option_label in options
    )
    return f'''<label><span>{escaped(label)}</span><select data-filter-extra="{escaped(parameter)}">{"".join(rendered_options)}</select></label>'''


def render_journey_filter_controls(
    chapters: list[dict[str, Any]],
    events: list[dict[str, Any]],
    contexts: dict[str, dict[str, Any]],
) -> str:
    chapter_options = [
        (filter_token(chapter.get("id")), str(chapter.get("title")))
        for chapter in chapters
    ]
    release_options: dict[str, str] = {}
    roadmap_options: dict[str, str] = {"unclassified": "Unclassified"}
    decision_options: dict[str, str] = {"unclassified": "Unclassified"}
    actor_options: dict[str, str] = {"unattributed": "Unattributed"}
    assertions: dict[str, str] = {}
    freshness_values: dict[str, str] = {}
    for chapter in chapters:
        boundary = require_object(chapter.get("boundary"))
        release_key = str(boundary.get("key") or "unreleased")
        release_options[filter_token(release_key)] = str(
            boundary.get("title") or boundary.get("key") or "Unreleased"
        )
    for event in events:
        subject = entity(event.get("subject_entity"))
        context = contexts.get(str(subject.get("id") or ""), {})
        for kind, target in (("roadmap", roadmap_options), ("decisions", decision_options)):
            for reference in require_object(context.get(kind)).values():
                target[filter_token(reference.get("id"))] = str(
                    reference.get("key") or reference.get("title")
                )
        actor = require_object(event.get("actor"))
        if actor:
            actor_id = str(actor.get("id") or actor.get("kind") or "unknown")
            actor_options[filter_token(actor_id)] = actor_id
        assertion = str(event.get("assertion") or "unknown")
        freshness = str(event.get("freshness") or "unknown")
        assertions[assertion] = state_label(assertion)
        freshness_values[freshness] = state_label(freshness)
    return f'''<details class="ri-journey-filters"><summary>Refine the journey</summary><div>
      {journey_select("Chapter", "chapter", chapter_options)}
      {journey_select("Release boundary", "release", sorted(release_options.items(), key=lambda item: item[1].casefold()))}
      {journey_select("Quest context", "roadmap", sorted(roadmap_options.items(), key=lambda item: item[1].casefold()))}
      {journey_select("Decision context", "decision", sorted(decision_options.items(), key=lambda item: item[1].casefold()))}
      {journey_select("Actor", "actor", sorted(actor_options.items(), key=lambda item: item[1].casefold()))}
      {journey_select("Assertion", "assertion", sorted(assertions.items()))}
      {journey_select("Freshness", "freshness", sorted(freshness_values.items()))}
      <label><span>From date</span><input type="date" data-journey-date-from></label>
      <label><span>Through date</span><input type="date" data-journey-date-to></label>
    </div><p>Branch names and file paths are not projected by the current public-safe journey contract. They remain unavailable instead of being reconstructed from titles or commit messages.</p></details>'''


def render_journey_context_links(
    context: dict[str, Any],
    roadmap_anchors: dict[str, str],
    decision_anchors: dict[str, str],
) -> str:
    links = []
    for reference in require_object(context.get("roadmap")).values():
        anchor = roadmap_anchors.get(str(reference.get("id") or ""))
        if anchor:
            links.append(
                f'<a class="ri-journey-context" data-context-kind="roadmap" data-preserve-context href="../roadmap/#{escaped(anchor)}"><span>Quest</span>{escaped(reference.get("key") or reference.get("title"))}</a>'
            )
    for reference in require_object(context.get("decisions")).values():
        anchor = decision_anchors.get(str(reference.get("id") or ""))
        if anchor:
            links.append(
                f'<a class="ri-journey-context" data-context-kind="decision" data-preserve-context href="../decisions/#{escaped(anchor)}"><span>ADR</span>{escaped(reference.get("key") or reference.get("title"))}</a>'
            )
    if links:
        return f'<div class="ri-journey-contexts" aria-label="Explicitly linked intent">{"".join(links)}</div>'
    return '<p class="ri-journey-unclassified"><strong>Unclassified context.</strong> No roadmap or ADR relationship is projected for this event.</p>'


def render_journey_changes(event: dict[str, Any]) -> str:
    changes = require_list(event.get("changes"))
    if not changes:
        return '<p>No field transition is projected for this event.</p>'
    rows = []
    for change in changes:
        record = require_object(change)
        before = record.get("from")
        after = record.get("to")
        rows.append(
            f'<li><code>{escaped(record.get("field") or "unknown field")}</code><span>{escaped(before if before is not None else "not previously projected")} → {escaped(after if after is not None else "not subsequently projected")}</span></li>'
        )
    return f'<ul class="ri-journey-changes">{"".join(rows)}</ul>'


def render_journey_files(context: dict[str, Any]) -> str:
    files = list(require_object(context.get("changed_files")).values())
    if not files:
        return ""
    records = []
    for file_entity in files:
        url = safe_href(file_entity.get("canonical_url"))
        title = file_entity.get("title") or file_entity.get("key") or "Changed file"
        records.append(
            f'<li>{f"<a href=\"{escaped(url)}\">{escaped(title)}</a>" if url else escaped(title)}</li>'
        )
    return f'''<section><h4>Quest-level changed files</h4><p>These files belong to an explicitly linked quest; the journey does not claim that this individual event changed each file.</p><ul>{"".join(records)}</ul></section>'''


def render_journey_event(
    event: dict[str, Any],
    *,
    index: int,
    total: int,
    chapter: dict[str, Any],
    context: dict[str, Any],
    release_token: str,
    roadmap_anchors: dict[str, str],
    decision_anchors: dict[str, str],
) -> str:
    subject = entity(event.get("subject_entity"))
    identifier = str(event.get("id") or "")
    anchor = stable_fragment("event", identifier)
    lane, lane_label = journey_lane(subject.get("kind"))
    title = subject.get("title") or subject.get("key") or "Untitled event"
    state = normalize_state(subject.get("state"))
    kind = normalize_state(subject.get("kind"))
    assertion = normalize_state(event.get("assertion"))
    freshness = normalize_state(event.get("freshness"))
    actor = require_object(event.get("actor"))
    actor_id = str(actor.get("id") or actor.get("kind") or "unattributed")
    actor_token = filter_token(actor_id) if actor else "unattributed"
    roadmap = list(require_object(context.get("roadmap")).values())
    decisions = list(require_object(context.get("decisions")).values())
    roadmap_tokens = " ".join(filter_token(record.get("id")) for record in roadmap) or "unclassified"
    decision_tokens = " ".join(filter_token(record.get("id")) for record in decisions) or "unclassified"
    occurred_at = str(event.get("occurred_at") or "")
    canonical_url = safe_href(subject.get("canonical_url"))
    provenance = require_list(event.get("provenance"))
    search = " ".join(
        str(value)
        for value in (
            event.get("type"),
            title,
            subject.get("key"),
            subject.get("kind"),
            subject.get("state"),
            actor_id,
            chapter.get("title"),
            *(record.get("key") for record in roadmap),
            *(record.get("title") for record in roadmap),
            *(record.get("key") for record in decisions),
            *(record.get("title") for record in decisions),
            *provenance,
        )
        if value is not None
    ).casefold()
    changes_text = " ".join(
        str(value)
        for change in require_list(event.get("changes"))
        for value in require_object(change).values()
        if value is not None
    ).casefold()
    node_symbol = {
        "intent": "◇",
        "work": "□",
        "code": "⌘",
        "proof": "✓" if state not in BROKEN_STATES else "!",
        "delivery": "◎",
        "other": "·",
    }[lane]
    source = (
        f'<a class="ri-button ri-button--quiet" href="{escaped(canonical_url)}">Open canonical {escaped(state_label(kind))} <span aria-hidden="true">↗</span></a>'
        if canonical_url
        else '<span class="ri-status" data-state="unknown"><span></span>Canonical source unavailable</span>'
    )
    actor_url = safe_href(actor.get("url"))
    actor_value = (
        f'<a href="{escaped(actor_url)}">{escaped(actor_id)}</a>'
        if actor_url
        else escaped(actor_id)
    )
    return f'''<li class="ri-journey-event" id="{escaped(anchor)}" data-entity-id="{escaped(identifier)}" data-filter-item data-journey-event data-journey-event-id="{escaped(identifier)}" data-journey-event-title="{escaped(title)}" data-journey-occurred-at="{escaped(occurred_at)}" data-lane="{escaped(lane)}" data-state="{escaped(state)}" data-kind="{escaped(kind)}" data-filter-chapter="{escaped(filter_token(chapter.get("id")))}" data-filter-release="{escaped(release_token)}" data-filter-roadmap="{escaped(roadmap_tokens)}" data-filter-decision="{escaped(decision_tokens)}" data-filter-actor="{escaped(actor_token)}" data-filter-assertion="{escaped(assertion)}" data-filter-freshness="{escaped(freshness)}" data-search="{escaped(search + " " + changes_text)}" data-context-status="{("linked" if roadmap or decisions else "unclassified")}" aria-posinset="{index + 1}" aria-setsize="{total}">
      <div class="ri-journey-event__lane"><span>{escaped(lane_label)}</span><i aria-hidden="true">{escaped(node_symbol)}</i></div>
      <article class="ri-journey-event__card"><header><div><span class="ri-eyebrow">{escaped(journey_event_label(event))}</span><h3>{f"<a href=\"{escaped(canonical_url)}\">{escaped(title)}</a>" if canonical_url else escaped(title)}</h3><p><time datetime="{escaped(occurred_at)}">{escaped(format_date(occurred_at))}</time> · {status_pill(state)} · {escaped(subject.get("key"))}</p></div><a class="ri-journey-permalink" data-journey-link href="#{escaped(anchor)}" aria-label="Link to {escaped(title)}">#{index + 1:03d}</a></header>
      {render_journey_context_links(context, roadmap_anchors, decision_anchors)}
      <details data-journey-evidence><summary>Inspect event evidence</summary><div class="ri-journey-evidence"><section><h4>Recorded transition</h4>{render_journey_changes(event)}</section><section><h4>Provenance</h4><dl><div><dt>Assertion</dt><dd>{escaped(state_label(assertion))}</dd></div><div><dt>Freshness</dt><dd>{escaped(state_label(freshness))}</dd></div><div><dt>Actor</dt><dd>{actor_value}</dd></div><div><dt>Recorded</dt><dd>{escaped(format_date(event.get("recorded_at")))}</dd></div></dl><p>Source IDs: {escaped(", ".join(str(value) for value in provenance))}</p></section>{render_journey_files(context)}</div><footer>{source}</footer></details></article>
    </li>'''


def render_journey_gap(previous: dict[str, Any], current: dict[str, Any]) -> str:
    """Expose a large projected time gap without claiming repository inactivity."""

    before = parse_rfc3339(previous.get("occurred_at"), "journey previous event")
    after = parse_rfc3339(current.get("occurred_at"), "journey current event")
    seconds = (after - before).total_seconds()
    if seconds < 72 * 60 * 60:
        return ""
    days = seconds / (24 * 60 * 60)
    label = f"{days:.1f}".rstrip("0").rstrip(".")
    return f'''<li class="ri-journey-gap"><span>{escaped(label)} days between projected lifecycle events</span><small>This gap is not evidence that no repository work occurred.</small></li>'''


def journey_chapter_counts(
    events: list[dict[str, Any]],
    contexts: dict[str, dict[str, Any]],
) -> dict[str, int]:
    counts = {
        "events": len(events),
        "quests": 0,
        "decisions": 0,
        "commits": 0,
        "merged_pull_requests": 0,
        "checks": 0,
        "failures": 0,
        "deliveries": 0,
        "unclassified": 0,
    }
    quest_ids: set[str] = set()
    decision_ids: set[str] = set()
    for event in events:
        subject = entity(event.get("subject_entity"))
        kind = normalize_state(subject.get("kind"))
        state = normalize_state(subject.get("state"))
        context = contexts.get(str(subject.get("id") or ""), {})
        quest_ids.update(require_object(context.get("roadmap")))
        decision_ids.update(require_object(context.get("decisions")))
        counts["commits"] += int(kind == "commit")
        counts["merged_pull_requests"] += int(event.get("type") == "pull_request.merged")
        counts["checks"] += int(kind == "check")
        regressed = any(
            normalize_state(require_object(change).get("to")) in BROKEN_STATES
            for change in require_list(event.get("changes"))
        )
        counts["failures"] += int(state in BROKEN_STATES or regressed)
        counts["deliveries"] += int(kind in {"deployment", "release"})
        counts["unclassified"] += int(not context.get("roadmap") and not context.get("decisions"))
    counts["quests"] = len(quest_ids)
    counts["decisions"] = len(decision_ids)
    return counts


def render_journey_compare(chapters: list[dict[str, Any]]) -> str:
    if len(chapters) < 2:
        return f'''<section class="ri-journey-compare" data-journey-compare aria-labelledby="journey-compare-heading"><div><span class="ri-eyebrow">Then and now</span><h2 id="journey-compare-heading">Compare delivery chapters</h2><p>At least two release-bounded chapters are needed for a structural comparison. This never infers causality.</p></div></section>'''
    options = "".join(
        f'<option value="{escaped(chapter.get("id"))}">{escaped(chapter.get("title"))}</option>'
        for chapter in chapters
    )
    return f'''<section class="ri-journey-compare" data-journey-compare aria-labelledby="journey-compare-heading"><div><span class="ri-eyebrow">Then and now</span><h2 id="journey-compare-heading">Compare delivery chapters</h2><p>Place two projected chapters side by side. Counts describe structure, not causality or productivity.</p></div><div class="ri-journey-compare__controls"><label><span>Earlier chapter</span><select data-journey-compare-left>{options}</select></label><button class="ri-button ri-button--quiet" type="button" data-journey-compare-swap>Swap</button><label><span>Later chapter</span><select data-journey-compare-right>{options}</select></label></div><div class="ri-journey-compare__output" data-journey-compare-output aria-live="polite"><p>Choose two different chapters to compare.</p></div></section>'''


def journey_body(snapshot: dict[str, Any] | None) -> str:
    if snapshot is None:
        unavailable = empty_state(
            "Observatory journey unavailable",
            "Relay never reconstructs semantic history from raw Git output when the commit-matched lifecycle projection is absent.",
            "partial",
        )
        return f'''<section class="ri-section ri-section--lead" aria-labelledby="journey-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Semantic history</span><h2 id="journey-heading">The repository journey</h2></div><p>Unknown history remains visible until the Observatory journey view is supplied.</p></div>{unavailable}</section>'''
    views = require_object(snapshot.get("views"))
    journey = require_object(views.get("journey"))
    events = [require_object(value) for value in require_list(journey.get("events"))]
    chapters = [require_object(value) for value in require_list(journey.get("chapters"))]
    if not events:
        return f'''<section class="ri-section ri-section--lead" aria-labelledby="journey-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Semantic history</span><h2 id="journey-heading">The repository journey</h2></div><p>No lifecycle event is projected for this represented commit.</p></div>{empty_state("No journey events projected", "This is not evidence that the repository has no Git history. The public-safe Observatory projection is empty for this snapshot.", "not_applicable")}</section>'''
    contexts = journey_context_index(snapshot)
    roadmap = require_object(views.get("roadmap"))
    roadmap_anchors = {
        str(entity(step).get("id")): stable_fragment("quest", entity(step).get("id"))
        for step in require_list(roadmap.get("steps"))
    }
    decisions_view = require_object(views.get("decisions"))
    decision_anchors = {
        str(entity(decision).get("id")): stable_fragment("decision", entity(decision).get("id"))
        for decision in require_list(decisions_view.get("decisions"))
    }
    events_by_id = {str(event.get("id")): event for event in events}
    rendered_chapters = []
    index_links = []
    sequence = 0
    release_count = 0
    unclassified = 0
    for chapter_number, chapter in enumerate(chapters, start=1):
        chapter_events = [events_by_id[str(identifier)] for identifier in chapter["event_ids"]]
        boundary = require_object(chapter.get("boundary"))
        release_key = str(boundary.get("key") or "unreleased")
        release_token = filter_token(release_key)
        if boundary:
            release_count += 1
            reason = f"Closed by the authoritative {release_key} release event."
        elif release_count:
            reason = "Open chapter containing events after the latest projected release boundary."
        else:
            reason = "No release boundary is projected, so the events remain one unreleased chapter."
        anchor = stable_fragment("chapter", chapter.get("id"))
        index_links.append(
            f'<li><a data-journey-index href="#{escaped(anchor)}"><span>{chapter_number:02d}</span><small>{escaped(chapter.get("title"))}</small></a></li>'
        )
        rendered_events = []
        previous_event: dict[str, Any] | None = None
        for event in chapter_events:
            if previous_event is not None:
                gap = render_journey_gap(previous_event, event)
                if gap:
                    rendered_events.append(gap)
            subject = entity(event.get("subject_entity"))
            context = contexts.get(
                str(subject.get("id") or ""),
                {"roadmap": {}, "decisions": {}, "changed_files": {}},
            )
            unclassified += int(not context.get("roadmap") and not context.get("decisions"))
            rendered_events.append(
                render_journey_event(
                    event,
                    index=sequence,
                    total=len(events),
                    chapter=chapter,
                    context=context,
                    release_token=release_token,
                    roadmap_anchors=roadmap_anchors,
                    decision_anchors=decision_anchors,
                )
            )
            sequence += 1
            previous_event = event
        counts = journey_chapter_counts(chapter_events, contexts)
        boundary_label = str(boundary.get("title") or boundary.get("key") or "Open chapter")
        rendered_chapters.append(
            f'''<section class="ri-journey-chapter" id="{escaped(anchor)}" data-journey-chapter data-journey-chapter-id="{escaped(chapter.get("id"))}" data-journey-chapter-title="{escaped(chapter.get("title"))}" data-journey-start="{escaped(chapter.get("start_at"))}" data-journey-end="{escaped(chapter.get("end_at"))}" data-journey-boundary="{escaped(boundary_label)}" data-journey-counts="{escaped(json.dumps(counts, sort_keys=True, separators=(",", ":")))}"><header class="ri-journey-chapter__heading"><div><span class="ri-eyebrow">Chapter {chapter_number:02d}</span><h2>{escaped(chapter.get("title"))}</h2><p><time datetime="{escaped(chapter.get("start_at"))}">{escaped(format_date(chapter.get("start_at")))}</time> — <time datetime="{escaped(chapter.get("end_at"))}">{escaped(format_date(chapter.get("end_at")))}</time></p></div><div class="ri-journey-boundary"><span>Grouping rule</span><strong>{escaped(boundary_label)}</strong><p>{escaped(reason)}</p></div></header><div class="ri-journey-chapter__metrics" aria-label="Chapter composition"><span><strong>{counts["events"]}</strong> events</span><span><strong>{counts["quests"]}</strong> quests</span><span><strong>{counts["decisions"]}</strong> decisions</span><span><strong>{counts["commits"]}</strong> commits</span><span><strong>{counts["deliveries"]}</strong> deliveries</span></div><ol class="ri-journey-events" data-journey-viewport data-virtualization="content-visibility">{"".join(rendered_events)}</ol></section>'''
        )
    lane_legend = "".join(
        f'<li data-lane="{escaped(lane)}"><i aria-hidden="true"></i><span>{escaped(label)}</span></li>'
        for lane, label, _ in JOURNEY_LANES
    )
    return f'''<section class="ri-section ri-section--lead ri-journey-intro" aria-labelledby="journey-heading"><div class="ri-section-heading"><div><span class="ri-eyebrow">Semantic Git history</span><h2 id="journey-heading">The repository journey</h2></div><p>Release-bounded chapters turn lifecycle evidence into a readable story while every event remains source-linked and independently inspectable.</p></div><div class="ri-roadmap-metrics" aria-label="Journey summary"><article><strong>{len(chapters)}</strong><span>delivery chapters</span></article><article><strong>{len(events)}</strong><span>lifecycle events</span></article><article><strong>{release_count}</strong><span>release boundaries</span></article><article><strong>{unclassified}</strong><span>unclassified events</span></article></div><div class="ri-journey-contract"><article><span class="ri-eyebrow">Grouping</span><strong>Deterministic chapters</strong><p>Each release closes a chapter; later events form the current chapter.</p></article><article><span class="ri-eyebrow">Topology</span><strong>Only projected merges</strong><p>PR merges are shown. Raw Git parents, private branches, and paths are never invented.</p></article><article><span class="ri-eyebrow">Meaning</span><strong>Explicit links only</strong><p>Unlinked work stays visible as unclassified rather than being assigned intent.</p></article></div><ul class="ri-journey-lanes" aria-label="Semantic delivery lanes">{lane_legend}</ul>{render_journey_filter_controls(chapters, events, contexts)}</section><details class="ri-journey-tools"><summary>Open playback and chapter comparison tools</summary><div><section class="ri-journey-replay" aria-labelledby="journey-replay-heading"><div><span class="ri-eyebrow">Optional replay</span><h2 id="journey-replay-heading">Traverse the projected sequence</h2><p>Scrub manually or replay visible events. Reduced-motion preferences disable automatic playback.</p></div><div class="ri-journey-replay__controls"><button class="ri-button" type="button" data-journey-replay>Replay journey</button><label><span class="ri-visually-hidden">Journey replay position</span><input type="range" min="1" max="{len(events)}" value="{len(events)}" data-journey-scrubber></label><output data-journey-replay-output aria-live="polite">Showing all {len(events)} events</output></div></section>{render_journey_compare(chapters)}</div></details><div class="ri-journey-layout"><nav class="ri-map ri-journey-map" aria-label="Journey chapters"><span class="ri-eyebrow">Journey map</span><p>{len(chapters)} chronological chapters · release boundaries remain authoritative</p><ol>{"".join(index_links)}</ol></nav><div class="ri-journey-story">{"".join(rendered_chapters)}</div></div>'''


def build_status(summary: dict[str, Any]) -> tuple[str, str]:
    execution = require_object(require_object(summary.get("states")).get("execution"))
    if int(execution.get("failure", 0) or 0) > 0:
        return "failure", "Build signals failing"
    if int(execution.get("success", 0) or 0) > 0 and int(execution.get("unknown", 0) or 0) == 0:
        return "success", "Build signals passing"
    return "unknown", "Build status partial"


def projection_freshness(
    snapshot: dict[str, Any] | None,
    route: str,
    *,
    projected: bool | None = None,
) -> str:
    """Report freshness only when this route's accepted evidence is present."""

    if snapshot is None:
        return "unknown"
    if projected is None:
        projected = route in require_object(snapshot.get("views"))
    if not projected:
        return "unknown"
    return normalize_state(require_object(snapshot.get("coverage")).get("status"))


def navigation(current: str, prefix: str) -> str:
    overview_current = ' aria-current="page"' if current == "intelligence" else ""
    links = [
        f'<a href="{escaped(prefix or "./")}"{overview_current}>Overview</a>'
    ]
    for route, label in ROUTES:
        current_attribute = ' aria-current="page"' if current == route else ""
        links.append(
            f'<a href="{escaped(prefix + route + "/")}"{current_attribute}>{escaped(label)}</a>'
        )
    links.append(
        f'<a href="{escaped(prefix + "dashboard/")}">Dashboard</a>'
    )
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
        "intelligence": "Orient in one commit-matched Repository Intelligence projection, then move into the focused evidence view that answers the next question.",
        **ROUTE_QUESTIONS,
    }
    route_description = route_descriptions.get(
        route,
        "Explore one commit-matched projection without replacing its canonical repository sources.",
    )
    command_bar = ""
    if route != "intelligence":
        command_bar = '''<div class="ri-command-bar" data-filters>
          <label class="ri-search"><span class="ri-visually-hidden">Search this view</span><span aria-hidden="true">⌕</span><input type="search" data-filter-query placeholder="Search this view…" autocomplete="off"></label>
          <label><span>State</span><select data-filter-state><option value="all">All states</option><option value="accepted">Accepted</option><option value="active">Active</option><option value="blocked">Blocked</option><option value="complete">Complete</option><option value="deprecated">Deprecated</option><option value="deferred">Deferred</option><option value="failure">Failure</option><option value="planned">Planned</option><option value="proposed">Proposed</option><option value="ready">Ready</option><option value="rejected">Rejected</option><option value="superseded">Superseded</option><option value="unknown">Unknown</option></select></label>
          <label><span>Kind</span><select data-filter-kind><option value="all">All evidence</option><option value="roadmap_step">Quest</option><option value="architecture_decision">Decision</option><option value="check">Check</option><option value="commit">Commit</option><option value="issue">Issue</option><option value="pull_request">Pull request</option><option value="release">Release</option><option value="deployment">Deployment</option><option value="file">Changed file</option></select></label>
          <button class="ri-button ri-button--quiet" type="button" data-filter-reset>Reset</button>
          <output data-filter-results aria-live="polite">Showing the full view</output>
        </div>'''
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
    <a class="ri-skip" href="#main-content">Skip to view content</a>
    <header class="ri-global-header">
      <a class="ri-brand" data-preserve-context href="{escaped(prefix)}"><span aria-hidden="true">EH</span><strong>Repository Intelligence</strong></a>
      <nav aria-label="Global navigation"><a href="https://github.com/egohygiene">Ego Hygiene</a><a href="{escaped(repository_url)}">Repository source</a></nav>
    </header>
    <div class="ri-layout">
      <aside class="ri-sidebar" aria-label="Repository Intelligence navigation">
        <div class="ri-repository"><span class="ri-eyebrow">Repository</span><strong>{escaped(repository)}</strong><span>{status_pill(freshness)}</span></div>
        <nav class="ri-route-nav" data-preserve-context-links>{navigation(route, prefix)}</nav>
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
          <a data-preserve-context href="{escaped(prefix)}dashboard/"><span>Build evidence</span>{status_pill(state, build_label)}</a>
          <a href="{escaped(prefix)}provenance.json"><span>Generator</span><strong>View provenance ↗</strong></a>
        </section>
        <div class="ri-visually-hidden" role="status" aria-live="polite" aria-atomic="true" data-context-status></div>
        {command_bar}
        <main id="main-content" tabindex="-1">{body}<div class="ri-no-results" data-no-results hidden>{empty_state("No matching evidence", "Clear a filter or broaden the search to continue.", "empty")}</div></main>
        <footer><span>Operational state is rendered only from <code>{escaped(SNAPSHOT_SCHEMA)}</code>.</span><a href="#main-content">Back to top ↑</a></footer>
      </div>
    </div>
    <script src="{escaped(prefix)}site.js" defer></script>
  </body>
</html>
'''


def overview_body() -> str:
    """Render the product entry point without duplicating the operational Now view."""

    cards = []
    for index, (route, label) in enumerate(ROUTES, start=1):
        question = ROUTE_QUESTIONS[route]
        cards.append(
            f'''<article class="ri-panel">
              <div class="ri-panel-heading"><span class="ri-panel-icon" aria-hidden="true">{index:02d}</span><div><span class="ri-eyebrow">Evidence view</span><h3>{escaped(label)}</h3></div></div>
              <p>{escaped(question)}</p>
              <a class="ri-button ri-button--quiet" data-preserve-context href="./{escaped(route)}/">Open {escaped(label)}</a>
            </article>'''
        )
    return f'''<section class="ri-section ri-section--lead" aria-labelledby="intelligence-heading">
      <div class="ri-section-heading"><div><span class="ri-eyebrow">Repository orientation</span><h2 id="intelligence-heading">Choose the evidence question</h2></div><p>Each route answers one bounded question from the same represented commit. Unknown and unavailable evidence stays explicit inside the selected view.</p></div>
      <div class="ri-now-grid ri-overview-grid">{"".join(cards)}</div>
    </section>
    <section class="ri-section" aria-labelledby="dashboard-heading"><div class="ri-panel ri-panel--wide"><div class="ri-panel-heading"><span class="ri-panel-icon" aria-hidden="true">↗</span><div><span class="ri-eyebrow">Build evidence</span><h2 id="dashboard-heading">Inspect the analytics dashboard</h2></div></div><p>Review source-tree, activity, dependency, and generator evidence without confusing the compatibility dashboard with a canonical repository view.</p><a class="ri-button ri-button--quiet" data-preserve-context href="./dashboard/">Open Dashboard</a></div></section>'''


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
        shell_document(
            route="intelligence",
            route_label="Intelligence",
            body=overview_body(),
            prefix="",
            **shared,
        ),
    )
    atomic_write(
        output_root / "now/index.html",
        shell_document(
            route="now",
            route_label="Now",
            body=now_body(snapshot),
            prefix="../",
            **shared,
        ),
    )
    for route, label in ROUTES[1:]:
        body = (
            roadmap_body(snapshot)
            if route == "roadmap"
            else decisions_body(snapshot)
            if route == "decisions"
            else journey_body(snapshot)
            if route == "journey"
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
