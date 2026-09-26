---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: '2026-09-26T23:34:01Z'
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: 'Hand off Relay #99 checkpoint 4: read-only reusable architecture validation and current-run report
    retention.'
  includes:
  - Caller contract, isolated runtime preparation, shared adapter execution, bounded presentation, failure
    retention and local evidence.
  excludes:
  - Consumer source changes, broader checkpoint-5 dogfood, hosted checkpoint-6 acceptance, required mode, release,
    publication and merge.
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
  - docs/repository-architecture-workflow.md
  - docs/repository-architecture-validation.md
  - schemas/architecture-workflow-evidence.v1.schema.json
  - catalog/repository-architecture-validation.json
  - workflow-catalog.json
  - catalog/ci-run-lifecycle.json
  - https://github.com/egohygiene/relay/issues/99
  - https://github.com/egohygiene/egolint/issues/73
  - https://github.com/egohygiene/egolint/issues/74
work:
  objective: Review the reusable architecture workflow with explicit semantic, execution and retention outcomes.
  success_conditions:
  - Call exact Relay and sibling source revisions under contents-read authority without executing caller code.
  - Preserve fresh normalized adapter evidence, bounded annotations and stage summaries before enforcement.
  - Keep advisory semantic findings distinct from unavailable execution, reporting failure and required-mode
    gates.
  active_issue:
    provider: github
    id: egohygiene/relay#99
    url: https://github.com/egohygiene/relay/issues/99
  next:
    kind: action
    id: relay-99-checkpoint-4-review
    description: 'Review this checkpoint. After a verified merge, continue #99 checkpoint 5 fixtures, dogfood
      and recovery in one PR.'
    readiness: ready
    references:
    - https://github.com/egohygiene/relay/issues/99
    depends_on: []
state:
  base:
    revision: cf1413703160d4eac4ef66a10beb9415d40e42a2
    ref: refs/heads/main
    verified_at: '2026-09-26T23:34:01Z'
  candidate:
    branch: feat/architecture-validation-workflow-99
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: partial
    observed_at: '2026-09-26T23:34:01Z'
    default_branch_revision: cf1413703160d4eac4ef66a10beb9415d40e42a2
    issue_state: open
    pull_request_state: not-applicable
    notes: 'PR #117 is merged and current main. #99 checkpoints 1-3 are checked. No open Relay PR was observed
      before this candidate. EgoLint #73 and #74 remain open. Hosted CI was not polled.'
  parallel_changes: []
review:
  status: partial
  reviewed_at: '2026-09-26T23:34:01Z'
  reviewed_by: Codex
  evidence:
  - command: RELAY_ARCHITECTURE_RUNTIME=ARCHITECTURE_RUNTIME RELAY_ROADMAP_RUNTIME=ROADMAP_RUNTIME RELAY_AKASHIC_REPOSITORY=AKASHIC_SOURCE
      python3 -m unittest discover --start-directory tests --pattern "test_*.py" --verbose
    outcome: passed
    observed_at: '2026-09-26T23:34:01Z'
    notes: 583 tests passed without skips in 42.376 seconds, including 25 new workflow tests. Covers real native
      evidence parity, private data, stale/tampered report rejection, escaped annotations, unsupported events,
      required-mode denial and preservation failures.
  - command: 'Local workflow CLI simulation: build, validate, finalize and preserve-ci-report'
    outcome: passed
    observed_at: '2026-09-26T23:34:01Z'
    notes: Prepared the real pinned native runtime offline in isolated storage using previously acquired verified
      wheels, Cargo dependencies and Rust 1.85.1. Inspected 294 immutable Relay files at the recorded base;
      retained four normalized files including one diagram source. Result incomplete/warning; caller Git state
      clean; retained manifest digests verified. Provider identity was synthetic fixture input, not GitHub
      execution.
  - command: Fresh isolated dependency acquisition through the workflow helper
    outcome: limited
    observed_at: '2026-09-26T23:34:01Z'
    notes: PyPI DNS resolution was unavailable in this environment. Network wheel/toolchain/Cargo acquisition
      is not claimed verified; the subsequent offline build used previously acquired trusted dependencies.
  - command: python3 scripts/validate_actions.py; python3 scripts/validate_ci_run_lifecycle.py; python3 scripts/validate_continuity_preflight_contract.py
      validate; python3 scripts/validate_repository_architecture_contract.py validate; python3 scripts/validate_repository_journal_runtime.py
      validate
    outcome: passed
    observed_at: '2026-09-26T23:34:01Z'
    notes: All five validators passed. Workflow/action/lifecycle catalog JSON Schemas and new workflow evidence
      schema passed, including the actual local canary envelope. Corrected the pre-existing workflow schema
      schedule enum for its already-cataloged journal trigger.
  - command: python3 -m compileall -q actions scripts tests; YAML parsing and bash -n for new inline shell;
      git diff --check; continuity structural review
    outcome: passed
    observed_at: '2026-09-26T23:34:01Z'
    notes: Compilation, metadata, shell and whitespace checks passed. Reviewed code, documentation, bounded
      privacy and authority. No deployment/recovery job dependencies or gates changed; hosted acceptance remains
      checkpoint 6.
  - command: Architecture decision impact and maintain-repository-continuity review
    outcome: passed
    observed_at: '2026-09-26T23:34:01Z'
    notes: 'No new ADR: this composition implements ADR-001/002/003/005/006 without transferring sibling ownership.
      Applied the Aether continuity skill and its authoring/privacy/checklist guides; structural verification
      does not establish released continuity conformance.'
  - command: Hosted Actions acquisition, scheduling, artifact upload and live acceptance
    outcome: not-run
    observed_at: '2026-09-26T23:34:01Z'
    notes: 'No hosted run was dispatched or polled. Local report preservation validates the manifest, not GitHub
      upload. #99 checkpoints 5-6, #5, immutable release and fleet adoption remain open.'
  environment_limitations:
  - Fresh network dependency acquisition could not pass local PyPI DNS; offline runtime preparation and the
    actual adapter CLI passed using trusted pre-acquired inputs.
  - The workflow requires GitHub.com job workflow identity, exact called-revision actions, Ubuntu 24.04 x86_64
    and CPython 3.12. GitHub scheduling/upload and emulator or Enterprise Server support are unverified.
  - 'EgoLint #73 still blocks ratified ADR-policy conformance; #74 owns missing reviewed diagram semantic validators.
    The proposed profile remains advisory-only.'
  - Cancellation or artifact-service failure may prevent retention. Released continuity semantic conformance
    and hosted acceptance are unavailable.
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

Hand off the #99 checkpoint-4 candidate. Canonical contracts and owning issues
retain authority. This handoff grants no merge, release or deployment power.

## Resume protocol

Read instructions and canonical sources, inspect the checkout, and reverify
main, issue and PR state. PR #117 is verified merged; #99 checkpoints 1-3 are
complete. The prior candidate wording describes its recorded observation time.

## Current objective and success conditions

Review one reusable architecture workflow that uses the shared local adapter,
retains fresh bounded evidence, and keeps semantic and execution states distinct.

## State snapshot

The candidate targets the recorded main revision. Candidate commit/PR fields
are null before creation; do not infer merge or hosted success from this file.

## Completed and material changes

The [workflow guide](docs/repository-architecture-workflow.md) owns caller inputs,
stage semantics, trust, bounds and retry behavior. The internal helper prepares
an isolated runtime, calls the adapter, verifies fresh-evidence receipts and
retains only closed normalized files through the #6 lifecycle. It emits escaped
annotations and a fixed-label summary, then enforces actual preservation.
Catalogs inventory the new workflow; the existing schedule enum drift is repaired.

## Validation and review evidence

All 583 local tests passed without skips, including 25 new workflow cases.
The real offline canary built the pinned runtime, inspected 294 immutable files,
and retained four normalized evidence files with verified manifest digests.
The consumer remained clean. Fresh network acquisition was limited by PyPI DNS;
verified cached dependencies were used for the offline build. Five validators,
JSON Schemas, YAML, shell, compilation and whitespace checks passed.
The Aether maintain-repository-continuity skill at revision
9e2ba7d8fb118c0976356225dcac54209fe44eee and its referenced guides were applied.
Pinned schema, twelve-section and bounds checks establish structure only.

## Blockers, risks, unknowns, and deferred work

EgoLint #73 owns ratified ADR-policy compatibility; #74 owns offline diagram
backends. Required mode remains unavailable. Checkpoints 5-6 retain broader
fixtures/dogfood and hosted acceptance. Network acquisition, GitHub scheduling
and upload were not proven here. Runner cancellation can interrupt retention.
Observatory #25 still blocks partial-domain snapshot publication; Relay
#112/#113, #106/#33 and #101 retain separate acceptance gates.

## Next dependency-ready work

Review this candidate, verify its merge, then continue #99 checkpoint 5 in one
reviewable PR. Resolve owner capability gaps before claiming full conformance.
Relay #115 and Aether #91 retain collection/build and continuous-capture work.
Pace #5 coordinates ADR adoption; roadmap rollout in Pace #31 follows it.

## Parallel changes and reconciliation

Main was unchanged and no open Relay PR was observed before this handoff.
Recheck live state before continuing and reconcile by evidence, not concatenation.

## Privacy and redaction

Only public repository facts and synthetic fixture evidence appear here. Source
bodies, logs, private paths, credentials and personal context are omitted.
References provide context and do not grant authority.

## Handoff update protocol

Refresh after domain validation and before PR presentation. Verify schema,
headings, bounds, links, base and whitespace. Reconcile merged state on the next
authorized task; this checkpoint describes a candidate at its recorded time.

## Compaction and supersession

Stay below 16,384 UTF-8 bytes and 240 lines. Keep history in Git and owning
issues; replace stale operational prose instead of appending transcripts.
