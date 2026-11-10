#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Presentation and byte-binding support for the separate Audits/Sanity models.

Owner helpers validate domain meaning and public admission. This module only
binds their exact bytes and renders escaped, complete static source records.
"""

from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
HASH = re.compile(r"[0-9a-f]{64}")
SHA = re.compile(r"[0-9a-f]{40}")
MAX_BYTES = 4 * 1024 * 1024
MAX_PAGE = 16 * 1024 * 1024


class ReviewViewError(ValueError):
    """A closed review input error without rejected content or paths."""


def require(condition):
    if not condition:
        raise ReviewViewError("Review evidence input or binding is incompatible")


def read(path):
    path = Path(path).absolute()
    try:
        require(".." not in path.parts and not any(item.is_symlink() for item in (path, *path.parents))
            and path.is_file() and path.stat().st_size <= MAX_BYTES)
        content = path.read_bytes()
    except OSError:
        raise ReviewViewError("Review evidence source is unavailable") from None
    require(len(content) <= MAX_BYTES)
    return content


def digest(content):
    return hashlib.sha256(content).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def unique(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value)
        value[key] = item
    return value


class Boundary:
    def __init__(self, *, route, renderer, lock, owner_module, files, schema):
        self.route, self.renderer, self.lock = route, Path(renderer), Path(lock)
        self.vendor = ROOT / ("contracts/observatory-" + route)
        self.owner_module, self.files, self.schema = owner_module, files, schema

    def owner(self):
        lock = json.loads(read(self.lock), object_pairs_hook=unique)
        require(isinstance(lock, dict) and set(lock) == {"schema", "owner", "revision", "contract", "files"}
            and lock["schema"] == f"egohygiene.relay.observatory-{self.route}-lock/v1"
            and lock["owner"] == "egohygiene/observatory" and isinstance(lock["revision"], str)
            and SHA.fullmatch(lock["revision"]) and set(lock["files"]) == set(self.files))
        for upstream, filename in self.files.items():
            entry = lock["files"][upstream]
            relative = "contracts/observatory-" + self.route + "/" + filename
            require(isinstance(entry, dict) and set(entry) == {"vendored", "sha256"}
                and entry["vendored"] == relative and isinstance(entry["sha256"], str)
                and HASH.fullmatch(entry["sha256"]) and digest(read(ROOT / relative)) == entry["sha256"])
        contract = module("relay_pinned_observatory_" + self.route, self.vendor / self.owner_module)
        require(lock["contract"] == {"schema": contract.SCHEMA, "version": contract.VERSION})
        return contract, lock

    def implementation(self):
        return {"renderer_sha256": digest(read(self.renderer)), "support_sha256": digest(read(Path(__file__))),
            "lock_sha256": digest(read(self.lock))}

    def admit(self, path, repository, source_commit, as_of):
        contract, lock = self.owner()
        raw = read(path)
        value = contract.parse(raw)
        # Authenticate selected public target before counts, prose or hashes.
        require(isinstance(value, dict) and value.get("visibility") == "public"
            and isinstance(value.get("repository"), dict)
            and value["repository"].get("full_name") == repository)
        contract.validate(value, admission_root=self.vendor)
        require(value["represented_commit"] == source_commit and value["as_of"] == as_of)
        receipt = {"schema": self.schema, "repository": repository, "source_commit": source_commit, "as_of": as_of,
            "owner": {"repository": lock["owner"], "revision": lock["revision"],
                "schema": contract.SCHEMA, "contract_version": contract.VERSION},
            "input_sha256": digest(raw), "model_sha256": contract.digest(value), "implementation": self.implementation()}
        return contract, value, receipt

    def validate_core(self, receipt, repository, source_commit, as_of, fields):
        contract, lock = self.owner()
        require(isinstance(receipt, dict) and set(receipt) == {"schema", "repository", "source_commit", "as_of", "owner",
            "input_sha256", "model_sha256", "implementation"} | set(fields))
        require(receipt["schema"] == self.schema and receipt["repository"] == repository
            and receipt["source_commit"] == source_commit and isinstance(source_commit, str)
            and SHA.fullmatch(source_commit) and receipt["as_of"] == as_of)
        contract.instant(as_of)
        contract.admission(repository, admission_root=self.vendor)
        require(receipt["owner"] == {"repository": lock["owner"], "revision": lock["revision"],
            "schema": contract.SCHEMA, "contract_version": contract.VERSION}
            and receipt["implementation"] == self.implementation()
            and all(isinstance(receipt[name], str) and HASH.fullmatch(receipt[name]) for name in ("input_sha256", "model_sha256"))
            and receipt["freshness"] in {"current", "stale", "unknown", "not_applicable"})
        return contract

    def bindings(self, receipt):
        result = {f"data-{self.route}-model-sha256": receipt["model_sha256"],
            f"data-{self.route}-model-schema": receipt["owner"]["schema"],
            f"data-{self.route}-owner-revision": receipt["owner"]["revision"],
            f"data-{self.route}-repository": receipt["repository"],
            f"data-{self.route}-source-commit": receipt["source_commit"], f"data-{self.route}-as-of": receipt["as_of"]}
        if self.route == "sanity":
            result["data-sanity-effective-human-state"] = receipt["human_state"]
        return result

    def validate_page(self, document, receipt):
        route, expected = self.route, self.bindings(receipt)

        class Page(HTMLParser):
            def __init__(self):
                super().__init__(); self.bound = []; self.heading = 0; self.body = 0; self.filters = 0; self.query = 0
                self.records = {}

            def handle_starttag(self, tag, attrs):
                values = dict(attrs)
                if values.get("id") == route + "-evidence":
                    require(tag == "section" and len(values) == len(attrs)); self.bound.append(values)
                if tag == "h2" and values.get("id") == route + "-heading":
                    require(len(values) == len(attrs)); self.heading += 1
                if tag == "body" and values.get("data-ri-route") == route and values.get("data-ri-renderer-state") == "implemented":
                    require(len(values) == len(attrs)); self.body += 1
                if "data-filters" in values: self.filters += 1
                if tag == "input" and values.get("type") == "search" and "data-filter-query" in values: self.query += 1
                kind = values.get("data-" + route + "-record")
                if kind is not None:
                    require(tag == "article" and len(values) == len(attrs))
                    self.records[kind] = self.records.get(kind, 0) + 1

        require(isinstance(document, str) and len(document.encode()) <= MAX_PAGE)
        page = Page(); page.feed(document); page.close()
        require(len(page.bound) == 1 and page.heading == 1 and page.body == 1 and page.filters >= 1 and page.query >= 1
            and all(page.bound[0].get(name) == value for name, value in expected.items())
            and {name: page.records.get(name, 0) for name in receipt["counts"]} == receipt["counts"]
            and not set(page.records) - set(receipt["counts"]))
        return document


def site():
    return module("relay_review_site_shell", Path(__file__).with_name("generate_repository_intelligence_site.py"))


class Display:
    def __init__(self, boundary, value, receipt):
        self.boundary, self.value, self.receipt = boundary, value, receipt
        self.site = site(); self.esc = self.site.escaped
        self.validator = None
        self.repository, self.source_commit = receipt["repository"], receipt["source_commit"]

    def link(self, url, label):
        if self.validator is None:
            self.validator = module("relay_review_host_url_boundary", Path(__file__).with_name("validate_repository_intelligence_bundle.py"))
        target = None
        try:
            parsed = urlsplit(url)
            if parsed.hostname == "github.com":
                parts = parsed.path.strip("/").split("/")
                if len(parts) >= 2: target = "/".join(parts[:2])
            self.validator.validate_https_reference(url, self.repository, self.source_commit, {target} if target else None)
        except (ValueError, TypeError):
            return f'<span>{self.esc(label)}: <code>{self.esc(url)}</code> <small>(not linked by this host profile)</small></span>'
        attribute = f' data-source-repository="{self.esc(target)}"' if target else ""
        return f'<a href="{self.esc(url)}"{attribute} rel="noopener noreferrer">{self.esc(label)} ↗</a>'

    def detail(self, value):
        """Keep every owner-projected field in static HTML, without Markdown execution."""
        if isinstance(value, dict):
            return '<dl>' + ''.join(f'<dt>{self.esc(key.replace("_", " "))}</dt><dd>{self.detail(item)}</dd>' for key, item in value.items()) + '</dl>'
        if isinstance(value, list):
            return '<ul>' + ''.join('<li>' + self.detail(item) + '</li>' for item in value) + '</ul>' if value else '<span>None supplied</span>'
        if value is None: return '<span>Not supplied</span>'
        if isinstance(value, str) and value.startswith("https://"): return self.link(value, value)
        return self.esc(value)

    def facet(self, name, label, values):
        values = sorted(set(values))
        options = '<option value="all">All</option>' + ''.join(f'<option value="{self.token(value)}">{self.esc(value.replace("_", " "))}</option>' for value in values)
        return f'<label>{self.esc(label)}<select data-filter-extra="{self.esc(name)}">{options}</select></label>'

    @staticmethod
    def token(value):
        # The existing filter engine splits attributes on whitespace. Opaque
        # selectors preserve multiword owner labels without changing their text.
        return "v-" + digest(value.encode())[:24]

    def fragment(self, group, identifier):
        return self.boundary.route + '-' + group + '-' + digest(identifier.encode())[:24]

    def record(self, *, group, identifier, title, state, fields, facets=(), intro=None):
        fragment = self.fragment(group, identifier)
        attributes = ' '.join(f'data-filter-{self.esc(name)}="{" ".join(self.token(value) for value in (item if isinstance(item, list) else [item]))}"' for name, item in facets)
        search = json.dumps(fields, ensure_ascii=False, sort_keys=True).lower()
        overview = self.detail(intro) if intro else ""
        return f'''<li><article class="ri-record" id="{fragment}" data-filter-item data-kind="{self.esc(group)}" data-state="{self.esc(state)}" data-{self.boundary.route}-record="{self.esc(group)}" data-search="{self.esc(search)}" {attributes}>
          <div class="ri-record__top"><span class="ri-eyebrow">{self.esc(group.replace('_', ' '))}</span>{self.site.status_pill(state)}</div>
          <h4>{self.esc(title)}</h4>{overview}<details class="ri-evidence"><summary>Source record and evidence</summary>{self.detail(fields)}</details>
        </article></li>'''

    def section(self, title, records, empty):
        contents = '<ul class="ri-record-list">' + ''.join(records) + '</ul>' if records else self.site.empty_state(title + ' unavailable', empty, 'unknown')
        return '<section class="ri-section"><h3>' + self.esc(title) + '</h3>' + contents + '</section>'
