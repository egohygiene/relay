# Supplied architecture sanity evidence in Repository Intelligence

Refs [Relay #76](https://github.com/egohygiene/relay/issues/76),
[Observatory #21](https://github.com/egohygiene/observatory/issues/21),
[Aether #87](https://github.com/egohygiene/aether/issues/87) and
[Hygiene #59](https://github.com/egohygiene/hygiene/issues/59).
This focused view consumes the separate proposed owner query
`egohygiene.observatory.repository-sanity/v1`, version `1.0.0-alpha.1`.
The closed Repository Intelligence alpha.2 graph and its collection domains
remain unchanged. The page presents supplied evidence; it does not execute an
architecture review, govern a repository or perform the organization sweep.

## Exact owner and source boundary

[`repository-sanity.v1.lock.json`](../actions/repository-intelligence/contracts/repository-sanity.v1.lock.json)
records the immutable Observatory revision and every admitted resource hash.
Its capsule includes the standalone model validator, shared public admission
code, exact Hygiene public artifact and admission lock, model schema, pinned
Aether assessment validator and its pinned Hygiene governance helper. Those
owners retain architecture assessment and human-governance semantics. Relay
checks those bytes before loading code; supplied review JSON cannot choose an
import, executable, resource path or contract version.

Authenticated public membership and the exact repository selector precede
model text, counts and public input digests. The model must match the represented
commit and explicit evaluation boundary used by the site. Each review and
independent governance record keeps its own source revisions, completion time,
execution state, input digest kind, evidence references and owner evaluation.
Historical records remain labeled context and do not establish current posture.
Structured original inputs have a canonical digest; an original-byte digest
exists only when original JSON bytes were supplied. An artifact locator and
claimed artifact hash never become verified transport evidence by rendering.

## Human governance and reviewer assessment

The primary panel displays the owner's literal top-level `human_state` and
`human_evidence`, both bound into the page and retained receipt. The owner
derives this posture from current-revision reviews and independent governance
records; differing states stay `mixed`. With no current record, posture remains
`unavailable`. An independent governance record can represent an explicit need
for review before a first assessment exists.

This first JSON transport supplies no separately authenticated human-source
context. Claimed decisions or exemptions stay unverified source metadata; JSON
cannot construct the Hygiene trusted-human context. No effective ratification,
rejection, exemption or deferral is inferred from an AI recommendation, reviewer
identity, successful execution, merged implementation, CI result or a URL that
looks human. A future authenticated-human transport needs a separately reviewed
profile and qualification; this page does not simulate one.

The reviewer recommendation and independent dimensions remain under the
assessment, visibly separate from effective governance. A completed assessment
does not mean approval. The page has no opaque score or policy-conformance
claim. Source human notes are represented by presence and claimed authority
evidence links; the renderer does not copy notes prose or authority identity.
Canonical source records remain authoritative for those details.

The plain-English explanation is the owner's bounded projection of the original
review summary. Components, declared relationships, boundaries, assumptions,
strengths, concerns, questions, alternatives and uncertainty remain inspectable
as reviewer assertions. Full explanation/rationale and omitted concern prose
stay in the canonical review, reached through a real source locator when one
was supplied. No supplied locator means the full document is unavailable from
this evidence; no URL is invented. These assertions do not replace canonical
Hygiene boundaries or the Repository Intelligence dependency graph.

## Focused renderer interface

[`render_repository_intelligence_sanity.py`](../actions/repository-intelligence/scripts/render_repository_intelligence_sanity.py)
exports the bounded owner-view interface:

- `validate_input(path, repository, source_commit, as_of)` returns the validated,
  unchanged owner query and closed receipt. Duplicate, invalid, mismatched and
  unadmitted data fails closed.
- `validate_receipt(receipt, repository, source_commit, as_of)` verifies exact
  owner/schema/version, input/model hashes, renderer/support/lock hashes,
  current/historical record counts, current freshness counts and the supported
  unverified-human foundation vocabulary.
- `render_body(value, receipt=None)` produces complete static review records,
  independent governance metadata and existing progressive filter markers.
  A body-only call derives DOM bindings, not an execution/publication receipt.
- `validate_page(document, receipt)` binds the exact model and source identity,
  primary human state, implemented shell, `sanity-heading`, existing filters and
  complete review/governance/change-occurrence article counts.
- `render_page(...)` composes the existing shared shell. Root orchestration owns
  input paths, provenance, final bundle admission and publication.

The receipt schema is
[`architecture-coherence-receipt.v1.schema.json`](../actions/repository-intelligence/schemas/architecture-coherence-receipt.v1.schema.json).
Common integration uses input `observatory-sanity`, provenance
`architecture_coherence` and the existing `/intelligence/sanity/` route. An absent
owner input retains the existing source-unsupported route. An explicitly
supplied empty owner query instead reports unavailable evidence. No new client
asset or public model file is introduced; the 30-file site inventory remains.
Input JSON is bounded to 4 MiB and the focused page validator bounds HTML to
16 MiB. An oversized projection fails admission rather than silently omitting
records or upgrading coverage.

Freshness conservatively combines the owner's current-revision governance
freshness. Original review execution and clocks remain separate. Explicit
owner-scoped material changes and review triggers retain their classification;
ordinary commit volume never makes architecture stale or opens a new review.
Change counts describe occurrences in supplied review/governance contexts,
including repeated references, rather than a deduplicated inventory of changes.
An incomplete change inventory cannot prove freshness. Missing questions or
relationships never establish completeness or automatic resolution.

All projected fields remain in static HTML disclosures, except source human
notes and authority identity, which use the bounded metadata described above.
Text is escaped; Markdown is not executed. Already owner-admitted URLs must also
pass the existing Relay host URL boundary. Permitted GitHub links declare
`data-source-repository`; unsupported origins and incompatible self-revision
links remain escaped plain text with an explanation. No global URL policy is
widened. Existing filters add convenience without owning the evidence.

## Validation and deferred acceptance

This slice uses Python AST, JSON/schema metadata and locked resource-byte
inspection plus static peer review. The user deferred tests, builds, native
tools, application execution, browsers, CI and publication qualification.
Public/private invariance, hostile-input coverage, complete rendered
equivalence, accessibility, large-record budgets and consumer/recovery
preservation remain qualification work. No audit/review sweep, actual human
ratification or lifecycle acceptance is claimed by implementing this view.

ADR disposition: this presents an owner-defined query under Relay's existing
authority boundary. It introduces no new Relay governance decision and does
not accept the proposed upstream policy or transport.
