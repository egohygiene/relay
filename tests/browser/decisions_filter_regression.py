#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT
"""Build a standalone browser regression using the real Decisions renderer.

Run: python3 tests/browser/decisions_filter_regression.py --output /tmp/decisions-filter.html
Open that file in a browser. The visible report must pass every check.
--stylesheet-source can select pre-fix CSS to demonstrate the regression.
This command builds the fixture; it does not execute or emulate a browser.
"""

import argparse
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_repository_intelligence_site import RepositoryIntelligenceSiteTests


ASSERTIONS = r'''
(() => {
    const report = document.getElementById("browser-regression-report");
    const results = report.querySelector("ol");
    const records = [...document.querySelectorAll("[data-decision-record]")];
    const query = document.querySelector("[data-filter-query]");
    const state = document.querySelector("[data-filter-state]");
    const implementation = document.querySelector('[data-filter-extra="implementation"]');
    const reset = document.querySelector("[data-filter-reset]");
    const count = document.querySelector("[data-filter-results]");
    const visible = (node) => getComputedStyle(node).display !== "none" &&
        getComputedStyle(node).visibility !== "hidden" && node.getClientRects().length > 0;
    const select = (node, value, event) => {
        node.value = value;
        node.dispatchEvent(new Event(event, { bubbles: true }));
    };
    const check = (condition, message) => { if (!condition) throw new Error(message); };
    const expect = (predicate, label) => {
        for (const record of records) {
            const expected = predicate(record);
            check(visible(record) === expected, `${label}: record ${record.dataset.decisionId}`);
            check(visible(record.querySelector("h3")) === expected,
                `${label}: heading ${record.dataset.decisionId}`);
        }
    };
    let failures = 0;
    const test = (label, callback) => {
        const row = document.createElement("li");
        try { reset.click(); callback(); row.textContent = `PASS — ${label}`; }
        catch (error) { failures++; row.textContent = `FAIL — ${label}: ${error.message}`; }
        results.append(row);
    };
    test("initial/reset view shows all six generated records", () => {
        check(records.length === 6, "expected the existing six-record fixture");
        expect(() => true, "reset");
    });
    test("single-record search hides other cards and headings", () => {
        select(query, "ADR-007", "input");
        check(count.value === "1 matching records", "search result count");
        expect(record => record.dataset.decisionId.endsWith(":ADR-007"), "search");
    });
    test("state selection hides nonmatching cards and headings", () => {
        select(state, "proposed", "change");
        check(count.value === "1 matching records", "state result count");
        expect(record => record.dataset.state === "proposed", "state");
    });
    test("implementation facet hides nonmatching cards and headings", () => {
        select(implementation, "verified", "change");
        check(count.value === "2 matching records", "facet result count");
        expect(record => record.dataset.filterImplementation === "verified", "facet");
    });
    test("no matches hides every card and shows the empty state", () => {
        select(query, "no-such-decision-139", "input");
        check(count.value === "0 matching records", "empty result count");
        expect(() => false, "empty");
        check(visible(document.querySelector("[data-no-results]")), "empty state must be visible");
    });
    test("reset restores cards and hides the empty state", () => {
        expect(() => true, "final reset");
        check(count.value === "Showing the full view", "reset result count");
        check(!visible(document.querySelector("[data-no-results]")), "empty state must be hidden");
    });
    report.dataset.result = failures ? "failed" : "passed";
    report.querySelector("h1").textContent = failures ?
        `FAIL: ${failures} of 6 browser visibility checks` : "PASS: 6 browser visibility checks";
})();
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stylesheet-source", type=Path)
    args = parser.parse_args()
    fixture = RepositoryIntelligenceSiteTests()
    fixture.setUp()
    try:
        bundle = fixture.build("dist/intelligence")
        html = (bundle / "decisions/index.html").read_text(encoding="utf-8")
        css = (args.stylesheet_source or bundle / "site.css").read_text(encoding="utf-8")
        script = (bundle / "site.js").read_text(encoding="utf-8")
        html, styles = re.subn(r'<link rel="stylesheet" href="\.\./site\.css">',
                               lambda _: f"<style>{css}</style>", html)
        html, scripts = re.subn(r'<script\b[^>]*\bsrc="\.\./site\.js"[^>]*></script>', "", html)
        assert styles == scripts == 1, "generated asset references changed"
        report = ('<section id="browser-regression-report" style="position:relative;z-index:100;'
                  'padding:1rem;background:white;color:black"><h1>RUNNING browser visibility checks</h1>'
                  '<p>Real generated Decisions markup and production CSS/JS; checks include computed style '
                  'and layout boxes, not only the hidden property.</p><ol></ol></section>')
        html = re.sub(r'(<body\b[^>]*>)', lambda match: match[0] + report, html, count=1)
        html = html.replace("</body>", "<script>" + script.replace("</script", "<\\/script") +
                            "</script><script>" + ASSERTIONS + "</script></body>")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(html, encoding="utf-8")
        print(args.output)
    finally:
        fixture.doCleanups()


if __name__ == "__main__":
    main()
