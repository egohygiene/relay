---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: "2026-09-10T13:08:12Z"
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Preserve the minimum verified state needed to resume Relay continuity-preflight work safely.
  includes:
    - The active contract issue, represented Git state, exact validation evidence, release gates, and next dependency-ready work.
  excludes:
    - Conversation transcripts and duplicated architecture, roadmap, or changelog history.
  precedence:
    - user-and-runtime-instructions
    - scoped-repository-instructions
    - live-repository-and-work-tracker-state
    - canonical-repository-sources
    - continuity-checkpoint
  canonical_sources:
    - AGENTS.md
    - README.md
    - ARCHITECTURE.md
    - SYSTEM.md
    - DECISIONS.md
    - ROADMAP.md
    - catalog/repository-continuity-preflight.json
    - docs/repository-continuity-preflight.md
work:
  objective: Implement Relay's read-only local continuity preflight adapter for issue 62 against the reviewed contract.
  success_conditions:
    - Resolve and verify the pinned EgoLint source before offline execution.
    - Preserve explicit base/head, rollout, live-evidence, and parallel-head inputs.
    - Normalize one privacy-safe result without modifying the inspected checkout.
    - Pass Relay validation and present one independently reviewable pull request without merging it.
  active_issue:
    provider: github
    id: egohygiene/relay#62
    url: https://github.com/egohygiene/relay/issues/62
  next:
    kind: issue
    id: egohygiene/relay#63
    description: Publish the read-only continuity pull-request workflow and dogfood integration.
    readiness: blocked
    references:
      - https://github.com/egohygiene/relay/issues/63
    depends_on:
      - egohygiene/relay#62
state:
  base:
    revision: 8092fd5bf8089bcf24f81d1754dce14bb97b565b
    ref: refs/heads/main
    verified_at: "2026-09-10T13:08:12Z"
  candidate:
    branch: codex/relay-62-continuity-preflight-adapter
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: verified
    observed_at: "2026-09-10T13:08:12Z"
    default_branch_revision: 8092fd5bf8089bcf24f81d1754dce14bb97b565b
    issue_state: open
    pull_request_state: not-applicable
    notes: GitHub confirmed PR 64 merged at the represented main revision and issue 62 is open; no issue 62 pull request existed before implementation.
  parallel_changes: []
review:
  status: partial
  reviewed_at: "2026-09-10T13:12:00Z"
  reviewed_by: Codex
  evidence:
    - command: Repository and live GitHub baseline inspection
      outcome: passed
      observed_at: "2026-09-10T13:08:12Z"
      notes: Relay main at merged PR 64, repository instructions, architecture, roadmap, action catalogs, and issue 62 were inspected before implementation.
    - command: python3 scripts/validate_continuity_preflight_contract.py validate; targeted adapter and contract tests
      outcome: passed
      observed_at: "2026-09-10T13:12:00Z"
      notes: The closed profile and schemas passed; adapter tests covered explicit offline argv, normalization, privacy-safe unavailable output, and caller-checkout isolation.
    - command: python3 scripts/validate_actions.py; full unittest discovery; compileall; git diff --check
      outcome: passed
      observed_at: "2026-09-10T13:12:00Z"
      notes: Relay validated 9 actions, 14 workflows, and 10 reusable workflows; all 204 tests passed; Python compilation and whitespace validation passed.
  environment_limitations:
    - Organization CI is intentionally deferred for this push; local validation is the current review evidence.
    - Aether, Hygiene, EgoLint, and Holon continuity inputs remain unreleased and therefore cannot be promoted beyond observe.
    - Cargo is unavailable in this environment, so the pinned native EgoLint validator could not be executed against Relay; the profile and exact validator contract bytes were verified instead.
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

This checkpoint preserves the minimum public operational state for Relay issue
#62. It remains subordinate to user and repository instructions, live Git and
GitHub evidence, and the canonical sources listed above; it grants no authority.

## Resume protocol

1. Read `AGENTS.md`, inspect the branch, status, recent history, and repository
   shape.
2. Read the named canonical sources and active issue.
3. Read this checkpoint and independently verify mutable issue, pull-request,
   branch, and merge claims.
4. Surface missing, stale, or contradictory evidence before continuing only the
   named dependency-ready work.

## Current objective and success conditions

Implement the local preflight against the reviewed request/result boundary.
This slice succeeds when pinned EgoLint source is verified, execution is
offline, the consumer checkout remains unchanged, failure is explicit, and
normalized evidence contains no checkpoint prose.

## State snapshot

The verified base is Relay `main` at
`8092fd5bf8089bcf24f81d1754dce14bb97b565b`. The candidate branch is
`codex/relay-62-continuity-preflight-adapter`; issue #62 is open, no candidate
pull request exists yet, and this claim must be rechecked before handoff.

## Completed and material changes

- PR #64 merged the reviewed contract and unblocked issue #62.
- The candidate adds the composite action, Task entry point, offline pinned
  source execution, ephemeral checkout isolation, normalized evidence,
  unavailable-state handling, documentation, and tests.
- The contract keeps Aether, Hygiene, EgoLint, Holon, Observatory, Pace, and
  consumer ownership distinct.

## Validation and review evidence

- Baseline repository and live GitHub inspection passed before implementation.
- The closed profile and schemas passed offline validation; every pinned source
  artifact matched its exact local revision and SHA-256 digest.
- Relay's action/workflow catalog check, all 201 tests, Python compilation, and
  whitespace validation passed. Native EgoLint execution remains unavailable
  locally because Cargo is absent and must not be inferred from these checks.

## Blockers, risks, unknowns, and deferred work

- Implementation blocker: Cargo is unavailable locally, so executable coverage
  uses deterministic unit seams and the explicit unavailable path.
- Release blocker: all four pinned continuity inputs remain draft or proposed
  and excluded from stable releases; Relay therefore remains at observe.
- Risk: exposing executable behavior before request/result review could fork
  EgoLint semantics or leak consumer checkpoint prose.
- Deferred: reusable PR CI, checkout acquisition, workflow dogfood, catalog
  release integration, and parent reconciliation belong to #63.

## Next dependency-ready work

After issue #62 is reviewed and merged, continue with
[`egohygiene/relay#63`](https://github.com/egohygiene/relay/issues/63).

## Parallel changes and reconciliation

No parallel continuity pull request was observed. Recheck remote heads and open
pull requests before final review and reconcile semantically if another branch
changes the same contracts or checkpoint.

## Privacy and redaction

This public checkpoint contains only public repository, Git, GitHub, contract,
and validation state. Credentials, conversation text, sensitive personal data,
private paths, unpublished business data, and unrelated context are excluded.

## Handoff update protocol

After project validation and before presenting, opening, or updating a pull
request, reconcile this snapshot, replace stale state, record exact evidence,
compact it, and include it in the same bounded change. Never infer a merge from
local Git or an open candidate.

## Compaction and supersession

Keep this file below 16,384 UTF-8 bytes and 240 lines. Replace stale snapshot
prose instead of accumulating history; Git and the work tracker own chronology.
Mark stale or superseded state explicitly with its required reason or pointer.
