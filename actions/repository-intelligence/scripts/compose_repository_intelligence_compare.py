#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Compose admitted Compare evidence into the same completed native bundle.

This is called only by the trusted artifact intake, with its in-memory admitted
current pair and comparison. It does not accept replacement source receipts or
external render inputs, collect again, acquire a runtime, or deploy anything.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

SCRIPTS = Path(__file__).resolve().parent


def require(value):
    if not value:
        raise ValueError("Native Compare composition denied")


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    require(spec is not None and spec.loader is not None)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def digest(content):
    return hashlib.sha256(content).hexdigest()


def atomic(path, content):
    descriptor, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def compose(args, current, comparison, runtime_identity):
    """Replace only Compare and its manifest, preserving the native source proof."""
    if not args.intelligence_directory:
        return {}
    # Provider/action identity is checked before reading candidate files. The
    # action's own immutable ref must match the producer, including when the
    # original builder was called through a pinned reusable workflow.
    require(args.visibility == "public" and args.generator_repository == "egohygiene/relay"
        and isinstance(args.generator_ref, str) and re.fullmatch(r"[0-9a-f]{40}", args.generator_ref))
    transport = module("relay_compose_compare_transport", "repository_capture_artifact.py")
    source = module("relay_compose_compare_sources", "repository_sources_build_contract.py")
    root = transport.safe(args.repository_root)
    relative = Path(args.intelligence_directory)
    require(not relative.is_absolute() and bool(relative.parts)
        and not any(part in {".", ".."} for part in relative.parts)
        and relative.as_posix() == args.intelligence_directory)
    output = transport.safe(root / relative)
    original = transport.safe(args.source_directory)
    require(output.is_dir() and output.name == "intelligence"
        and output.is_relative_to(root) and output != root
        and original.is_relative_to(root) and original != root
        and not original.is_relative_to(output) and not output.is_relative_to(original))
    # Native source files and the generated subtree must stay outside canonical
    # source history. A renderer never gains permission to replace tracked files.
    tracked = subprocess.check_output(["git", "--no-optional-locks", "-c", "core.hooksPath=/dev/null",
        "-c", "core.fsmonitor=false", "-C", str(root), "ls-files", "--", str(output), str(original)],
        stderr=subprocess.DEVNULL)
    require(not tracked)
    _, provenance = source.read(output / "provenance.json")
    require(provenance.get("consumer") == {"repository": args.repository,
        "source_commit": args.source_commit, "visibility": "public"})
    generator = provenance["generator"]
    release = json.loads((SCRIPTS.parents[2] / "release.json").read_bytes())
    require(generator["repository"] == args.generator_repository
        and generator["source_commit"] == args.generator_ref and generator["immutable"] is True
        and generator["version"] == release["version"].removeprefix("v"))
    _, receipt = source.read(original / "receipt.json")
    source.validate(receipt, args.repository, args.source_commit)
    require(provenance.get("source_collection") == receipt and "adr_collection" not in provenance)
    for name in ("snapshot", "projection"):
        content, _value = source.read(original / (name + ".json"))
        require(digest(content) == receipt["candidate_digests"][name + "_sha256"]
            == current[name + "_input_sha256"])
    require(receipt["observed_at"] == provenance["generated_at"] == current["snapshot"]["observed_at"])
    profile = receipt.get("normalization_profile")
    if profile is None:
        require(args.normalization_profile == "legacy-adr"
            and runtime_identity["lock_sha256"] == digest((SCRIPTS.parent / "contracts/adr-collector.v1.lock.json").read_bytes()))
    else:
        require(args.normalization_profile == profile["profile"]
            and runtime_identity["lock_sha256"] == profile["runtime"]["lock_sha256"])
    validator = module("relay_compose_compare_validator", "validate_repository_intelligence_bundle.py")
    manifest = module("relay_compose_compare_manifest", "create_repository_intelligence_build_manifest.py")
    renderer = module("relay_compose_compare_renderer", "render_repository_intelligence_compare.py")
    _, before = source.read(output / manifest.BUILD_MANIFEST_NAME)
    validation = {"repository_root": root, "output_root": output, "repository": args.repository,
        "repository_visibility": "public", "source_commit": args.source_commit,
        "generator_version": generator["version"], "generator_source_ref": generator["source_ref"],
        "generator_source_commit": args.generator_ref, "generator_immutable": True,
        "source_epoch": before["source_epoch"]}
    validator.validate_bundle(**validation)
    _, summary = source.read(output / "summary.json")
    snapshot = renderer.site.validate_snapshot(current["snapshot"], args.repository, args.source_commit)
    if comparison is not None:
        renderer.validate_comparison(comparison, repository=args.repository,
            source_commit=args.source_commit, snapshot=snapshot)
    html = renderer.render_page(comparison=comparison, snapshot=snapshot, summary=summary,
        repository=args.repository, source_commit=args.source_commit).encode("utf-8")
    compare_path = output / "compare/index.html"
    manifest_path = output / manifest.BUILD_MANIFEST_NAME
    original_page, original_manifest = compare_path.read_bytes(), manifest_path.read_bytes()
    try:
        atomic(compare_path, html)
        after = manifest.build_manifest(output_root=output, repository=args.repository,
            consumer_revision=args.source_commit, generator_revision=args.generator_ref,
            generator_version=generator["version"], source_epoch=before["source_epoch"])
        # All other route, asset, provenance and source-receipt bytes are exact.
        def immutable(value):
            return [row for row in value["bundle"]["files"] if row["path"] != "compare/index.html"]
        require(immutable(before) == immutable(after) and before["enabled_routes"] == after["enabled_routes"])
        manifest.write_json(manifest_path, after)
        validator.validate_bundle(**validation)
    except BaseException:
        atomic(compare_path, original_page)
        atomic(manifest_path, original_manifest)
        raise
    return {"manifest-sha256": manifest.sha256_file(manifest_path),
        "bundle-digest": after["bundle"]["digest"], "composition-status": "refreshed"}
