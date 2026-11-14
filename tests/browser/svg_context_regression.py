#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT
"""Exercise production HTML/SVG context links in a real Chromium DOM.

Run with Python Playwright and an installed Chromium browser:
python3 tests/browser/svg_context_regression.py --output /tmp/svg-context

The fixture scans every declared generated page and script, including the
compatibility dashboard using explorer.js instead of site.js. It composes the
real graph placements and an additional Roadmap stress case with the existing
public snapshot. It does not emulate SVG DOM properties or replace production
handlers. Optional script inputs demonstrate the pre-fix failure. This local
fixture is separate from any consumer publication or canonical live proof.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_repository_intelligence_site import (
    ACTION_ROOT,
    RepositoryIntelligenceSiteTests,
    load_module,
)


class QuietHandler(SimpleHTTPRequestHandler):
    """Keep the machine-readable result separate from HTTP access logs."""

    def log_message(self, format: str, *args: object) -> None:
        pass


def build_fixture(output: Path, site_script: Path | None, graph_script: Path | None,
                  explorer_script: Path | None) -> None:
    fixture = RepositoryIntelligenceSiteTests()
    fixture.setUp()
    try:
        bundle = fixture.build("dist/intelligence")
        graph = load_module(
            "svg_context_graph",
            ACTION_ROOT / "scripts/render_repository_intelligence_graph.py",
        )
        # The first three are actual production graph targets. Roadmap adds a
        # real-renderer stress case for shared filter/hash/entity initialization.
        for relative, prefix in (("index.html", ""), ("dependencies/index.html", "../"),
                                 ("dashboard/index.html", "../"), ("roadmap/index.html", "../")):
            document = bundle / relative
            document.write_text(
                graph.enhance_document(
                    document.read_text(encoding="utf-8"),
                    {**fixture.snapshot, "visibility": "public"},
                    "example/repository",
                    prefix,
                ),
                encoding="utf-8",
            )
        for name, source in (
            ("site.js", site_script or ACTION_ROOT / "assets/site.js"),
            ("graph.js", graph_script or ACTION_ROOT / "assets/graph.js"),
            ("explorer.js", explorer_script or ACTION_ROOT / "assets/explorer.js"),
            ("graph.css", ACTION_ROOT / "assets/graph.css"),
        ):
            shutil.copyfile(source, bundle / name)
        shutil.copytree(bundle, output / "intelligence", dirs_exist_ok=True)
    finally:
        fixture.doCleanups()


def run_browser(output: Path) -> dict:
    from playwright.sync_api import sync_playwright

    handler = partial(QuietHandler, directory=str(output))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    result = {"transport": "local-http", "page_errors": [], "checks": [], "routes": [], "scripts": {}}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=shutil.which("chromium"))
            page = browser.new_page()
            page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            origin = f"http://127.0.0.1:{server.server_port}"
            routes = json.loads((output / "intelligence/routes.json").read_text())["routes"]
            for route in routes:
                relative = route["relative_file"]
                target = origin + "/intelligence/" + relative.removesuffix("index.html")
                response = page.goto(target, wait_until="networkidle")
                assert response is not None and response.status == 200, relative
                scripts = page.locator("script[src]").evaluate_all("nodes => nodes.map(node => node.src)")
                result["routes"].append({"file": relative, "scripts": [urlparse(url).path for url in scripts]})
                for url in scripts:
                    path = urlparse(url).path
                    assert url.startswith(origin + "/intelligence/") and ".." not in path.split("/"), url
                    served = page.request.get(url)
                    assert served.status == 200 and served.body() == (output / path.lstrip("/")).read_bytes(), path
                    result["scripts"][path] = "exact served bytes"
            assert {"/intelligence/site.js", "/intelligence/explorer.js", "/intelligence/graph.js"} <= set(result["scripts"])
            result["checks"].append("every declared page and all referenced script bytes initialize")
            dashboard = origin + "/intelligence/dashboard/?q=bridge&entity=fixture-context"
            page.goto(dashboard, wait_until="networkidle")
            assert page.locator('script[src="../explorer.js"]').count() == 1
            assert page.locator('script[src="../site.js"]').count() == 0
            directory = page.locator('[data-ri-graph-directory-node="navigation:dependencies"] strong a')
            initial = directory.evaluate("el => { const url = new URL(el.getAttribute('href'),location.href); return {q:url.searchParams.get('q'),entity:url.searchParams.get('entity')}; }")
            assert initial == {"q": "bridge", "entity": "fixture-context"}, initial
            result["checks"].append("dashboard explorer initializes every context link before SVG focus")
            graph = page.locator("[data-ri-graph]").first
            svg_link = graph.locator('[data-ri-graph-node="navigation:dependencies"] a')
            svg_link.focus()
            assert graph.locator('h3[data-ri-graph-selected]').inner_text() == "Dependencies"
            result["checks"].append("dashboard native SVG focus inspects its destination")
            svg_link.click()
            page.wait_for_url("**/intelligence/dependencies/**")
            assert page.evaluate("new URL(location.href).searchParams.get('q')") == "bridge"
            assert page.evaluate("new URL(location.href).searchParams.get('entity')") == "fixture-context"
            result["checks"].append("dashboard native pointer navigation retains query and entity")
            page.goto(dashboard, wait_until="networkidle")
            page.locator('[data-ri-graph-node="navigation:dependencies"] a').focus()
            page.keyboard.press("Enter")
            page.wait_for_url("**/intelligence/dependencies/**")
            assert page.evaluate("new URL(location.href).searchParams.get('q')") == "bridge"
            assert page.evaluate("new URL(location.href).searchParams.get('entity')") == "fixture-context"
            result["checks"].append("dashboard native Enter navigation retains query and entity")
            page.goto(origin + "/intelligence/roadmap/", wait_until="networkidle")
            page.wait_for_function("document.querySelector('[data-ri-graph]').classList.contains('ri-graph--enhanced')")
            outcome = page.evaluate(r"""async () => {
                const checks = [];
                const check = (value, label) => {
                    if (!value) throw new Error(label);
                    checks.push(label);
                };
                const graph = document.querySelector('[data-ri-graph]');
                const svg = graph.querySelector('[data-ri-graph-svg]');
                const node = graph.querySelector('[data-ri-graph-node][data-entity-id]');
                check(node !== null, 'real generated graph includes an entity');
                const link = node.querySelector('a');
                check(link instanceof SVGAElement, 'target is a native SVG anchor');
                const directory = [...graph.querySelectorAll('[data-ri-graph-directory-node]')]
                    .find(item => item.dataset.riGraphDirectoryNode === node.dataset.riGraphNode);
                const html = directory.querySelector('strong a');
                check(html instanceof HTMLAnchorElement, 'directory target is a native HTML anchor');
                const query = document.querySelector('[data-filter-query]');
                query.value = 'no-such-svg-context-record';
                query.dispatchEvent(new Event('input', { bubbles: true }));
                check(document.querySelector('[data-filter-results]').value === '0 matching records',
                    'shared filter handlers initialized after SVG link setup');
                document.querySelector('[data-filter-reset]').click();
                history.replaceState(null, '', '?q=bridge&state=all');
                link.focus();
                check(document.activeElement === link, 'SVG anchor accepts keyboard focus');
                check(graph.querySelector('[data-ri-graph-select]').value === node.dataset.riGraphNode,
                    'SVG focus runs the real graph inspect handler');
                const expectContext = anchor => {
                    const target = new URL(anchor.getAttribute('href'), location.href);
                    check(target.searchParams.get('q') === 'bridge', 'query preserved in link destination');
                    check(target.searchParams.get('entity') === node.dataset.entityId,
                        'graph entity preserved in link destination');
                };
                expectContext(link);
                link.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, button: 0 }));
                expectContext(link);
                // Prevent only native navigation, after real handlers execute; no production handler is replaced.
                link.addEventListener('click', event => event.preventDefault(), { once: true });
                link.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }));
                expectContext(link);
                html.focus();
                expectContext(html);
                check(new URL(html.href).href === new URL(link.getAttribute('href'), location.href).href,
                    'HTML and SVG context destinations agree');
                const record = document.querySelector('[data-roadmap-quest][data-entity-id]');
                record.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, button: 0 }));
                check(new URL(location.href).searchParams.get('entity') === record.dataset.entityId,
                    'shared entity handler initialized after SVG link setup');
                location.hash = record.id;
                await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                check(record.hasAttribute('data-context-selected'), 'hash selection retains entity context');
                check(svg.querySelectorAll('[data-ri-graph-node]').length > 0, 'graph remains rendered');
                return checks;
            }""")
            result["checks"].extend(outcome)
            result["browser"] = browser.version
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
    if result["page_errors"]:
        raise AssertionError(json.dumps(result))
    result["result"] = "passed"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--site-script-source", type=Path)
    parser.add_argument("--graph-script-source", type=Path)
    parser.add_argument("--explorer-script-source", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    build_fixture(args.output, args.site_script_source, args.graph_script_source, args.explorer_script_source)
    result = run_browser(args.output)
    (args.output / "browser-result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
