#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Select the exact opt-in Observatory Search normalization runtime.

This profile changes final owner normalization only. Canonical collectors and
their existing runtime receipts keep their original immutable selections.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
LOCK_PATH = ROOT / "contracts/search-attribution-normalizer.v1.lock.json"
SCHEMA = "egohygiene.relay.search-normalization-profile/v1"
PROFILE = "search-attribution-v1"
SHA256 = re.compile(r"[0-9a-f]{64}")
FEATURE_KWARGS = {"search_attribution": True}
IMPLEMENTATION = (
    "repository_search_normalization.py",
    "collect_repository_adrs.py",
    "collect_repository_roadmap.py",
    "prepare_repository_adr_build.py",
)


def require(condition):
    if not condition:
        raise ValueError("Search normalization profile is incompatible")


def module(name, filename):
    specification = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    require(specification is not None and specification.loader is not None)
    result = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(result)
    return result


def digest(content):
    return hashlib.sha256(content).hexdigest()


def implementation():
    return {name: digest((SCRIPTS / name).read_bytes()) for name in IMPLEMENTATION}


def validate_metadata(value):
    """Validate public execution evidence without importing a caller runtime."""
    require(isinstance(value, dict) and set(value) == {
        "schema", "profile", "feature_kwargs", "runtime", "implementation"})
    require(value["schema"] == SCHEMA and value["profile"] == PROFILE)
    features = value["feature_kwargs"]
    require(isinstance(features, dict) and set(features) == {"search_attribution"}
        and type(features["search_attribution"]) is bool and features["search_attribution"])
    runtime = value["runtime"]
    require(isinstance(runtime, dict) and set(runtime) == {"lock_sha256", "egolint_sha256", "pins"})
    lock_bytes = LOCK_PATH.read_bytes()
    require(isinstance(runtime["pins"], dict)
        and json.dumps(runtime["pins"], sort_keys=True, separators=(",", ":"), allow_nan=False)
            == json.dumps(json.loads(lock_bytes), sort_keys=True, separators=(",", ":"), allow_nan=False)
        and runtime["lock_sha256"] == digest(lock_bytes)
        and isinstance(runtime["egolint_sha256"], str) and SHA256.fullmatch(runtime["egolint_sha256"]))
    require(value["implementation"] == implementation())
    return value


def metadata(runtime):
    """Bind the trusted executable, exact owner set, feature option and adapter."""
    native = module("relay_search_native_metadata", "collect_repository_adrs.py")
    root = native.base.safe_path(Path(runtime))
    lock, receipt = native.base.runtime_files(root, lock_path=LOCK_PATH)
    value = {"schema": SCHEMA, "profile": PROFILE, "feature_kwargs": dict(FEATURE_KWARGS),
        "runtime": {**receipt, "pins": lock}, "implementation": implementation()}
    return validate_metadata(value)


def public_projection(projection):
    # Reject excluded topology before hashing or normalizing any declared text.
    # Private/local profiles require their own separately reviewed authority.
    require(isinstance(projection, dict) and projection.get("visibility") == "public"
        and projection.get("redactions") == [] and projection.get("extensions") == {})
    for name in ("sources", "entities", "events"):
        records = projection.get(name)
        require(isinstance(records, list) and all(isinstance(record, dict)
            and record.get("visibility") == "public" for record in records))


def normalize(runtime, projection):
    """Use the existing native validators and the selected owner feature API."""
    public_projection(projection)
    metadata(runtime)
    native = module("relay_search_native_normalization", "collect_repository_adrs.py")
    return native.normalize(Path(runtime), projection, search_attribution=True)


def acquire(work):
    """Acquire only this trusted profile through the existing isolated preparer."""
    acquisition = module("relay_search_runtime_acquisition", "prepare_repository_adr_build.py")
    return acquisition.acquire(Path(work), normalization_profile=PROFILE)


def upgrade(legacy_runtime, work):
    """Reuse a verified legacy executable and fetch only the new owner bytes.

    The caller supplies a fresh trusted scratch directory outside any checkout.
    No legacy file is changed, and no Rust toolchain or Python environment is
    rebuilt. An incompatible typed runtime must use the separate acquire path.
    """
    native = module("relay_search_upgrade_native", "collect_repository_adrs.py")
    base = native.base
    original = base.safe_path(Path(legacy_runtime))
    work = base.safe_path(Path(work))
    require(not work.is_relative_to(original) and not original.is_relative_to(work)
        and not any((parent / ".git").exists() for parent in (work, *work.parents)))
    require(not work.exists() or work.is_dir() and not any(work.iterdir()))
    old_lock, old_receipt = base.runtime_files(original, lock_path=native.LOCK_PATH)
    new_lock = base.load_json(base.read_file(LOCK_PATH))
    require(set(new_lock["sources"]) == set(old_lock["sources"]))
    for name, pin in new_lock["sources"].items():
        if name != "observatory":
            require(pin == old_lock["sources"][name])
    owner = new_lock["sources"]["observatory"]
    require(owner["repository"] == "egohygiene/observatory"
        and re.fullmatch(r"[0-9a-f]{40}", owner["revision"])
        and re.fullmatch(r"[0-9a-f]{40}", owner["tree"]))
    work.mkdir(parents=True, exist_ok=True)
    destination = work / "runtime"
    acquisition = module("relay_search_upgrade_acquisition", "prepare_repository_adr_build.py")
    environment = base.environment()
    # Preserve managed routing and CA trust without inheriting Git credentials,
    # consumer configuration, Python hooks or executable source from a capture.
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy",
                "all_proxy", "no_proxy", "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE",
                "CURL_CA_BUNDLE", "GIT_SSL_CAINFO"):
        if key in os.environ:
            environment[key] = os.environ[key]
    with tempfile.TemporaryDirectory(prefix="search-profile-upgrade-", dir=work) as temporary:
        stage = Path(temporary) / "runtime"
        stage.mkdir(mode=0o700)
        for name, pin in new_lock["sources"].items():
            if name == "observatory":
                continue
            for relative, expected in pin["files"].items():
                relative = native.relative(relative)
                content = base.read_file(original / name / relative, base.MAX_OUTPUT)
                require(digest(content) == expected)
                target = stage / name / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
        executable = base.read_file(original / "egolint-bin", 128 * base.MAX_JSON)
        require(digest(executable) == old_receipt["egolint_sha256"])
        (stage / "egolint-bin").write_bytes(executable)
        (stage / "egolint-bin").chmod(0o700)
        repository = Path(temporary) / "observatory.git"
        command = ["git", "--no-optional-locks", "-c", "core.hooksPath=/dev/null",
                   "-c", "core.fsmonitor=false", "-c", "protocol.allow=never",
                   "-c", "protocol.https.allow=always"]
        acquisition.execute([*command, "init", "--bare", str(repository)], work, environment)
        acquisition.execute([*command, "-C", str(repository), "fetch", "--no-tags", "--depth=1",
            "https://github.com/egohygiene/observatory.git", owner["revision"]], work, environment)
        require(base.git(repository, "rev-parse", owner["revision"] + "^{tree}").decode().strip() == owner["tree"])
        for relative, expected in owner["files"].items():
            relative = native.relative(relative)
            content = base.git_blob(repository, owner["revision"], relative, base.MAX_OUTPUT)
            require(digest(content) == expected)
            target = stage / "observatory" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        receipt = {"lock_sha256": digest(LOCK_PATH.read_bytes()),
                   "egolint_sha256": old_receipt["egolint_sha256"]}
        (stage / "runtime.json").write_bytes(base.json_bytes(receipt))
        base.runtime_files(stage, lock_path=LOCK_PATH)
        require(not destination.exists())
        stage.rename(destination)
    return destination


def retention_adapter():
    """Reuse retention/CAS with this exact normalizer in an independent module.

    The legacy module and lock remain unchanged. Exact re-normalization requires
    an attributed original projection/snapshot pair on both sides, so a legacy
    pair cannot silently cross this profile boundary.
    """
    result = module("relay_search_profile_retention", "retain_repository_intelligence_snapshots.py")
    result.adr = SimpleNamespace(LOCK_PATH=LOCK_PATH, normalize=normalize, __file__=__file__)
    return result


class Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise ValueError("Search normalization input denied")


def parser():
    value = Parser(description=__doc__, allow_abbrev=False)
    commands = value.add_subparsers(dest="command", required=True, parser_class=Parser)
    setup = commands.add_parser("prepare", allow_abbrev=False)
    for owner in ("hygiene", "egolint", "observatory"):
        setup.add_argument("--" + owner, type=Path, required=True)
    setup.add_argument("--cargo", type=Path, default=Path("cargo"))
    setup.add_argument("--output", type=Path, required=True)
    return value


def main(argv=None):
    try:
        args = parser().parse_args(argv)
        native = module("relay_search_native_preparation", "collect_repository_adrs.py")
        native.base.prepare(args, lock_path=LOCK_PATH, reproducible=True)
        print("Search normalization runtime prepared")
        return 0
    except Exception:
        print("Search normalization runtime preparation denied", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
