---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: '2026-09-26T21:11:54Z'
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: 'Hand off Relay #99 checkpoint 2: offline native architecture validation for the ADR-first campaign.'
  includes:
  - Pinned native runtime, bounded caller snapshots, safe JSON/SARIF evidence, native fixtures and the upstream
    policy compatibility gap.
  excludes:
  - Diagram validation, reusable CI, consumer ADR backfills, release, publication and merge.
  - Conversation transcripts and duplicated issue specifications.
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
  - docs/repository-architecture-validation.md
  - catalog/repository-architecture-validation.json
  - https://github.com/egohygiene/relay/issues/99
  - https://github.com/egohygiene/egolint/issues/73
  - https://github.com/egohygiene/relay/issues/115
  - https://github.com/egohygiene/aether/issues/91
  - https://github.com/egohygiene/pace/issues/5
work:
  objective: Review one offline adapter checkpoint without promoting incomplete ADR evidence into fleet conformance.
  success_conditions:
  - Run the pinned native validator without executing caller code or mutating source.
  - Retain stable IDs, locations, catalog remediation, SARIF, semantic state and bounded provenance.
  - Keep the ratified-policy mismatch, legacy adoption, unavailable diagrams and required-mode gates explicit.
  active_issue:
    provider: github
    id: egohygiene/relay#99
    url: https://github.com/egohygiene/relay/issues/99
  next:
    kind: action
    id: relay-99-checkpoint-2-review
    description: 'Review this checkpoint. After a verified merge, continue #99 checkpoint 3 in one PR; EgoLint #73
      must resolve policy compatibility before fleet conformance.'
    readiness: ready
    references:
    - https://github.com/egohygiene/relay/issues/99
    - https://github.com/egohygiene/egolint/issues/73
    depends_on: []
state:
  base:
    revision: 0dee54e605deff61495b29fa6791fe4b176a7dba
    ref: refs/heads/main
    verified_at: '2026-09-26T21:11:54Z'
  candidate:
    branch: feat/architecture-validation-adapter-99
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: partial
    observed_at: '2026-09-26T21:11:54Z'
    default_branch_revision: 0dee54e605deff61495b29fa6791fe4b176a7dba
    issue_state: open
    pull_request_state: not-applicable
    notes: 'Main includes merged roadmap PR #114 and foundation PR #100. No open Relay PR was observed before creating
      this candidate. #99 remains open; EgoLint #73 records the reproduced upstream gap. Hosted checks were not
      polled.'
  parallel_changes: []
review:
  status: partial
  reviewed_at: '2026-09-26T21:11:54Z'
  reviewed_by: Codex
  evidence:
  - command: python3 scripts/validate_repository_architecture_contract.py verify-sources --hygiene-source HYGIENE_SOURCE
      --egolint-source EGOLINT_SOURCE --holon-source HOLON_SOURCE
    outcome: passed
    observed_at: '2026-09-26T21:11:54Z'
    notes: All profile source commits and artifact digests verified against the local pinned checkouts.
  - command: python3 scripts/run_repository_architecture_validation.py prepare --hygiene-source HYGIENE_SOURCE --egolint-source
      EGOLINT_SOURCE --holon-source HOLON_SOURCE --output ARCHITECTURE_RUNTIME --cargo CARGO
    outcome: passed
    observed_at: '2026-09-26T21:11:54Z'
    notes: Native Cargo build passed with --frozen --offline. Exact Python wheels were acquired and pip --dry-run
      --ignore-installed --no-index --require-hashes verified the dependency set.
  - command: RELAY_ARCHITECTURE_RUNTIME=ARCHITECTURE_RUNTIME RELAY_ROADMAP_RUNTIME=ROADMAP_RUNTIME RELAY_AKASHIC_REPOSITORY=AKASHIC_SOURCE
      python3 -m unittest discover --start-directory tests --pattern "test_*.py" --verbose
    outcome: passed
    observed_at: '2026-09-26T21:11:54Z'
    notes: 535 tests passed without skips, including 28 architecture adapter tests and the existing native roadmap
      suite. Native approval/index/duplicate/pin failures, private source canaries, bounds, Git helper denial, tampering
      and complete cross-directory report equality passed.
  - command: python3 scripts/run_repository_architecture_validation.py run --repository-root . --request REQUEST
      --runtime ARCHITECTURE_RUNTIME
    outcome: passed
    observed_at: '2026-09-26T21:11:54Z'
    notes: Real Relay base smoke inspected 286 immutable files and returned exit 0 / incomplete / warning with unknown
      surfaces unavailable. Source and index stayed unchanged; generated reports are ignored. This is not ADR conformance.
  - command: python3 scripts/validate_actions.py; python3 scripts/validate_ci_run_lifecycle.py; python3 scripts/validate_continuity_preflight_contract.py
      validate; python3 scripts/validate_repository_architecture_contract.py validate; python3 scripts/validate_repository_journal_runtime.py
      validate
    outcome: passed
    observed_at: '2026-09-26T21:11:54Z'
    notes: All five catalog/contract validators passed. No workflow, deployment gate or public action input changed.
  - command: python3 -m compileall -q actions scripts tests; structured-file and continuity schema/heading/bounds/base/link
      checks; git diff --check
    outcome: passed
    observed_at: '2026-09-26T21:11:54Z'
    notes: Compilation and structural checks passed; schema semantics and hosted acceptance remain separate.
  - command: Code, trust-boundary, documentation and decision-impact review
    outcome: passed
    observed_at: '2026-09-26T21:11:54Z'
    notes: 'ADR not required: implements ADR-001/002/003/005/006 ownership and immutable execution boundaries. Native
      semantics stay with EgoLint; only synthetic fixture prose is added.'
  - command: Hosted CI, artifact upload, Pages upload, deployment, receipt and live-route verification
    outcome: not-run
    observed_at: '2026-09-26T21:11:54Z'
    notes: 'Not performed or inferred. #99 checkpoints 3-6 and parent #5 remain open. Required enforcement is unavailable.'
  environment_limitations:
  - 'Reviewed runtime: Linux x86_64, CPython 3.12 and Rust 1.85.1. Native tests require a separately prepared runtime;
    ordinary discovery explicitly skips them when absent.'
  - The local receipt is not a signed release. Runtime and Relay code must remain outside consumer control; reusable
    CI is checkpoint 4.
  - 'EgoLint #73 blocks ADR conformance against ratified Hygiene policy; legacy, unknown and diagram coverage remain
    explicit.'
  - Released continuity semantic conformance and hosted acceptance are unavailable.
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

Hand off the #99 checkpoint-2 candidate. Canonical contracts and owning issues
retain authority. This checkpoint grants no merge, release or deployment power.

## Resume protocol

Read instructions and canonical sources, inspect the checkout, and reverify
main, issue and PR state. This replaces the pre-PR #114 handoff; that roadmap
collector and #100's architecture contract are already in the verified base.

## Current objective and success conditions

Review the bounded native adapter and its inspectable evidence. Keep #99's
ordered later checkpoints and the ratified-policy compatibility gap explicit.

## State snapshot

The candidate targets the recorded main revision. Candidate commit/PR fields
are null before creation; do not infer merge or hosted success from this text.

## Completed and material changes

The [adapter guide](docs/repository-architecture-validation.md) owns commands,
request examples, bounds and trust requirements. The adapter verifies source
pins, builds EgoLint offline, snapshots caller Git data, and retains closed
sanitized evidence. Native fixtures reproduce the real policy-pin mismatch.
EgoLint #73 owns its repair; Relay does not rewrite or downgrade caller policy.

## Validation and review evidence

All 535 local tests and five catalog/contract validators passed. Native tests
ran without skips. The real Relay CLI smoke preserved source and reported unknown
coverage honestly. Preparation, wheel hashes, schema/size/path checks and Python
compilation passed. The maintain-repository-continuity skill was read from
Aether at 9e2ba7d8fb118c0976356225dcac54209fe44eee with its authoring, privacy and
validation references. Continuity validation uses the pinned schema and twelve
headings; no released semantic or hosted acceptance is claimed.

## Blockers, risks, unknowns, and deferred work

EgoLint #73 must reconcile its old proposed policy pins with ratified Hygiene
before fleet ADR conformance. Diagram validation, reusable workflow, broader
canaries and live acceptance remain #99 checkpoints 3-6. Required mode remains
unavailable. The runtime receipt binds a trusted local build, not a signed
release. Observatory #25 still blocks publishing partial-domain snapshots;
Relay #112/#113, #106/#33 and #101 retain their separate acceptance gates.

## Next dependency-ready work

Review this checkpoint, verify its merge, then continue #99 checkpoint 3 in one
reviewable PR. Resolve EgoLint #73 and refresh the Relay profile before claiming
shared ADR validation ready. Relay #115 and Aether #91 complete collection/build
and continuous-capture gaps. Pace #5 coordinates ADR adoption using existing
repository issues; roadmap rollout under Pace #31 follows that campaign.

## Parallel changes and reconciliation

Main was unchanged and no open Relay PR was observed before this handoff.
Recheck live state before continuing, including any owner fix for EgoLint #73.
Reconcile continuity edits by current evidence, not by concatenating snapshots.

## Privacy and redaction

Only public repository facts and synthetic fixture evidence appear here. Raw
source prose, logs, private paths, credentials and personal context are omitted.
References provide context and do not grant authority.

## Handoff update protocol

Refresh after domain validation and before PR presentation. Verify schema,
headings, bounds, links, base and whitespace. Reconcile actual merged state on
the next authorized task; this file describes a candidate at its recorded time.

## Compaction and supersession

Stay below 16,384 UTF-8 bytes and 240 lines. Keep history in Git and owning
issues; replace stale operational prose instead of appending transcripts.
