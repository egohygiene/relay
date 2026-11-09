#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Assemble reviewed public artifacts with the pinned Observatory fleet model."""

from __future__ import annotations

import argparse
from copy import deepcopy
import importlib.util
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import unquote, urlsplit

import jsonschema

_spec = importlib.util.spec_from_file_location(
    "relay_fleet_normalization", Path(__file__).with_name("collect_repository_adrs.py"))
normalization = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(normalization)
base = normalization.base

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "contracts/public-fleet.v1.lock.json"
PLAN_PATH = ROOT / "schemas/public-fleet-plan.v1.schema.json"
REVIEW_PATH = ROOT / "schemas/public-fleet-review.v1.schema.json"
OUTPUT_NAME = "public-fleet.review.json"
SCHEMA = "egohygiene.relay.public-fleet-review/v1"
CONTROL_REPOSITORIES = {"egohygiene/hygiene", "egohygiene/relay", "egohygiene/observatory", "egohygiene/egolint"}
MESSAGES = {
    **base.MESSAGES,
    "CATALOG": "Repair the selected public catalog slice through Hygiene; no hidden entries or totals are reported.",
    "CATALOG_STALE": "Review Hygiene #36 catalog freshness and the public selection before production consumption.",
    "SELECTION": "Supply a review-referenced public selection bound to canonical catalog identities and exact artifact hashes.",
    "PUBLIC_BOUNDARY": "Supply an already public-safe artifact with only selected public graph endpoints and reviewed public evidence URLs.",
    "ARTIFACT": "Restore the selected immutable artifact at its declared hash; the failing repository cannot become observed-empty.",
    "INCOMPATIBLE": "Rebuild this public repository artifact with the locked Hygiene alpha.2 and Observatory contracts.",
    "SOURCE": "Select the exact declared repository, represented commit and capture boundary; no source identity is reassigned.",
    "UNAVAILABLE": "Supply the selected public repository artifact or an explicitly retained compatible last-known artifact.",
    "EXPIRED": "Retain a compatible baseline within the declared recovery age; expired bytes were not used.",
    "INTEGRATION": "Complete Hygiene #36 public-selection review and the consumer-owned host handoff before publication.",
}


def diagnostic(code: str, owner: str = "relay") -> dict:
    return {"code": code, "owner": owner, "remediation": MESSAGES.get(code, MESSAGES["INPUT"])}


def validator(path: Path):
    return jsonschema.Draft202012Validator(base.load_json(base.read_file(path)),
                                          format_checker=jsonschema.FormatChecker())


def relative_path(value: str) -> str:
    if (not isinstance(value, str) or not 1 <= len(value) <= 240
            or not re.fullmatch(r"[A-Za-z0-9._/-]+", value) or value.startswith("/")
            or any(part in {"", ".", "..", ".git"} for part in value.split("/"))):
        base.fail("PATH")
    return value


def public_url(value: str, permitted: set[str]) -> None:
    if not isinstance(value, str) or len(value) > 2000:
        base.fail("PUBLIC_BOUNDARY")
    parsed = urlsplit(value)
    parts = parsed.path.split("/")
    repository = "/".join(parts[1:3])
    decoded = parsed.path
    for _ in range(3):
        next_value = unquote(decoded)
        if next_value == decoded:
            break
        decoded = next_value
    decoded_parts = decoded.split("/")
    if (parsed.scheme != "https" or parsed.netloc != "github.com" or parsed.query
            or parsed.username or parsed.password or repository not in permitted
            or any(part in {".", ".."} for part in decoded_parts)
            or "/".join(decoded_parts[1:3]) != repository
            or "\\" in decoded or any(ord(character) < 32 or ord(character) == 127 for character in decoded)):
        base.fail("PUBLIC_BOUNDARY")


def public_graph(projection: dict, allowed: set[str]) -> None:
    """Guard public inputs before owner validation, traversal or aggregation."""
    if projection.get("visibility") != "public" or projection.get("repository") not in allowed:
        base.fail("PUBLIC_BOUNDARY")
    graph_ids = set()
    for name in ("sources", "entities"):
        collection = projection.get(name)
        if not isinstance(collection, list) or len(collection) > 10000:
            base.fail("INCOMPATIBLE")
        for item in collection:
            # Do not inspect identities or payloads of nonpublic records.
            if not isinstance(item, dict) or item.get("visibility") != "public":
                base.fail("PUBLIC_BOUNDARY")
            if item.get("repository") not in allowed:
                base.fail("PUBLIC_BOUNDARY")
            public_url(item.get("url") if name == "sources" else item.get("canonical_url"),
                       allowed | CONTROL_REPOSITORIES)
            if name == "entities":
                identity = item.get("id")
                if not isinstance(identity, str):
                    base.fail("INCOMPATIBLE")
                graph_ids.add(identity)
    for item in projection.get("events", []):
        if (not isinstance(item, dict) or item.get("visibility") != "public"
                or item.get("subject") not in graph_ids):
            base.fail("PUBLIC_BOUNDARY")
    for item in projection.get("relationships", []):
        if (not isinstance(item, dict) or item.get("source") not in graph_ids
                or item.get("target") not in graph_ids):
            base.fail("PUBLIC_BOUNDARY")
    # A public fleet does not export redacted-repository counts or unrestricted
    # extension payloads. Such projection decisions belong to the source owner.
    if projection.get("redactions") or projection.get("extensions"):
        base.fail("PUBLIC_BOUNDARY")
    visited = 0

    def inspect(value, depth=0, key=""):
        nonlocal visited
        visited += 1
        if visited > 100000 or depth > 24:
            base.fail("PUBLIC_BOUNDARY")
        if isinstance(value, dict):
            if key == "extensions" and value:
                base.fail("PUBLIC_BOUNDARY")
            for label, child in value.items():
                if label.lower() in {"email", "body", "comments", "token", "secret", "password", "headers", "logs", "raw"}:
                    base.fail("PUBLIC_BOUNDARY")
                inspect(child, depth + 1, label)
        elif isinstance(value, list):
            for child in value:
                inspect(child, depth + 1, key)
        elif isinstance(value, str):
            if base.SECRET.search(value) or any(ord(character) < 32 or ord(character) == 127 for character in value):
                base.fail("PUBLIC_BOUNDARY")
            if key in {"url", "canonical_url"} or key.endswith("_url"):
                public_url(value, allowed | CONTROL_REPOSITORIES)
            for match in re.finditer(r"https?://[^\s<>\"']+", value):
                public_url(match[0], allowed | CONTROL_REPOSITORIES)
            for match in re.finditer(r"egohygiene/(?:\.github|[a-z0-9][a-z0-9.-]*)", value):
                if match[0] not in allowed | CONTROL_REPOSITORIES:
                    base.fail("PUBLIC_BOUNDARY")

    inspect(projection)


def public_selection(args: argparse.Namespace, plan: dict) -> tuple[list, list, dict]:
    """Filter catalog visibility before inspecting a selection's artifact data."""
    if getattr(args, "catalog_profile", "legacy-review") == "public-catalog-v1":
        return admitted_public_selection(args, plan)
    if (plan.get("visibility") != "public" or not isinstance(plan.get("repositories"), list)
            or not isinstance(plan.get("catalog_revision"), str)
            or not base.SHA.fullmatch(plan["catalog_revision"])):
        base.fail("SELECTION")
    raw = base.git_blob(args.catalog_root, plan["catalog_revision"], "catalog/repositories.yaml", base.MAX_OUTPUT)
    catalog = base.load_json(raw)
    if not isinstance(catalog.get("repositories"), list):
        base.fail("CATALOG")
    requested = {item.get("repository") for item in plan["repositories"]
                 if isinstance(item, dict) and isinstance(item.get("repository"), str)}
    public = {}
    for item in catalog["repositories"]:
        if not isinstance(item, dict) or item.get("visibility") != "public":
            continue
        identity = item.get("full_name")
        if identity not in requested and identity != "egohygiene/hygiene":
            continue
        if not isinstance(identity, str) or not base.REPOSITORY.fullmatch(identity):
            continue
        if identity in public:
            base.fail("CATALOG")
        public[identity] = item
    selected, seen = [], set()
    for item in plan["repositories"]:
        if (not isinstance(item, dict) or not isinstance(item.get("repository"), str)
                or item["repository"] not in public):
            continue
        identity = item["repository"]
        if identity in seen:
            base.fail("SELECTION")
        seen.add(identity)
        selected.append(item)
    selected.sort(key=lambda item: item["repository"])
    # Only selected public entries are validated or hashed. Excluded entries
    # cannot cause named errors, artifact lookups, counts or changed digests.
    visible_plan = {**plan, "repositories": selected}
    if len(selected) > 64 or not validator(PLAN_PATH).is_valid(visible_plan):
        base.fail("SELECTION")
    if not selected:
        return [], [], {"schema_version": catalog.get("schema_version"), "observed_at": catalog.get("observed_at")}
    # Hygiene's complete catalog validator needs its canonical owner in scope.
    # Include that fixed public owner only as validation context, never as a
    # fabricated selected repository or unavailable fleet row.
    owner = catalog.get("canonical_repository")
    if owner != "hygiene" or "egohygiene/hygiene" not in public:
        base.fail("CATALOG")
    context = {item["repository"]: public[item["repository"]] for item in selected}
    context["egohygiene/hygiene"] = public["egohygiene/hygiene"]
    planes = {item.get("plane") for item in context.values()}
    projected = {key: catalog.get(key) for key in (
        "schema_version", "architecture_release", "observed_at", "organization", "canonical_repository")}
    projected.update(repositories=[context[key] for key in sorted(context)], proposed_repositories=[],
                     repository_count=len(context), planes=[item for item in catalog.get("planes", [])
                         if isinstance(item, dict) and item.get("id") in planes])
    schema = args.runtime / "hygiene_catalog/schemas/repository-catalog.v1.schema.json"
    owner_tool = base.module(args.runtime / "hygiene_catalog/tools/catalog.py", "pinned_fleet_catalog")
    if not validator(schema).is_valid(projected) or owner_tool.validate_catalog(projected):
        base.fail("CATALOG")
    metadata = {key: projected[key] for key in ("schema_version", "architecture_release", "observed_at")}
    public_rows = [{"repository": item["repository"], "plane": public[item["repository"]]["plane"],
                    "lifecycle": public[item["repository"]]["lifecycle"],
                    "source_url": public[item["repository"]]["source_url"]} for item in selected]
    return selected, public_rows, metadata


def admitted_public_selection(args: argparse.Namespace, plan: dict) -> tuple[list, list, dict]:
    """Opt into Hygiene's separately locked, public-only catalog projection."""
    helper = base.module(Path(__file__).with_name("public_catalog_admission.py"), "relay_fleet_public_catalog")
    requests = plan.get("repositories")
    if not isinstance(requests, list):
        base.fail("SELECTION")
    wanted = {item.get("repository") for item in requests
              if isinstance(item, dict) and isinstance(item.get("repository"), str)}
    rows, metadata = helper.load(args.catalog_root, wanted)
    public = {item["full_name"] for item in rows}
    selected = [item for item in requests if isinstance(item, dict) and item.get("repository") in public]
    visible = {**plan, "repositories": selected}
    if (len(selected) > 64 or len({item["repository"] for item in selected}) != len(selected)
            or not validator(PLAN_PATH).is_valid(visible)):
        base.fail("SELECTION")
    # The public artifact/profile is independently immutable. A caller cannot
    # use the new shape to reinterpret a historical raw-catalog revision.
    if plan["catalog_revision"] != metadata["revision"]:
        base.fail("CATALOG")
    return sorted(selected, key=lambda item: item["repository"]), rows, metadata


def artifact_projection(raw: dict, selection: dict, repository: str) -> dict:
    if selection["kind"] == "projection":
        projection = deepcopy(raw)
    else:
        if (raw.get("schema") != "egohygiene.observatory.repository-intelligence-read-model/v1"
                or raw.get("contract_version") != "1.0.0-alpha.2"
                or not isinstance(raw.get("repository"), dict)
                or raw["repository"].get("visibility") != "public"
                or raw["repository"].get("repository") != repository):
            base.fail("INCOMPATIBLE")
        upstream, graph = raw.get("upstream"), raw.get("graph")
        if not isinstance(upstream, dict) or not isinstance(graph, dict):
            base.fail("INCOMPATIBLE")
        # Raw views, search indexes and aggregate counts are never forwarded.
        # Recompute them from admitted owner graph data with the pinned model.
        coverage = raw.get("coverage")
        if not isinstance(coverage, dict):
            base.fail("INCOMPATIBLE")
        projection = {**deepcopy(graph), "schema": upstream.get("schema"),
            "contract_version": upstream.get("contract_version"), "projection_id": upstream.get("projection_id"),
            "repository": repository, "represented_commit": raw.get("represented_commit"),
            "visibility": raw.get("visibility"), "observed_at": raw.get("observed_at"),
            "generator": {"name": "egohygiene/relay:public-fleet-replay", "version": "0.1.0",
                          "contract": "egohygiene.repository-intelligence/v1"},
            "collection_coverage": coverage.get("domains")}
    if (projection.get("schema") != "egohygiene.repository-intelligence/v1"
            or projection.get("contract_version") != "1.0.0-alpha.2"):
        base.fail("INCOMPATIBLE")
    if (projection.get("repository") != repository
            or projection.get("represented_commit") != selection["represented_commit"]):
        base.fail("SOURCE")
    return projection


def age_projection(projection: dict, observed, maximum_age: int, fallback: bool) -> bool:
    capture = base.utc(projection["observed_at"])
    if capture > observed:
        base.fail("SOURCE")
    stale = fallback or (observed - capture).total_seconds() > maximum_age
    for item in projection.get("sources", []):
        instant = base.utc(item["observed_at"])
        if instant > observed:
            base.fail("SOURCE")
        expired = fallback or (observed - instant).total_seconds() > maximum_age
        if expired and item.get("freshness") == "current":
            item["freshness"] = "stale"
        stale |= item.get("freshness") == "stale"
    stale_sources = {item["id"] for item in projection.get("sources", []) if item.get("freshness") == "stale"}
    for collection in ("entities", "relationships", "events"):
        for item in projection.get(collection, []):
            if item.get("freshness") == "current" and (stale or stale_sources.intersection(item.get("provenance", []))):
                item["freshness"] = "stale"
    coverage = projection.get("collection_coverage")
    if not isinstance(coverage, dict):
        base.fail("INCOMPATIBLE")
    for claim in coverage.values():
        if not isinstance(claim, dict):
            base.fail("INCOMPATIBLE")
        instant = claim.get("observed_at")
        if instant is not None:
            instant = base.utc(instant)
            if instant > observed:
                base.fail("SOURCE")
            if (fallback or (observed - instant).total_seconds() > maximum_age) and claim.get("freshness") == "current":
                claim["freshness"] = "stale"
        stale |= claim.get("freshness") == "stale"
    return stale


def admit(args: argparse.Namespace, selection: dict, repository: str, allowed: set[str], fallback: bool) -> tuple[dict, bool, str]:
    raw = base.read_file(base.safe_path(args.artifact_root) / relative_path(selection["path"]), base.MAX_OUTPUT)
    if base.digest(raw) != selection["sha256"]:
        base.fail("ARTIFACT")
    projection = artifact_projection(base.load_json(raw), selection, repository)
    public_graph(projection, allowed)
    # Raw artifact hashes verify local acquisition only. Snapshot views/counts
    # are discarded and may not perturb a public receipt through a checksum.
    # Publish only a canonical admitted public-input digest after owner checks.
    public_input_digest = base.digest(base.json_bytes(projection))
    if fallback and (base.utc(args.observed_at) - base.utc(projection["observed_at"])).total_seconds() > args.maximum_last_known_age_seconds:
        base.fail("EXPIRED")
    stale = age_projection(projection, base.utc(args.observed_at), args.maximum_age_seconds, fallback)
    snapshot, validation = normalization.normalize(args.runtime, projection)
    if snapshot is None or validation["hygiene"] != "valid":
        base.fail("INCOMPATIBLE")
    return snapshot, stale, public_input_digest


def assemble(args: argparse.Namespace) -> dict:
    observed = base.utc(args.observed_at)
    if (not 1 <= args.maximum_age_seconds <= 2678400
            or not args.maximum_age_seconds <= args.maximum_last_known_age_seconds <= 31622400
            or not 1 <= args.maximum_catalog_age_days <= 366):
        base.fail("INPUT")
    lock, receipt = base.runtime_files(args.runtime, lock_path=LOCK_PATH)
    plan = base.load_json(base.read_file(args.plan))
    selected, public_rows, catalog_metadata = public_selection(args, plan)
    allowed = {item["repository"] for item in selected}
    snapshots, rows, diagnostics = [], [], []
    selection_evidence = []
    for item in selected:
        repository = item["repository"]
        row = {"repository": repository, "requested_commit": item["represented_commit"],
               "represented_commit": None, "status": "unavailable", "reason": "UNAVAILABLE",
               "public_input_sha256": None, "snapshot_sha256": None, "coverage": None,
               "admission": None}
        for name in ("candidate", "last_known"):
            choice = item[name]
            if choice is None:
                continue
            try:
                if name == "candidate" and choice["represented_commit"] != item["represented_commit"]:
                    base.fail("SOURCE")
                snapshot, stale, public_input_digest = admit(args, choice, repository, allowed, name == "last_known")
                row.update(represented_commit=snapshot["represented_commit"], status="last_known" if name == "last_known"
                           else "stale" if stale else "current", public_input_sha256=public_input_digest,
                           snapshot_sha256=base.digest(base.json_bytes(snapshot)), coverage=snapshot["coverage"]["domains"],
                           admission="projection" if choice["kind"] == "projection" else "snapshot_graph_replay")
                if name == "candidate":
                    row["reason"] = None
                snapshots.append(snapshot)
                break
            except (base.CollectorError, OSError, ValueError, KeyError, TypeError, RecursionError):
                error = sys.exception()
                row["reason"] = str(error) if isinstance(error, base.CollectorError) and str(error) in MESSAGES else "ARTIFACT"
        rows.append(row)
        selection_evidence.append({key: row[key] for key in (
            "repository", "requested_commit", "represented_commit", "public_input_sha256", "admission")})
    fleet = None
    if snapshots:
        observatory = base.module(args.runtime / "observatory/src/observatory/intelligence.py", "pinned_public_fleet")
        fleet = observatory.build_fleet_snapshot(snapshots)
        schema = args.runtime / "observatory/schemas/repository-intelligence-fleet.v1.schema.json"
        if not validator(schema).is_valid(fleet):
            base.fail("PIN")
    catalog_date = catalog_metadata.get("observed_at")
    catalog_instant = str(catalog_date)
    if len(catalog_instant) == 10:
        catalog_instant += "T00:00:00Z"
    catalog_age = ((observed - base.utc(catalog_instant)).total_seconds() / 86400
                   if getattr(args, "catalog_profile", "legacy-review") == "public-catalog-v1"
                   else (observed - base.utc(catalog_instant)).days)
    if catalog_age < 0:
        base.fail("CATALOG")
    catalog_stale = catalog_age > args.maximum_catalog_age_days
    if catalog_stale:
        diagnostics.append(diagnostic("CATALOG_STALE", "hygiene"))
    diagnostics.append(diagnostic("INTEGRATION"))
    status = "unavailable" if not snapshots else "partial" if catalog_stale or any(row["status"] != "current" for row in rows) else "ready"
    return {"schema": SCHEMA, "publication": "denied", "status": status, "observed_at": args.observed_at,
            "inputs": {"catalog_revision": plan["catalog_revision"], "catalog_metadata": catalog_metadata,
                       "catalog_public_sha256": base.digest(base.json_bytes(public_rows)),
                       "public_selection_sha256": base.digest(base.json_bytes(selection_evidence)),
                       "review_reference": plan["review_reference"], "maximum_age_seconds": args.maximum_age_seconds,
                       "maximum_last_known_age_seconds": args.maximum_last_known_age_seconds,
                       "maximum_catalog_age_days": args.maximum_catalog_age_days},
            "runtime": {**receipt, "pins": lock, "assembler_sha256": base.digest(Path(__file__).read_bytes()),
                        "normalizer_sha256": base.digest(Path(normalization.__file__).read_bytes()),
                        "shared_runtime_sha256": base.digest(Path(base.__file__).read_bytes())},
            "repositories": rows, "diagnostics": diagnostics, "fleet_snapshot_candidate": fleet,
            "candidate_sha256": base.digest(base.json_bytes(fleet)) if fleet else None}


def write_result(path: Path, result: dict, artifact_root: Path, catalog_root: Path,
                 runtime: Path, plan: Path) -> None:
    path = base.safe_path(path)
    if (path.name != OUTPUT_NAME or path.is_relative_to(base.safe_path(artifact_root))
            or path.is_relative_to(base.safe_path(catalog_root)) or (path.exists() and not path.is_file())):
        base.fail("PATH")
    if (path == base.safe_path(plan) or path.is_relative_to(base.safe_path(runtime))
            or path.is_relative_to(ROOT.parents[1])):
        base.fail("PATH")
    if not validator(REVIEW_PATH).is_valid(result):
        base.fail("INPUT")
    raw = base.json_bytes(result)
    if len(raw) > 64 * base.MAX_JSON:
        base.fail("INPUT")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = result.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("prepare", allow_abbrev=False)
    for owner in ("hygiene", "egolint", "observatory"):
        setup.add_argument("--" + owner, type=Path, required=True)
    setup.add_argument("--cargo", type=Path, default=Path("cargo"))
    setup.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("assemble", allow_abbrev=False)
    for name in ("runtime", "catalog-root", "artifact-root", "plan", "output"):
        command.add_argument("--" + name, type=Path, required=True)
    command.add_argument("--observed-at", required=True)
    command.add_argument("--maximum-age-seconds", type=int, default=86400)
    command.add_argument("--maximum-last-known-age-seconds", type=int, default=2678400)
    command.add_argument("--maximum-catalog-age-days", type=int, default=31)
    command.add_argument("--catalog-profile", choices=("legacy-review", "public-catalog-v1"), default="legacy-review")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "prepare":
            base.prepare(args, lock_path=LOCK_PATH, reproducible=True)
            return 0
        result = assemble(args)
        write_result(args.output, result, args.artifact_root, args.catalog_root, args.runtime, args.plan)
        print("Public fleet artifact retained for review; publication denied")
        return 0 if result["status"] == "ready" else 2
    except (base.CollectorError, OSError, ValueError, KeyError, TypeError, RecursionError):
        error = sys.exception()
        code = str(error) if isinstance(error, base.CollectorError) and str(error) in MESSAGES else "INPUT"
        if args.command == "assemble":
            try:
                write_result(args.output, {"schema": SCHEMA, "publication": "denied", "status": "denied",
                                          "diagnostics": [diagnostic(code)]}, args.artifact_root, args.catalog_root,
                             args.runtime, args.plan)
            except (base.CollectorError, OSError):
                pass
        print("Public fleet assembler: " + code, file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
