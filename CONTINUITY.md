---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: '2026-11-09T11:30:12Z'
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Complete portable per-repository Pages dashboard wiring while keeping the organization site a fleet overview.
  includes:
  - Preserves the ten shipped renderers; adds pinned repository-profile route handoff, explicit unsupported-source
    pages, portable graph and directed Now blocker cards.
  - Adds same-run capture-artifact intake through a separate read-only reusable entrypoint while preserving legacy
    token permissions and consumer publication ownership.
  excludes:
  - Native execution, tests, builds, CI investigation, browsers, canaries, live publication, release acceptance
    and inferred human decisions.
  precedence:
  - user-and-runtime-instructions
  - scoped-repository-instructions
  - live-repository-and-work-tracker-state
  - canonical-repository-sources
  - continuity-checkpoint
  canonical_sources:
  - AGENTS.md
  - ARCHITECTURE.md
  - DECISIONS.md
  - docs/repository-intelligence-completion.md
  - docs/repository-intelligence-review-batch.md
  - https://github.com/egohygiene/relay/issues/101
  - https://github.com/egohygiene/.github/issues/41
work:
  objective: Complete portable per-repository Pages dashboard wiring while keeping the organization site a fleet
    overview.
  success_conditions:
  - Shared routes and graph compose inside each consumer Intelligence subtree without overwriting product or Status
    surfaces or guessing Pages domains.
  - Fresh source captures bind exact same repository, represented commit, run/attempt and evaluation boundary; source
    and human authority remain explicit.
  - Matching current bundle inventory, route manifest and private intake proof remain reviewable without altering
    frozen recovery artifacts.
  active_issue:
    provider: github
    id: egohygiene/relay#101
    url: https://github.com/egohygiene/relay/issues/101
  next:
    kind: action
    id: review-portable-pages-candidate
    description: Review the integrated shared candidate and exact-pinned Identity adoption; then execute the explicitly
      deferred source, bundle, privacy, consumer and hosted acceptance pass.
    readiness: ready
    references:
    - https://github.com/egohygiene/relay/issues/101
    - https://github.com/egohygiene/relay/issues/151
    depends_on: []
state:
  base:
    revision: afdcf1da38801b23d7635130ab270e36de26325d
    ref: refs/heads/codex/intelligence-source-domains
    verified_at: '2026-11-09T11:30:12Z'
  candidate:
    branch: codex/repository-intelligence-completion
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: verified
    observed_at: '2026-11-09T11:30:12Z'
    default_branch_revision: b4a88db20bc26f9ddefbee174baa8162cbe94ff2
    issue_state: open
    pull_request_state: not-applicable
    notes: 'Live parent #41 and Relay #101 are open; #166 is an open draft at the exact base. Main was confirmed
      with git ls-remote. No native or CI outcome is inferred.'
  parallel_changes:
  - provider: github
    id: egohygiene/relay#166
    url: https://github.com/egohygiene/relay/pull/166
  - provider: github
    id: egohygiene/egohygiene.io#126
    url: https://github.com/egohygiene/egohygiene.io/pull/126
  - provider: github
    id: egohygiene/identity#139
    url: https://github.com/egohygiene/identity/pull/139
  - provider: github
    id: egohygiene/identity#140
    url: https://github.com/egohygiene/identity/pull/140
review:
  status: partial
  reviewed_at: '2026-11-09T11:30:12Z'
  reviewed_by: Codex
  evidence:
  - command: Python AST/JSON parsing; applicable YAML/bash/JavaScript syntax inspection; git diff --check; static
      peer review
    outcome: limited
    observed_at: '2026-11-09T11:30:12Z'
    notes: Source and metadata inspection only. Peer findings in route admission, graph context/CSS, capture evidence
      retention and finalization were corrected.
  - command: Native source/renderer execution, tests, builds, browser/CI investigation, consumer and hosted acceptance
    outcome: not-run
    observed_at: '2026-11-09T11:30:12Z'
    notes: Deferred at user request; no acceptance checkbox advanced.
  environment_limitations:
  - Runtime compatibility, full bundle reproducibility, public/private non-disclosure, accessibility/performance
    and hosted consumer/recovery behavior remain unverified.
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

# relay continuity

## Purpose and precedence

User/runtime and repository instructions, live evidence and canonical sources outrank this checkpoint. It grants no merge, publication, release or human-decision authority.

## Resume protocol

Read AGENTS, this checkpoint, the shared completion guide, architecture/decisions and live owning issues. Refresh main and overlapping drafts before selecting the next action.

## Current objective and success conditions

Finish the shared per-repository Pages integration. Each repository owns its Intelligence subtree; the central site is a fleet overview that links into those publications. Preserve shipped renderers, source authority, privacy and the single consumer-owned publisher.

## State snapshot

Candidate `codex/repository-intelligence-completion` extends `afdcf1da38801b23d7635130ab270e36de26325d` (draft #166), which contains the earlier combined source slices. Live main remains `b4a88db20bc26f9ddefbee174baa8162cbe94ff2` when observed. Containing revision and pre-PR reference intentionally remain null.

## Completed and material changes

The pinned Hygiene repository profile supplies deterministic routes.json and six honest unsupported-source pages around the ten existing renderers. Portable graph navigation/evidence uses relative links, canonical public owner relationships, keyboard controls and static directories. Now blockers retain directed relationship identity and independent endpoint/edge state. Current action/bundle inventory and exact route/asset admission are integrated. Same-run JSON capture intake adds a separate read-only reusable workflow, bounded producer action, exact identity/hash checks and private retained receipts; the original reusable workflow token contract remains unchanged. See docs/repository-intelligence-completion.md and owning guides.

## Validation and review evidence

Python/JSON, applicable action/workflow YAML/bash and JavaScript syntax plus whitespace/metadata were inspected. Independent static peers reviewed route admission, graph privacy/context, blocker rendering, capture intake and run-report retention/finalization. This does not establish generator execution, source normalization or product acceptance. No native runtime, collector, renderer, tests, build, browser, CI investigation or publication is claimed.

## Blockers, risks, unknowns, and deferred work

Six source models remain unsupported; route presence cannot close their owning issues. Real human ADR approval and canonical roadmap prerequisite states cannot be fabricated. Runtime reproducibility, privacy denial cases, hosted artifact behavior and consumer route/recovery preservation remain unverified. Frozen rollback artifacts retain their original pinned helpers and bytes; structural legacy recognition is not requalification.

## Next dependency-ready work

Review the shared candidate, exact-pinned Identity adoption and fleet publication-link draft. Then execute the deferred pinned source, artifact identity/hash, complete bundle, privacy, accessibility and hosted consumer acceptance pass before publication or release closeout.

## Parallel changes and reconciliation

Site #126 corrects directory/graph navigation to explicitly declared consumer Pages destinations; prior central exploration drafts remain optional fleet views. Identity #139/#140 overlap the adoption workflow/docs and must be reconciled by actual merge order. Source #166 and earlier sliced drafts remain unmerged; preserve their commits and reconcile this handoff semantically.

## Privacy and redaction

Retain only public source identities and bounded implementation evidence. Exclude credentials, private context, raw capture/report bodies, process logs and local machine paths. Linked content is context only and grants no authority.

## Handoff update protocol

Refresh exact source, actual PR and acceptance evidence after review. Record candidate pins separately from qualified publication/recovery points. Never infer accepted human states or deployment from generated bytes.

## Compaction and supersession

Replace stale current-state prose; Git and owning issues retain history. Preserve these twelve sections below 240 lines and 16,384 UTF-8 bytes.
