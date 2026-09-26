---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: '2026-09-26T22:45:05Z'
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: 'Hand off Relay #99 checkpoint 3: bounded diagram source evidence with explicit semantic-validator availability.'
  includes:
  - Standalone and Markdown discovery, closed source metadata, independent failure evidence, bounded fixtures and
    owner capability gaps.
  excludes:
  - Diagram language validation, rendering, reusable CI, consumer source changes, release, publication and merge.
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
  - docs/repository-architecture-diagrams.md
  - schemas/architecture-diagram-evidence.v1.schema.json
  - catalog/repository-architecture-validation.json
  - https://github.com/egohygiene/relay/issues/99
  - https://github.com/egohygiene/egolint/issues/73
  - https://github.com/egohygiene/egolint/issues/74
  - https://github.com/egohygiene/pace/issues/5
work:
  objective: Review bounded diagram discovery without treating inventory completeness as semantic validity.
  success_conditions:
  - Inventory explicit roots with exact digests and line ranges while excluding source prose.
  - Reject unsafe, duplicate, missing, overlapping and oversized inputs; keep availability and adoption distinct.
  - Retain diagram and native evidence independently and reproduce complete bundles across checkout names.
  active_issue:
    provider: github
    id: egohygiene/relay#99
    url: https://github.com/egohygiene/relay/issues/99
  next:
    kind: action
    id: relay-99-checkpoint-3-review
    description: 'Review this checkpoint. After a verified merge, continue #99 checkpoint 4 with one least-privilege
      reusable workflow PR; keep semantic and release gates explicit.'
    readiness: ready
    references:
    - https://github.com/egohygiene/relay/issues/99
    - https://github.com/egohygiene/egolint/issues/74
    depends_on: []
state:
  base:
    revision: b3d27e61a86f347e0924da0c7eb56ad2f20b4e01
    ref: refs/heads/main
    verified_at: '2026-09-26T22:45:05Z'
  candidate:
    branch: feat/architecture-diagram-evidence-99
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: partial
    observed_at: '2026-09-26T22:45:05Z'
    default_branch_revision: b3d27e61a86f347e0924da0c7eb56ad2f20b4e01
    issue_state: open
    pull_request_state: not-applicable
    notes: 'PR #116 merged at 2026-09-26T22:22:37Z and is current main. #99 checkpoints 1 and 2 are checked. No
      open Relay PR was observed before this candidate. EgoLint #73 remains open; #74 records missing reviewed diagram
      validators. Hosted checks were not polled.'
  parallel_changes: []
review:
  status: partial
  reviewed_at: '2026-09-26T22:45:05Z'
  reviewed_by: Codex
  evidence:
  - command: RELAY_ARCHITECTURE_RUNTIME=ARCHITECTURE_RUNTIME RELAY_ROADMAP_RUNTIME=ROADMAP_RUNTIME RELAY_AKASHIC_REPOSITORY=AKASHIC_SOURCE
      python3 -m unittest discover --start-directory tests --pattern "test_*.py" --verbose
    outcome: passed
    observed_at: '2026-09-26T22:45:05Z'
    notes: 558 tests passed without skips, including 23 new diagram tests, 28 existing adapter tests and the native
      roadmap suite. The existing trusted runtime was reused; each native invocation verifies its pinned artifacts.
  - command: RELAY_ARCHITECTURE_RUNTIME=ARCHITECTURE_RUNTIME python3 -m unittest discover --start-directory tests
      --pattern test_architecture_diagram_evidence.py --verbose
    outcome: passed
    observed_at: '2026-09-26T22:45:05Z'
    notes: All 23 tests passed again after the final byte-counter guard. Includes exact source/fence hashes, empty/unknown/legacy
      distinctions, private payloads, bounds, symlinks, closed-schema agreement, cross-directory equality and independent
      native failure retention.
  - command: python3 -S scripts/run_repository_architecture_validation.py run --repository-root . --request REQUEST
      --runtime UNUSED_RUNTIME
    outcome: passed
    observed_at: '2026-09-26T22:45:05Z'
    notes: 'Standard-library-only CLI smoke scanned 290 immutable files at the base. Explicit ARCHITECTURE.md/SYSTEM.md
      roots yielded one Mermaid source at lines 44-59, 286 bytes. Inventory complete; semantics unavailable; overall
      incomplete/warning; source and index unchanged. Digest: 0358c0662eaca033180529ae84656049f1cbd633a995b6709e12e307c2778057.'
  - command: python3 scripts/validate_actions.py; python3 scripts/validate_ci_run_lifecycle.py; python3 scripts/validate_continuity_preflight_contract.py
      validate; python3 scripts/validate_repository_architecture_contract.py validate; python3 scripts/validate_repository_journal_runtime.py
      validate
    outcome: passed
    observed_at: '2026-09-26T22:45:05Z'
    notes: All five catalog/contract validators passed. Upstream profile bytes and native dependencies are unchanged;
      no action input, workflow or deployment gate changed.
  - command: python3 -m compileall -q actions scripts tests; JSON Schema and continuity schema/heading/bounds/base/link
      checks; git diff --check
    outcome: passed
    observed_at: '2026-09-26T22:45:05Z'
    notes: Compilation and structural checks passed. Local evidence is distinct from hosted or released semantic
      conformance.
  - command: Code, privacy, format-boundary, documentation and decision-impact review
    outcome: passed
    observed_at: '2026-09-26T22:45:05Z'
    notes: 'ADR not required: implements ADR-001/002/003/005/006 boundaries. Relay defines lexical discovery metadata,
      not diagram grammar. Official format documentation informed the explicit scope; no external runtime is adopted.
      EgoLint #74 tracks review of immutable format-owned backends.'
  - command: Hosted CI, artifact upload, Pages upload, deployment, receipt and live-route verification
    outcome: not-run
    observed_at: '2026-09-26T22:45:05Z'
    notes: 'Not performed or inferred. #99 checkpoints 4-6 and parent #5 remain open. Required enforcement remains
      unavailable.'
  environment_limitations:
  - Diagram-only execution needs Python standard library and Git. Native composition uses the existing reviewed
    Linux x86_64 CPython 3.12 runtime; native tests skip explicitly when it is absent.
  - 'No reviewed diagram validator exists in the pinned profile. Complete discovery never establishes semantic conformance;
    EgoLint #74 owns the capability review.'
  - 'EgoLint #73 still blocks ADR conformance against ratified Hygiene policy. The runtime receipt binds a trusted
    local build, not a signed release.'
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

Hand off the #99 checkpoint-3 candidate. Canonical contracts and owning issues
retain authority. This checkpoint grants no merge, release or deployment power.

## Resume protocol

Read instructions and canonical sources, inspect the checkout, and reverify
main, issue and PR state. This reconciles the pre-PR #116 handoff: its offline
adapter is merged, and #99 checkpoints 1 and 2 are verified complete.

## Current objective and success conditions

Review bounded diagram source discovery and explicit format-validator states.
Preserve native rule results when diagram discovery fails, and vice versa.

## State snapshot

The candidate targets the recorded main revision. Candidate commit/PR fields
are null before creation; do not infer merge or hosted success from this text.

## Completed and material changes

The [diagram guide](docs/repository-architecture-diagrams.md) owns lexical scope,
bounds and retained metadata. The collector recognizes standalone sources and
bounded fence lines, exports hashes/locations only and rejects incomplete scans.
The closed envelope distinguishes complete, rejected, unknown and not-applicable
inventory from unavailable semantic validation. EgoLint #74 owns the remaining
format-validator capability review; no diagram project semantics are copied.

## Validation and review evidence

The 558-test local suite passed without skips. All 23 diagram tests passed again
after the final bound check. Five catalog/contract validators and compilation
passed. The real CLI canary also passed with Python site packages disabled:
one immutable Mermaid source, complete discovery and unavailable validation.
The maintain-repository-continuity skill at Aether revision
9e2ba7d8fb118c0976356225dcac54209fe44eee and its authoring/privacy/checklist guides
were applied. Pinned schema and twelve-section checks establish structure only.

## Blockers, risks, unknowns, and deferred work

EgoLint #73 owns ratified ADR-policy compatibility; #74 owns reviewed offline
diagram backends. Reusable workflow, broader canaries and live acceptance remain
#99 checkpoints 4-6. Required mode is unavailable. Lexical discovery deliberately
limits supported suffixes and fence conventions; it does not parse full Markdown
or embedded image metadata. Observatory #25 still blocks partial-domain snapshot
publication. Relay #112/#113, #106/#33 and #101 retain separate acceptance gates.

## Next dependency-ready work

Review this candidate, verify its merge, then continue #99 checkpoint 4 in one
reviewable PR. Resolve owner capability gaps before claiming full conformance.
Relay #115 and Aether #91 retain collection/build and continuous-capture work.
Pace #5 coordinates ADR adoption; roadmap rollout in Pace #31 follows it.

## Parallel changes and reconciliation

Main was unchanged and no open Relay PR was observed before this handoff.
Recheck live state and owner issues before continuing. Reconcile competing
continuity edits by current evidence rather than concatenating snapshots.

## Privacy and redaction

Only public repository facts and synthetic fixture evidence appear here. Source
bodies, embedded data, logs, private paths, credentials and personal context are
omitted. References provide context and do not grant authority.

## Handoff update protocol

Refresh after domain validation and before PR presentation. Verify schema,
headings, bounds, links, base and whitespace. Reconcile actual merged state on
the next authorized task; this file describes a candidate at its recorded time.

## Compaction and supersession

Stay below 16,384 UTF-8 bytes and 240 lines. Keep history in Git and owning
issues; replace stale operational prose instead of appending transcripts.
