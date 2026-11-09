#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Render the real Hygiene view from the exact bounded Observatory owner query."""

from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "contracts/repository-conformance.v1.lock.json"
SCHEMA = "egohygiene.relay.hygiene-conformance-receipt/v1"
HASH = re.compile(r"[0-9a-f]{64}")
SHA = re.compile(r"[0-9a-f]{40}")
MAX_BYTES = 4 * 1024 * 1024
OWNER_FILES = {
    "src/observatory/conformance_contract.py": "conformance_contract.py",
    "src/observatory/data/hygiene.public-repositories.v1.json": "hygiene.public-repositories.v1.json",
    "contracts/hygiene.public-conformance.v1.lock.json": "hygiene.public-conformance.v1.lock.json",
    "schemas/repository-conformance.v1.schema.json": "repository-conformance.v1.schema.json",
}


class HygieneViewError(ValueError):
    """A bounded input or provenance failure without raw source content."""


def require(condition):
    if not condition:
        raise HygieneViewError("Hygiene conformance input or binding is incompatible")


def read(path):
    path = Path(path).absolute()
    try:
        require(".." not in path.parts and not any(item.is_symlink() for item in (path, *path.parents))
            and path.is_file() and path.stat().st_size <= MAX_BYTES)
        content = path.read_bytes()
    except OSError:
        raise HygieneViewError("Hygiene conformance source is unavailable") from None
    require(len(content) <= MAX_BYTES)
    return content


def digest(content):
    return hashlib.sha256(content).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def owner():
    lock = json.loads(read(LOCK))
    require(set(lock) == {"schema", "owner", "revision", "contract", "files"}
        and lock["schema"] == "egohygiene.relay.observatory-conformance-lock/v1"
        and lock["owner"] == "egohygiene/observatory"
        and isinstance(lock["revision"], str) and SHA.fullmatch(lock["revision"])
        and set(lock["files"]) == set(OWNER_FILES))
    for upstream, filename in OWNER_FILES.items():
        entry = lock["files"][upstream]
        require(set(entry) == {"vendored", "sha256"}
            and entry["vendored"] == "contracts/observatory-conformance/" + filename
            and isinstance(entry["sha256"], str) and HASH.fullmatch(entry["sha256"])
            and digest(read(ROOT / entry["vendored"])) == entry["sha256"])
    contract = module("relay_pinned_observatory_conformance", ROOT / "contracts/observatory-conformance/conformance_contract.py")
    require(lock["contract"] == {"schema": contract.SCHEMA, "version": contract.VERSION})
    return contract, lock


def implementation():
    return {"renderer_sha256": digest(read(Path(__file__))), "lock_sha256": digest(read(LOCK))}


def validate_input(path, repository, source_commit, as_of):
    """Validate before reading public counts or hashing selected model bytes."""
    try:
        contract, lock = owner()
        raw = read(path)
        value = contract.parse(raw)
        # Visibility and authenticated target identity precede all row content.
        require(isinstance(value, dict) and value.get("visibility") == "public"
            and isinstance(value.get("repository"), dict)
            and value["repository"].get("full_name") == repository)
        contract.validate(value, admission_root=ROOT / "contracts/observatory-conformance")
        require(value["represented_commit"] == source_commit and value["as_of"] == as_of)
        current = [item for item in value["checks"] if item["revision_status"] == "matched"]
        freshness = "stale" if any(item["freshness"] == "stale" for item in current) else "current" if current else "unknown"
        receipt = {"schema": SCHEMA, "repository": repository, "source_commit": source_commit, "as_of": as_of,
            "owner": {"repository": lock["owner"], "revision": lock["revision"],
                "schema": contract.SCHEMA, "contract_version": contract.VERSION},
            "input_sha256": digest(raw), "model_sha256": contract.digest(value),
            "implementation": implementation(), "freshness": freshness,
            "assessment_status": value["assessment"]["status"], "applicability": "unknown", "contract_inventory": "unknown",
            "checks": len(value["checks"]), "current_checks": len(current),
            "other_revision_checks": len(value["checks"]) - len(current)}
        validate_receipt(receipt, repository, source_commit, as_of)
        return value, receipt
    except Exception:
        raise HygieneViewError("Hygiene conformance input denied; inspect exact public owner evidence") from None


def validate_receipt(receipt, repository, source_commit, as_of):
    """Verify closed provenance without requiring a new public input asset."""
    contract, lock = owner()
    require(isinstance(receipt, dict) and set(receipt) == {"schema", "repository", "source_commit", "as_of", "owner",
        "input_sha256", "model_sha256", "implementation", "freshness", "assessment_status", "applicability",
        "contract_inventory", "checks", "current_checks", "other_revision_checks"})
    require(receipt["schema"] == SCHEMA and receipt["repository"] == repository and receipt["source_commit"] == source_commit
        and isinstance(source_commit, str) and SHA.fullmatch(source_commit) and receipt["as_of"] == as_of)
    contract.instant(as_of)
    contract.admission(repository, admission_root=ROOT / "contracts/observatory-conformance")
    require(receipt["owner"] == {"repository": lock["owner"], "revision": lock["revision"],
        "schema": contract.SCHEMA, "contract_version": contract.VERSION}
        and receipt["implementation"] == implementation()
        and all(isinstance(receipt[name], str) and HASH.fullmatch(receipt[name]) for name in ("input_sha256", "model_sha256"))
        and receipt["applicability"] == "unknown" and receipt["contract_inventory"] == "unknown"
        and receipt["freshness"] in ("current", "stale", "unknown")
        and receipt["assessment_status"] in ("conformant", "non_conformant", "blocked", "stale", "unknown", "partial", "not_applicable"))
    require(all(type(receipt[name]) is int and 0 <= receipt[name] <= contract.MAX_CHECKS
                for name in ("checks", "current_checks", "other_revision_checks")))
    require(receipt["checks"] == receipt["current_checks"] + receipt["other_revision_checks"]
        and (receipt["current_checks"] > 0 and receipt["freshness"] != "unknown"
             or receipt["current_checks"] == 0 and receipt["freshness"] == "unknown" and receipt["assessment_status"] == "unknown"))
    return receipt


def bindings(receipt):
    return {"data-hygiene-model-sha256": receipt["model_sha256"], "data-hygiene-model-schema": receipt["owner"]["schema"],
        "data-hygiene-owner-revision": receipt["owner"]["revision"], "data-hygiene-repository": receipt["repository"],
        "data-hygiene-source-commit": receipt["source_commit"], "data-hygiene-as-of": receipt["as_of"]}


def validate_page(document, receipt):
    """Require exact model binding and real shared-shell/filter integration."""
    class Page(HTMLParser):
        def __init__(self):
            super().__init__(); self.bound = []; self.heading = 0; self.body = 0; self.filters = 0; self.query = 0

        def handle_starttag(self, tag, attrs):
            values = dict(attrs)
            if values.get("id") == "hygiene-evidence":
                require(tag == "section" and len(values) == len(attrs))
                self.bound.append(values)
            if tag == "h2" and values.get("id") == "hygiene-heading":
                require(len(values) == len(attrs)); self.heading += 1
            if tag == "body" and values.get("data-ri-route") == "hygiene" and values.get("data-ri-renderer-state") == "implemented":
                require(len(values) == len(attrs)); self.body += 1
            if "data-filters" in values: self.filters += 1
            if tag == "input" and values.get("type") == "search" and "data-filter-query" in values: self.query += 1
    require(isinstance(document, str) and len(document.encode()) <= 16 * 1024 * 1024)
    page = Page(); page.feed(document); page.close()
    require(len(page.bound) == 1 and page.heading == 1 and page.body == 1 and page.filters >= 1 and page.query >= 1)
    require(all(page.bound[0].get(name) == value for name, value in bindings(receipt).items()))
    return document


def _site():
    return module("relay_hygiene_site_shell", Path(__file__).with_name("generate_repository_intelligence_site.py"))


def _link(value, label, repository, source_commit, esc, validator):
    """Intersect already owner-admitted links with the unchanged host policy."""
    parsed = urlsplit(value)
    target = None
    if parsed.hostname == "github.com":
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2:
            target = "/".join(parts[:2])
    try:
        validator.validate_https_reference(value, repository, source_commit, {target} if target else None)
    except (ValueError, TypeError):
        return f'<span>{esc(label)}: <code>{esc(value)}</code> <small>(not linked by this host profile)</small></span>'
    attribute = f' data-source-repository="{esc(target)}"' if target else ""
    return f'<a href="{esc(value)}"{attribute} rel="noopener noreferrer">{esc(label)} ↗</a>'


def render_body(value, receipt=None):
    """Render supplied contract evidence; missing inventory/applicability stays unknown."""
    contract, lock = owner()
    contract.validate(value, admission_root=ROOT / "contracts/observatory-conformance")
    if receipt is None:
        # Body-only composition may derive display bindings from an already
        # validated model. This is not an execution receipt; common bundle glue
        # separately retains the receipt returned by validate_input.
        receipt = {"model_sha256": contract.digest(value), "owner": {"schema": contract.SCHEMA, "revision": lock["revision"]},
            "repository": value["repository"]["full_name"], "source_commit": value["represented_commit"], "as_of": value["as_of"]}
    else:
        validate_receipt(receipt, value["repository"]["full_name"], value["represented_commit"], value["as_of"])
    require(contract.digest(value) == receipt["model_sha256"])
    site = _site(); esc = site.escaped
    validator = module("relay_hygiene_host_url_boundary", Path(__file__).with_name("validate_repository_intelligence_bundle.py"))
    repository, source_commit = value["repository"]["full_name"], value["represented_commit"]
    def link(url, label):
        return _link(url, label, repository, source_commit, esc, validator)
    attrs = " ".join(f'{name}="{esc(item)}"' for name, item in bindings(receipt).items())
    facets = []
    for name, label, values in (
        ("hygiene-result", "Assessment result", sorted({item["status"] for item in value["checks"]})),
        ("hygiene-domain", "Domain", sorted({item["domain"] for item in value["checks"]})),
        ("hygiene-severity", "Required/advisory", sorted({item["severity"] for item in value["checks"]})),
        ("hygiene-revision", "Represented revision", ["matched", "different"]),
    ):
        options = '<option value="all">All</option>' + "".join(f'<option value="{esc(item)}">{esc(item.replace("_", " "))}</option>' for item in values)
        facets.append(f'<label>{esc(label)}<select data-filter-extra="{name}">{options}</select></label>')
    cards = []
    for check in value["checks"]:
        observation, policy = check["observation"], check["contract"]
        search = " ".join(str(check[name]) for name in ("id", "title", "domain", "status", "severity")) + " " + policy["id"] + " " + policy["version"]
        evidence = "".join(f'<li>{link(url, "Evidence " + str(index + 1))}</li>' for index, url in enumerate(check["evidence"]))
        cards.append(f'''<li><article class="ri-record" data-filter-item data-kind="check" data-state="{esc(check['status'])}" data-source-repository="{esc(value['repository']['full_name'])}" data-filter-hygiene-result="{esc(check['status'])}" data-filter-hygiene-domain="{esc(check['domain'])}" data-filter-hygiene-severity="{esc(check['severity'])}" data-filter-hygiene-revision="{esc(check['revision_status'])}" data-search="{esc(search.lower())}">
          <div class="ri-record__top"><span class="ri-eyebrow">{esc(check['domain'])} · {esc(check['severity'])}</span>{site.status_pill(check['status'])}</div>
          <h3>{esc(check['title'])}</h3><p>{link(policy['url'], policy['id'] + ' · ' + policy['version'])}</p>
          <p>Applicability unknown · validator reported {esc(check['reported_status'])} · freshness {esc(check['freshness'])} · revision {esc(check['revision_status'])}</p>
          <details class="ri-evidence"><summary>Source, validity and evidence</summary><dl><dt>Represented commit</dt><dd>{link('https://github.com/' + repository + '/commit/' + observation['represented_commit'], observation['represented_commit'])}</dd><dt>Observed</dt><dd>{esc(observation['observed_at'])}</dd><dt>Valid through</dt><dd>{esc(observation['valid_until'])}</dd><dt>Producer</dt><dd>{link(observation['producer']['url'], observation['producer']['name'] + ' · ' + observation['producer']['version'])}</dd></dl><p>{link(observation['source']['url'], 'Canonical observation source')}</p><ul>{evidence}</ul></details>
        </article></li>''')
    records = '<ul class="ri-record-list">' + "".join(cards) + '</ul>' if cards else site.empty_state("Conformance evidence unavailable", "No admitted supplied conformance assessments were provided. This does not establish that no contracts apply or that this repository conforms.", "unknown")
    return f'''<section id="hygiene-evidence" class="ri-section ri-section--lead" {attrs}>
      <div class="ri-section-heading"><div><span class="ri-eyebrow">Assessed contract evidence</span><h2 id="hygiene-heading">Hygiene conformance</h2></div><p>Supplied assessments retain their contract, source, revision and freshness.</p></div>
      <div class="ri-panel"><p>{site.status_pill(value['assessment']['status'])} Current-revision supplied required assessments only.</p><p>{esc(value['assessment']['reason'])}</p><p>Applicability: <strong>unknown</strong>. Complete contract inventory: <strong>unknown</strong>. Advisory rows do not determine this assessment; other-revision rows are context only. No score, exemption, migration completion or human ratification is inferred.</p><p>Evidence records {value['evidence']['record_count']} · current-revision checks {value['evidence']['current_check_count']} · other-revision checks {value['evidence']['other_revision_check_count']}</p></div>
      <div class="ri-command-bar">{''.join(facets)}</div>{records}
      <p>Contract semantics and normalization: <code>{esc(contract.SCHEMA)}</code> {esc(contract.VERSION)}. {link(value['repository']['source_url'], 'Repository source')}</p>
    </section>'''


def render_page(*, value, receipt, summary, repository, source_commit):
    site = _site()
    return site.shell_document(route="hygiene", route_label="Hygiene", repository=repository, source_commit=source_commit,
        observed_at=value["as_of"], freshness=receipt["freshness"], summary=summary, body=render_body(value, receipt),
        prefix="../", snapshot_available=True, supported_views=("hygiene",), source_schema=receipt["owner"]["schema"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ("repository-root", "output-root", "summary", "provenance", "conformance", "repository", "source-commit"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        site = _site(); root = Path(args.repository_root).resolve(strict=True)
        for name in ("output_root", "summary", "provenance", "conformance"):
            site.validate_repository_path(root, Path(getattr(args, name)).absolute(), name)
        summary = site.load_object(Path(args.summary), "dashboard summary")
        provenance = site.load_object(Path(args.provenance), "bundle provenance")
        site.validate_site_contracts(summary, provenance, args.repository, args.source_commit)
        value, receipt = validate_input(args.conformance, args.repository, args.source_commit, provenance["generated_at"])
        require(provenance.get("hygiene_conformance") == receipt)
        document = render_page(value=value, receipt=receipt, summary=summary, repository=args.repository, source_commit=args.source_commit)
        validate_page(document, receipt)
        site.atomic_write(Path(args.output_root) / "hygiene/index.html", document)
        return 0
    except Exception:
        print("Hygiene rendering denied; inspect bound public owner evidence", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
