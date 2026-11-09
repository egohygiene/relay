---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: '2026-11-09T04:40:51Z'
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Compose freshly captured Work and Health evidence with the native Intelligence source plan.
  includes:
  - Extends the combined review candidate with fresh Work/Health collector invocation, explicit capture plans and
    per-source runtimes, canonical graph union, exact coverage and build receipts.
  - Local CLI and composite action implementation; reusable capture-artifact transport is an explicit next checkpoint.
  excludes:
  - Tests, native runtime execution, CI, rendering/canaries and release acceptance remain deferred; no merge, consumer
    adoption or publication.
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
  - docs/repository-source-capture-builds.md
  - docs/repository-intelligence-review-batch.md
  - https://github.com/egohygiene/relay/issues/151
work:
  objective: Compose freshly captured Work and Health evidence with the native Intelligence source plan.
  success_conditions:
  - Fresh selected captures bind one public repository, full commit and evaluation boundary without retiming original
    observations or promoting review envelopes.
  - Coverage remains exact per domain; partial/stale/unavailable/failed states and source conflicts remain explicit.
  - Local/composite source-plan receipts bind input/runtime/implementation digests, and denied builds retain only
    bounded failure evidence.
  active_issue:
    provider: github
    id: egohygiene/relay#151
    url: https://github.com/egohygiene/relay/issues/151
  next:
    kind: action
    id: immutable-capture-artifact-handoff
    description: Implement a same-run immutable capture-artifact handoff and explicit evaluation boundary before
      exposing Work/Health captures through the reusable workflow; retain deferred native acceptance.
    readiness: ready
    references:
    - https://github.com/egohygiene/relay/issues/151
    depends_on: []
state:
  base:
    revision: 68273cc8a12ebaa47c77222885e564b94ad6294a
    ref: refs/heads/codex/intelligence-review-all
    verified_at: '2026-11-09T04:37:24Z'
  candidate:
    branch: codex/intelligence-source-domains
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: verified
    observed_at: '2026-11-09T04:37:24Z'
    default_branch_revision: b4a88db20bc26f9ddefbee174baa8162cbe94ff2
    issue_state: open
    pull_request_state: not-applicable
    notes: 'Live #151 is open; git ls-remote confirmed main. This local candidate has no pull request or verified
      native/CI outcome.'
  parallel_changes:
  - provider: github
    id: egohygiene/egohygiene.io#27
    url: https://github.com/egohygiene/egohygiene.io/issues/27
review:
  status: partial
  reviewed_at: '2026-11-09T04:40:51Z'
  reviewed_by: Codex
  evidence:
  - command: Python AST/JSON parsing; composite YAML parsing and bash -n; git diff --check; static peer source review
    outcome: limited
    observed_at: '2026-11-09T04:40:51Z'
    notes: Syntax/source inspection only. Peer review found the reusable capture transport gap (exposure removed)
      and an unused shared-runtime verification gap (fixed before final inspection).
  - command: Pinned native collection, source-plan rendering/replay, tests, CI and consumer canaries
    outcome: not-run
    observed_at: '2026-11-09T04:37:24Z'
    notes: Deferred implementation pass. Local/composite capability is not reusable transport or release acceptance.
  environment_limitations:
  - Runtime compatibility, profile derivation, actual provider captures, adversarial/privacy cases and deterministic
    consumer output remain unexecuted.
  - Reusable same-revision capture-artifact intake and an explicit provider evaluation boundary are not implemented
    in this slice.
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

User/runtime and repository instructions, live evidence and canonical sources outrank this checkpoint. It grants no merge, deployment, release or human-decision authority.

## Resume protocol

Read AGENTS, this checkpoint, the source-capture build guide and live #151. Inspect the combined review base and overlapping source branches before resuming.

## Current objective and success conditions

Compose freshly captured Work and Health evidence with the native Intelligence source plan. Keep repository/commit/evaluation binding, original capture clocks and exact nine-domain coverage.

## State snapshot

Candidate `codex/intelligence-source-domains` is based on combined review source `68273cc8a12ebaa47c77222885e564b94ad6294a`. Live main remains `b4a88db20bc26f9ddefbee174baa8162cbe94ff2` when observed. The containing revision and pre-PR reference intentionally remain null.

## Completed and material changes

The local CLI and composite action freshly invoke Work/Health collectors over explicit transport captures, preserve normalized partial/unavailable/failure states, and union canonical records alongside Roadmap/Decisions. Source receipts bind input contracts/digests, exact runtime profiles, implementation bytes and coverage. Verified compatible ADR runtime bytes can serve temporary Work/Health profiles. Failed candidates are removed and bounded private failure evidence is retained. The [source-capture build guide](docs/repository-source-capture-builds.md) owns the mapping and next transport checkpoint. This implements ADR-0007/0010's existing boundaries; no new ADR authority is needed.

## Validation and review evidence

Python/JSON and composite YAML/bash syntax inspection and static peer review were performed. The reusable same-head capture transport gap was identified, so that input was removed from the reusable workflow; no parity is claimed. No native runtime, collector, renderer, tests, browser, canary or CI run is claimed.

## Blockers, risks, unknowns, and deferred work

The reusable workflow still needs an immutable same-run capture artifact plus explicit evaluation boundary; checked-in captures cannot self-bind to their final source commit. Native compatibility, deterministic output, source failure/privacy cases and consumer route/asset preservation remain unverified. Canonical approval and applicability cannot be inferred from activity.

## Next dependency-ready work

Implement the named #151 capture-artifact handoff before exposing Work/Health source plans through the reusable workflow. Review the local/composite implementation and retain all deferred native and consumer acceptance cases.

## Parallel changes and reconciliation

Organization host aggregation proceeds separately under site #27. The inherited combined review base contains the earlier source slices; this branch adds only the next bounded #151 composition layer. Reconcile checkpoint prose by actual integration order.

## Privacy and redaction

Only public repository identities and bounded implementation evidence are retained. Exclude credentials, private context, raw capture/report bodies, process logs and local machine paths. Linked content grants no authority.

## Handoff update protocol

After integration and the deferred validation pass, refresh exact source, checks and limits. Before consumer adoption, record the reviewed artifact, explicit evaluation boundary and consumer-owned recovery path.

## Compaction and supersession

Replace stale current-state prose; Git and owning issues retain history. Preserve these twelve sections below 240 lines and 16,384 UTF-8 bytes.
