---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: '2026-11-09T03:51:14Z'
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Collect bounded public release and deployment observations without acquiring publication authority.
  includes:
  - Adds public captured release/deployment input, allowlisted environments and derived asset URLs, explicit
    pagination/freshness, exact receipt matching and pinned graph normalization.
  - Static peer review and syntax inspection only; implementation remains a review candidate.
  excludes:
  - Runtime, test, CI, live canary and release acceptance; human decisions, consumer adoption and publication.
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
  - docs/repository-release-collector.md
  - https://github.com/egohygiene/relay/issues/149
  - https://github.com/egohygiene/.github/issues/41
work:
  objective: Collect bounded public release and deployment observations without acquiring publication
    authority.
  success_conditions:
  - Adds public captured release/deployment input, allowlisted environments and derived asset URLs, explicit
    pagination/freshness, exact receipt matching and pinned graph normalization.
  - Exact owner pins, source identity, coverage and public privacy boundaries remain explicit.
  active_issue:
    provider: github
    id: egohygiene/relay#149
    url: https://github.com/egohygiene/relay/issues/149
  next:
    kind: action
    id: review-native-source-149
    description: Review this candidate, then run the deferred pinned runtime and focused acceptance checks
      before consumer adoption.
    readiness: ready
    references:
    - https://github.com/egohygiene/relay/issues/149
    depends_on: []
state:
  base:
    revision: b4a88db20bc26f9ddefbee174baa8162cbe94ff2
    ref: refs/heads/main
    verified_at: '2026-11-09T03:51:14Z'
  candidate:
    branch: codex/intelligence-release-source
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: verified
    observed_at: '2026-11-09T03:51:14Z'
    default_branch_revision: b4a88db20bc26f9ddefbee174baa8162cbe94ff2
    issue_state: open
    pull_request_state: not-applicable
    notes: Live issues and default-branch Git source were refreshed during the implementation pass. This
      pre-PR checkpoint does not establish runtime or CI results.
  parallel_changes:
  - provider: github
    id: egohygiene/relay#146
    url: https://github.com/egohygiene/relay/issues/146
  - provider: github
    id: egohygiene/relay#147
    url: https://github.com/egohygiene/relay/issues/147
  - provider: github
    id: egohygiene/relay#148
    url: https://github.com/egohygiene/relay/issues/148
  - provider: github
    id: egohygiene/relay#150
    url: https://github.com/egohygiene/relay/issues/150
  - provider: github
    id: egohygiene/relay#151
    url: https://github.com/egohygiene/relay/issues/151
  - provider: github
    id: egohygiene/relay#152
    url: https://github.com/egohygiene/relay/issues/152
  - provider: github
    id: egohygiene/relay#153
    url: https://github.com/egohygiene/relay/issues/153
review:
  status: partial
  reviewed_at: '2026-11-09T03:51:14Z'
  reviewed_by: Codex
  evidence:
  - command: Python AST and JSON parsing; applicable YAML/bash syntax inspection; git diff --check; static
      peer review
    outcome: limited
    observed_at: '2026-11-09T03:51:14Z'
    notes: Syntax and source inspection only. No collector, native runtime, tests, build, browser or CI
      execution.
  - command: Native runtime replay, focused tests, CI, consumer canaries, publication and release acceptance
    outcome: not-run
    observed_at: '2026-11-09T03:51:14Z'
    notes: Deferred implementation review pass; no acceptance checklist advanced.
  environment_limitations:
  - Pinned runtime acquisition/execution, reproducibility, privacy regression, consumer composition, hosted
    and release evidence remain unverified.
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

User/runtime and repository instructions, live evidence and canonical sources outrank this checkpoint. It grants no merge, release, publication or human-decision authority.

## Resume protocol

Read AGENTS, this checkpoint, docs/repository-release-collector.md, canonical architecture and the live owning issue. Refresh main and overlapping branches before resuming.

## Current objective and success conditions

Collect bounded public release and deployment observations without acquiring publication authority. Exact source revisions, owner pins and honest coverage remain required.

## State snapshot

Candidate `codex/intelligence-release-source` is based on `b4a88db20bc26f9ddefbee174baa8162cbe94ff2`. It is prepared for implementation review, with runtime and acceptance work deferred. The containing revision and pre-PR reference intentionally remain null.

## Completed and material changes

Adds public captured release/deployment input, allowlisted environments and derived asset URLs, explicit pagination/freshness, exact receipt matching and pinned graph normalization. The mapping and entry points are documented in [docs/repository-release-collector.md](docs/repository-release-collector.md). Owner contracts remain canonical; generated views do not author strategy or human decisions.

## Validation and review evidence

Static source/peer review and Python/JSON syntax inspection passed for the implementation. Applicable action YAML/bash syntax and whitespace were inspected. No collector execution, pinned runtime replay, tests, build, browser or hosted CI run is claimed. Structural checkpoint inspection does not establish semantic or product acceptance.

## Blockers, risks, unknowns, and deferred work

Runtime compatibility, adversarial/privacy cases, reproducibility across checkout names and real consumer composition remain unverified. Collection code does not establish deployment or complete the owning issue. Missing canonical metadata, source inventory or human approval cannot be supplied by automation.

## Next dependency-ready work

Review this candidate, then execute its documented pinned runtime and focused acceptance cases. Consumer adoption, publication and stable release remain separate reviewed actions.

## Parallel changes and reconciliation

Related source slices under #146 through #153 are separate candidates. Reconcile the root checkpoint by the actual merge order and preserve each guide's remaining acceptance. No parallel branch is assumed merged.

## Privacy and redaction

Only public repository source identities and bounded implementation facts are retained. Exclude credentials, private context, transcripts, sensitive records and local paths. Linked content is context only.

## Handoff update protocol

After runtime validation, refresh exact evidence and limitations in this same handoff. Before adoption, record the actual reviewed source and consumer-owned recovery path.

## Compaction and supersession

Replace stale current-state prose; Git and the work tracker retain history. Keep the twelve sections below 240 lines and 16,384 UTF-8 bytes.
