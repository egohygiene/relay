# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Portable architecture assessment contract; human authority stays external.

Stdlib only. Loading, validation and evaluation never fetch sources, execute a
reviewed repository, import its code, or authenticate a human from a URL. The
adjacent pinned Hygiene implementation owns governance semantics.
"""
from __future__ import annotations

import hashlib
import importlib.util
import ipaddress
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

SCHEMA = "egohygiene.architecture-coherence-review/v1"
CONTRACT_VERSION = "1.0.0-alpha.1"
MAX_BYTES = 2 * 1024 * 1024
DIMENSIONS = (
    "purpose", "responsibility-boundaries", "source-of-truth",
    "dependency-direction", "cohesion", "duplicate-ownership",
    "speculative-abstractions", "missing-ownership", "coupling",
    "documentation-divergence", "decision-consistency", "replaceability",
    "operational-plausibility", "security-privacy-trust", "maintainability",
    "justified-complexity", "simplest-credible-alternative",
)
_REPOSITORY = re.compile(r"[a-z0-9][a-z0-9-]*/(?:\.github|[a-z0-9][a-z0-9_.-]*)\Z")
_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}\Z")
_REVISION = re.compile(r"[0-9a-f]{40}\Z")
_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
_SENSITIVE = re.compile(r"(?:github_pat_|gh[pousr]_|(?:token|password|secret)\s*[:=]|[\w.+-]+@[\w.-]+\.[a-z]{2,}|/(?:home|Users|workspace|tmp)/|[A-Za-z]:\\|\\\\)", re.I)
_GOVERNANCE = None


class ContractError(ValueError):
    """Bounded, non-payload validation error safe for a public failure record."""


def _require(condition, code):
    if not condition:
        raise ContractError(code)


def _object(value, keys, code):
    _require(isinstance(value, dict) and not getattr(value, "duplicate_keys", ()) and set(value) == set(keys), code)
    return value


def _text(value, code, limit=12000):
    _require(type(value) is str and 0 < len(value) <= limit, code)
    _require(not any(ord(c) < 32 and c not in "\n\t" for c in value), code)
    _require(not any(0xD800 <= ord(c) <= 0xDFFF for c in value), code)
    return value


def _identifier(value, code):
    _require(type(value) is str and _ID.fullmatch(value) is not None, code)
    return value


def _repository(value, code):
    _require(type(value) is str and len(value) <= 200 and _REPOSITORY.fullmatch(value) is not None, code)
    _require(value.split("/")[1] not in (".", ".."), code)
    return value


def _revision(value, code):
    _require(type(value) is str and _REVISION.fullmatch(value) is not None, code)
    return value


def _time(value, code):
    _require(type(value) is str and _UTC.fullmatch(value) is not None, code)
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        raise ContractError(code) from None


def _array(value, code, limit=256):
    _require(type(value) is list and len(value) <= limit, code)
    return value


def _strings(value, code, limit=64):
    _array(value, code, limit)
    for item in value:
        _text(item, code)
    _require(len(value) == len(set(value)), code)
    return value


def _choice(value, choices, code):
    _require(type(value) is str and value in choices, code)


def _nullable_text(value, code, limit=512):
    if value is not None:
        _text(value, code, limit)


def _path(value):
    _text(value, "SOURCE_PATH", 1024)
    _require(not value.startswith(("/", "~")) and "\\" not in value and ":" not in value, "SOURCE_PATH")
    _require(all(part not in ("", ".", "..") for part in value.split("/")), "SOURCE_PATH")
    _require(str(PurePosixPath(value)) == value, "SOURCE_PATH")


def _url(value, repository=None, revision=None, path=None):
    _text(value, "SOURCE_URL", 4096)
    _require(not any(c.isspace() or ord(c) < 32 for c in value), "SOURCE_URL")
    try:
        parsed = urlsplit(value)
        _require(parsed.scheme == "https" and bool(parsed.hostname), "SOURCE_URL")
        _require(parsed.username is None and parsed.password is None and parsed.port in (None, 443), "SOURCE_URL")
        _require(not parsed.query and re.fullmatch(r"[A-Za-z0-9._-]{0,256}", parsed.fragment) is not None, "SOURCE_URL")
        hostname = parsed.hostname.rstrip(".").lower()
        _require("." in hostname and not hostname.endswith((".localhost", ".local", ".internal", ".test", ".invalid", ".example", ".onion")), "SOURCE_URL")
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            address = None
        _require(address is not None or re.fullmatch(r"(?:[0-9]+|0x[0-9a-f]+)", hostname.rsplit(".", 1)[-1]) is None, "SOURCE_URL")
        _require(address is None or address.is_global, "SOURCE_URL")
    except (ValueError, UnicodeError):
        raise ContractError("SOURCE_URL") from None
    _require("\\" not in value and "%" not in value, "SOURCE_URL")
    for segment in parsed.path.split("/"):
        decoded = unquote(segment)
        _require(decoded not in (".", "..") and not any(c in decoded for c in "/\\"), "SOURCE_URL")
        _require(not any(ord(c) < 32 or ord(c) == 127 for c in decoded), "SOURCE_URL")
    if parsed.hostname == "github.com":
        _require(parsed.netloc == "github.com" and not parsed.query, "SOURCE_URL")
        _require(parsed.path == f"/{repository}/blob/{revision}/{path}", "SOURCE_URL_BINDING")


def _scope(value, revisions):
    _object(value, ("kind", "key", "repositories"), "SCOPE")
    _choice(value["kind"], ("repository", "subsystem", "organization"), "SCOPE")
    _text(value["key"], "SCOPE", 256)
    repositories = _array(value["repositories"], "SCOPE", 128)
    _require(bool(repositories), "SCOPE")
    for repository in repositories:
        _repository(repository, "SCOPE")
    _require(repositories == sorted(set(repositories)), "SCOPE")
    if value["kind"] == "repository":
        _require(len(repositories) == 1 and value["key"] == repositories[0], "SCOPE")
    elif value["kind"] == "subsystem":
        _require(len(repositories) == 1 and value["key"].startswith(repositories[0] + ":"), "SCOPE")
        _identifier(value["key"].split(":", 1)[1], "SCOPE")
    else:
        _require(re.fullmatch(r"[a-z0-9][a-z0-9-]*", value["key"]) is not None, "SCOPE")
        _require(all(repo.split("/")[0] == value["key"] for repo in repositories), "SCOPE")
    _array(revisions, "REVISIONS", 128)
    for row in revisions:
        _object(row, ("repository", "revision"), "REVISIONS")
        _repository(row["repository"], "REVISIONS")
        _revision(row["revision"], "REVISIONS")
    _require([row["repository"] for row in revisions] == repositories, "REVISIONS")


def _indexed(rows, keys, code, limit=256):
    result = {}
    for row in _array(rows, code, limit):
        _object(row, keys, code)
        identifier = _identifier(row["id"], code)
        _require(identifier not in result, code)
        result[identifier] = row
    return result


def _evidence(value, sources, code, *, required=False):
    _strings(value, code)
    _require(all(identifier in sources for identifier in value), code)
    if required:
        _require(bool(value) and any(sources[i]["origin"] != "prior-ai-review" for i in value), code)


def _confidence(value):
    _choice(value, ("high", "medium", "low", "unknown"), "CONFIDENCE")


def _base(value):
    _object(value, (
        "schema", "contract_version", "id", "visibility", "scope",
        "represented_revisions", "generated_at", "reviewer", "execution",
        "sources", "explanation", "components", "relationships", "dimensions",
        "assumptions", "strengths", "concerns", "questions", "alternatives",
        "recommendation", "governance",
    ), "REVIEW")
    _require(value["schema"] == SCHEMA and value["contract_version"] == CONTRACT_VERSION, "VERSION")
    _identifier(value["id"], "REVIEW_ID")
    _choice(value["visibility"], ("public", "internal", "restricted"), "VISIBILITY")
    _scope(value["scope"], value["represented_revisions"])
    generated_at = _time(value["generated_at"], "GENERATED_AT")
    reviewer = _object(value["reviewer"], ("kind", "provider", "model", "method", "independent_challenge"), "REVIEWER")
    _choice(reviewer["kind"], ("ai", "human", "mixed", "tool"), "REVIEWER")
    for field in ("provider", "model"):
        _nullable_text(reviewer[field], "REVIEWER", 128)
    _text(reviewer["method"], "REVIEWER", 2000)
    _choice(reviewer["independent_challenge"], ("performed", "not-performed", "unknown"), "REVIEWER")
    execution = _object(value["execution"], ("status", "completed_at", "limitations"), "EXECUTION")
    _choice(execution["status"], ("complete", "partial", "blocked", "failed"), "EXECUTION")
    _strings(execution["limitations"], "EXECUTION")
    if execution["status"] == "complete":
        _require(_time(execution["completed_at"], "COMPLETED_AT") <= generated_at, "COMPLETED_AT")
    else:
        _require(execution["completed_at"] is None and bool(execution["limitations"]), "EXECUTION")
    sources = _indexed(value["sources"], ("id", "repository", "revision", "path", "kind", "origin", "visibility", "url"), "SOURCES")
    for source in sources.values():
        _repository(source["repository"], "SOURCE_REPOSITORY")
        _revision(source["revision"], "SOURCE_REVISION")
        _path(source["path"])
        _choice(source["kind"], ("architecture", "adr", "specification", "code", "catalog", "policy", "dependency", "runtime", "deployment", "other"), "SOURCE_KIND")
        _choice(source["origin"], ("canonical", "implementation", "human-record", "prior-ai-review", "external"), "SOURCE_ORIGIN")
        _choice(source["visibility"], ("public", "internal", "restricted"), "SOURCE_VISIBILITY")
        _require(value["visibility"] != "public" or source["visibility"] == "public", "SOURCE_VISIBILITY")
        if source["url"] is not None:
            _url(source["url"], source["repository"], source["revision"], source["path"])
    if execution["status"] == "complete":
        _require(bool(sources) and any(s["origin"] != "prior-ai-review" for s in sources.values()), "SOURCES_REQUIRED")
        for target in value["represented_revisions"]:
            _require(any(s["repository"] == target["repository"] and s["revision"] == target["revision"] and s["origin"] != "prior-ai-review" for s in sources.values()), "TARGET_SOURCE_REQUIRED")
    explanation = _object(value["explanation"], ("system", "boundaries", "flows", "rationale", "summary"), "EXPLANATION")
    for text in explanation.values():
        _text(text, "EXPLANATION")
    components = _indexed(value["components"], ("id", "name", "responsibility", "owner", "evidence"), "COMPONENTS", 128)
    for component in components.values():
        for field in ("name", "responsibility", "owner"):
            _text(component[field], "COMPONENTS", 3000)
        _evidence(component["evidence"], sources, "COMPONENT_EVIDENCE")
    relationships = _indexed(value["relationships"], ("id", "from", "to", "kind", "summary", "evidence"), "RELATIONSHIPS")
    for relationship in relationships.values():
        _identifier(relationship["from"], "RELATIONSHIP_COMPONENT")
        _identifier(relationship["to"], "RELATIONSHIP_COMPONENT")
        _require(relationship["from"] in components and relationship["to"] in components, "RELATIONSHIP_COMPONENT")
        _choice(relationship["kind"], ("data", "dependency", "control", "trust", "deployment"), "RELATIONSHIP_KIND")
        _text(relationship["summary"], "RELATIONSHIPS", 3000)
        _evidence(relationship["evidence"], sources, "RELATIONSHIP_EVIDENCE")
    dimensions = _indexed(value["dimensions"], ("id", "status", "summary", "evidence", "confidence"), "DIMENSIONS", len(DIMENSIONS))
    _require(set(dimensions).issubset(DIMENSIONS), "DIMENSION_ID")
    if execution["status"] == "complete":
        _require(set(dimensions) == set(DIMENSIONS), "DIMENSION_COVERAGE")
    for dimension in dimensions.values():
        _choice(dimension["status"], ("coherent", "concern", "unknown", "not-assessed"), "DIMENSION_STATUS")
        _text(dimension["summary"], "DIMENSIONS", 3000)
        _confidence(dimension["confidence"])
        _evidence(dimension["evidence"], sources, "DIMENSION_EVIDENCE", required=dimension["status"] in ("coherent", "concern"))
    assumptions = _indexed(value["assumptions"], ("id", "statement", "basis", "consequence", "evidence"), "ASSUMPTIONS")
    for assumption in assumptions.values():
        _choice(assumption["basis"], ("observed", "reported", "inferred", "unverified"), "ASSUMPTION_BASIS")
        _text(assumption["statement"], "ASSUMPTIONS", 3000)
        _text(assumption["consequence"], "ASSUMPTIONS", 3000)
        _evidence(assumption["evidence"], sources, "ASSUMPTION_EVIDENCE", required=assumption["basis"] == "observed")
    strengths = _indexed(value["strengths"], ("id", "summary", "evidence", "confidence"), "STRENGTHS")
    for strength in strengths.values():
        _text(strength["summary"], "STRENGTHS", 3000)
        _confidence(strength["confidence"])
        _evidence(strength["evidence"], sources, "STRENGTH_EVIDENCE", required=True)
    alternatives = _indexed(value["alternatives"], ("id", "summary", "tradeoffs", "why_not_chosen", "evidence", "confidence"), "ALTERNATIVES")
    for alternative in alternatives.values():
        for field in ("summary", "tradeoffs", "why_not_chosen"):
            _text(alternative[field], "ALTERNATIVES", 4000)
        _confidence(alternative["confidence"])
        _evidence(alternative["evidence"], sources, "ALTERNATIVE_EVIDENCE")
    concerns = _indexed(value["concerns"], ("id", "category", "importance", "summary", "detail", "evidence", "confidence", "alternative_ids"), "CONCERNS")
    for concern in concerns.values():
        _choice(concern["category"], ("wrong", "risky", "unverified", "intentional-tradeoff", "complex-but-justified"), "CONCERN_CATEGORY")
        _choice(concern["importance"], ("consequential", "advisory"), "CONCERN_IMPORTANCE")
        _text(concern["summary"], "CONCERNS", 3000)
        _text(concern["detail"], "CONCERNS", 6000)
        _confidence(concern["confidence"])
        _evidence(concern["evidence"], sources, "CONCERN_EVIDENCE", required=concern["category"] != "unverified")
        _strings(concern["alternative_ids"], "CONCERN_ALTERNATIVES")
        _require(all(identifier in alternatives for identifier in concern["alternative_ids"]), "CONCERN_ALTERNATIVES")
        _require(concern["importance"] != "consequential" or bool(concern["alternative_ids"]), "CONCERN_ALTERNATIVES")
    questions = _indexed(value["questions"], ("id", "question", "owner", "evidence"), "QUESTIONS")
    for question in questions.values():
        _text(question["question"], "QUESTIONS", 4000)
        _nullable_text(question["owner"], "QUESTIONS", 256)
        _evidence(question["evidence"], sources, "QUESTION_EVIDENCE")
    recommendation = _object(value["recommendation"], ("disposition", "reason"), "RECOMMENDATION")
    _choice(recommendation["disposition"], ("ratify", "ratify-with-notes", "revise", "reject", "defer"), "RECOMMENDATION")
    _text(recommendation["reason"], "RECOMMENDATION", 6000)
    _require(execution["status"] == "complete" or recommendation["disposition"] == "defer", "INCOMPLETE_RECOMMENDATION")
    if value["visibility"] == "public":
        def public_text(item):
            if type(item) is str:
                _require(not _SENSITIVE.search(item), "PUBLIC_SENSITIVE_CONTENT")
            elif isinstance(item, dict):
                for child in item.values():
                    public_text(child)
            elif type(item) is list:
                for child in item:
                    public_text(child)
        public_text(value)
    return value


def canonical_bytes(value):
    """Canonical assessment encoding: sorted compact UTF-8 JSON, no newline."""
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ContractError("CANONICAL_JSON") from None


def review_subject(value):
    """Return immutable assessment identity; governance is excluded from digest."""
    _require(isinstance(value, dict) and "governance" in value
             and not getattr(value, "duplicate_keys", ()), "REVIEW")
    assessment = {k: v for k, v in value.items() if k != "governance"}
    encoded = canonical_bytes(assessment)
    _require(len(encoded) <= MAX_BYTES, "REVIEW_LIMIT")
    _unambiguous(assessment)
    _base({**assessment, "governance": None})
    return {
        "id": value["id"],
        "assessment_sha256": hashlib.sha256(encoded).hexdigest(),
        "scope": json.loads(canonical_bytes(value["scope"])),
        "represented_revisions": json.loads(canonical_bytes(value["represented_revisions"])),
        "completed_at": value["execution"]["completed_at"],
    }


def governance_contract():
    """Load the byte-pinned adjacent Hygiene owner contract, never repository code."""
    global _GOVERNANCE
    if _GOVERNANCE is None:
        directory = Path(__file__).resolve().parent
        try:
            lock = json.loads((directory / "governance.lock.json").read_bytes())
            source = directory / "architecture_coherence_governance.py"
            _require(lock["owner"] == "egohygiene/hygiene" and _REVISION.fullmatch(lock["revision"]), "GOVERNANCE_PIN")
            _require(type(lock["helper_sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", lock["helper_sha256"]), "GOVERNANCE_PIN")
            _require(hashlib.sha256(source.read_bytes()).hexdigest() == lock["helper_sha256"], "GOVERNANCE_PIN")
            name = "egohygiene_hygiene_architecture_coherence_" + lock["revision"]
            module = sys.modules.get(name)
            if module is None:
                spec = importlib.util.spec_from_file_location(name, source)
                _require(spec is not None and spec.loader is not None, "GOVERNANCE_PIN")
                module = importlib.util.module_from_spec(spec)
                module.__owner_revision__ = lock["revision"]
                module.__owner_helper_sha256__ = lock["helper_sha256"]
                sys.modules[name] = module
                try:
                    spec.loader.exec_module(module)
                except Exception:
                    sys.modules.pop(name, None)
                    raise
            _require(getattr(module, "__owner_revision__", None) == lock["revision"]
                     and getattr(module, "__owner_helper_sha256__", None) == lock["helper_sha256"], "GOVERNANCE_PIN")
            _GOVERNANCE = module
        except (OSError, ValueError, KeyError, TypeError, ImportError, AttributeError):
            raise ContractError("GOVERNANCE_PIN") from None
    return _GOVERNANCE


def validate_review(value, *, public_repositories=None):
    """Validate shape/bindings; a valid human claim is still not authenticated."""
    _require(len(canonical_bytes(value)) <= MAX_BYTES, "REVIEW_LIMIT")
    _unambiguous(value)
    _base(value)
    if value["governance"] is not None:
        _require(public_repositories is not None, "GOVERNANCE_ADMISSION_REQUIRED")
        owner = governance_contract()
        try:
            admitted = owner.validate_governance(value["governance"], public_repositories=public_repositories)
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
            raise ContractError("GOVERNANCE") from None
        _require(admitted is not None, "GOVERNANCE_ADMISSION")
        subject = review_subject(value)
        governance = value["governance"]
        _require(governance["scope"] == subject["scope"] and governance["represented_revisions"] == subject["represented_revisions"], "GOVERNANCE_SUBJECT")
        reference = governance["review_ref"]
        if reference is not None:
            _require(subject["completed_at"] is not None, "GOVERNANCE_COMPLETION")
            for field in ("id", "assessment_sha256", "completed_at"):
                _require(reference[field] == subject[field], "GOVERNANCE_SUBJECT")
    return value


def _unambiguous(value, depth=0):
    _require(depth <= 24, "REVIEW_DEPTH")
    if isinstance(value, dict):
        _require(not getattr(value, "duplicate_keys", ()), "DUPLICATE_MEMBER")
        for child in value.values():
            _unambiguous(child, depth + 1)
    elif type(value) is list:
        for child in value:
            _unambiguous(child, depth + 1)


def evaluate_review(value, *, as_of, public_repositories, trusted_human_evidence=(),
                    material_changes=(), change_inventory="unknown", current_revisions=None):
    """Evaluate assessment and separately trusted governance; never infer approval."""
    validate_review(value, public_repositories=public_repositories)
    _require(_time(value["generated_at"], "GENERATED_AT") <= _time(as_of, "AS_OF"), "FUTURE_REVIEW")
    subject = review_subject(value)
    owner = governance_contract()
    try:
        governance = owner.evaluate(
            value["governance"], as_of=as_of, public_repositories=public_repositories,
            trusted_human_evidence=trusted_human_evidence, material_changes=material_changes,
            change_inventory=change_inventory, current_revisions=current_revisions,
            availability="missing" if value["governance"] is None else "present",
        )
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise ContractError("GOVERNANCE_EVALUATION") from None
    return {"schema": SCHEMA, "contract_version": CONTRACT_VERSION,
            "subject": subject, "execution": value["execution"]["status"],
            "reviewer_recommendation": value["recommendation"]["disposition"],
            "governance": governance, "evaluated_at": as_of}


def human_statement(value, *, public_repositories, kind="decision"):
    """Bound statement for an EXTERNAL human-source verifier, not a proof."""
    validate_review(value, public_repositories=public_repositories)
    _require(value["governance"] is not None, "GOVERNANCE_REQUIRED")
    try:
        return governance_contract().human_statement(
            value["governance"], public_repositories=public_repositories, kind=kind)
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise ContractError("HUMAN_STATEMENT") from None


def import_human_decision(value, governance, *, as_of, public_repositories,
                          trusted_human_evidence):
    """Return a new review ONLY after separately trusted evidence binds the claim.

    This function neither verifies identity nor creates trusted evidence. The
    caller's privileged adapter must verify authentic human provenance BEFORE
    constructing governance_contract().TrustedHumanEvidence. There is purposely
    no JSON decoder for trusted context and no CLI flag to assert verification.
    """
    validate_review(value, public_repositories=public_repositories)
    _require(value["execution"]["status"] == "complete", "HUMAN_REVIEW_INCOMPLETE")
    candidate = json.loads(canonical_bytes(value))
    candidate["governance"] = json.loads(canonical_bytes(governance))
    evaluated = evaluate_review(candidate, as_of=as_of, public_repositories=public_repositories,
        trusted_human_evidence=trusted_human_evidence)
    _require(evaluated["governance"]["human_evidence"] == "verified", "HUMAN_EVIDENCE_REQUIRED")
    _require(review_subject(candidate) == review_subject(value), "ASSESSMENT_IMMUTABLE")
    return candidate


def loads_review(raw, *, public_repositories=None):
    """Reject duplicate members before last-value JSON parsing can erase them."""
    _require(type(raw) in (bytes, str), "REVIEW_JSON")
    if type(raw) is str:
        try:
            raw = raw.encode("utf-8")
        except UnicodeError:
            raise ContractError("REVIEW_JSON") from None
    _require(len(raw) <= MAX_BYTES, "REVIEW_LIMIT")
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, "DUPLICATE_MEMBER")
            result[key] = value
        return result
    def constant(_):
        raise ContractError("REVIEW_JSON")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, ValueError, RecursionError) as error:
        if isinstance(error, ContractError):
            raise
        raise ContractError("REVIEW_JSON") from None
    return validate_review(value, public_repositories=public_repositories)


def load_review(path, *, public_repositories=None):
    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    except OSError:
        raise ContractError("REVIEW_READ") from None
    return loads_review(raw, public_repositories=public_repositories)
