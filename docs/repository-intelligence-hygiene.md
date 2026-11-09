# Evidence-backed Hygiene view

Refs [Relay #75](https://github.com/egohygiene/relay/issues/75) and
[Observatory #5](https://github.com/egohygiene/observatory/issues/5).
This focused renderer consumes the proposed bounded owner query
`egohygiene.observatory.repository-conformance/v1`, `1.0.0-alpha.1`, rather than
turning operational Health checks into a contract-applicability model.

## Owner boundary

The exact Observatory source is
`a1884942e953bb371499b2822b52f6865ecdae9d`, recorded in
[`repository-conformance.v1.lock.json`](../actions/repository-intelligence/contracts/repository-conformance.v1.lock.json).
The standalone owner validator, model schema, public admission lock and exact
Hygiene public artifact are retained with independent byte hashes. No full or
protected catalog is copied. The owner authenticates membership against the
fixed public artifact, not a caller's asserted subset or digest.

Generate the owner query using its `observatory-conformance` CLI or
`build_repository_conformance`. Public evidence wrappers surround the existing
repository-evidence/v1 contract. Visibility and admitted target selection
precede nested payload validation, IDs, text, counts and hashes. Selected
ambiguous/malformed inputs fail closed. Older observations retain their actual
clocks and represented commits; different-revision rows remain context and do
not determine the current assessment.

Only supplied current-revision conformance assessments determine the displayed
required-check rollup. Advisory rows remain visible. Expired observations stay
stale even if the historical producer reported pass. No evidence remains
unavailable/unknown. Complete contract inventory and applicability remain
unknown, including when all supplied checks pass. No exemption, migration
completion, ratification, percentage or universal obligation is invented.

## Common builder interface

The focused module is
[`render_repository_intelligence_hygiene.py`](../actions/repository-intelligence/scripts/render_repository_intelligence_hygiene.py).
Its standard-library interface is:

- `validate_input(path, repository, source_commit, as_of)` returns the unchanged
  validated owner value and a closed execution receipt. It verifies the pinned
  owner bytes, public admission and semantic model before hashing the public
  input. Repository/revision and owner evaluation time must match the build.
- `validate_receipt(receipt, repository, source_commit, as_of)` checks the exact
  owner schema/revision, model/input hashes, implementation hashes, typed public
  row counts, freshness and unchanged unknown-applicability boundary.
- `render_body(value, receipt=None)` emits complete static evidence and existing
  progressive filter markers. Without a receipt it derives only DOM identity
  attributes; it never manufactures execution or publication provenance.
- `validate_page(document, receipt)` checks exact model/schema/owner/repository/
  commit/as-of attributes, the Hygiene heading, shared implemented-shell marker
  and filter controls. It does not execute a browser.
- `render_page(...)` and the standalone CLI compose through the shared shell.
  The CLI requires an already bound `provenance.hygiene_conformance` receipt;
  isolated rendering does not seal or publish a complete bundle.

Root integration threads the optional owner JSON path through the shared action,
reusable workflows, builder and provenance. It retains the receipt under
`provenance.hygiene_conformance`. Only a validated receipt supports an implemented
Hygiene route; absent evidence preserves the existing source-unsupported page.
Other reserved routes remain unchanged. The existing Hygiene page path is reused,
and the input model is not copied into a new public asset; inventory remains 30.
The shared footer must identify the conformance owner schema for this page.

The binding section has ID `hygiene-evidence` and exact `data-hygiene-*`
attributes for model SHA, model schema, owner revision, repository, source commit
and evaluation time. Cards retain actual contract/version, status, reported
status, freshness, observation/validity, revision match, producer and evidence.
Domain/result/required-or-advisory/revision filters use existing site.js hooks;
no new browser runtime or asset is introduced. Text is escaped. Each already
owner-admitted URL additionally passes Relay's unchanged host URL boundary;
permitted GitHub anchors declare their admitted target repository. An owner URL
outside that narrower host profile (including an unsupported origin or a
different-revision self-source link) remains full escaped text labelled
"not linked by this host profile". This limitation does not rewrite the owner
evidence or broaden global URI policy.

## Validation and remaining work

This slice supplies source, Python AST/JSON-schema/lock byte inspection and
independent static review only. Tests, builds, owner/native/consumer execution,
browser/accessibility review, CI and publication were deferred by the user.
Three diverse repository canaries, hostile/duplicate/private invariance cases,
rendered semantic equality, package installation, deterministic complete bundles
and actual composed-site preservation remain qualification work.

Existing source flags, old runtime locks, source/deployment gates, permissions
and frozen recovery records are untouched. This optional view neither runs
validators nor fixes policy. A future organization sanity sweep must establish
its own review/applicability and explicit human ratification evidence. #5/#75
remain open; implementation is not complete fleet adoption or conformance.

ADR disposition: Relay implements its existing source/renderer authority design
and the proposed Observatory query under accepted Hygiene ADR-0002; no duplicate
Relay ADR or human lifecycle transition is required.
