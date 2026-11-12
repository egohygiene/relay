#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT
"""Portable receipt binding, not an audit/model/policy implementation.

Consumers supply independently authenticated public admission and immutable
implementation hashes. Passing a receipt's own claims as those expectations is
not verification. Model semantics still require the existing Observatory owner
validator; this module never re-normalizes, retimes or ratifies a source.
"""

from __future__ import annotations

from datetime import datetime, UTC
import hashlib
import json
import re

SCHEMA = "egohygiene.relay.typed-review-feed-receipt/v1"
PLAN_SCHEMA = "egohygiene.relay.typed-review-plan/v1"
VERSION = "1.0.0-alpha.1"
OBSERVATORY = "7b857de2424f90de519fbc2e24332a7c0a89991b"
AETHER = "74490907bf3979ac45594d97fb1bb5fa7071346d"
HYGIENE = "49639c1845cdfd08fbd5a768261a8b3cf515f80f"
GOVERNANCE = "d11580e9a9c5d78b9a5d21474deaa612712a0fb9"
CATALOG = "af9c7186ded0bb57b18741eaa5905314b96d6adb03736946c868e0fc4aa50b26"
HASH = re.compile(r"[a-f0-9]{64}")
SHA = re.compile(r"[a-f0-9]{40}")
MAX_PLAN = 64 * 1024
MAX_REPORT = 2 * 1024 * 1024
MAX_MODEL = 4 * 1024 * 1024
MAX_RECEIPT = 256 * 1024
MAX_REPORTS = 64
MODELS = ("repository-audits", "repository-sanity", "fleet-audits", "fleet-sanity")
IMPLEMENTATION = {"producer_sha256", "contract_sha256", "lock_sha256", "receipt_schema_sha256", "plan_schema_sha256"}
QUALIFICATION = {"normalization": "pinned-observatory-owner-only", "auditor_execution": "not-performed",
    "model_execution": "not-performed", "human_verification": "unavailable-no-trusted-context",
    "source_profile": "immutable-git-sidecars", "publication": "not-authorized"}


class FeedError(ValueError):
    """Closed error code; no rejected payload or path is included."""


def require(condition, code="INPUT"):
    if not condition:
        raise FeedError(code)


def closed(value, keys):
    require(type(value) is dict and set(value) == set(keys))
    return value


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def digest(content):
    return hashlib.sha256(content).hexdigest()


def unique(entries):
    result = {}
    for key, value in entries:
        require(key not in result)
        result[key] = value
    return result


def parse(content, limit=MAX_RECEIPT):
    require(type(content) is bytes and len(content) <= limit)
    value = content.decode("utf-8", errors="strict")
    require(not value.startswith("\ufeff") and "\x00" not in value)
    result = json.loads(value, object_pairs_hook=unique, parse_constant=lambda unused: require(False))
    # JSON escape sequences can introduce lone surrogate code points.
    encoded(result)
    return result


def instant(value):
    require(type(value) is str and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value))
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def relative(value):
    require(type(value) is str and 0 < len(value) <= 240
        and re.fullmatch(r"[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*", value)
        and all(part not in {".", "..", ".git"} for part in value.split("/")), "PATH")
    return value


def hexadecimal(value, pattern=HASH):
    require(type(value) is str and pattern.fullmatch(value))
    return value


def validate_plan(value, repository):
    closed(value, {"schema", "contract_version", "visibility", "repository", "audits", "sanity"})
    require(value["schema"] == PLAN_SCHEMA and value["contract_version"] == VERSION
        and value["visibility"] == "public" and value["repository"] == repository)
    for domain in ("audits", "sanity"):
        require(type(value[domain]) is list and len(value[domain]) <= MAX_REPORTS)
        paths = []
        for item in value[domain]:
            closed(item, {"path", "sha256"})
            paths.append(relative(item["path"]))
            require(item["path"].endswith(".json"))
            hexadecimal(item["sha256"])
        require(paths == sorted(set(paths)))
    require(not ({row["path"] for row in value["audits"]} & {row["path"] for row in value["sanity"]}))
    return value


def owner_profile(lock_sha256):
    hexadecimal(lock_sha256)
    return {"observatory": {"repository": "egohygiene/observatory", "revision": OBSERVATORY, "lock_sha256": lock_sha256},
        "aether": {"repository": "egohygiene/aether", "revision": AETHER},
        "catalog": {"repository": "egohygiene/hygiene", "revision": HYGIENE, "artifact_sha256": CATALOG},
        "governance": {"repository": "egohygiene/hygiene", "revision": GOVERNANCE, "policy_status": "proposed"}}


def validate_receipt(value, *, admission, expected_implementation, repository, represented_commit=None, as_of=None):
    """Validate serialized binding using independent trusted expectations.

    `admission` must come from the exact owner public catalog for the selected
    repository. `expected_implementation` must be computed from the five pinned
    Relay source resources, never copied out of this receipt.
    """
    require(type(repository) is str)
    if type(value) is bytes:
        value = parse(value)
    closed(value, {"schema", "contract_version", "visibility", "status", "publication", "source", "admission",
        "plan", "reports", "models", "owners", "implementation", "qualification"})
    require(value["schema"] == SCHEMA and value["contract_version"] == VERSION and value["visibility"] == "public"
        and value["status"] == "normalized" and value["publication"] == "review-only")
    source = closed(value["source"], {"repository", "represented_commit", "commit_at", "as_of"})
    require(type(source["repository"]) is str and re.fullmatch(r"egohygiene/(?:\.github|[a-z0-9][a-z0-9.-]*)", source["repository"]))
    hexadecimal(source["represented_commit"], SHA)
    require(instant(source["commit_at"]) <= instant(source["as_of"]))
    for expected, field in ((repository, "repository"), (represented_commit, "represented_commit"), (as_of, "as_of")):
        require(expected is None or expected == source[field])
    closed(admission, {"schema", "owner", "revision", "artifact_path", "artifact_sha256", "schema_sha256",
        "helper_sha256", "observed_at", "selected_sha256"})
    require(admission["schema"] == "egohygiene.relay.public-catalog-admission/v1"
        and admission["owner"] == "egohygiene/hygiene" and admission["revision"] == HYGIENE
        and admission["artifact_path"] == "catalog/public-repositories.json" and admission["artifact_sha256"] == CATALOG)
    require(encoded(value["admission"]) == encoded(admission))
    closed(expected_implementation, IMPLEMENTATION)
    for item in expected_implementation.values():
        hexadecimal(item)
    require(encoded(value["implementation"]) == encoded(expected_implementation)
        and value["owners"] == owner_profile(expected_implementation["lock_sha256"])
        and value["qualification"] == QUALIFICATION)
    plan = closed(value["plan"], {"path", "sha256", "state"})
    relative(plan["path"])
    require(plan["state"] in {"present", "missing"})
    if plan["state"] == "present":
        hexadecimal(plan["sha256"])
    else:
        require(plan["sha256"] is None)
    require(type(value["reports"]) is list and len(value["reports"]) <= MAX_REPORTS * 2)
    selected = []
    for report in value["reports"]:
        closed(report, {"domain", "path", "expected_sha256", "state", "sha256"})
        require(report["domain"] in {"audits", "sanity"} and report["state"] in {"provided", "missing"})
        relative(report["path"])
        hexadecimal(report["expected_sha256"])
        if report["state"] == "provided":
            hexadecimal(report["sha256"])
            require(report["sha256"] == report["expected_sha256"])
        else:
            require(report["sha256"] is None)
        selected.append((report["domain"], report["path"]))
    require(selected == sorted(set(selected)) and (plan["state"] == "present" or not selected))
    closed(value["models"], MODELS)
    for key, item in value["models"].items():
        closed(item, {"path", "sha256", "size_bytes", "schema", "contract_version", "repository", "represented_commit",
            "as_of", "evidence_state", "canonical_digest"})
        require(item["path"] == key + ".json" and item["schema"] == "egohygiene.observatory." + key + "/v1"
            and item["contract_version"] == VERSION and item["repository"] == source["repository"]
            and item["represented_commit"] == source["represented_commit"] and item["as_of"] == source["as_of"]
            and item["evidence_state"] in {"supplied", "unavailable"}
            and type(item["size_bytes"]) is int and 0 < item["size_bytes"] <= MAX_MODEL)
        hexadecimal(item["sha256"]); hexadecimal(item["canonical_digest"])
        domain = key.rsplit("-", 1)[1]
        require(item["evidence_state"] == ("supplied" if any(row["domain"] == domain and row["state"] == "provided"
            for row in value["reports"]) else "unavailable"))
    return value


def validate_model_bytes(value, key, content):
    """Check retained byte/source binding; owner semantic validation stays external."""
    require(key in MODELS)
    item, source = value["models"][key], value["source"]
    require(type(content) is bytes and len(content) == item["size_bytes"] and digest(content) == item["sha256"])
    model = parse(content, MAX_MODEL)
    require(type(model) is dict and model.get("visibility") == "public" and model.get("schema") == item["schema"]
        and model.get("contract_version") == VERSION and model.get("as_of") == source["as_of"]
        and model.get("digest") == item["canonical_digest"])
    if key.startswith("fleet-"):
        require(type(model.get("repositories")) is list and len(model["repositories"]) == 1)
        entry = model["repositories"][0]
    else:
        entry = model
    require(type(entry) is dict and type(entry.get("repository")) is dict
        and entry["repository"].get("full_name") == source["repository"]
        and entry.get("represented_commit") == source["represented_commit"] and entry.get("as_of") == source["as_of"]
        and type(entry.get("source_owner")) is dict and entry["source_owner"].get("revision") == AETHER
        and type(entry.get("evidence")) is dict and entry["evidence"].get("state") == item["evidence_state"])
    return model
