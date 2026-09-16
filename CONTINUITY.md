---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: "2026-09-16T14:14:00Z"
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Preserve the minimum verified state needed to review the fourth bounded REL-RI-006 supporting-view checkpoint.
  includes:
    - Repository Intelligence Search-route issue, pull request, and exact candidate state.
    - Accepted Observatory Search query boundary and rendering constraints.
    - Merged Dependencies, Work, and Releases checkpoints.
    - Roadmap impact, ADR impact, validation evidence, upstream gates, and next dependency-ready action.
  excludes:
    - Conversation transcripts, duplicated architecture history, source-code/full-text search, fuzzy or semantic ranking, live provider search, and organization-level semantics not accepted upstream.
  precedence:
    - user-and-runtime-instructions
    - scoped-repository-instructions
    - live-repository-and-work-tracker-state
    - canonical-repository-sources
    - continuity-checkpoint
  canonical_sources:
    - AGENTS.md
    - ARCHITECTURE.md
    - SYSTEM.md
    - DECISIONS.md
    - ROADMAP.md
    - actions/repository-intelligence/action.yml
    - actions/repository-intelligence/assets/site.js
    - actions/repository-intelligence/scripts/generate_repository_intelligence_site.py
    - actions/repository-intelligence/scripts/render_repository_intelligence_dependencies.py
    - actions/repository-intelligence/scripts/render_repository_intelligence_search.py
work:
  objective: Materialize Repository Intelligence /search/ from Observatory's accepted normalized Search query without creating Relay-local indexing, ranking, or provider-search semantics.
  success_conditions:
    - Render every normalized Search record with kind, key, state, repository, assertion, freshness, and canonical source.
    - Use Observatory-supplied search_text directly for browser matching.
    - Preserve normalized record order and shared URL-backed text/state/kind filtering.
    - Keep unavailable Search evidence, empty Search evidence, and a zero-match browser filter distinct.
    - Keep Repository Intelligence generation and public bundle validation green.
  active_issue:
    provider: github
    id: egohygiene/relay#83
    url: https://github.com/egohygiene/relay/issues/83
  next:
    kind: pull-request
    id: egohygiene/relay#85
    description: Review and merge the validated bounded /search/ implementation if acceptable.
    readiness: ready-for-review-after-final-head-ci
    references:
      - https://github.com/egohygiene/relay/issues/83
      - https://github.com/egohygiene/relay/pull/85
      - https://github.com/egohygiene/relay/issues/29
      - https://github.com/egohygiene/observatory/issues/7
    depends_on: []
state:
  base:
    revision: e30ddd79204cbf6da919acdda20b33b1514dce73
    ref: refs/heads/main
    verified_at: "2026-09-16T14:00:00Z"
  candidate:
    branch: feat/83-repository-intelligence-search
    implementation_revision: 36a9d7b30e494f3677a2e829122d35e20bc33f37
    pull_request: https://github.com/egohygiene/relay/pull/85
    handoff_state: ready-for-review-after-final-head-ci
  live:
    status: verified
    observed_at: "2026-09-16T14:14:00Z"
    default_branch_revision: e30ddd79204cbf6da919acdda20b33b1514dce73
    dependencies_checkpoint:
      issue: egohygiene/relay#77
      pull_request: egohygiene/relay#78
      state: merged
    work_checkpoint:
      issue: egohygiene/relay#79
      pull_request: egohygiene/relay#80
      state: merged
    releases_checkpoint:
      issue: egohygiene/relay#81
      pull_request: egohygiene/relay#82
      state: merged
    search_checkpoint:
      issue: egohygiene/relay#83
      pull_request: egohygiene/relay#85
      state: open
    notes: Observatory #7 owns Search and Compare queries. Search records expose normalized search_text from title, key, kind, state, and repository, but do not identify which individual field matched. Health remains only partially represented by the core graph while broader fleet Hygiene/conformance belongs to Observatory #5. Organization Roadmap remains gated by Hygiene #60 and Observatory #22. Accidental issue #84 was immediately closed not_planned and owns no work.
review:
  status: complete-for-implementation-revision
  reviewed_at: "2026-09-16T14:14:00Z"
  reviewed_by: ChatGPT
  evidence:
    - command: Verify Relay main, merged #82, parent #29, open PRs, repository instructions, and accepted Observatory Search implementation.
      outcome: passed
      notes: No competing /search/ child issue or PR existed; live main was e30ddd79204cbf6da919acdda20b33b1514dce73.
    - command: Inspect Observatory _search_view and entity-reference contract.
      outcome: passed
      notes: Search emits compact entity references plus search_text normalized only from publishable title, key, kind, state, and repository fields.
    - command: Add bounded Search renderer, compose it through the existing supporting-view entry point, and add focused tests.
      outcome: passed
      notes: Dependencies, Work, Releases, and Search render from the same repository- and commit-matched snapshot. Tests prove Relay consumes supplied search_text rather than rebuilding it.
    - command: GitHub Actions Validate Relay actions run 35106533975, run 62, on 36a9d7b30e494f3677a2e829122d35e20bc33f37.
      outcome: passed
      notes: Full unit/integration tests, action/catalog and continuity-contract validation, Python compilation, Bash and inline-shell syntax, JSON/YAML parsing, caller-owned publication fixture, reusable Repository Intelligence generation/provenance, publication review, and reviewed-byte preservation all passed.
    - command: GitHub Actions Relay continuity preflight run 35106534011, run 15.
      outcome: passed
      notes: Shared continuity adapter and bounded evidence path passed on the implementation candidate.
    - command: GitHub Actions Dependency review run 35106533379, run 22.
      outcome: passed
      notes: Dependency review passed; Dependabot automerge run 35106533360 / #22 skipped as expected.
  environment_limitations:
    - Direct GitHub network access from the local shell is unavailable; repository reads, writes, and validation status use the connected GitHub integration.
roadmap_impact:
  disposition: no-state-transition
  rationale: REL-RI-006 is already active and explicitly owns Search. Issue #83 is a bounded implementation child; accepting it adds normalized discovery but does not complete Health, Compare, deterministic publication, or organization aggregation.
adr_impact:
  disposition: none
  rationale: The change implements ADR-007's existing Observatory-normalization and Relay-presentation boundary without changing authority or dependency direction.
privacy:
  classification: public-repository
  contains_sensitive_data: false
  redactions: []
---

# Relay continuity

## Current checkpoint

Issue #83 implements the fourth bounded `REL-RI-006` supporting view: `/search/`.
Observatory supplies stable entity records plus a normalized `search_text` built
only from already-publishable title, key, kind, state, and repository fields.

Relay filters that supplied string; it does not build a second index, inspect
canonical URL contents, rank by activity, or query GitHub/providers at runtime.

## Candidate implementation

Branch: `feat/83-repository-intelligence-search`

Implementation revision:
`36a9d7b30e494f3677a2e829122d35e20bc33f37`

Pull request: https://github.com/egohygiene/relay/pull/85

The implementation:

- keeps the existing supporting-view action invocation stable;
- renders `/dependencies/`, `/work/`, `/releases/`, then `/search/` from one accepted snapshot;
- uses Observatory's exact supplied `search_text` as each record's browser-search value;
- preserves Observatory record order instead of relevance/activity ranking;
- reuses shared URL-backed text, state, and kind filters and adds an evidence-freshness facet;
- deep-links every result to its canonical source and exposes kind, key, repository, state, assertion, and freshness;
- distinguishes missing Search evidence, an explicitly empty projection, and a browser query with zero visible matches;
- fails closed for duplicate IDs, missing search text, malformed records, and unsafe canonical URLs;
- keeps every projected record in static HTML and adds escaping, deterministic, mixed-kind, stale/unknown, empty/unavailable, and filtering-hook tests.

The current Observatory contract does not identify the individual field that
matched a query, so Relay explicitly documents the searchable field set rather
than inventing matched-field metadata.

## Validation evidence

On implementation revision `36a9d7b30e494f3677a2e829122d35e20bc33f37`:

- `Validate Relay actions` run 35106533975 / #62 passed its complete chain.
- `Relay continuity preflight` run 35106534011 / #15 passed.
- `Dependency review` run 35106533379 / #22 passed.
- Dependabot automerge run 35106533360 / #22 skipped as expected.

This continuity-only checkpoint creates a new final PR head. Verify the same
required workflows on that exact head before merge.

## Roadmap and decision reconciliation

`REL-RI-006` remains active. Dependencies (#77/#78), Work (#79/#80), and Releases
(#81/#82) are merged; Search (#83/#85) is the current candidate. No roadmap state
transition is appropriate because Health, Compare, deterministic publication,
and organization aggregation remain broader work.

No new ADR is required. This implementation follows ADR-007: Observatory owns
normalized truth; Relay owns static route composition and validated artifacts.

## Blockers and deferred work

- No implementation blocker remains for `/search/`; only final-head CI and review remain.
- Search is normalized entity discovery, not source-code/full-text, fuzzy/vector, or live provider search.
- `/health/` must not absorb unfinished fleet-conformance semantics from Observatory #5.
- `/audits/`, `/hygiene/`, and `/sanity/` remain gated by their normalized owner contracts.
- Organization `/roadmap/` remains gated by Hygiene #60 and Observatory #22.

## Next dependency-ready work

After #85 merges, prefer a bounded `/compare/` checkpoint if live state remains
unchanged. Observatory #7 already owns the deterministic two-snapshot compare
contract, so Relay can visualize additions, removals, field changes, relationship
changes, event changes, and per-view content digests without claiming causality.

## Resume protocol

1. Verify newest Relay `main`, issue #83, PR #85, and exact-head checks.
2. Re-read parent #29 and `REL-RI-006` before selecting another view.
3. Do not duplicate a route with an open implementation PR.
4. Keep one bounded supporting-view checkpoint per PR.
5. Reconcile this continuity checkpoint before every handoff.
