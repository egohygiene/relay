"""Closed public repository-conformance contract and standalone owner validator.

The pinned public artifact authenticates membership; a self-asserted subset or
digest does not. This module uses only the standard library so renderers can
consume its exact owner bytes without owning assessment or admission rules.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

SCHEMA = "egohygiene.observatory.repository-conformance/v1"
VERSION = "1.0.0-alpha.1"
HYGIENE_REVISION = "49639c1845cdfd08fbd5a768261a8b3cf515f80f"
CATALOG_SHA256 = "af9c7186ded0bb57b18741eaa5905314b96d6adb03736946c868e0fc4aa50b26"
CATALOG_SCHEMA_SHA256 = "eeb88b6a99de987500b946bd71c987e1fb7d0bd7350f466885c11ac7603c96d8"
CATALOG_HELPER_SHA256 = "fd3bb2099f2b9040502f19a8e582e4c4100653bd6cf2ea640cc36338dcfc4273"
ADMISSION_SCHEMA = "egohygiene.relay.public-catalog-admission/v1"
MAX_BYTES = 4 * 1024 * 1024
MAX_CHECKS = 4096
STATUSES = ("pass", "fail", "partial", "unknown", "blocked", "not_applicable", "stale")
DOMAINS = ("lifecycle", "foundation", "identity", "architecture", "automation", "security",
           "documentation", "releases", "sites", "migration", "dependencies")
SENSITIVE = re.compile(r"(?:github_pat_|gh[pousr]_|(?:token|password|secret)\s*[:=]|[\w.+-]+@[\w.-]+\.[a-z]{2,}|/(?:home|Users|workspace|tmp)/|[A-Za-z]:\\|\\\\)", re.I)
SHA = re.compile(r"[0-9a-f]{40}")
HASH = re.compile(r"[0-9a-f]{64}")
REPOSITORY = re.compile(r"egohygiene/(?:\.github|[a-z0-9][a-z0-9.-]*)")


class ConformanceError(ValueError):
    """Closed diagnostic; never includes rejected identities or input text."""


def require(condition):
    if not condition:
        raise ConformanceError("Public repository conformance input is incompatible")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def selected_digest(rows):
    # Match Hygiene's public_inventory.encoded rather than inventing a second
    # public-admission identity format.
    content = json.dumps(sorted(rows, key=lambda row: row["full_name"]), indent=2,
                         sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    return hashlib.sha256(content.encode()).hexdigest()


class ParsedObject(dict):
    def __init__(self):
        super().__init__()
        self.duplicate_keys = set()


def _pairs(items):
    value = ParsedObject()
    for key, item in items:
        if key in value:
            value.duplicate_keys.add(key)
        value[key] = item
    return value


def parse(content):
    require(isinstance(content, bytes) and len(content) <= MAX_BYTES)
    try:
        return json.loads(content, object_pairs_hook=_pairs,
                          parse_constant=lambda _: require(False))
    except (ValueError, UnicodeError, RecursionError):
        raise ConformanceError("Public repository conformance JSON is incompatible") from None


def plain(value):
    require(isinstance(value, dict) and not getattr(value, "duplicate_keys", set()))
    return value


def closed(value, keys):
    require(set(plain(value)) == set(keys))
    return value


def unambiguous(value):
    """Reject nested duplicate keys only after the caller has admitted visibility."""
    if isinstance(value, dict):
        plain(value)
        for item in value.values():
            unambiguous(item)
    elif isinstance(value, list):
        for item in value:
            unambiguous(item)


def text(value, maximum=2048):
    require(isinstance(value, str) and 0 < len(value) <= maximum
            and not any(ord(c) < 32 or ord(c) == 127 or 0xD800 <= ord(c) <= 0xDFFF for c in value)
            and not SENSITIVE.search(value))
    return value


def instant(value):
    require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value))
    try:
        result = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        raise ConformanceError("Public repository conformance timestamp is incompatible") from None
    require(result.strftime("%Y-%m-%dT%H:%M:%SZ") == value)
    return result


def _read(path):
    path = Path(path).absolute()
    require(".." not in path.parts and not any(item.is_symlink() for item in (path, *path.parents))
            and path.is_file() and path.stat().st_size <= MAX_BYTES)
    try:
        content = path.read_bytes()
    except OSError:
        raise ConformanceError("Public conformance source is unavailable") from None
    require(len(content) <= MAX_BYTES)
    return content


def admission(repository, *, admission_root):
    """Authenticate one canonical identity against the exact reviewed PUBLIC artifact."""
    require(isinstance(repository, str) and REPOSITORY.fullmatch(repository))
    content = _read(Path(admission_root) / "hygiene.public-repositories.v1.json")
    require(hashlib.sha256(content).hexdigest() == CATALOG_SHA256)
    document = plain(parse(content))
    require(document.get("schema") == "egohygiene.repository-public-catalog/v1"
            and document.get("organization") == "egohygiene")
    rows = [item for item in document["repositories"]
            if isinstance(item, dict) and item.get("visibility") == "public"]
    selected = [item for item in rows if item["full_name"] == repository]
    require(len(selected) == 1)
    row = selected[0]
    metadata = {"schema": ADMISSION_SCHEMA, "owner": "egohygiene/hygiene", "revision": HYGIENE_REVISION,
        "artifact_path": "catalog/public-repositories.json", "artifact_sha256": CATALOG_SHA256,
        "schema_sha256": CATALOG_SCHEMA_SHA256, "helper_sha256": CATALOG_HELPER_SHA256,
        "observed_at": document["observed_at"], "selected_sha256": selected_digest(selected)}
    instant(metadata["observed_at"])
    return row, metadata, frozenset(item["full_name"] for item in rows)


def url(value, allowed):
    value = text(value)
    try:
        parsed = urlsplit(value)
        require(parsed.scheme == "https" and parsed.hostname is not None and parsed.username is None
                and parsed.password is None and parsed.port in (None, 443) and not parsed.query)
    except ValueError:
        raise ConformanceError("Public conformance URL is incompatible") from None
    if parsed.hostname.lower() in {"github.com", "api.github.com", "raw.githubusercontent.com"}:
        # Browser/server path normalization must not escape an admitted prefix.
        # This bounded profile uses plain canonical GitHub paths only.
        require("%" not in parsed.path and "\\" not in parsed.path
                and not any(part in (".", "..") for part in parsed.path.split("/")))
        parts = parsed.path.strip("/").split("/")
        if parsed.hostname.lower() == "api.github.com":
            require(len(parts) >= 3 and parts[0] == "repos")
            parts = parts[1:]
        require(len(parts) >= 2 and "/".join(parts[:2]) in allowed)
    return value


def rollup(checks):
    """The existing health._rollup conformance rule, fixed for this owner version."""
    relevant = [item for item in checks if "conformance" in item["assesses"] and item["severity"] == "required"]
    counts = Counter(item["status"] for item in relevant)
    cases = (("fail", "non_conformant", "at least one current required check failed"),
             ("blocked", "blocked", "at least one current required check was blocked"),
             ("stale", "stale", "at least one required check is stale"),
             ("unknown", "unknown", "at least one required check is unknown"),
             ("partial", "partial", "at least one required check has partial coverage"),
             ("pass", "conformant", "all applicable required checks passed with current evidence"))
    status, reason = ("not_applicable", "every required check is explicitly not applicable") if relevant else ("unknown", "no required evidence assesses this dimension")
    for state, candidate, explanation in cases:
        if counts[state]:
            status, reason = candidate, explanation
            break
    return {"status": status, "reason": reason,
        "rule": "required checks only; precedence is fail, blocked, stale, unknown, partial, pass, not_applicable; no numeric score",
        "counts": {state: counts[state] for state in STATUSES},
        "check_ids": sorted(item["key"] for item in relevant)}


def validate(value, *, admission_root):
    """Validate the complete owner model without executing a validator or inferring policy."""
    require(isinstance(value, dict) and value.get("visibility") == "public")
    unambiguous(value)
    closed(value, {"schema", "contract_version", "visibility", "repository", "represented_commit", "as_of",
                   "admission", "scope", "assessment", "checks", "evidence"})
    require(value["schema"] == SCHEMA and value["contract_version"] == VERSION and value["visibility"] == "public")
    repository = closed(value["repository"], {"full_name", "repository_id", "visibility", "source_url"})
    row, metadata, allowed = admission(repository.get("full_name"), admission_root=admission_root)
    require(type(repository["repository_id"]) is int and repository == {name: row[name] for name in repository})
    require(value["admission"] == metadata and isinstance(value["represented_commit"], str)
            and SHA.fullmatch(value["represented_commit"]))
    as_of = instant(value["as_of"])
    require(value["scope"] == {"contracts": "supplied-conformance-assessments-only",
        "applicability": "unknown", "contract_inventory": "unknown"})
    require(isinstance(value["checks"], list) and len(value["checks"]) <= MAX_CHECKS)
    identities = []
    observations = set()
    for item in value["checks"]:
        closed(item, {"id", "title", "domain", "status", "severity", "assesses", "contract", "evidence",
                      "key", "reported_status", "freshness", "observation", "revision_status"})
        text(item["id"], 256); text(item["key"], 512); text(item["title"])
        require(item["domain"] in DOMAINS and item["severity"] in ("required", "advisory")
                and item["reported_status"] in STATUSES[:-1])
        require(isinstance(item["assesses"], list) and 1 <= len(item["assesses"]) <= 2
                and all(isinstance(assessment, str) for assessment in item["assesses"])
                and len(set(item["assesses"])) == len(item["assesses"])
                and "conformance" in item["assesses"]
                and all(assessment in ("conformance", "maturity") for assessment in item["assesses"]))
        contract = closed(item["contract"], {"id", "version", "url"})
        text(contract["id"], 256); text(contract["version"], 256); url(contract["url"], allowed)
        require(isinstance(item["evidence"], list) and 1 <= len(item["evidence"]) <= 32)
        for link in item["evidence"]:
            url(link, allowed)
        require(item["evidence"] == sorted(set(item["evidence"])))
        observation = closed(item["observation"], {"observed_at", "valid_until", "represented_commit", "producer", "source"})
        observed, expires = instant(observation["observed_at"]), instant(observation["valid_until"])
        require(observed <= as_of and expires >= observed and isinstance(observation["represented_commit"], str)
                and SHA.fullmatch(observation["represented_commit"]))
        producer = closed(observation["producer"], {"name", "version", "url"})
        text(producer["name"], 128); text(producer["version"], 256); url(producer["url"], allowed)
        source = closed(observation["source"], {"kind", "url", "sha256"})
        text(source["kind"], 128); url(source["url"], allowed)
        require(source["sha256"] is None or isinstance(source["sha256"], str) and HASH.fullmatch(source["sha256"]))
        require(item["key"] == producer["name"] + ":" + item["id"])
        fresh = "stale" if expires < as_of else "current"
        require(item["freshness"] == fresh and item["status"] == ("stale" if fresh == "stale" else item["reported_status"]))
        require(item["revision_status"] == ("matched" if observation["represented_commit"] == value["represented_commit"] else "different"))
        identities.append(item["key"])
        observations.add(digest(observation))
    require(identities == sorted(set(identities)))
    current = [item for item in value["checks"] if item["revision_status"] == "matched"]
    require(canonical(value["assessment"]) == canonical(rollup(current)))
    require(canonical(value["evidence"]) == canonical({"state": "supplied" if value["checks"] else "unavailable",
        "record_count": len(observations), "checks_sha256": digest(value["checks"]),
        "current_check_count": len(current), "other_revision_check_count": len(value["checks"]) - len(current)}))
    return value
