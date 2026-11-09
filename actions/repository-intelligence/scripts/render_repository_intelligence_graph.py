#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Enhance a generated repository overview with portable graph navigation."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import re
import subprocess
import sys
from typing import Any
from urllib.parse import urlsplit


def load_site():
    path = Path(__file__).with_name("generate_repository_intelligence_site.py")
    spec = importlib.util.spec_from_file_location("relay_repository_graph_site", path)
    if spec is None or spec.loader is None:
        raise ValueError("GRAPH_INPUT")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


site = load_site()
ASSETS = Path(__file__).resolve().parents[1] / "assets"
MAX_NODES = 112
MAX_ENTITIES = 96
MAX_EDGES = 288
MAX_INPUT = 8 * 1024 * 1024
REPOSITORY = re.compile(r"(?!\.{1,2}/)(?![^/]+/\.{1,2}$)[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
ASSERTIONS = {"authoritative", "inferred", "unknown"}
FRESHNESS = {"current", "stale", "unknown", "not_applicable"}
RELATIONSHIPS = {"blocks", "depends-on", "deploys", "evidences", "implements", "informs", "releases", "supersedes", "tracks", "verifies"}
KINDS = {"repository", "roadmap_step", "architecture_decision", "issue", "pull_request", "commit", "check", "release", "deployment", "file"}
BEGIN = "<!-- BEGIN RELAY REPOSITORY GRAPH -->"
END = "<!-- END RELAY REPOSITORY GRAPH -->"
UNSAFE = re.compile(r"(?:/(?:home|Users|workspace|tmp)/|[A-Za-z]:\\|\\\\)")


def text(value: Any, maximum: int = 512) -> str:
    if (not isinstance(value, str) or not value or len(value) > maximum
            or any(ord(character) < 32 or ord(character) == 127 for character in value)
            or site.EMAIL.search(value) or site.SECRET.search(value) or UNSAFE.search(value)):
        raise ValueError("GRAPH_INPUT")
    return value


def github_href(value: Any, repository: str) -> str:
    """Use public canonical GitHub evidence, never a guessed repository Pages host."""
    if (not isinstance(value, str) or len(value) > 2048 or "%" in value or "\\" in value
            or any(character.isspace() for character in value) or not site.safe_href(value)):
        return ""
    parsed = urlsplit(value)
    if parsed.netloc != "github.com" or parsed.query:
        return ""
    if parsed.fragment and not re.fullmatch(r"[A-Za-z0-9._-]+", parsed.fragment):
        return ""
    prefix = "/" + repository
    if parsed.path == prefix and not parsed.fragment:
        return value
    if not parsed.path.startswith(prefix + "/"):
        return ""
    path = parsed.path[len(prefix) + 1:]
    if any(part in {"", ".", ".."} for part in path.split("/")):
        return ""
    allowed = r"(?:(?:issues|pull)/[1-9][0-9]*|commit/[0-9a-f]{40}|(?:blob|tree)/[0-9a-f]{40}(?:/[A-Za-z0-9._/-]+)?|releases(?:/tag/[A-Za-z0-9._-]+)?)"
    return value if re.fullmatch(allowed, path) else ""


def public_entity(candidate: Any) -> dict[str, str] | None:
    """Apply visibility before reading identity, state, title, URL or provenance."""
    if not isinstance(candidate, dict) or candidate.get("visibility") != "public":
        return None
    repository = text(candidate.get("repository"), 240)
    if not REPOSITORY.fullmatch(repository):
        raise ValueError("GRAPH_INPUT")
    kind = text(candidate.get("kind"), 64)
    if kind not in KINDS:
        raise ValueError("GRAPH_INPUT")
    state = candidate.get("state")
    assertion = state.get("assertion") if isinstance(state, dict) else candidate.get("assertion")
    state_value = state.get("value") if isinstance(state, dict) else state
    freshness = candidate.get("freshness")
    if assertion not in ASSERTIONS or freshness not in FRESHNESS:
        raise ValueError("GRAPH_INPUT")
    key = text(candidate.get("key"))
    identifier = text(candidate.get("id"))
    return {"id": "entity:" + identifier, "entity_id": identifier, "label": text(candidate.get("title") or key),
            "kind": "entity", "entity_kind": kind, "repository": repository,
            "state": text(state_value, 128), "assertion": assertion, "freshness": freshness,
            "source_href": github_href(candidate.get("canonical_url"), repository)}


def _view_ids(snapshot: dict, route: str, field: str) -> set[str]:
    view = site.require_object(site.require_object(snapshot.get("views")).get(route))
    return {value["id"] for item in site.require_list(view.get(field))
            if isinstance((value := site.entity(item)), dict) and value.get("visibility") == "public"
            and isinstance(value.get("id"), str)}


def _entity_href(node: dict, snapshot: dict, repository: str, prefix: str) -> str:
    if node["repository"] != repository:
        return node["source_href"]
    kind, identifier = node["entity_kind"], node["entity_id"]
    if kind == "repository":
        return prefix or "./"
    if kind == "roadmap_step" and identifier in _view_ids(snapshot, "roadmap", "steps"):
        return prefix + "roadmap/#" + site.stable_fragment("quest", identifier)
    if kind == "architecture_decision" and identifier in _view_ids(snapshot, "decisions", "decisions"):
        return prefix + "decisions/#" + site.stable_fragment("decision", identifier)
    if kind in {"issue", "pull_request"}:
        field = "open_issues" if kind == "issue" else "open_pull_requests"
        if identifier in _view_ids(snapshot, "work", field):
            return prefix + "work/"
    if kind == "check" and identifier in _view_ids(snapshot, "health", "checks"):
        return prefix + "health/"
    if kind == "release" and identifier in _view_ids(snapshot, "releases", "releases"):
        return prefix + "releases/"
    return prefix + "search/"


def graph_model(snapshot: dict | None, repository: str, prefix: str = "") -> dict:
    """Project a bounded navigation aid from an already-admitted owner snapshot."""
    if prefix not in {"", "../"} or not REPOSITORY.fullmatch(repository):
        raise ValueError("GRAPH_INPUT")
    current = snapshot if isinstance(snapshot, dict) and snapshot.get("visibility") == "public" else None
    if current and site.require_object(current.get("repository")).get("key") != repository:
        current = None
    nodes = [{"id": "navigation:repository", "label": repository, "kind": "repository", "state": "unknown",
              "assertion": "presentation", "freshness": "not_applicable", "repository": repository,
              "href": prefix or "./", "description": "This repository's generated Intelligence subtree."}]
    for route, label in (("intelligence", "Overview"), *site.ROUTES, ("dashboard", "Dashboard")):
        try:
            projected = current and (route == "intelligence" or isinstance(site.require_object(current.get("views")).get(route), dict))
            state = site.projection_freshness(current, route) if projected else "unavailable"
        except (ValueError, TypeError, KeyError, AttributeError):
            state = "unknown"
        nodes.append({"id": "navigation:" + route, "label": label, "kind": "view", "state": state,
                      "assertion": "presentation", "freshness": "not_applicable", "repository": repository,
                      "href": (prefix or "./") if route == "intelligence" else prefix + route + "/",
                      "description": site.ROUTE_QUESTIONS.get(route, "Inspect this generated repository view.")})
    edges = [{"id": "navigation:opens:" + node["id"], "source": nodes[0]["id"], "target": node["id"],
              "label": "opens view", "kind": "navigation", "assertion": "presentation", "freshness": "not_applicable",
              "provenance": []} for node in nodes[1:]]
    if current is None:
        return {"nodes": nodes, "edges": edges, "state": "unavailable", "truncated": False, "repository": repository}
    graph = site.require_object(current.get("graph"))
    partial = not isinstance(current.get("graph"), dict) or any(not isinstance(graph.get(key), list) for key in ("sources", "entities", "relationships"))
    sources, repeated_sources = {}, set()
    for value in site.require_list(graph.get("sources")):
        if not isinstance(value, dict) or value.get("visibility") != "public":
            continue
        try:
            owner = text(value.get("repository"), 240)
            if REPOSITORY.fullmatch(owner):
                identifier = text(value.get("id"))
                if identifier in sources:
                    repeated_sources.add(identifier)
                else:
                    sources[identifier] = {"id": identifier, "repository": owner,
                        "href": github_href(value.get("url"), owner)}
        except ValueError:
            partial = True
            continue
    for identifier in repeated_sources:
        sources.pop(identifier, None)
        partial = True
    entities, duplicate_ids = {}, set()
    for value in site.require_list(graph.get("entities")):
        try:
            node = public_entity(value)
            if node is not None:
                identifier = node["entity_id"]
                if identifier in entities:
                    duplicate_ids.add(identifier)
                else:
                    node["href"] = _entity_href(node, current, repository, prefix)
                    node["description"] = node["entity_kind"].replace("_", " ") + " · " + node["assertion"] + " · " + node["freshness"]
                    entities[identifier] = node
        except (ValueError, TypeError, KeyError):
            partial = True
            continue
    for identifier in duplicate_ids:
        entities.pop(identifier, None)
        partial = True
    ordered = sorted(entities.values(), key=lambda value: (value["repository"] != repository, value["entity_kind"], value["entity_id"]))
    admitted = ordered[:min(MAX_ENTITIES, MAX_NODES - len(nodes))]
    canonical = {node["entity_id"]: node for node in admitted}
    nodes.extend(admitted)
    for node in admitted:
        if node["repository"] == repository:
            edges.append({"id": "navigation:contains:" + node["id"], "source": "navigation:repository", "target": node["id"],
                          "label": "contains projected entity", "kind": "navigation", "assertion": "presentation",
                          "freshness": "not_applicable", "provenance": []})
    declared, repeated = {}, set()
    for value in site.require_list(graph.get("relationships")):
        if not isinstance(value, dict):
            continue
        # Unadmitted endpoints are filtered before IDs, type, counts or source expansion.
        if (not isinstance(value.get("source"), str) or not isinstance(value.get("target"), str)
                or value["source"] not in canonical or value["target"] not in canonical):
            continue
        try:
            identifier = text(value.get("id"))
            kind = text(value.get("type"), 64)
            provenance = value.get("provenance")
            if (kind not in RELATIONSHIPS or value.get("direction") != "directed"
                    or value.get("assertion") not in ASSERTIONS or value.get("freshness") not in FRESHNESS
                    or not isinstance(provenance, list) or not provenance):
                partial = True
                continue
            # Restricted or unprojected sources do not alter public state/counts.
            if any(not isinstance(source, str) or source not in sources for source in provenance):
                continue
            edge = {"id": "declared:" + identifier, "source": canonical[value["source"]]["id"],
                    "target": canonical[value["target"]]["id"], "label": kind, "kind": "declared",
                    "assertion": value["assertion"], "freshness": value["freshness"],
                    "provenance": [sources[source] for source in sorted(set(provenance))]}
            if identifier in declared:
                repeated.add(identifier)
            else:
                declared[identifier] = edge
        except (ValueError, TypeError, KeyError):
            partial = True
            continue
    for identifier in repeated:
        declared.pop(identifier, None)
        partial = True
    explicit = [declared[key] for key in sorted(declared)]
    available = MAX_EDGES - len(edges)
    edges.extend(explicit[:max(0, available)])
    return {"nodes": nodes, "edges": edges, "state": "partial" if partial else "available", "repository": repository,
            "truncated": len(ordered) > len(admitted) or len(explicit) > available}


def _link(node: dict, content: str) -> str:
    if not node.get("href"):
        return content
    context = ' data-preserve-context' if not node["href"].startswith("https://") else ""
    return f'<a href="{site.escaped(node["href"])}"{context}>{content}</a>'


def graph_body(snapshot: dict | None, repository: str, prefix: str = "") -> str:
    """Keep the same graph and evidence directories in static/no-script output."""
    model = graph_model(snapshot, repository, prefix)
    nodes, edges = model["nodes"], model["edges"]
    rows = {"view": 0, "repository": 0, "entity": 0}
    columns = {"repository": 0, "view": 1, "entity": 2}
    positions = {}
    for node in nodes:
        positions[node["id"]] = (180 + columns[node["kind"]] * 370, 100 + rows[node["kind"]] * 94)
        rows[node["kind"]] += 1
    svg_nodes, directory, options = [], [], []
    for node in nodes:
        x, y = positions[node["id"]]
        fragment = site.stable_fragment("graph-node", node["id"])
        entity = f' data-entity-id="{site.escaped(node["entity_id"])}"' if "entity_id" in node else ""
        attributes = (f'data-ri-graph-node="{site.escaped(node["id"])}" data-ri-graph-label="{site.escaped(node["label"])}" '
                      f'data-ri-graph-kind="{site.escaped(node["kind"])}" data-ri-graph-state="{site.escaped(node["state"])}" '
                      f'data-ri-graph-x="{x}" data-ri-graph-y="{y}" data-source-repository="{site.escaped(node["repository"])}"{entity}')
        label = site.escaped(node["label"][:34] + ("…" if len(node["label"]) > 34 else ""))
        content = (f'<rect x="{x - 145}" y="{y - 34}" width="290" height="68" rx="10"></rect>'
                   f'<text x="{x - 132}" y="{y - 10}" class="ri-graph-node-kind">{site.escaped(node["kind"])} · {site.escaped(node["state"])}</text>'
                   f'<text x="{x - 132}" y="{y + 15}" class="ri-graph-node-label">{label}</text>'
                   f'<title>{site.escaped(node["label"])} · {site.escaped(node["description"])}</title>')
        svg_nodes.append(f'<g class="ri-graph-node" {attributes}>{_link(node, content)}</g>')
        source = node.get("source_href")
        source_link = f'<a href="{site.escaped(source)}">Canonical source</a>' if source else ""
        directory.append(f'<li id="{site.escaped(fragment)}" data-ri-graph-directory-node="{site.escaped(node["id"])}" data-source-repository="{site.escaped(node["repository"])}"{entity}><strong>{_link(node, site.escaped(node["label"]))}</strong><p>{site.escaped(node["kind"])} · {site.escaped(node["state"])} · {site.escaped(node["description"])}</p>{source_link}<button class="ri-button ri-button--quiet" type="button" data-ri-graph-inspect="{site.escaped(node["id"])}" hidden>Inspect connections</button></li>')
        options.append(f'<option value="{site.escaped(node["id"])}">{site.escaped(node["kind"])}: {site.escaped(node["label"])}</option>')
    svg_edges, relationships = [], []
    for edge in edges:
        source = next(node for node in nodes if node["id"] == edge["source"])
        target = next(node for node in nodes if node["id"] == edge["target"])
        sx, sy = positions[source["id"]]
        tx, ty = positions[target["id"]]
        path = f'M {sx} {sy} C {sx + 180} {sy}, {tx - 180} {ty}, {tx} {ty}'
        if source["id"] == target["id"]:
            path = f'M {sx + 140} {sy} C {sx + 230} {sy - 100}, {sx - 230} {sy - 100}, {sx - 140} {sy}'
        arrow = ' marker-end="url(#ri-repository-graph-arrow)"' if edge["kind"] == "declared" else ""
        label = f'{source["label"]} → {target["label"]}: {edge["label"]} · {edge["kind"]} · {edge["assertion"]} · {edge["freshness"]}'
        svg_edges.append(f'<g class="ri-graph-edge" data-ri-graph-edge="{site.escaped(edge["id"])}" data-ri-graph-source="{site.escaped(edge["source"])}" data-ri-graph-target="{site.escaped(edge["target"])}" data-kind="{site.escaped(edge["kind"])}"><title>{site.escaped(label)}</title><path d="{path}"{arrow}></path></g>')
        provenance_items = []
        for value in edge["provenance"]:
            source_text = site.escaped(value["id"])
            if value["href"]:
                source_text = f'<a href="{site.escaped(value["href"])}">{source_text}</a>'
            provenance_items.append(f'<li data-source-repository="{site.escaped(value["repository"])}">{source_text}</li>')
        provenance = "".join(provenance_items)
        relationships.append(f'<li data-ri-graph-directory-edge="{site.escaped(edge["id"])}"><strong>{site.escaped(source["label"])} → {site.escaped(target["label"])}</strong><p>{site.escaped(edge["label"])} · {site.escaped(edge["kind"])} · Assertion: {site.escaped(edge["assertion"])} · Freshness: {site.escaped(edge["freshness"])}</p>{f"<details><summary>Canonical provenance</summary><ul>{provenance}</ul></details>" if provenance else ""}</li>')
    boundary = ("Only navigation is available. No accepted public semantic snapshot is connected."
                if model["state"] == "unavailable" else "Some public graph input is incompatible; retained records remain available."
                if model["state"] == "partial" else "Nodes and declared arrows retain the represented snapshot's state, assertion and freshness.")
    bounded = '<p class="ri-graph-note">This graph is a bounded presentation. Follow the focused views and canonical sources for complete inventories.</p>' if model["truncated"] else ""
    return f'''{BEGIN}
<section class="ri-section ri-repository-graph" data-ri-graph data-ri-graph-state="{site.escaped(model['state'])}" data-ri-graph-root="{site.escaped(prefix or './')}" data-ri-graph-height="{max(600, 150 + max(rows.values()) * 94)}" aria-labelledby="repository-graph-heading">
  <div class="ri-section-heading"><div><span class="ri-eyebrow">Repository navigation</span><h2 id="repository-graph-heading">Explore the connected views</h2></div><p>{boundary}</p></div>
  <p class="ri-graph-note">Dashed lines open views or group projected entities. Solid arrows are explicit relationships, directed source → target. Position never establishes dependency, causality, completion or approval.</p>
  <div class="ri-graph-controls" data-ri-graph-controls hidden><label>Inspect a node<select data-ri-graph-select><option value="">Choose a destination</option>{"".join(options)}</select></label><label><input type="checkbox" data-ri-graph-neighbors disabled>Selected connections only</label><div role="group" aria-label="Graph controls"><button type="button" data-ri-graph-action="in" aria-label="Zoom in">+</button><button type="button" data-ri-graph-action="out" aria-label="Zoom out">−</button><button type="button" data-ri-graph-action="fit">Fit graph</button><button type="button" data-ri-graph-action="reset">Reset</button><button type="button" data-ri-graph-action="left" aria-label="Pan left">←</button><button type="button" data-ri-graph-action="up" aria-label="Pan up">↑</button><button type="button" data-ri-graph-action="down" aria-label="Pan down">↓</button><button type="button" data-ri-graph-action="right" aria-label="Pan right">→</button></div></div>
  <p class="ri-graph-note" id="repository-graph-instructions">Open a graph link to navigate. With JavaScript, select a node to inspect connections; focus the canvas for arrow-key pan, +/− zoom, Home reset and F fit. The directories below work without JavaScript.</p>
  <div class="ri-graph-canvas"><svg viewBox="0 0 1200 600" role="group" aria-label="Repository Intelligence navigation graph" aria-describedby="repository-graph-instructions" data-ri-graph-svg><defs><marker id="ri-repository-graph-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z"></path></marker></defs><g aria-hidden="true">{"".join(svg_edges)}</g><g>{"".join(svg_nodes)}</g></svg></div>
  <p class="ri-graph-note" data-ri-graph-status role="status" aria-live="polite">{len(nodes)} public navigation/evidence nodes · {len(edges)} presentation/declared connections.</p>{bounded}
  <aside class="ri-panel ri-graph-inspector" data-ri-graph-inspector hidden aria-labelledby="repository-graph-selected"><h3 id="repository-graph-selected" data-ri-graph-selected>Inspect a node</h3><p data-ri-graph-selected-detail></p><div data-ri-graph-selected-links></div><ul data-ri-graph-selected-edges></ul></aside>
  <div class="ri-graph-directories"><details open><summary>Node directory</summary><ul>{"".join(directory)}</ul></details><details open><summary>Relationship directory</summary><ul>{"".join(relationships)}</ul></details></div>
</section>
{END}'''


def enhance_document(document: str, snapshot: dict | None, repository: str, prefix: str = "") -> str:
    body = graph_body(snapshot, repository, prefix)
    if BEGIN in document or END in document:
        if document.count(BEGIN) != 1 or document.count(END) != 1:
            raise ValueError("GRAPH_DOCUMENT")
        start, finish = document.index(BEGIN), document.index(END) + len(END)
        if start >= finish:
            raise ValueError("GRAPH_DOCUMENT")
        document = document[:start] + body + document[finish:]
    else:
        markers = ('<main id="main-content" tabindex="-1">', '<main id="main-content" class="shell">')
        marker = next((value for value in markers if document.count(value) == 1), None)
        if marker is None:
            raise ValueError("GRAPH_DOCUMENT")
        document = document.replace(marker, marker + body, 1)
    stylesheet = f'<link rel="stylesheet" href="{prefix}graph.css">'
    script = f'<script src="{prefix}graph.js" defer></script>'
    if stylesheet not in document:
        document = document.replace("</head>", stylesheet + "\n  </head>", 1)
    if script not in document:
        document = document.replace("</body>", script + "\n  </body>", 1)
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ("repository-root", "output-root", "summary", "provenance", "repository", "source-commit"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--snapshot", default="")
    parser.add_argument("--target", choices=("overview", "dependencies", "dashboard", "both", "all"), default="both")
    args = parser.parse_args()
    try:
        root = Path(args.repository_root).absolute()
        output = Path(args.output_root).absolute()
        paths = [Path(args.summary).absolute(), Path(args.provenance).absolute()]
        snapshot_path = Path(args.snapshot).absolute() if args.snapshot else None
        if snapshot_path:
            paths.append(snapshot_path)
        if not site.FULL_SHA.fullmatch(args.source_commit) or output.relative_to(root).parts[0] in {".git", ".github", "actions", "schemas", "scripts", "tests"}:
            raise ValueError("GRAPH_INPUT")
        for path in (root, output, *paths):
            if ".." in path.parts or any(parent.is_symlink() for parent in (path, *path.parents)):
                raise ValueError("GRAPH_PATH")
            site.validate_repository_path(root, path, "graph input/output")
        if any(not path.is_file() or path.stat().st_size > MAX_INPUT for path in paths):
            raise ValueError("GRAPH_INPUT")
        summary = site.load_object(paths[0], "dashboard summary")
        provenance = site.load_object(paths[1], "bundle provenance")
        site.validate_site_contracts(summary, provenance, args.repository, args.source_commit)
        snapshot = site.validate_snapshot(site.load_object(snapshot_path, "Observatory snapshot"), args.repository, args.source_commit) if snapshot_path else None
        targets = []
        if args.target in {"overview", "both", "all"}:
            targets.append((output / "index.html", ""))
        if args.target in {"dependencies", "all"}:
            targets.append((output / "dependencies/index.html", "../"))
        if args.target in {"dashboard", "both", "all"}:
            targets.append((output / "dashboard/index.html", "../"))
        owned = [path for path, _ in targets] + [output / "graph.js", output / "graph.css"]
        for path in owned:
            site.validate_repository_path(root, path, "graph output")
            if path in paths or path.is_symlink() or (path.exists() and not path.is_file()):
                raise ValueError("GRAPH_PATH")
        tracked = subprocess.check_output(["git", "--no-optional-locks", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", "-C", str(root), "ls-files", "--", *[str(path.relative_to(root)) for path in owned]], stderr=subprocess.DEVNULL)
        if tracked:
            raise ValueError("GRAPH_PATH")
        rendered = []
        for path, prefix in targets:
            if not path.is_file() or path.stat().st_size > MAX_INPUT:
                raise ValueError("GRAPH_DOCUMENT")
            rendered.append((path, enhance_document(path.read_text(encoding="utf-8"), snapshot, args.repository, prefix)))
        for path, content in rendered:
            site.atomic_write(path, content)
        for name in ("graph.js", "graph.css"):
            site.atomic_write(output / name, (ASSETS / name).read_text(encoding="utf-8"))
        print("Repository graph: portable overview enhancement prepared")
        return 0
    except Exception:
        print("Repository graph: input or rendering denied", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
