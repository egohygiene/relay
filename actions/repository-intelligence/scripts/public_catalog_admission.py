#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Admit a selected public slice of Hygiene's exact reviewed projection.

The Git source supplies immutable owner bytes, never consumer executable code.
Public selection precedes identity, duplicate, schema and digest operations.
"""

from __future__ import annotations

from datetime import datetime, UTC
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "contracts/public-catalog-admission.v1.lock.json"
SCHEMA = "egohygiene.relay.public-catalog-admission/v1"
PUBLIC_ARTIFACT = ROOT / "contracts/public-repositories.hygiene-49639c1.json"
HASH = re.compile(r"[0-9a-f]{64}")


def require(condition):
    if not condition:
        raise ValueError("Public catalog admission is incompatible")


def module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    require(specification is not None and specification.loader is not None)
    result = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(result)
    return result


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def lock():
    return json.loads(LOCK_PATH.read_bytes())


def acquire(work):
    """Fetch only the exact reviewed public owner revision into a fresh bare Git.

    This stdlib-only transport neither installs dependencies nor executes owner
    or consumer files. load() performs the subsequent public source admission.
    """
    work = Path(work).absolute()
    require(".." not in work.parts and work.is_dir()
        and not any(path.is_symlink() for path in (work, *work.parents)))
    target = work / "public-catalog"
    require(not target.exists() and not target.is_symlink())
    environment = {"PATH": os.defpath, "LC_ALL": "C.UTF-8", "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull, "GIT_NO_REPLACE_OBJECTS": "1", "GIT_TERMINAL_PROMPT": "0"}
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy",
                "all_proxy", "no_proxy", "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE",
                "CURL_CA_BUNDLE", "GIT_SSL_CAINFO"):
        if key in os.environ:
            environment[key] = os.environ[key]
    pin = lock()
    commands = (["init", "--bare", str(target)],
        ["-C", str(target), "-c", "protocol.allow=never", "-c", "protocol.https.allow=always",
         "fetch", "--no-tags", "--depth=1", "https://github.com/" + pin["owner"] + ".git", pin["revision"]])
    try:
        for command in commands:
            with tempfile.TemporaryFile() as log:
                completed = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", *command],
                    cwd=work, env=environment, stdout=log, stderr=log, timeout=180, check=False)
                require(completed.returncode == 0 and log.tell() <= 32 * 1024 * 1024)
    except (OSError, subprocess.SubprocessError):
        raise ValueError("Public catalog acquisition is unavailable") from None
    return target


def validate_metadata(value, selected=None):
    """Check execution receipt structure; a digest alone cannot prove membership.

    Untrusted serialized rows still require the pinned owner public artifact.
    Only load() authenticates that source and selects canonical public members.
    """
    require(isinstance(value, dict) and set(value) == {"schema", "owner", "revision", "artifact_path",
        "artifact_sha256", "schema_sha256", "helper_sha256", "observed_at", "selected_sha256"})
    pin = lock()
    require(value["schema"] == SCHEMA and value["owner"] == pin["owner"]
        and value["revision"] == pin["revision"] and value["artifact_path"] == pin["artifact_path"]
        and value["artifact_sha256"] == pin["files"][pin["artifact_path"]]
        and value["schema_sha256"] == pin["files"][pin["schema_path"]]
        and value["helper_sha256"] == pin["files"][pin["helper_path"]])
    require(isinstance(value["observed_at"], str)
        and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value["observed_at"]))
    datetime.strptime(value["observed_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    require(isinstance(value["selected_sha256"], str) and HASH.fullmatch(value["selected_sha256"]))
    if selected is not None:
        require(value["selected_sha256"] == digest(encoded(selected)))
    return value


def public_document():
    """Load only the hash-authenticated byte mirror of the public artifact."""
    pin = lock()
    content = PUBLIC_ARTIFACT.read_bytes()
    require(digest(content) == pin["files"][pin["artifact_path"]])
    return json.loads(content)


def validate_rows(selected):
    """Authenticate sorted public rows before any caller hashes their content."""
    document = public_document()
    permitted = {row["full_name"]: row for row in document["repositories"]
                 if row.get("visibility") == "public"}
    require(isinstance(selected, list) and len(selected) <= 256)
    names = []
    for row in selected:
        require(isinstance(row, dict) and row.get("visibility") == "public")
        name = row.get("full_name")
        require(isinstance(name, str) and name in permitted
            and encoded(row) == encoded(permitted[name]))
        names.append(name)
    require(names == sorted(set(names)))
    return document


def validate_selection(selected, metadata):
    """Authenticate serialized public rows and metadata against exact owner bytes."""
    document = validate_rows(selected)
    require(isinstance(metadata, dict)
        and metadata.get("observed_at") == document["observed_at"])
    return validate_metadata(metadata, selected)


def validate_identities(identities, metadata):
    """Authenticate a compact explicit public selection and return its owner rows."""
    require(isinstance(identities, list) and len(identities) <= 256
        and all(isinstance(name, str) for name in identities) and identities == sorted(set(identities)))
    document = public_document()
    permitted = {row["full_name"]: row for row in document["repositories"] if row.get("visibility") == "public"}
    require(all(name in permitted for name in identities))
    rows = [permitted[name] for name in identities]
    validate_selection(rows, metadata)
    return rows


def load(catalog_root, requested=None):
    """Return (selected owner rows, public metadata), silently omitting exclusions.

    Unknown and historical-alias selectors do not create guessed identities.
    Passing no selector admits all explicitly public owner projection rows.
    """
    import jsonschema

    base = module("relay_public_catalog_git", ROOT / "scripts/collect_repository_roadmap.py")
    source_root = base.safe_path(Path(catalog_root))
    pin = lock()
    require(base.git(source_root, "rev-parse", pin["revision"] + "^{tree}").decode().strip() == pin["tree"])
    contents = {}
    for path, checksum in pin["files"].items():
        content = base.git_blob(source_root, pin["revision"], path, base.MAX_OUTPUT)
        require(digest(content) == checksum)
        contents[path] = content
    if requested is not None:
        require(isinstance(requested, (list, tuple, set)) and len(requested) <= 100000)
        requested = {value for value in requested if isinstance(value, str)}
    with tempfile.TemporaryDirectory(prefix="relay-public-catalog-owner-") as temporary:
        helper_path = Path(temporary) / "public_inventory.py"
        helper_path.write_bytes(contents[pin["helper_path"]])
        owner = module("relay_pinned_public_catalog", helper_path)
        # Use the owner's ambiguity-preserving parser. Exact source hashes
        # authenticate this public artifact without reading the mixed catalog.
        artifact = Path(temporary) / "public-repositories.json"
        artifact.write_bytes(contents[pin["artifact_path"]])
        document = owner.read(artifact)
        public = owner.selected_public_rows(document.get("repositories"))
        selected = [row for row in public if requested is None or row.get("full_name") in requested]
        admitted = {**document, "repositories": selected}
        schema = json.loads(contents[pin["schema_path"]])
        require(jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).is_valid(admitted)
            and document.get("schema") == pin["contract"])
        for row in selected:
            owner.plain(row)
            identity = owner.identity(row)
            require(row["name"] == identity["name"] and row["source_url"] == identity["source_url"])
        owner.uniqueness(selected)
        names = {row["name"] for row in selected}
        aliases = [alias for row in selected for alias in row["aliases"]]
        require(len(aliases) == len(set(aliases)) and not names.intersection(aliases))
        selected = json.loads(encoded(sorted(selected, key=lambda row: row["full_name"])))
        observed = document["observed_at"]
    metadata = {"schema": SCHEMA, "owner": pin["owner"], "revision": pin["revision"],
        "artifact_path": pin["artifact_path"], "artifact_sha256": pin["files"][pin["artifact_path"]],
        "schema_sha256": pin["files"][pin["schema_path"]], "helper_sha256": pin["files"][pin["helper_path"]],
        "observed_at": observed, "selected_sha256": digest(encoded(selected))}
    return selected, validate_metadata(metadata, selected)
