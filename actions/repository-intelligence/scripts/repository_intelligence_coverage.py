# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Validate and present the pinned Observatory alpha.2 collection boundary."""

from datetime import datetime

DOMAINS = ("roadmap", "decisions", "git", "issues", "pull_requests", "checks",
           "releases", "deployments", "history")
VIEW_DOMAINS = {
    "roadmap": ("roadmap",), "decisions": ("decisions",), "journey": ("history",),
    "health": ("checks",), "releases": ("releases", "deployments"),
    "work": ("roadmap", "issues", "pull_requests"),
    "now": DOMAINS, "dependencies": DOMAINS, "search": DOMAINS,
}
# Compatibility checks mirror the immutable owner's collectionDomain schema.
CLAIMS = {
    "uncollected": ({"not_requested"}, {"unknown"}, False),
    "unavailable": ({"access_denied", "provider_unavailable", "legacy_unspecified"}, {"unknown"}, False),
    "failed": ({"collection_failed"}, {"unknown"}, False),
    "partial": ({"filtered", "truncated", "incomplete"}, {"current", "stale"}, True),
    "observed_empty": ({"complete"}, {"current", "stale"}, True),
    "observed": ({"complete"}, {"current", "stale"}, True),
    "not_applicable": ({"explicit_not_applicable"}, {"not_applicable"}, True),
}


def validate_domains(domains, observed_at):
    if not isinstance(domains, dict) or set(domains) != set(DOMAINS):
        raise ValueError("snapshot collection coverage must describe all nine domains")
    boundary = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    for claim in domains.values():
        if not isinstance(claim, dict) or set(claim) != {"collection", "freshness", "reason", "observed_at"}:
            raise ValueError("snapshot collection claim is not closed")
        try:
            reasons, freshness, captured = CLAIMS[claim["collection"]]
            valid = claim["reason"] in reasons and claim["freshness"] in freshness
        except (KeyError, TypeError):
            valid = False
        if not valid:
            raise ValueError("snapshot collection claim is contradictory")
        instant = claim["observed_at"]
        if captured:
            if not isinstance(instant, str) or not instant.endswith("Z"):
                raise ValueError("snapshot collection observation must be UTC")
            if datetime.fromisoformat(instant.replace("Z", "+00:00")) > boundary:
                raise ValueError("snapshot collection observation exceeds its boundary")
        elif instant is not None:
            raise ValueError("unobserved collection must not have an observation time")


def validate(snapshot):
    coverage = snapshot.get("coverage", {})
    alpha2 = snapshot.get("contract_version") == "1.0.0-alpha.2"
    if not alpha2:
        if "domains" in coverage or "record_status" in coverage or any(
                "collection_coverage" in view for view in snapshot.get("views", {}).values()
                if isinstance(view, dict)):
            raise ValueError("collection coverage requires the alpha.2 read model")
        return
    if snapshot.get("visibility") != "public":
        raise ValueError("alpha.2 snapshots must have explicit public visibility")
    if set(coverage) != {"record_status", "counts", "freshness", "assertions", "domains"}:
        raise ValueError("alpha.2 coverage must retain record and collection states separately")
    if coverage["record_status"] not in {"current", "stale", "unknown", "not_applicable"}:
        raise ValueError("alpha.2 record status is unsupported")
    if not all(isinstance(coverage[name], dict) for name in ("counts", "freshness", "assertions")):
        raise ValueError("alpha.2 record distributions must be objects")
    validate_domains(coverage["domains"], snapshot["observed_at"])
    for name, domains in VIEW_DOMAINS.items():
        view = snapshot.get("views", {}).get(name)
        expected = {domain: coverage["domains"][domain] for domain in domains}
        if not isinstance(view, dict) or view.get("collection_coverage") != expected:
            raise ValueError("view collection coverage must match the normalized domain claims")


def claims(snapshot, route):
    if not snapshot or snapshot.get("contract_version") != "1.0.0-alpha.2":
        return {}
    return snapshot.get("views", {}).get(route, {}).get("collection_coverage", snapshot["coverage"]["domains"])


def display_status(snapshot, route):
    values = list(claims(snapshot, route).values())
    if not values:
        return (snapshot or {}).get("coverage", {}).get("status", "unknown")
    if any(v["collection"] == "failed" for v in values):
        return "error"
    if all(v["collection"] == "not_applicable" for v in values):
        return "not_applicable"
    if any(v["collection"] in {"unavailable", "uncollected", "partial"} for v in values):
        return "unknown" if all(v["collection"] in {"unavailable", "uncollected"} for v in values) else "partial"
    return "stale" if any(v["freshness"] == "stale" for v in values) else "current"
