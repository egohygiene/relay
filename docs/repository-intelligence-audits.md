# Supplied audit evidence in Repository Intelligence

Refs [Relay #74](https://github.com/egohygiene/relay/issues/74),
[Observatory #20](https://github.com/egohygiene/observatory/issues/20) and
[Aether #86](https://github.com/egohygiene/aether/issues/86).
This focused view consumes the separate proposed owner query
`egohygiene.observatory.repository-audits/v1`, version `1.0.0-alpha.1`.
The closed Repository Intelligence alpha.2 graph and its collection domains are
unchanged. Audit Markdown/sidecars remain canonical; Relay does not scrape
report prose or run an auditor.

## Exact owner and source boundary

[`repository-audits.v1.lock.json`](../actions/repository-intelligence/contracts/repository-audits.v1.lock.json)
records the actual immutable Observatory revision and every admitted resource
hash. The capsule includes the standalone model validator, shared public
admission code, exact Hygiene public artifact and admission lock, model schema,
and exact Aether audit-report/profile-registry helper, schemas and lock. No full
or private catalog is copied. Owner code, resources and schema are checked
before admitting the caller's JSON; target visibility and authenticated public
membership precede model text, counts and public input digests.

The Observatory builder selects supplied authored Aether sidecars. Repository
and represented commit are explicit, and every source keeps its original
run times, scope, profile version, command state, input digest kind and report
reference. Structured source objects have a canonical digest; an original-byte
digest exists only when original JSON bytes were actually supplied. Those
different facts remain owner metadata, not a Relay integrity upgrade.

The page does not treat the supplied inventory as a complete history of all
audits. A partial/blocked/failed run retains its inspected and uninspected scope;
completion describes execution coverage, never a clean-audit assertion. Older
revision runs remain labeled context. Page freshness is a conservative display
of the supplied current-revision row freshness; historical runs do not make
current evidence fresh. The original owner freshness policy stays inspectable.

## Focused renderer interface

[`render_repository_intelligence_audits.py`](../actions/repository-intelligence/scripts/render_repository_intelligence_audits.py)
exports the same bounded interface as the Hygiene view:

- `validate_input(path, repository, source_commit, as_of)` returns the validated
  unchanged owner query and a closed receipt. Repository/commit/evaluation time
  must match the build. Duplicate/invalid/unadmitted data fails closed.
- `validate_receipt(receipt, repository, source_commit, as_of)` checks exact
  owner/schema/version, input/model hashes, renderer/support/lock hashes,
  typed record counts, revision counts and current-row freshness counts.
- `render_body(value, receipt=None)` emits complete static records and existing
  progressive filter markers. A body-only call derives DOM bindings, not an
  execution or publication receipt.
- `validate_page(document, receipt)` checks the exact model and source binding,
  implemented shared shell, `audits-heading`, filter controls and complete
  run/finding/candidate article counts. It does not execute HTML or a browser.
- `render_page(...)` composes the existing shared shell. Root orchestration owns
  input paths, provenance attachment, final bundle validation and publication.

The receipt schema is
[`audit-evidence-receipt.v1.schema.json`](../actions/repository-intelligence/schemas/audit-evidence-receipt.v1.schema.json).
Common integration uses input `observatory-audits`, provenance `audit_evidence`
and the existing `/intelligence/audits/` route. Without an admitted owner input,
the existing source-unsupported page remains. An explicitly supplied empty owner
query instead shows that no admitted evidence was supplied, without claiming
that the repository has never been audited. No new published input or client
asset is introduced; the existing 30-file site inventory remains unchanged.

## What the page preserves

The current posture shows supplied/current/other-revision run and record counts,
owner latest-by-profile metadata and source freshness. There is no score,
automatic policy conformance, inferred acceptance or audit pass. Each finding
keeps its nature, classification, severity, confidence, status, area, effort,
impact, evidence classification, source profile and authored history claim.
Nature headings keep defects, risks, opportunities and experiments distinct.
Profile/audit/revision and finding facets use the existing filters. Multiword
labels use disposable opaque UI selectors rather than changing owner values.

Audit history exposes complete run scope, requested/resolved profiles,
per-profile completion, original time boundaries, command-state counts, limits
and canonical report links. Finding and candidate cards also link to that
canonical report, where omitted full prose and acceptance criteria remain.

The candidate backlog is explicitly proposals only. The current owner query
does not supply authenticated GitHub issue materialization, so the page renders
that state unavailable; a proposal is never described as created or accepted.
Explicit source recurrence/resolution claims are displayed with their prior
audit/finding references. Disappearance never creates a resolution, and the UI
does not invent a two-snapshot comparison algorithm. Orchestration campaigns
stay explicitly unavailable until a compatible owner adapter supplies them.

All normalized record fields remain in static HTML disclosures, including
no-script output. Text is escaped and Markdown is not executed. Already
owner-admitted URLs must also pass the existing Relay host URL boundary;
permitted GitHub links declare `data-source-repository`. Unsupported origins,
fragments or different-revision self-links stay escaped plain text with a
visible explanation. Global URL policy is not widened by this renderer.

## Validation and deferred acceptance

This slice records Python AST, JSON/schema metadata and locked resource-byte
inspection plus static source review. It does not execute owner applications,
native tools, tests, builds, browsers, CI or publication. The user deferred
those qualification steps. Public/private invariance, hostile inputs, complete
rendered equivalence, large-history budgets, responsive/keyboard/screen-reader
behavior and consumer route/recovery preservation remain acceptance work.

The organization sanity sweep is a separate later activity requiring actual
supplied audit/review evidence. Implementing these contracts and pages does not
execute that sweep or supply human ratification. ADR disposition: this renders
an owner-defined source under the existing Relay authority boundary; no new
Relay architecture decision or lifecycle acceptance is inferred.
