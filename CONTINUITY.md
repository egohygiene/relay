---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: "2026-09-16T13:01:00Z"
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Preserve the minimum verified state needed to review the second bounded REL-RI-006 supporting-view checkpoint.
  includes:
    - Repository Intelligence Work-route issue and candidate branch.
    - Accepted Observatory Work query boundary and rendering constraints.
    - Prior merged Dependencies checkpoint and next supporting-view dependencies.
    - Roadmap impact, ADR impact, validation status, and next dependency-ready action.
  excludes:
    - Conversation transcripts, duplicated architecture history, unrelated release work, and organization-level semantics not accepted upstream.
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
  objective: Materialize Repository Intelligence /work/ from Observatory's accepted normalized Work query without recreating GitHub execution or Relay-local readiness semantics.
  success_conditions:
    - Render open issues and pull requests as direct GitHub execution links.
    - Keep active, ready, waiting, blocked, and unknown roadmap queues distinct.
    - Keep unavailable and empty Work evidence distinct and explicit.
    - Preserve useful static HTML while reusing the shared shell, state vocabulary, filters, and roadmap deep links.
    - Keep Repository Intelligence generation and public bundle validation green.
  active_issue:
    provider: github
    id: egohygiene/relay#79
    url: https://github.com/egohygiene/relay/issues/79
  next:
    kind: pull-request
    id: pending
    description: Review the bounded /work/ implementation after required validation passes.
    readiness: implementation-ready-for-ci
    references:
      - https://github.com/egohygiene/relay/issues/79
      - https://github.com/egohygiene/relay/issues/29
      - https://github.com/egohygiene/observatory/issues/7
    depends_on: []
state:
  base:
    revision: 2480bd307f067b7d54f7661340a0b8b41fc1c750
    ref: refs/heads/main
    verified_at: "2026-09-16T12:54:07Z"
  candidate:
    branch: feat/79-repository-intelligence-work
    revision: 97348a096ee68e96162e03a68ab124295ed33835
    pull_request: null
    handoff_state: implementation-ready-for-ci
  live:
    status: verified
    observed_at: "2026-09-16T13:01:00Z"
    default_branch_revision: 2480bd307f067b7d54f7661340a0b8b41fc1c750
    dependencies_checkpoint:
      issue: egohygiene/relay#77
      pull_request: egohygiene/relay#78
      state: merged
    work_checkpoint:
      issue: egohygiene/relay#79
      state: open
    notes: Observatory #7 already owns open issues, open pull requests, and active/ready/waiting/blocked/unknown roadmap queues. Health remains partially gated by Observatory #5, while Organization Roadmap remains gated by Hygiene #60 and Observatory #22.
review:
  status: in-progress
  reviewed_at: "2026-09-16T13:01:00Z"
  reviewed_by: ChatGPT
  evidence:
    - command: Verify Relay main, AGENTS.md, ARCHITECTURE.md, SYSTEM.md, DECISIONS.md, ROADMAP.md, CONTINUITY.md, parent #29, and merged #78.
      outcome: passed
      notes: REL-RI-006 is active and explicitly names Work as remaining supporting-view work.
    - command: Inspect Observatory Repository Intelligence read-model implementation and accepted Work query.
      outcome: passed
      notes: Work is a deterministic query over open issue/PR entity refs plus five roadmap readiness queues; Relay does not own those readiness semantics.
    - command: Add bounded Work renderer and focused tests while preserving the existing dependency route renderer.
      outcome: authored
      notes: The existing supporting-view action invocation now renders Dependencies and Work from the same accepted snapshot.
    - command: Repository-required GitHub Actions validation.
      outcome: pending
      notes: Full validation begins after the pull request is opened.
  environment_limitations:
    - Direct GitHub network access from the local shell is unavailable; repository reads, writes, and validation status use the connected GitHub integration.
roadmap_impact:
  disposition: no-state-transition
  rationale: REL-RI-006 is already active and explicitly owns Work. Issue #79 is a bounded implementation child, so no canonical roadmap state change is required before merge; merge evidence should be added to REL-RI-006 when accepted.
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

Issue #79 implements the second bounded `REL-RI-006` supporting view: `/work/`.
The accepted Observatory Work query supplies open issues, open pull requests, and
roadmap queues for active, ready, waiting, blocked, and unknown readiness.

Relay renders those records; it does not reconstruct readiness, prioritize work,
or mutate GitHub execution state.

## Candidate implementation

Branch: `feat/79-repository-intelligence-work`

Current implementation revision:
`97348a096ee68e96162e03a68ab124295ed33835`

The implementation:

- preserves the existing `/dependencies/` renderer as a dedicated route module;
- keeps the already-wired supporting-view action entry point stable;
- renders `/work/` from the same repository- and commit-matched snapshot;
- shows active work first, then blocked/waiting/unknown attention queues, then
  ready work and progressively disclosed GitHub execution records;
- links issue/PR records directly to GitHub and roadmap records back to both the
  generated roadmap route and canonical roadmap source;
- distinguishes missing Work evidence from an explicitly empty Work query;
- adds focused deterministic, static-first, filter, malformed-input, and
  accessibility-oriented tests.

## Roadmap and decision reconciliation

`REL-RI-006` is already active and explicitly includes Work, so this bounded
slice does not require a roadmap state transition before merge. If accepted,
merge evidence should be added to the step alongside #77/#78.

No new ADR is required. This implementation follows ADR-007: Observatory owns
normalized truth; Relay owns static route composition and validated artifacts.

## Blockers and deferred work

- The candidate still requires Relay's complete pull-request validation.
- `/health/` must not absorb unfinished fleet-conformance semantics from
  Observatory #5.
- `/audits/`, `/hygiene/`, and `/sanity/` remain gated by their normalized owner
  contracts.
- Organization `/roadmap/` remains gated by Hygiene #60 and Observatory #22.

## Next dependency-ready work

After #79 merges, re-fetch Relay #29/#33 and the upstream models. Prefer
`/releases/` or `/search/` if their accepted Observatory queries remain sufficient
for a truthful bounded implementation; use `/health/` only for the already
accepted check/freshness slice unless fleet-conformance semantics have landed.

## Resume protocol

1. Verify newest Relay `main`, issue #79, and its pull request/checks.
2. Re-read parent #29 and `REL-RI-006` before selecting another view.
3. Do not duplicate a route with an open implementation PR.
4. Keep one bounded supporting-view checkpoint per PR.
5. Reconcile this continuity checkpoint before every handoff.
