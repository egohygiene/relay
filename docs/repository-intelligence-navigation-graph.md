# Portable Repository Intelligence graph

Refs [Relay #27](https://github.com/egohygiene/relay/issues/27) and
[#101](https://github.com/egohygiene/relay/issues/101). This slice belongs to
Relay's reusable per-repository publisher. It has no React, central-website,
hosted service or browser-token dependency.

The graph enhances existing overview and compatibility-dashboard pages. It adds
no route and preserves the substantial focused renderers. Organization/fleet
sites may deep-link to a consumer's published repository Intelligence; the graph
never guesses that hosting URL from a repository name.

## Renderer interface

`actions/repository-intelligence/scripts/render_repository_intelligence_graph.py`
exports `graph_model(snapshot, repository, prefix="")`,
`graph_body(snapshot, repository, prefix="")` and
`enhance_document(document, snapshot, repository, prefix="")`. The first returns
bounded presentation data, the second returns escaped static SVG and directories,
and the third idempotently enhances shared-shell or legacy-dashboard HTML.

The only prefixes are `""` for the subtree overview and `"../"` for immediate
child routes. Local static links are relative and query-free, preserving GitHub
project Pages prefixes and offline layout. Known Roadmap/Decision fragments reuse
`site.stable_fragment` when the normalized target contains the record. Other
entities navigate to their owning route or Search. Runtime context uses existing
`data-preserve-context` and `data-entity-id` conventions.

```sh
python3 -I actions/repository-intelligence/scripts/render_repository_intelligence_graph.py \
  --repository-root "$CONSUMER_ROOT" \
  --output-root "$CONSUMER_ROOT/dist/intelligence" \
  --summary "$CONSUMER_ROOT/dist/intelligence/summary.json" \
  --provenance "$CONSUMER_ROOT/dist/intelligence/provenance.json" \
  --snapshot "$CONSUMER_ROOT/.cache/repository-intelligence/sources/snapshot.json" \
  --repository egohygiene/relay --source-commit "$SOURCE_COMMIT" --target both
```

`both`, the default, updates overview and `dashboard/index.html`. `overview`,
`dependencies`, `dashboard`, and `all` are supported; `all` also enhances
Dependencies. Omitting `--snapshot` preserves view navigation with explicit
unavailable semantic evidence. The command admits commit-matched inputs through
the existing site contract, rejects symlink/traversal/oversized inputs and tracked
output targets, and writes only selected generated HTML plus `graph.js` and
`graph.css` at the Intelligence root. It executes no consumer program or provider
request.

## Evidence and privacy

Navigation nodes use the current `site.ROUTES` plus overview/dashboard. Dashed
membership edges are explicitly presentation claims. Unsupported normalized
modules remain evidence-unavailable; overall freshness cannot make Sanity or
Hygiene conformance appear observed.

Canonical entity nodes/arrows come directly from the accepted snapshot `graph`.
The closed existing owner relationship vocabulary is preserved: blocks,
depends-on, deploys, evidences, implements, informs, releases, supersedes, tracks
and verifies. Direction, assertion, freshness and public source provenance remain
explicit. No edge is inferred from proximity, titles, activity, Git parents,
missing records or transitive expansion.

Visibility precedes identity/metadata lookup and counts. Both relationship
endpoints and all cited sources must remain admitted public records. Protected
records introduce no placeholders, omitted counts, raw checksums or diagnostics.
Duplicate public identities are withheld rather than choosing a winner;
incompatible public records remain a partial presentation. The helper consumes
reviewed upstream classification and cannot detect a producer incorrectly
classifying restricted content as public.

The presentation is bounded to 112 total nodes, at most 96 entities and 288
connections. Shared route nodes have priority. Only admitted public records
affect limits; a notice directs users to complete focused views. No new published
JSON index or competing canonical model is created.

Source links use literal credential-free GitHub HTTPS URLs scoped to the explicit
public repository, with bounded issue/PR/commit/blob/tree/release paths. Public
repository attributes retain existing validator allowlisting. Guessed hosting,
encoded traversal, query strings, machine paths and credentials are excluded.
Labels/attributes are escaped and client updates use DOM `textContent`.

## Enhancement and integration

`graph.js` adds URL `graph` selection, neighbor inspection/filtering, deterministic
pan/zoom/fit/reset, canvas keyboard commands and pointer-background dragging.
Native node links and admitted node/relationship directories remain in static
HTML, with direction, class, assertion, freshness and canonical provenance as
text. Failed enhancement leaves them available. Scoped focus, reduced-motion,
forced-color and print styles are provided without animation or new libraries.

Run enhancement after focused renderers and before build-manifest creation,
inventory validation and consumer composition. Its parent integration must add
`graph.js`/`graph.css` to the closed routed inventory and canonical byte checks.
This slice leaves that shared wiring to the parent and adds no uploader,
deployer, publication authority or rollback point.

## Deferred verification

Only Python AST, JavaScript syntax, whitespace inspection and static peer source
review are claimed. No renderer/native runtime, tests, build, typecheck, browser,
assistive-technology, deployment, performance or CI acceptance ran. Later work
must verify prefix-safe navigation, actual fragments, public/private invariance,
no-JavaScript/failed-enhancement states, pointer/focus behavior, large graphs and
consumer-route preservation under #101 and its publication/consumer owners.
