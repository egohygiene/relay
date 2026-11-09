#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Collect canonical roadmap Git objects through the supported alpha.2 runtime.

The historical review-only collector and its lock remain unchanged. This adapter
reuses its bounded extraction, with the same owner set as native ADR builds.
"""

from __future__ import annotations

import argparse
from datetime import datetime, UTC
from pathlib import Path

from importlib.util import spec_from_file_location, module_from_spec


def module(name, filename):
    spec = spec_from_file_location(name, Path(__file__).with_name(filename))
    result = module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


adrs = module("relay_roadmap_source_adrs", "collect_repository_adrs.py")
base = adrs.base
DOMAINS = adrs.DOMAINS


def collect(args):
    if base.safe_path(args.runtime).is_relative_to(base.safe_path(args.repository_root)):
        base.fail("PATH")
    if (args.visibility != "public" or not base.REPOSITORY.fullmatch(args.repository)
            or not base.SHA.fullmatch(args.source_commit)):
        base.fail("VISIBILITY")
    observed = base.utc(args.observed_at)
    lock, runtime_receipt = base.runtime_files(args.runtime, lock_path=adrs.LOCK_PATH)
    raw = base.git_blob(args.repository_root, args.source_commit, "ROADMAP.md")
    text = raw.decode("utf-8")
    declared = base.manifest(text)
    if (declared.get("repository") != args.repository or declared.get("visibility") != "public"
            or declared.get("publication") not in {"canonical", "composed", "central"}
            or base.SECRET.search(text)):
        base.fail("VISIBILITY")
    if not 1 <= args.maximum_intent_age_days <= 3650:
        base.fail("INPUT")
    updated = datetime.strptime(declared["updated"], "%Y-%m-%d").replace(tzinfo=UTC)
    if updated > observed:
        base.fail("INPUT")
    freshness = "stale" if (observed - updated).days > args.maximum_intent_age_days else "current"
    commit = base.git(args.repository_root, "cat-file", "commit", args.source_commit, limit=base.MAX_SOURCE)
    report = base.ego_validate(args.runtime, args.repository, args.source_commit, raw, commit)
    if report["status"] not in {"valid", "incomplete"} or len(report["diagnostics"]) > base.MAX_RECORDS:
        base.fail("EXTRACTION")
    steps = base.extract(text)
    # Roadmap issue declarations are references, never a provider inventory. The
    # dedicated Work collector owns issue/PR state. Do not create placeholder
    # entities or infer closure from checked canonical exit criteria.
    references = []
    for step in steps:
        step["issue_numbers"] = []
        for reference in step["issues"]:
            ref = str(reference)
            match = base.re.fullmatch(r"#?([1-9][0-9]{0,9})", ref) or base.re.fullmatch(
                r"https://github\.com/" + base.re.escape(args.repository) + r"/issues/([1-9][0-9]{0,9})", ref)
            if not match:
                base.fail("PROVIDER")
            references.append({"step": step["id"], "url": f"https://github.com/{args.repository}/issues/{int(match[1])}"})
    projection = base.project(args.repository, args.source_commit, args.observed_at, steps, freshness, {})
    references_by_step = {}
    for reference in references:
        references_by_step.setdefault(reference["step"], set()).add(reference["url"])
    for entity in projection["entities"]:
        if entity["kind"] == "roadmap_step":
            entity["attributes"]["issue_references"] = sorted(references_by_step.get(entity["key"], set()))
    projection["contract_version"] = "1.0.0-alpha.2"
    projection["generator"]["name"] = "egohygiene/relay:roadmap-source-collector"
    projection["collection_coverage"] = {domain: {"collection": "uncollected", "freshness": "unknown",
        "reason": "not_requested", "observed_at": None} for domain in DOMAINS}
    # A new capture is current even when its canonical intent is visibly stale.
    projection["collection_coverage"]["roadmap"] = {"collection": "observed", "freshness": "current",
        "reason": "complete", "observed_at": args.observed_at}
    snapshot, validation = adrs.normalize(args.runtime, projection)
    if snapshot is None or validation != {"hygiene": "valid", "coverage": "valid", "observatory": "normalized"}:
        base.fail("HYGIENE")
    return {"projection": projection, "snapshot": snapshot,
        "receipt": {"repository": args.repository, "source_commit": args.source_commit,
            "observed_at": args.observed_at, "roadmap_sha256": base.digest(raw),
            "maximum_intent_age_days": args.maximum_intent_age_days, "intent_freshness": freshness,
            "reference_count": len(references), "runtime": {**runtime_receipt, "pins": lock},
            "validation": {**validation, "egolint": report["status"], "diagnostics_truncated": False},
            "coverage": projection["collection_coverage"],
            "projection_sha256": base.digest(base.json_bytes(projection)),
            "snapshot_sha256": base.digest(base.json_bytes(snapshot))}}


def parser():
    value = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ("runtime", "repository-root", "output"):
        value.add_argument("--" + name, required=True, type=Path)
    for name in ("repository", "visibility", "source-commit", "observed-at"):
        value.add_argument("--" + name, required=True)
    value.add_argument("--maximum-intent-age-days", type=int, default=30)
    return value


def main():
    args = parser().parse_args()
    try:
        destination = base.safe_path(args.output)
        if destination.exists() or destination.is_relative_to(base.safe_path(args.repository_root)):
            base.fail("PATH")
        result = collect(args)
        content = base.json_bytes({"schema": "egohygiene.relay.roadmap-source-review/v1",
            "publication": "denied", **result})
        if len(content) > base.MAX_OUTPUT:
            base.fail("INPUT")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as handle:
            handle.write(content)
        return 0
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, RecursionError, base.yaml.YAMLError):
        print("Roadmap source: collection or owner validation denied")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
