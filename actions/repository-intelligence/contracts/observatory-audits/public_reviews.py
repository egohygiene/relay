"""Standard-library transport/admission shared by separate public review models.

This is not an audit, applicability, assessment or ratification policy owner.
It authenticates public selectors before payloads and immutable owner resources
before loading their explicit contract validators.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import ipaddress
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


def _module(path, name):
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise ValueError("Public review owner module is unavailable")
    value = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(value)
    return value


base = _module(Path(__file__).with_name("conformance_contract.py"), "observatory_public_review_admission")
DEFAULT_ROOT = Path(__file__).resolve().parent / "data"
MAX_RECORDS = 256
MAX_FINDINGS = 4096
MAX_TARGETS = 1024
canonical = base.canonical
digest = base.digest
parse = base.parse
instant = base.instant
plain = base.plain
closed = base.closed
require = base.require
text = base.text
admission = base.admission


def owner_resources(root, filename, expected_sha256):
    """Read only an adapter-fixed, content-bound owner resource selection."""
    content = base._read(Path(root) / filename)
    require(hashlib.sha256(content).hexdigest() == expected_sha256)
    lock = closed(parse(content), {"schema", "owner", "revision", "files"})
    require(lock["schema"] == "egohygiene.observatory.public-review-owner-lock/v1"
            and isinstance(lock["revision"], str) and base.SHA.fullmatch(lock["revision"])
            and isinstance(lock["files"], list) and 1 <= len(lock["files"]) <= 16)
    result = {}
    for item in lock["files"]:
        closed(item, {"source", "local", "sha256"})
        source = text(item["source"], 256)
        local = text(item["local"], 256)
        require(source not in result and not Path(local).is_absolute()
                and all(part not in {"", ".", ".."} for part in local.split("/")))
        value = base._read(Path(root) / local)
        require(isinstance(item["sha256"], str) and base.HASH.fullmatch(item["sha256"])
                and hashlib.sha256(value).hexdigest() == item["sha256"])
        result[source] = {"local": Path(root) / local, "bytes": value}
    return lock, result


def load_owner(path, name):
    """The path must come from owner_resources, never a report field."""
    return _module(path, name)


def public_catalog(root=DEFAULT_ROOT):
    # Reuse the existing exact public artifact, not an asserted roster/digest.
    _row, _metadata, allowed = admission("egohygiene/observatory", admission_root=root)
    document = plain(parse(base._read(Path(root) / "hygiene.public-repositories.v1.json")))
    rows = {item["full_name"]: item for item in document["repositories"]
            if isinstance(item, dict) and item.get("visibility") == "public"}
    require(frozenset(rows) == allowed)
    return rows, allowed


def targets(values, root=DEFAULT_ROOT):
    """Discard unadmitted selectors before revisions, duplicate checks or counts."""
    rows, allowed = public_catalog(root)
    result = {}
    for item in values:
        if not isinstance(item, dict):
            continue
        if "repository" in getattr(item, "duplicate_keys", set()):
            continue
        name = item.get("repository")
        if not isinstance(name, str) or name not in allowed:
            continue
        closed(item, {"repository", "represented_commit"})
        require(name not in result and isinstance(item["represented_commit"], str)
                and base.SHA.fullmatch(item["represented_commit"]) and len(result) < MAX_TARGETS)
        result[name] = item["represented_commit"]
    return dict(sorted(result.items())), rows, allowed


def wrappers(values, repository, allowed):
    """Yield only public selected source documents without inspecting hidden text."""
    for item in values:
        if (not isinstance(item, dict) or item.get("visibility") != "public"
                or {"visibility", "repository"} & getattr(item, "duplicate_keys", set())):
            continue
        name = item.get("repository")
        if not isinstance(name, str) or name not in allowed or name != repository:
            continue
        artifact = item.get("source")
        if artifact is not None:
            if not isinstance(artifact, dict) or artifact.get("repository") not in allowed:
                continue
        raw = item.get("evidence")
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        if isinstance(raw, bytes):
            value = parse(raw)
            input_kind, raw_bytes = "raw-json", raw
        else:
            value = raw
            input_kind, raw_bytes = "structured", None
        # Nested scope admission remains a domain prerequisite before callers
        # may inspect IDs, validate content, count, or publish either digest.
        yield value, {"input_kind": input_kind, "raw_bytes": raw_bytes, "wrapper": item}


def scope_admitted(value, allowed, *, objects=False):
    """Admit all declared repositories before a mixed scope can expose payloads."""
    if not isinstance(value, dict) or value.get("visibility") != "public":
        return False
    if {"visibility", "scope"} & getattr(value, "duplicate_keys", set()):
        return False
    scope = value.get("scope")
    if not isinstance(scope, dict) or "repositories" in getattr(scope, "duplicate_keys", set()):
        return False
    repositories = scope.get("repositories")
    if not isinstance(repositories, list) or not repositories:
        return False
    for item in repositories:
        if objects:
            if (not isinstance(item, dict) or item.get("visibility") != "public"
                    or "visibility" in getattr(item, "duplicate_keys", set())):
                return False
            item = item.get("full_name")
        if not isinstance(item, str) or item not in allowed:
            return False
    return True


def _public_host(host):
    host = host.rstrip(".").lower()
    if "." not in host or host.endswith((".localhost", ".local", ".internal", ".test", ".invalid", ".example", ".onion")):
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is None and re.fullmatch(r"(?:[0-9]+|0x[0-9a-f]+)", host.rsplit(".", 1)[-1]):
        return False
    return address is None or address.is_global


def public_url(value, allowed):
    value = base.url(value, allowed)
    require(_public_host(urlsplit(value).hostname))
    require(url_scope_admitted(value, allowed))
    return value


def url_scope_admitted(value, allowed):
    """Read only URL ownership before payload validation or source hashing."""
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        if (parsed.scheme != "https" or not host or parsed.username is not None or parsed.password is not None
                or parsed.port not in {None, 443} or parsed.query or "%" in parsed.path or "\\" in value
                or any(part in {".", ".."} for part in parsed.path.split("/"))):
            return False
        if not _public_host(host):
            return False
        host = host.rstrip(".")
        if host in {"github.com", "api.github.com", "raw.githubusercontent.com"}:
            parts = parsed.path.strip("/").split("/")
            if host == "api.github.com":
                if not parts or parts.pop(0) != "repos":
                    return False
            return len(parts) >= 2 and "/".join(parts[:2]) in allowed
        return True
    except (ValueError, UnicodeError):
        return False


def ownership_preflight(value, allowed):
    """Exclude protected repository mentions even inside otherwise public prose.

    This runs after public scope/source headers and before owner validation,
    source IDs, counters or either raw/canonical input digest. It is bounded
    and never reports the excluded token, URI, path or number of exclusions.
    """
    nodes = 0
    repository_token = re.compile(r"egohygiene/(?:\.github|[A-Za-z0-9][A-Za-z0-9.-]*)", re.IGNORECASE)
    public_names = {name.lower() for name in allowed}
    url_token = re.compile(r"https?://[^\s<>\"'`\)\]]+", re.IGNORECASE)

    def visit(item, depth, *, authority_reference=False):
        nonlocal nodes
        nodes += 1
        if depth > 32 or nodes > 100000:
            return False
        if isinstance(item, dict):
            if "visibility" in item and (item.get("visibility") != "public"
                    or "visibility" in getattr(item, "duplicate_keys", set())):
                return False
            for key, child in item.items():
                if not visit(key, depth + 1) or not visit(child, depth + 1,
                        authority_reference=key == "reference" and item.get("kind") == "human"):
                    return False
            return True
        if isinstance(item, list):
            return all(visit(child, depth + 1) for child in item)
        if isinstance(item, str):
            for match in repository_token.finditer(item):
                name = match.group().rstrip(".").lower()
                if name.endswith(".git"):
                    name = name[:-4]
                if name not in public_names:
                    return False
            for match in url_token.finditer(item):
                url = match.group().rstrip(".,;")
                if authority_reference and re.fullmatch(r"https://github\.com/[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", url):
                    continue
                if url == "https://github.com/egohygiene":
                    continue
                if not url_scope_admitted(url, allowed):
                    return False
        return True

    return visit(value, 0)

def repository_identity(row):
    return {name: row[name] for name in ("full_name", "repository_id", "visibility", "source_url")}


def seal(value):
    require(len(canonical(value)) <= base.MAX_BYTES)
    result = deepcopy(value)
    result["digest"] = digest(value)
    return result


def verify_seal(value):
    require(isinstance(value.get("digest"), str) and base.HASH.fullmatch(value["digest"]))
    require(value["digest"] == digest({key: item for key, item in value.items() if key != "digest"}))


def fleet_admission(selected, rows, root=DEFAULT_ROOT):
    _row, metadata, _allowed = admission("egohygiene/observatory", admission_root=root)
    return {**metadata, "selected_sha256": base.selected_digest([rows[name] for name in sorted(selected)])}


def source_input(metadata, value):
    """Call only after all source-scope members have passed public admission."""
    wrapper = plain(metadata["wrapper"])
    require(set(wrapper) in ({"visibility", "repository", "evidence"}, {"visibility", "repository", "evidence", "source"}))
    base.unambiguous(value)
    raw = metadata["raw_bytes"]
    raw_sha256 = hashlib.sha256(raw).hexdigest() if raw is not None else None
    artifact = wrapper.get("source")
    if artifact is not None:
        closed(artifact, {"repository", "revision", "path", "url", "sha256"})
        require(isinstance(artifact["revision"], str) and base.SHA.fullmatch(artifact["revision"])
                and isinstance(artifact["sha256"], str) and base.HASH.fullmatch(artifact["sha256"]))
        path = text(artifact["path"], 512)
        require(not path.startswith("/") and "\\" not in path and "%" not in path
                and all(part not in {"", ".", "..", ".git"} for part in path.split("/")))
        require(artifact["url"] == f"https://github.com/{artifact['repository']}/blob/{artifact['revision']}/{path}")
        require(raw_sha256 is None or artifact["sha256"] == raw_sha256)
    return {"input_kind": metadata["input_kind"],
        "raw_input_sha256": raw_sha256, "canonical_input_sha256": digest(value),
        "artifact": deepcopy(artifact), "artifact_integrity": "verified-input-bytes" if artifact is not None and raw is not None
            else "unverified-claim" if artifact is not None else "unavailable"}


def native_value(value):
    """Convert only already-admitted, ambiguity-checked transport dictionaries."""
    base.unambiguous(value)
    return json.loads(canonical(value))


def input_metadata(value, allowed):
    closed(value, {"input_kind", "raw_input_sha256", "canonical_input_sha256", "artifact", "artifact_integrity"})
    require(value["input_kind"] in {"raw-json", "structured"})
    for name in ("canonical_input_sha256", "raw_input_sha256"):
        require(value[name] is None and name == "raw_input_sha256" and value["input_kind"] == "structured"
                or isinstance(value[name], str) and base.HASH.fullmatch(value[name]))
    require(value["input_kind"] != "raw-json" or value["raw_input_sha256"] is not None)
    artifact = value["artifact"]
    if artifact is None:
        require(value["artifact_integrity"] == "unavailable")
    else:
        closed(artifact, {"repository", "revision", "path", "url", "sha256"})
        require(artifact["repository"] in allowed and isinstance(artifact["revision"], str)
                and base.SHA.fullmatch(artifact["revision"]) and isinstance(artifact["sha256"], str)
                and base.HASH.fullmatch(artifact["sha256"]))
        path = text(artifact["path"], 512)
        require(not path.startswith("/") and "\\" not in path and "%" not in path
                and all(part not in {"", ".", "..", ".git"} for part in path.split("/")))
        public_url(artifact["url"], allowed)
        require(artifact["url"] == f"https://github.com/{artifact['repository']}/blob/{artifact['revision']}/{artifact['path']}")
        if value["input_kind"] == "raw-json":
            require(value["artifact_integrity"] == "verified-input-bytes" and artifact["sha256"] == value["raw_input_sha256"])
        else:
            require(value["artifact_integrity"] == "unverified-claim")
    return value
