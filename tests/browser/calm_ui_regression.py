#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT
"""Check the actual static repository UI at desktop, tablet and mobile widths.

Default input is the existing explicitly synthetic renderer fixture. Optional
--retained-context consumes a previously retained mindgarden directory containing
site/intelligence, repository-intelligence/sources/snapshot.json and review-feed.
It rerenders through production functions with unchanged captured model bytes.
Neither mode is a sealed bundle, canonical HTTPS or publication qualification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svg_context_regression import QuietHandler, build_fixture
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_repository_intelligence_site import ACTION_ROOT, load_module


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def retained_fixture(context: Path, output: Path):
    """Use real captured inputs without changing their source, clocks or claims."""
    source = context / "site/intelligence"
    target = output / "intelligence"
    shutil.copytree(source, target)
    # The old manifest describes old rendered bytes. A UI fixture cannot reuse it.
    (target / "build-manifest.json").unlink()
    site = load_module("calm_retained_site", ACTION_ROOT / "scripts/generate_repository_intelligence_site.py")
    summary = site.load_object(source / "summary.json", "retained dashboard")
    provenance = site.load_object(source / "provenance.json", "retained provenance")
    repository, commit = summary["repository"]["name"], summary["repository"]["source_commit"]
    site.validate_site_contracts(summary, provenance, repository, commit)
    snapshot_path = context / "repository-intelligence/sources/snapshot.json"
    snapshot = site.validate_snapshot(site.load_object(snapshot_path, "retained snapshot"), repository, commit)
    models, receipts, inputs = {}, {}, [source / "summary.json", source / "provenance.json", snapshot_path]
    for identifier, filename in (("audits", "repository-audits.json"), ("sanity", "repository-sanity.json")):
        path = context / "review-feed" / filename
        if path.is_file():
            models[identifier], receipts[identifier] = site.owner_views.helper(identifier).validate_input(
                path, repository, commit, summary["generated_at"])
            inputs.append(path)
    site.write_site(output_root=target, summary=summary, provenance=provenance, snapshot=snapshot,
                    repository=repository, source_commit=commit,
                    stylesheet_source=ACTION_ROOT / "assets/site.css", script_source=ACTION_ROOT / "assets/site.js",
                    owner_models=models, owner_receipts=receipts)
    for identifier, filename in (("dependencies", "dependencies_route"), ("health", "health"),
                                 ("work", "work"), ("releases", "releases"), ("search", "search"),
                                 ("compare", "compare")):
        renderer = load_module("calm_retained_" + identifier,
                               ACTION_ROOT / f"scripts/render_repository_intelligence_{filename}.py")
        arguments = dict(snapshot=snapshot, summary=summary, repository=repository, source_commit=commit)
        if identifier == "compare":
            # The selected captured input has no comparison. Do not invent one.
            assert "Comparison evidence unavailable" in (source / "compare/index.html").read_text()
            arguments["comparison"] = None
        (target / identifier / "index.html").write_text(renderer.render_page(**arguments), encoding="utf-8")
    dashboard = load_module("calm_retained_dashboard", ACTION_ROOT / "scripts/generate_repository_intelligence_dashboard.py")
    (target / "dashboard/index.html").write_text(dashboard.render_html(
        summary, "../", "styles.css", include_shell_navigation=True), encoding="utf-8")
    shutil.copyfile(ACTION_ROOT / "assets/dashboard.css", target / "styles.css")
    graph = load_module("calm_retained_graph", ACTION_ROOT / "scripts/render_repository_intelligence_graph.py")
    for relative, prefix in (("index.html", ""), ("dashboard/index.html", "../")):
        path = target / relative
        path.write_text(graph.enhance_document(path.read_text(), snapshot, repository, prefix,
                                               owner_views=receipts), encoding="utf-8")
    for name in ("graph.js", "graph.css", "explorer.js"):
        shutil.copyfile(ACTION_ROOT / "assets" / name, target / name)
    return {"repository": repository, "represented_commit": commit,
            "inputs": {str(path.relative_to(context)): sha(path) for path in inputs},
            "scope": "production rerender of retained captured inputs; no new normalization or publication",
            "old_manifest_reused": False}


def browser_check(output: Path):
    from playwright.sync_api import sync_playwright

    result = {"checks": [], "layouts": [], "page_errors": [], "console_errors": [], "failed_requests": []}
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(output)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    routes = json.loads((output / "intelligence/routes.json").read_text())["routes"]
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=shutil.which("chromium"))
            page = browser.new_page(reduced_motion="reduce")
            page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            page.on("console", lambda message: result["console_errors"].append(message.text) if message.type == "error" else None)
            page.on("requestfailed", lambda request: result["failed_requests"].append(request.url))
            for width, height in ((1440, 1000), (768, 1024), (390, 844)):
                page.set_viewport_size({"width": width, "height": height})
                for route in routes:
                    path = route["relative_file"].removesuffix("index.html")
                    response = page.goto(origin + "/intelligence/" + path, wait_until="networkidle")
                    assert response and response.status == 200, path
                    # Exercise every native navigation group, not just its closed footprint.
                    for disclosure in page.locator("nav[data-preserve-context-links] > details").all():
                        disclosure.evaluate("element => { element.open = true; }")
                    dimensions = page.evaluate("({viewport:innerWidth,document:document.documentElement.scrollWidth})")
                    result["layouts"].append({"route": path or "overview", "width": width, **dimensions})
                    assert dimensions["document"] <= dimensions["viewport"] + 1, result["layouts"][-1]
                    current = page.locator('nav[data-preserve-context-links] a[aria-current="page"]')
                    assert current.count() == 1 and current.is_visible(), path
            result["checks"].append("all declared routes initialize and expanded navigation stays bounded at three widths")
            page.goto(origin + "/intelligence/?q=repository&entity=fixture-context", wait_until="networkidle")
            assert page.locator('.ri-overview-grid > article').count() == 3
            disclosure = page.locator('[data-ri-graph-disclosure]')
            assert not disclosure.evaluate("element => element.open")
            assert page.locator('#intelligence-heading').evaluate(
                "element => element.compareDocumentPosition(document.querySelector('[data-ri-graph-disclosure]')) & Node.DOCUMENT_POSITION_FOLLOWING")
            summary = disclosure.locator(":scope > summary")
            summary.focus()
            page.keyboard.press("Enter")
            assert disclosure.evaluate("element => element.open")
            svg_link = page.locator('[data-ri-graph-node="navigation:dependencies"] a')
            svg_link.focus()
            page.keyboard.press("Enter")
            page.wait_for_url("**/intelligence/dependencies/**")
            assert page.evaluate("new URL(location.href).searchParams.get('q')") == "repository"
            assert page.evaluate("new URL(location.href).searchParams.get('entity')") == "fixture-context"
            result["checks"].append("optional graph follows home content and keyboard disclosure/SVG Enter preserve context")
            page.goto(origin + "/intelligence/?graph=navigation:dependencies", wait_until="networkidle")
            assert page.locator('[data-ri-graph-disclosure]').evaluate("element => element.open")
            result["checks"].append("explicit graph selection opens its native disclosure")
            for route in ("audits", "sanity", "dashboard"):
                page.goto(origin + "/intelligence/" + route + "/?q=repository&entity=fixture-context", wait_until="networkidle")
                nav = page.locator('nav[data-preserve-context-links]')
                assert nav.locator('a[aria-current="page"]').is_visible()
                nav.locator('a').filter(has_text="Overview").click()
                page.wait_for_url("**/intelligence/?**")
                assert page.evaluate("new URL(location.href).searchParams.get('entity')") == "fixture-context"
            result["checks"].append("focused owner views and alternate dashboard return with URL context intact")
            page.screenshot(path=str(output / "overview-mobile.png"), full_page=True)
            page.set_viewport_size({"width": 1440, "height": 1000})
            page.screenshot(path=str(output / "overview-desktop.png"), full_page=True)
            no_js = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
            static = no_js.new_page()
            for route in ("", "audits/", "sanity/", "dashboard/"):
                static.goto(origin + "/intelligence/" + route, wait_until="networkidle")
                for item in static.locator('nav[data-preserve-context-links] > details').all():
                    # Native summary activation works without browser scripting.
                    if item.get_attribute("open") is None:
                        item.locator(":scope > summary").click()
                assert static.locator('nav[data-preserve-context-links] a').count() == len(routes)
                if not route:
                    static.locator('[data-ri-graph-disclosure] > summary').click()
                    assert static.locator('[data-ri-graph-directory-node="navigation:dependencies"] strong a').is_visible()
                    static.locator('[data-ri-graph-directory-node="navigation:dependencies"] strong a').click()
                    static.wait_for_url("**/intelligence/dependencies/")
            result["checks"].append("all navigation and graph directories remain usable without JavaScript")
            result["browser"] = browser.version
            no_js.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert not result["page_errors"], result["page_errors"]
    assert not result["console_errors"], result["console_errors"]
    assert not result["failed_requests"], result["failed_requests"]
    result["outcome"] = "passed"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--retained-context", type=Path)
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("output must be empty; retained evidence is never overwritten")
    args.output.mkdir(parents=True, exist_ok=True)
    if args.retained_context:
        inputs = retained_fixture(args.retained_context, args.output)
    else:
        build_fixture(args.output, None, None, None)
        (args.output / "intelligence/build-manifest.json").unlink()
        inputs = {"scope": "existing explicitly synthetic production-renderer fixture", "old_manifest_reused": False}
    result = {"input": inputs, **browser_check(args.output)}
    (args.output / "browser-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"outcome": result["outcome"], "checks": result["checks"], "layouts": len(result["layouts"])}))


if __name__ == "__main__":
    main()
