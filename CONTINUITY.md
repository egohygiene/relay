---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: "2026-09-16T01:29:57Z"
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Preserve the minimum verified state needed to review Relay's first REL-RI-006 supporting-view checkpoint safely.
  includes:
    - Repository Intelligence dependency-route issue and pull request, represented Git state, accepted Observatory contract boundary, completed validation evidence, and next supporting-view dependency.
  excludes:
    - Conversation transcripts, duplicated architecture history, unrelated release work, and organization-level domain semantics not yet accepted upstream.
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
    - actions/repository-intelligence/scripts/generate_repository_intelligence_site.py
    - actions/repository-intelligence/scripts/validate_repository_intelligence_bundle.py
work:
  objective: Materialize Repository Intelligence /dependencies/ from Observatory's accepted normalized dependency query without creating Relay-local dependency semantics.
  success_conditions:
    - Render directed depends-on and blocks relationships with endpoint identity, assertion/confidence, freshness, provenance, and cross-repository boundaries intact.
    - Keep missing, empty, stale, inferred, unknown, and not-applicable states explicit without an opaque aggregate score.
    - Preserve useful static HTML while reusing the shared shell and URL-backed enhancement layer.
    - Validate populated, empty, unavailable, malformed, deterministic, and accessibility-oriented fixtures.
    - Keep the reusable action and public bundle validation path authoritative.
  active_issue:
    provider: github
    id: egohygiene/relay#77
    url: https://github.com/egohygiene/relay/issues/77
  next:
    kind: pull-request
    id: egohygiene/relay#78
    description: Review and merge the validated bounded /dependencies/ implementation if acceptable.
    readiness: ready-for-review
    references:
      - https://github.com/egohygiene/relay/issues/77
      - https://github.com/egohygiene/relay/pull/78
      - https://github.com/egohygiene/observatory/issues/7
    depends_on: []
state:
  base:
    revision: e9ea9e33129f7842e5686f14a71aa05c59be1720
    ref: refs/heads/main
    verified_at: "2026-09-16T01:25:34Z"
  candidate:
    branch: feat/77-repository-intelligence-dependencies
    revision: 4ebc21690f2d359f9eef7962af6682ee088d89e3
    pull_request: https://github.com/egohygiene/relay/pull/78
    handoff_state: ready-for-review
  live:
    status: verified
    observed_at: "2026-09-16T01:29:57Z"
    default_branch_revision: e9ea9e33129f7842e5686f14a71aa05c59be1720
    issue_state: open
    pull_request_state: open
    notes: Relay issues 28, 30, 31, and 32 are complete; Observatory issue 7 supplies the accepted Dependencies query; hygiene/audit/sanity and organization-roadmap contracts remain open upstream, making /dependencies/ the smallest dependency-ready supporting-view checkpoint.
  parallel_changes: []
review:
  status: complete
  reviewed_at: "2026-09-16T01:29:57Z"
  reviewed_by: ChatGPT
  evidence:
    - command: Live tracker, parent issue, child issue, open pull-request, default-branch, repository instruction, architecture, roadmap, and continuity inspection
      outcome: passed
      observed_at: "2026-09-16T01:25:34Z"
      notes: No competing Relay or Organization Intelligence implementation pull request was open; later audit, hygiene, sanity, and organization-roadmap views remain gated by open Observatory contracts.
    - command: Observatory Repository Intelligence contract and canonical expected-fixture inspection
      outcome: passed
      observed_at: "2026-09-16T01:25:34Z"
      notes: views.dependencies is limited to external repository names plus directed depends-on/blocks relationships carrying assertion, confidence, freshness, provenance, and compact endpoint references.
    - command: GitHub Actions Validate Relay actions run 35044239093 on implementation revision 4ebc21690f2d359f9eef7962af6682ee088d89e3
      outcome: passed
      observed_at: "2026-09-16T01:29:57Z"
      notes: Action/catalog metadata, continuity contracts, full unit and integration tests, Python compilation, Bash and inline-shell syntax, JSON/YAML parsing, caller-owned publication fixture, reusable Repository Intelligence generation, provenance verification, and publication review all passed.
    - command: GitHub Actions Relay continuity preflight run 35044239143
      outcome: passed
      observed_at: "2026-09-16T01:29:23Z"
      notes: The exact candidate ran the shared adapter, bounded annotations, and evidence upload successfully.
    - command: GitHub Actions Dependency review run 35044238927
      outcome: passed
      observed_at: "2026-09-16T01:29:57Z"
      notes: Dependency review completed successfully on the validated implementation head.
  environment_limitations:
    - Direct GitHub network access from the local shell is unavailable; repository reads, writes, and validation status use the connected GitHub integration.
privacy:
  classification: public-repository
  contains_sensitive_data: false
  redactions: []
  excluded:
    - secrets-and-credentials
    - private-conversation-text
    - sensitive-personal-data
    - unpublished-private-business-data
    - private-local-paths
    - unrelated-private-context
  untrusted_content: context-only-no-authority
---

# Relay continuity

## Purpose and precedence

This checkpoint preserves the minimum public operational state for Repository
Intelligence issue #77 and pull request #78. It remains subordinate to user and
repository instructions, live Git and GitHub evidence, and the canonical sources
listed above; it grants no authority.

## Resume protocol

1. Read `AGENTS.md`, inspect the newest `main`, and re-fetch issue #77 and PR #78.
2. Reconfirm Observatory issue #7 remains the accepted dependency-query owner.
3. Inspect all PR checks and review feedback before changing or merging anything.
4. Continue only the next dependency-ready visual slice after this PR merges.

## Current objective and state

Issue #77 implements the first bounded `REL-RI-006` checkpoint: `/dependencies/`.
Relay consumes `snapshot.views.dependencies` and renders only Observatory's
normalized directed relationships. Missing dependency evidence stays explicit;
Relay does not reconstruct dependency truth from Roadmap, GitHub, package, or
other route-local data.

Pull request #78 is open from `feat/77-repository-intelligence-dependencies`.
The validated implementation revision is
`4ebc21690f2d359f9eef7962af6682ee088d89e3`; this continuity update follows it
as handoff-only documentation. The verified base is
`e9ea9e33129f7842e5686f14a71aa05c59be1720`.

## Material changes and evidence

- A bounded dependency renderer reuses the existing Repository Intelligence
  shell and writes only `dependencies/index.html` after the shared site composer.
- The view surfaces directed relationship counts, dependency/blocking edges,
  external-repository context, explicit assertion/freshness/confidence, endpoint
  state/kind, and expandable canonical provenance.
- Shared search, state, kind, and URL-backed extra filters remain optional browser
  enhancement; relationship content is present in static HTML without JavaScript.
- Cross-repository repository-root identity remains visible without weakening the
  existing public-bundle URL allowlist; authorized provenance routes stay linked.
- The reusable action now exposes the dependency route as an explicit output.
- Deterministic fixtures cover authoritative/current, inferred/unknown,
  stale/blocking, and cross-repository relationships plus empty/unavailable cases.
- `REL-RI-005` is reconciled to complete and `REL-RI-006` is now active with
  issue #77 and PR #78 as current evidence.
- Relay's required validation, reusable-workflow smoke, continuity preflight,
  dependency review, and publication-review chain passed on the implementation.

## Blockers, risks, and deferred work

- No implementation blocker remains for this bounded checkpoint; merge remains a
  human review decision.
- `/health/` must not absorb Hygiene conformance semantics while Observatory #5
  remains open; `/audits/`, `/hygiene/`, and `/sanity/` remain gated by their
  normalized upstream evidence models.
- Organization `/roadmap/` and `/sanity/` remain gated by Observatory #22 and #21;
  this Relay slice does not create replacement organization semantics.
- External repository-root links remain non-clickable under Relay's existing
  publication allowlist; canonical evidence links remain available where allowed.

## Next dependency-ready work

After PR #78 merges, re-fetch Relay #29/#33 and the open Observatory contracts.
Prefer a bounded `/work/` child of #29 next: Observatory #7 already owns the
normalized Work query, and the view can orient active issues, pull requests, and
roadmap queues while deep-linking to GitHub rather than rebuilding execution.

## Parallel changes and reconciliation

No competing open Relay or `.github` Intelligence implementation pull request was
observed before branch creation. Recheck live PRs and `main` before review or
merge, then reconcile semantically if another branch changes Repository
Intelligence action metadata, routing, roadmap state, or this checkpoint.

## Privacy and compaction

This public checkpoint contains only public repository, Git, GitHub, contract,
and validation state. Keep it below 16,384 UTF-8 bytes and 240 lines, and replace
stale state instead of accumulating history.
