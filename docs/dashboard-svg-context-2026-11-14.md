# Complete dashboard SVG context initialization

[Relay #189](https://github.com/egohygiene/relay/issues/189) remains open for
actual final consumer acceptance. The earlier site/graph repair did not cover
`explorer.js`, which the compatibility dashboard loads instead of `site.js`.
Its duplicate context loop still assigned getter-only native SVG `href`
properties. Actual S3 browser checks exposed the dashboard exception; that
source's successful owner/producer/publication work does not erase the finding.

Exactly two explorer writes now use `setAttribute("href", ...)`. Validated URL
construction and context allowlists remain unchanged. Accepted site/graph
assets stay byte-identical. The complete href audit classifies the remaining
four Relay property writers as HTML anchors: three explicitly created with
`document.createElement("a")`, and the generated `<a data-resume-link>`.
Graph Python `node["href"]` is data mapping, not a DOM writer. All five mixed
HTML/SVG writes now use the common native attribute operation.

The [bounded evidence](evidence/2026-11-14-dashboard-svg-context.json) binds clean
functional `e2f7062b29a320153881ef0f2343cf8a4db23e9c` on accepted base
`2d0d88bdcfa1c9614a9a6bf7f66b26a397dfec2a`. The checked-in real Chromium driver
visits every declared generated page, including all three JavaScript asset
sets and the actual overview/dependencies/dashboard graph placements. It
verifies served script bytes and zero page errors, then tests initial dashboard
HTML-directory query/entity context **before focus can repair a link**, real
SVG focus, pointer navigation and Enter. The existing shared filter, entity,
hash and HTML/SVG parity regression remains. All 18 declared pages and 23
assertions pass; the original explorer script fails initial query/entity
context with both values absent.

The focused dashboard suite passes 23 methods and context checks pass three,
with no skips. Node syntax, scoped Ruff, Python compilation and whitespace
checks pass. Previously recorded broader catalog/Hygiene route-lock findings
remain separate; no broad whole-suite green result is claimed.

The actual S3 dashboard does not select optional tree controls. Its defect is
failed context-link initialization and TypeErrors, not a demonstrated live
tree-filter failure. Local generated/retained-consumer browser fixtures stay
separate from canonical publication and a new immutable consumer source cycle.
UI layout redesign, full accessibility and human acceptance remain outside this
runtime correction.

An independent local witness uses exact retained S3 source
`88667126133cdec5843bf22a09b1ef40b493f5f9`, run `43560603493/1`, manifest
`0e5a33806a8009a5bd775923b26c65573a801dbad383ee8053e91ef0694c46bc`.
Only the candidate explorer asset is substituted; HTML, CSS, data and accepted
site/graph scripts are unchanged. All 18 published Intelligence HTML routes
return 200 with no candidate page errors. Original explorer produces four SVG
TypeErrors across the witness and misses initial directory context; native
focus/pointer/Enter already work under the earlier graph repair and are not
misreported as new failures. The candidate passes initial context and those
controls. This derived local fixture is neither a canonical deployment nor a
new valid composed bundle.

A separate independent audit inventories all 18 JavaScript assets in the actual
composed S3 site, including preserved Quartz assets, and pairs the source audit
with native DOM inspection on all 37 retained HTML pages. The original site has
11 direct href property writes: two unsafe explorer writes, four Relay HTML
anchor writes and five Quartz HTML/template or `window.location.href` writes.
The correction leaves nine legitimate property writes; all 37 candidate pages
have zero application page errors. Native resume and cloned-template anchors
are verified as HTML elements. All other fixture bytes are unchanged. This is
bounded existing-asset/DOM evidence, not a guarantee about future markup,
optional unselected tree behavior or canonical S4 publication.
