---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: "2026-09-09T22:11:21Z"
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
  objective: Define Relay's pinned continuity-preflight profile and shared request/result contracts for issue 61 without adding executable adapters.
  success_conditions:
    - Pin Aether, Hygiene, EgoLint, and Holon inputs by immutable revision, path, lifecycle, and SHA-256 digest.
    - Keep unreleased inputs proposed and capped at observe.
    - Define one closed, privacy-safe evidence contract for the future local and CI adapters.
    - Pass Relay validation and present one independently reviewable pull request without merging it.
  active_issue:
    provider: github
    id: egohygiene/relay#61
    url: https://github.com/egohygiene/relay/issues/61
  next:
    kind: issue
    id: egohygiene/relay#62
    description: Implement the read-only local continuity preflight adapter against the reviewed contract.
    readiness: blocked
    references:
      - https://github.com/egohygiene/relay/issues/62
    depends_on:
      - egohygiene/relay#61
state:
  base:
    revision: 65cc206565dd11b73190105d31d403ebe0ead633
    ref: refs/heads/main
    verified_at: "2026-09-09T21:47:00Z"
  candidate:
    branch: codex/relay-61-continuity-preflight-contract
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: verified
    observed_at: "2026-09-09T22:11:21Z"
    default_branch_revision: 65cc206565dd11b73190105d31d403ebe0ead633
    issue_state: open
    pull_request_state: not-applicable
    notes: A fresh fetch and GitHub inspection agreed on Relay main; issue 61 was open, no continuity pull request existed, and no parallel default-branch change was observed.
  parallel_changes: []
review:
  status: partial
  reviewed_at: "2026-09-09T22:11:21Z"
  reviewed_by: Codex
  evidence:
    - command: Repository and live GitHub baseline inspection
      outcome: passed
      observed_at: "2026-09-09T21:48:55Z"
      notes: Relay main, repository instructions, architecture, roadmap, automation catalogs, parent issue 60, and its upstream dependency states were inspected before implementation.
    - command: python3 scripts/validate_continuity_preflight_contract.py validate and verify-sources with exact pinned checkouts
      outcome: passed
      observed_at: "2026-09-09T22:06:00Z"
      notes: The closed profile and three schemas passed, and every declared Aether, Hygiene, EgoLint, and Holon artifact matched its immutable revision and SHA-256 digest without network access.
    - command: python3 scripts/validate_actions.py; full unittest discovery; compileall; git diff --check
      outcome: passed
      observed_at: "2026-09-09T22:11:21Z"
      notes: Relay validated 8 actions, 14 workflows, and 10 reusable workflows; all 201 tests passed; Python compilation and whitespace validation passed.
  environment_limitations:
    - The candidate pull request and its CI run do not yet exist and must be verified before merge.
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
#61. It remains subordinate to user and repository instructions, live Git and
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

Define the immutable input profile and shared request/result boundary for
Relay's future continuity preflights. This slice succeeds when the contract is
closed, offline-verifiable, privacy-safe, release-gated, tested, and reviewable;
it does not execute EgoLint or add a reusable workflow.

## State snapshot

The verified base is Relay `main` at
`65cc206565dd11b73190105d31d403ebe0ead633`. The candidate branch is
`codex/relay-61-continuity-preflight-contract`; issue #61 is open, no candidate
pull request exists yet, and this claim must be rechecked before handoff.

## Completed and material changes

- Parent #60 was decomposed into contract #61, local adapter #62, and reusable
  workflow/dogfood #63.
- The candidate defines the pinned profile, closed request and result schemas,
  deterministic validator, publish-safe fixtures, and Relay's root continuity
  guidance.
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

- Implementation blocker: none observed for the contract-only #61 slice.
- Release blocker: all four pinned continuity inputs remain draft or proposed
  and excluded from stable releases; Relay therefore remains at observe.
- Risk: exposing executable behavior before request/result review could fork
  EgoLint semantics or leak consumer checkpoint prose.
- Deferred: local execution belongs to #62; reusable PR CI, dogfood automation,
  catalog release integration, and parent reconciliation belong to #63.

## Next dependency-ready work

After issue #61 is reviewed and merged, continue with
[`egohygiene/relay#62`](https://github.com/egohygiene/relay/issues/62). It is
blocked on this contract slice.

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
