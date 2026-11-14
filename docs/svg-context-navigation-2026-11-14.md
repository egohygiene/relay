# Native SVG context-link repair

[Relay #189](https://github.com/egohygiene/relay/issues/189) owns a functional
navigation defect exposed while qualifying [Empathy #105](https://github.com/egohygiene/empathy/issues/105).
The shared strict initializer assigned `link.href` to native SVG anchors,
whose `href` property is getter-only. The exception interrupted later shared
filter/entity/hash initialization. Graph focus, pointer and click handlers shared the same incompatible
destination write; the exception also interrupted focus inspection.

Three assignments now use the native `href` attribute for both HTML and SVG
anchors. Every existing URL construction, context allowlist, destination
validation and trust boundary remains unchanged. Production markup, schemas,
owner locks, workflow permissions and historical rollback are unchanged.

The [source-bound evidence](evidence/2026-11-14-svg-context-navigation.json)
records functional `62dd90d41264ba3100f4f1730df98a550b8a32cf` on base
`f7f9bd44713606d9c099adda715db2542c8b66bf`. A real Chromium regression uses
existing generated Roadmap markup and the production graph renderer, CSS and
scripts. Native SVG focus, pointer/click updates, HTML parity, query/entity
context, shared filtering and hash selection pass 18 assertions without page
errors. Selecting both original scripts reproduces interrupted initialization.
This is local HTTP browser evidence, separate from consumer live acceptance.

An independent mixed-script matrix isolates the two defects: original shared
code fails initialization even with the corrected graph script; original graph
code fails SVG focus even with corrected shared code. Both corrected scripts
pass with zero errors, and two existing URL/context methods pass independently.

A second independent Chromium witness uses exact retained Empathy S2 HTML,
CSS and data at manifest `06abfba2f5d35979a75d585926095c611b6d2f66f8fba1995a77268ecdec4f57`,
substituting only the two reviewed scripts. Original scripts produce seven
SVG TypeErrors and fail initialization/focus/pointer/Enter context checks.
The candidate passes all seven checks without page errors. No request
interception or certificate bypass is used. This derived local fixture is
explicitly not a canonical deployment or valid recomposed publication bundle.

The focused site suite has 33 passing methods and one inherited Hygiene
route-lock failure, reproduced on exact clean f7. Its existing HTML mock now
implements native attribute writes while preserving every original URL and
secret-exclusion assertion. Node syntax, scoped Ruff, Python compilation and
whitespace checks pass. The action catalog validator retains ten inherited
SPDX/README findings; no full-repository clean result is claimed.

The incompatible shared writer dates to September 21; SVG graph integration
and its focus-context writer date to November 9. Both changed production assets are
byte-identical between the pre-batch Relay source and f7. Previous Empathy
`9a631597` had no SVG graph, so this is an inherited owner defect newly exposed
by consumer adoption. Historical f7/S2 results remain literal.

Root owns reviewed owner integration and a separately qualified Empathy source
cycle. Actual consumer publication, fresh report intake, rollback/restoration,
canonical browser acceptance and issue disposition remain with Empathy #105/#98.
This repair changes runtime correctness; UI redesign remains deferred.
