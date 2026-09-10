---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: "2026-09-10T13:57:38Z"
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
  objective: Publish and dogfood Relay's read-only continuity pull-request workflow for issue 63.
  success_conditions:
    - Preserve the local adapter's exact request/result contract in CI.
    - Use read-only permissions, safe pull-request events, immutable dependencies, and bounded evidence.
    - Dogfood the workflow in Relay without authoring or mutating semantic checkpoint content.
    - Pass Relay validation and present one independently reviewable pull request without merging it.
  active_issue:
    provider: github
    id: egohygiene/relay#63
    url: https://github.com/egohygiene/relay/issues/63
  next:
    kind: issue
    id: egohygiene/observatory#18
    description: Observe continuity adoption and freshness without ingesting handoff content.
    readiness: blocked
    references:
      - https://github.com/egohygiene/observatory/issues/18
    depends_on:
      - egohygiene/relay#60
state:
  base:
    revision: 861887a2d2223b80e9e6076c3ae7f88dc132d8b9
    ref: refs/heads/main
    verified_at: "2026-09-10T13:54:10Z"
  candidate:
    branch: codex/relay-63-continuity-pr-workflow
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: verified
    observed_at: "2026-09-10T13:54:10Z"
    default_branch_revision: 861887a2d2223b80e9e6076c3ae7f88dc132d8b9
    issue_state: open
    pull_request_state: not-applicable
    notes: GitHub confirmed PR 65 merged at the represented main revision and issue 63 is open; no issue 63 pull request existed before implementation.
  parallel_changes: []
review:
  status: partial
  reviewed_at: "2026-09-10T13:57:38Z"
  reviewed_by: Codex
  evidence:
    - command: Repository and live GitHub baseline inspection
      outcome: passed
      observed_at: "2026-09-10T13:08:12Z"
      notes: Relay main at merged PR 65, repository instructions, architecture, roadmap, action catalogs, and issue 63 were inspected before implementation.
    - command: python3 scripts/validate_continuity_preflight_contract.py validate; targeted adapter and contract tests
      outcome: passed
      observed_at: "2026-09-10T13:54:10Z"
      notes: The closed profile and schemas passed; adapter tests covered explicit offline argv, normalization, privacy-safe unavailable output, and caller-checkout isolation.
    - command: python3 scripts/validate_actions.py; full unittest discovery; compileall; git diff --check
      outcome: passed
      observed_at: "2026-09-10T13:57:38Z"
      notes: Relay validated 9 actions, 16 workflows, and 11 reusable workflows; all 210 tests passed; workflow YAML parsed, Python compilation passed, whitespace validation passed, and the checkpoint remained within its byte and line bounds.
  environment_limitations:
    - Organization CI is intentionally deferred for this push; local validation is the current review evidence.
    - Aether, Hygiene, EgoLint, and Holon continuity inputs remain unreleased and therefore cannot be promoted beyond observe.
    - Cargo is unavailable in this environment, so the pinned native EgoLint validator could not be executed against Relay; the profile and exact validator contract bytes were verified instead.
    - actionlint is unavailable in this environment; Relay's catalog validator, workflow-focused tests, and PyYAML parsing supplied the local static workflow evidence.
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
#63. It remains subordinate to user and repository instructions, live Git and
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

Publish the reusable pull-request backstop against the reviewed local adapter.
This slice succeeds when permissions and triggers are safe, dependencies are
immutable, local and CI evidence remain compatible, artifacts and annotations
are bounded, and Relay dogfoods the workflow without semantic authoring.

## State snapshot

The verified base is Relay `main` at
`861887a2d2223b80e9e6076c3ae7f88dc132d8b9`. The candidate branch is
`codex/relay-63-continuity-pr-workflow`; issue #63 is open, no candidate
pull request exists yet, and this claim must be rechecked before handoff.

## Completed and material changes

- PR #65 merged the local adapter and unblocked issue #63.
- The candidate adds the reusable workflow, Relay pull-request dogfood caller,
  pinned contract projections, a consumer example, bounded evidence behavior,
  catalogs, documentation, and workflow tests.
- The contract keeps Aether, Hygiene, EgoLint, Holon, Observatory, Pace, and
  consumer ownership distinct.

## Validation and review evidence

- Baseline repository and live GitHub inspection passed before implementation.
- The closed profile and schemas passed offline validation; every pinned source
  artifact matched its exact local revision and SHA-256 digest.
- Relay's action/workflow catalog check, all 210 tests, workflow YAML parsing,
  Python compilation, and whitespace validation passed. Native EgoLint
  execution remains unavailable
  locally because Cargo is absent and must not be inferred from these checks.

## Blockers, risks, unknowns, and deferred work

- Implementation limitation: Cargo is unavailable locally, so native workflow
  execution remains unclaimed; static contracts and deterministic tests cover
  its authority, pins, evidence bounds, and caller shape.
- Release blocker: all four pinned continuity inputs remain draft or proposed
  and excluded from stable releases; Relay therefore remains at observe.
- Risk: exposing executable behavior before request/result review could fork
  EgoLint semantics or leak consumer checkpoint prose.
- Deferred: parent #60 remains open until upstream contracts are released and
  the workflow is published at an immutable Relay release revision.

## Next dependency-ready work

After issue #63 is reviewed and merged, reconcile parent #60's release gates;
then continue to [`egohygiene/observatory#18`](https://github.com/egohygiene/observatory/issues/18).

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
