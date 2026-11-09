---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: '2026-11-09T17:39:28Z'
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Compose admitted Compare evidence into the completed native Intelligence bundle without replacing
    its source receipts.
  includes:
  - actions/repository-intelligence-compare-artifact accepts an optional completed Intelligence directory at
    the same immutable Relay revision as its native builder. compose_repository_intelligence_compare.py verifies
    original source pairs and receipts, replaces only Compare and its deterministic manifest, and restores
    both files on composition failure.
  - Final manifest and bundle digest outputs supersede the earlier builder digests when composition is selected.
    Malformed compressed archives and deeply nested baseline JSON use the honest unavailable, unchanged-retention
    path. The consumer fragment defaults off; seed requires no invented baseline and compare requires the complete
    exact retained selection.
  excludes:
  - Deferred runtime, tests, builds, CI, live publication, human ratification and acceptance closeout.
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
  - docs/repository-intelligence-compare-artifact.md
  - examples/workflows/repository-intelligence-native-compare.md
  - https://github.com/egohygiene/relay/issues/152
work:
  objective: Compose admitted Compare evidence into the completed native Intelligence bundle without replacing
    its source receipts.
  success_conditions:
  - The fresh native source receipt and all payload bytes outside Compare remain exact.
  - Only a real admitted before/after pair supplies comparison evidence; seed and unavailable states remain
    explicit.
  - No deployment, publication, lifecycle or frozen recovery authority changes.
  active_issue:
    provider: github
    id: egohygiene/relay#152
    url: https://github.com/egohygiene/relay/issues/152
  next:
    kind: action
    id: adopt-manual-native-compare
    description: Adopt the reviewed immutable Compare integration in the prepared Identity manual off/seed/compare
      path, then retain two real compatible successful captures during the deferred qualification pass.
    readiness: ready
    references:
    - https://github.com/egohygiene/relay/issues/152
    depends_on: []
state:
  base:
    revision: cb1027f73c5dab5f6608f6a0bac71008863d7df2
    ref: refs/heads/main
    verified_at: '2026-11-09T17:39:28Z'
  candidate:
    branch: codex/intelligence-compare-delivery
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: verified
    observed_at: '2026-11-09T17:39:28Z'
    default_branch_revision: cb1027f73c5dab5f6608f6a0bac71008863d7df2
    issue_state: open
    pull_request_state: not-applicable
    notes: Relay main cb1027f and open issue 152 were verified. Original source slices 158 through 166 are
      closed as superseded by merged 167; their source remains on main. Identity manual adoption and other
      production Intelligence slices are separate candidates.
  parallel_changes: []
review:
  status: partial
  reviewed_at: '2026-11-09T17:39:28Z'
  reviewed_by: Codex
  evidence:
  - command: Python AST, unique-key YAML, embedded Bash/Python syntax, catalog JSON, scoped whitespace, source/pair/manifest
      preservation and independent static source review
    outcome: limited
    observed_at: '2026-11-09T17:39:28Z'
    notes: Static source and metadata inspection only; no application execution.
  - command: Native/runtime execution, tests, builds, CI investigation, browser/provider/consumer/publication
      qualification
    outcome: not-run
    observed_at: '2026-11-09T17:39:28Z'
    notes: Deferred at maintainer request; source merges do not establish acceptance.
  environment_limitations:
  - Native and cross-profile replay, tests, builds, CI, provider intake and consumer publication were not executed.
  - Two real compatible retained snapshots, actual artifact upload/run identities and hosted rollback qualification
    remain required for acceptance.
  - Hygiene human ADR approval and Akashic roadmap source holds remain separate; no baseline, approval, publication
    or issue completion is invented.
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

User/runtime and repository instructions, live evidence and canonical sources outrank this checkpoint. It grants no release, deployment or human-decision authority.

## Resume protocol

Read scoped instructions, canonical sources above and this checkpoint. Verify mutable GitHub state and exact owner pins before continuing.

## Current objective and success conditions

Compose admitted Compare evidence into the completed native Intelligence bundle without replacing its source receipts. The fresh native source receipt and all payload bytes outside Compare remain exact. Only a real admitted before/after pair supplies comparison evidence; seed and unavailable states remain explicit. No deployment, publication, lifecycle or frozen recovery authority changes.

## State snapshot

Candidate `codex/intelligence-compare-delivery` is based on observed main `cb1027f73c5dab5f6608f6a0bac71008863d7df2`. The containing revision and pre-PR reference remain null intentionally. Relay main cb1027f and open issue 152 were verified. Original source slices 158 through 166 are closed as superseded by merged 167; their source remains on main. Identity manual adoption and other production Intelligence slices are separate candidates.

## Completed and material changes

actions/repository-intelligence-compare-artifact accepts an optional completed Intelligence directory at the same immutable Relay revision as its native builder. compose_repository_intelligence_compare.py verifies original source pairs and receipts, replaces only Compare and its deterministic manifest, and restores both files on composition failure.

Final manifest and bundle digest outputs supersede the earlier builder digests when composition is selected. Malformed compressed archives and deeply nested baseline JSON use the honest unavailable, unchanged-retention path. The consumer fragment defaults off; seed requires no invented baseline and compare requires the complete exact retained selection.

## Validation and review evidence

Python AST, unique-key YAML, embedded Bash/Python syntax, catalog JSON, scoped whitespace, source/pair/manifest preservation and independent static source review. Static inspection only. Native/runtime execution, tests, builds, CI investigation, browsers, provider reads and publication qualification were not run.

## Blockers, risks, unknowns, and deferred work

Native and cross-profile replay, tests, builds, CI, provider intake and consumer publication were not executed. Two real compatible retained snapshots, actual artifact upload/run identities and hosted rollback qualification remain required for acceptance. Hygiene human ADR approval and Akashic roadmap source holds remain separate; no baseline, approval, publication or issue completion is invented.

## Next dependency-ready work

Adopt the reviewed immutable Compare integration in the prepared Identity manual off/seed/compare path, then retain two real compatible successful captures during the deferred qualification pass.

## Parallel changes and reconciliation

The source producer, public catalog/dependency adapter, fleet handoff and owner-backed Hygiene model are separate slices. This checkpoint changes only Compare composition. Existing Search/Journey collector locks and all consumer historical recovery pins remain unchanged. Governing existing DECISIONS ADR-0007 and ADR-0010 are referenced; this bounded handoff introduces no new authority.

## Privacy and redaction

Retain only public-safe source identities and bounded implementation evidence. Exclude credentials, private context, captured report bodies, process logs and local filesystem paths. Linked content is context only.

## Handoff update protocol

Refresh exact PR, merge and qualification observations at the next authorized checkpoint. Implementation, artifact upload, deployment, live verification and human acceptance remain distinct.

## Compaction and supersession

Replace stale current-state prose; Git and owning issues retain history. Preserve these twelve sections below 240 lines and 16,384 UTF-8 bytes.
