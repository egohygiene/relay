# A calmer repository entry point

The repository home now starts with three choices: pick up work in Now, check
the Roadmap, or find a canonical source through Search. The other focused views
remain in a compact directory. Shared navigation groups the remaining routes by
task, including the alternate analytics dashboard; every destination remains a
normal link in static HTML.

Source identity, original observation time, collection state and build evidence
remain visible. The collection disclosure summarizes the actual owner-projected
states before expansion, including failed, partial and uncollected domains. It
does not turn unavailable input into a clean or passing result.

The home and analytics dashboard place the optional connection graph after
their main content. A native disclosure reveals the complete graph and evidence
directories without JavaScript. An explicit supported graph selection opens it
after enhancement. Dependencies retains its focused presentation. Graph IDs,
destinations, source references, filters and URL context are preserved.

## Responsive regression

The original canonical S4 observation used Empathy source `41d4c8bdba88`, Relay
`41fe97bc69e4` and manifest `be7024621c67`. The candidate rerenders the same
retained normalized inputs through the production renderers over local HTTP.
The original observation and its clocks remain unchanged.

| View | Viewport | Original document | Candidate document |
| --- | ---: | ---: | ---: |
| Dashboard | 768 px | 853 px | 768 px |
| Overview | 390 px | 540 px | 390 px |
| Dashboard | 390 px | 540 px | 390 px |
| Audits | 390 px | 640 px | 390 px |
| Sanity | 390 px | 663 px | 390 px |

All 18 declared routes pass at 1440, 768 and 390 pixels with every navigation
group expanded. Six additional observations open the optional graphs at every
width: they remain bounded when used. The repair wraps source identifiers,
nested owner fields, controls and dashboard freshness rows within their layout;
it does not clip the document to conceal overflowing content.

Real Chromium checks native disclosure keyboard activation, SVG Enter
navigation, explicit graph selection, query/entity retention, owner-view and
dashboard return links, and no-JavaScript navigation and graph directories.
The retained-input run has zero page, console or request errors. Desktop and
mobile screenshots were inspected. The existing 23-assertion SVG regression
also passes across all 18 generated pages and three script asset sets.

## Reproduce the source UI checks

With Python Playwright and Chromium installed, use a new empty output directory:

```bash
python3 tests/browser/calm_ui_regression.py --output /tmp/intelligence-calm-ui
python3 tests/browser/svg_context_regression.py --output /tmp/intelligence-svg
```

The first command defaults to the existing explicitly synthetic renderer
fixture. Its optional `--retained-context` accepts a retained `mindgarden`
directory containing the original `site/intelligence`, captured snapshot and
review-feed inputs. It validates the inputs, calls the real renderers and
records input hashes. It removes the old build manifest: regenerated UI bytes
cannot reuse a previously sealed manifest. Inputs and original evidence are
never rewritten. Neither mode establishes publication or canonical HTTPS.

The [bounded receipt](evidence/2026-11-14-intelligence-calm-ui.json) binds the
functional source, browser results, original measurements and limitations.
Dashboard tests pass 23/23. Shared-shell tests pass 33/34; the unchanged
route-lock fixture also fails at the exact accepted base. The documented full
suite runs 725 tests with 12 failures, 24 errors and 93 skips at both revisions;
all 36 failure/error identities match. The action validator retains the same
ten pre-existing metadata/catalog findings. Compilation, graph JavaScript
syntax and whitespace checks pass. No broad green status is claimed.

## Acceptance and ownership

This advances the shared experience in [#27](https://github.com/egohygiene/relay/issues/27)
and polish in [#101](https://github.com/egohygiene/relay/issues/101), plus the
responsive/navigation clauses in [Audits #74](https://github.com/egohygiene/relay/issues/74)
and [Sanity #76](https://github.com/egohygiene/relay/issues/76). Their broader
original acceptance criteria remain open. Human ratification, normalized owner
semantics, consumer publication and fleet adoption keep their existing owners.
The sparse retained owner input is not exhaustive lifecycle or screen-reader
certification. The prior SVG correction in #189 remains covered.

Decision impact: **ADR not required**. This is presentation within the accepted
shared static shell; no route registry, schema, authority, collector, source
clock, immutable pin, publisher, permission or historical recovery boundary
changes. Consumers must separately adopt and qualify a new immutable Relay pin
before these source changes can appear on their published dashboards.
