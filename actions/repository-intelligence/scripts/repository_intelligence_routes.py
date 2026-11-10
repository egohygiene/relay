# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Compose the repository route profile from the locked Hygiene registry.

This is Relay presentation metadata, not a new canonical surface registry.
Consumer origins, site prefixes, redirects and publication remain external.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "contracts/repository-intelligence-siblings.v1.lock.json"
REGISTRY = ROOT / "contracts/repository-intelligence-routes.v1.registry.json"
SCHEMA = "egohygiene.relay.repository-intelligence-routes/v1"
CORE_IDS = ("now", "roadmap", "decisions", "journey", "dependencies", "health",
            "releases", "work", "search", "compare")
RESERVED_IDS = ("audits", "hygiene", "sanity", "diagnostics", "distribution", "identity")
_SURFACE_IDS = {"identity": "identity_intelligence"}
_QUESTIONS = {
    "intelligence": "Which repository evidence question needs attention next?",
    "dashboard": "Which source-tree, activity and build signals were represented?",
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
    "audits": "Which audit runs, findings and dispositions have source-linked evidence?",
    "hygiene": "Which versioned contracts apply, and what adoption or exemption evidence is available?",
    "sanity": "What architecture review and explicit human ratification evidence is available?",
    "diagnostics": "What investigations, hypotheses, remediation and validation are documented?",
    "distribution": "Which declared channels have package, delivery and installation evidence?",
    "identity": "What Identity adoption, version and asset-provenance evidence is available?",
}
_ISSUES = {
    "intelligence": 27, "dashboard": 27, "now": 28, "roadmap": 31, "decisions": 30,
    "journey": 32, "dependencies": 77, "health": 88, "releases": 81,
    "work": 79, "search": 83, "compare": 86, "audits": 74,
    "hygiene": 75, "sanity": 76, "diagnostics": 57, "distribution": 48, "identity": 27,
}
_SOURCE_BOUNDARIES = {
    "audits": "The pinned read model has no accepted audit-run or finding projection. Audit Markdown remains canonical; absent data cannot establish that no findings exist.",
    "hygiene": "The pinned read model has no accepted contract applicability/conformance projection. Operational Health checks cannot substitute for contract adoption, exemptions or policy evidence.",
    "sanity": "The pinned read model has no accepted architecture-review/ratification projection. Build activity and passing checks cannot establish explicit human acceptance.",
    "diagnostics": "The pinned read model has no accepted diagnostic-investigation projection. Unrestricted logs, telemetry and exception prose are not a safe substitute.",
    "distribution": "The pinned read model has no accepted distribution-channel/installability projection. A published release or successful build does not prove installation or channel delivery.",
    "identity": "The pinned read model has no accepted Identity adoption/provenance projection. The consumer-owned Identity product and approved brand assets retain their separate authority.",
}


def _read(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 262144:
        raise ValueError("Repository route contract is unavailable")
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError("Repository route contract is incompatible")
    return value


_lock = _read(LOCK)["hygiene"]
if hashlib.sha256(REGISTRY.read_bytes()).hexdigest() != _lock["registry_sha256"]:
    raise ValueError("Repository route registry does not match the locked owner bytes")
_registry = _read(REGISTRY)
if (_registry.get("schema") != _lock["contract"]
        or _registry.get("version") != _lock["contract_version"]
        or _lock.get("route_profile") != "repository"):
    raise ValueError("Repository route profile is incompatible")
_surfaces = {surface["id"]: surface for surface in _registry["surfaces"]}


def _definition(identifier: str) -> dict:
    surface_id = _SURFACE_IDS.get(identifier, identifier)
    source = _surfaces[surface_id]
    binding = source["route_bindings"]["repository"]
    canonical = binding["canonical_route"]
    expected = "/intelligence/" if identifier == "intelligence" else f"/intelligence/{identifier}/"
    if canonical != expected or source["renderer_contract"] != "relay-compatible":
        raise ValueError("Surface is not a supported repository Intelligence route")
    aliases = binding["aliases"]
    if (not isinstance(aliases, list) or len(aliases) != len(set(aliases))
            or any(not isinstance(alias, str) or len(alias) > 240
                   or not re.fullmatch(r"/(?:[a-z0-9]+(?:-[a-z0-9]+)*/)+", alias) for alias in aliases)):
        raise ValueError("Repository route aliases are incompatible")
    return {
        "id": identifier, "surface_id": surface_id, "title": source["title"],
        "canonical_route": canonical,
        "relative_file": "index.html" if identifier == "intelligence" else f"{identifier}/index.html",
        "aliases": aliases,
        "renderer_state": "source-unsupported" if identifier in RESERVED_IDS else "implemented",
        "primary_question": _QUESTIONS[identifier],
        "owning_issue": f"https://github.com/egohygiene/relay/issues/{_ISSUES[identifier]}",
    }


_DEFINITIONS = {identifier: _definition(identifier)
                for identifier in ("intelligence", *CORE_IDS, *RESERVED_IDS, "dashboard")}
# Preserve the existing tuple API consumed by the shared shell and callers.
CORE_ROUTES = tuple((identifier, _DEFINITIONS[identifier]["title"]) for identifier in CORE_IDS)
RESERVED_ROUTES = tuple((identifier, _DEFINITIONS[identifier]["title"]) for identifier in RESERVED_IDS)
ROUTES = CORE_ROUTES + RESERVED_ROUTES
ROUTE_QUESTIONS = dict(_QUESTIONS)


def route(identifier: str, *, supported_views=()) -> dict:
    """Return independent metadata; callers cannot mutate the trusted inventory."""
    if not set(supported_views) <= {"hygiene", "audits", "sanity"}:
        raise ValueError("Owner view support is incompatible")
    value = json.loads(json.dumps(_DEFINITIONS[identifier]))
    if identifier in supported_views:
        value["renderer_state"] = "implemented"
    return value


def canonical_routes() -> tuple[str, ...]:
    return tuple(sorted(value["canonical_route"] for value in _DEFINITIONS.values()))


def source_boundary(identifier: str) -> str:
    return _SOURCE_BOUNDARIES[identifier]


def manifest(repository: str, source_commit: str, *, supported_views=()) -> dict:
    """Describe routes and consumer-only aliases without publishing redirects."""
    if (not isinstance(repository, str)
            or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)
            or any(part in {".", ".."} for part in repository.split("/"))
            or not isinstance(source_commit, str) or not re.fullmatch(r"[a-f0-9]{40}", source_commit)):
        raise ValueError("Repository route source binding is incompatible")
    external = []
    for identifier in ("status", "identity"):
        external.append({"surface_id": identifier,
            "canonical_route": _surfaces[identifier]["route_bindings"]["repository"]["canonical_route"],
            "reason": "consumer-owned surface outside Intelligence subtree"})
    return {"schema": SCHEMA, "schema_version": 1, "profile": "repository",
        "repository": repository, "represented_commit": source_commit,
        "registry": {"owner": _lock["owner"], "source_commit": _lock["source_commit"],
            "path": _lock["registry_path"], "sha256": _lock["registry_sha256"],
            "contract_version": _lock["contract_version"]},
        "consumer_boundary": {"canonical_origin": "consumer-owned", "base_path": "consumer-owned",
            "aliases": "consumer-owned redirects only"},
        "routes": [route(identifier, supported_views=supported_views) for identifier in _DEFINITIONS],
        "external_surfaces": external}
