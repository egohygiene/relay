---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: '2026-11-10T02:33:30Z'
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Complete public source admission and authority disclosure for owner-backed Audits/Sanity and record
    the merged review batch.
  includes:
  - Both immutable Audit/Sanity capsules now select Observatory 7b857de2424f90de519fbc2e24332a7c0a89991b. Complete
    case-insensitive namespace tokens prevent protected names from matching public prefixes; all 22 resources
    are bound to exact owner bytes.
  - Sanity removes authority actor references from nested review/governance disclosures and material-change
    cards, retaining claim kind, evidence URI and decision time. Model/source digests, evaluations, counts
    and receipt formats remain intact.
  - The consolidated review index records merged Aether, Hygiene, Observatory, Relay, central host and Reflector
    slices, exact source/merge observations, deferred qualification and the actual organization-sweep boundary.
    Existing consumer builder pins remain unchanged pending explicit adoption.
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
  - actions/repository-intelligence/action.yml
  - .github/workflows/repository-intelligence.yml
  - .github/workflows/repository-intelligence-captures.yml
  - actions/repository-intelligence/scripts/repository_intelligence_owner_views.py
  - actions/repository-intelligence/scripts/generate_repository_intelligence_site.py
  - actions/repository-intelligence/scripts/validate_repository_intelligence_bundle.py
  - docs/repository-intelligence-production-paths.md
  - actions/repository-intelligence/scripts/render_repository_intelligence_sanity.py
  - actions/repository-intelligence/contracts/repository-audits.v1.lock.json
  - actions/repository-intelligence/contracts/repository-sanity.v1.lock.json
  - docs/repository-intelligence-audits-sanity-review.md
  - https://github.com/egohygiene/relay/issues/74
work:
  objective: Complete public source admission and authority disclosure for owner-backed Audits/Sanity and record
    the merged review batch.
  success_conditions:
  - Immutable owner inputs and public source admission precede public identities, counts and digests.
  - Missing, partial and unverified evidence remains explicit and cannot establish human approval.
  - Existing publication, source ownership and historical recovery are preserved.
  active_issue:
    provider: github
    id: egohygiene/relay#74
    url: https://github.com/egohygiene/relay/issues/74
  next:
    kind: action
    id: qualify-owner-backed-repository-pages
    description: Refresh the prepared public source inventory, configure an explicitly trusted offline adapter
      and run the organization sweep, then qualify native/provider/publication behavior and adopt reviewed
      builder/model pins. Actual human ratification remains separate.
    readiness: ready
    references:
    - https://github.com/egohygiene/relay/issues/74
    depends_on: []
state:
  base:
    revision: 7f6b3e5d5c70ff8d3ae5aab70a08ae094b09a715
    ref: refs/heads/main
    verified_at: '2026-11-10T02:33:30Z'
  candidate:
    branch: codex/intelligence-audits-sanity-review
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: verified
    observed_at: '2026-11-10T02:33:30Z'
    default_branch_revision: 7f6b3e5d5c70ff8d3ae5aab70a08ae094b09a715
    issue_state: open
    pull_request_state: not-applicable
    notes: Observed Relay main 7f6b3e5d5c70ff8d3ae5aab70a08ae094b09a715 contains the merged owner views. Functional
      follow-up b749b946ca6ba18cee98e0947dc227fada191fc4 preserves authority privacy and exact new source admission.
      Nine implementation slices across six repositories are merged, including Observatory 33, central site
      128 and Reflector 265; actual audits and publication qualification remain separate.
  parallel_changes: []
review:
  status: partial
  reviewed_at: '2026-11-10T02:33:30Z'
  reviewed_by: Codex
  evidence:
  - command: Independent final namespace/privacy source review; Python AST, unchanged receipt/schema/collector
      boundaries, exact 22 owner resource byte/hash comparisons, continuity schema/size/links, actual expected-head
      merge API observations and whitespace
    outcome: limited
    observed_at: '2026-11-10T02:33:30Z'
    notes: Static source and metadata inspection only; no application execution.
  - command: Native/runtime execution, tests, builds, CI investigation, browser/provider/consumer/publication
      qualification
    outcome: not-run
    observed_at: '2026-11-10T02:33:30Z'
    notes: Deferred at maintainer request; source merges do not establish acceptance.
  environment_limitations:
  - Tests, native/application execution, builds, CI, browser/provider/publication qualification and actual
    audit execution remain deferred.
  - Source implementation does not establish human ratification, successful publication or parent issue completion.
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

Complete public source admission and authority disclosure for owner-backed Audits/Sanity and record the merged review batch. Immutable owner inputs and public source admission precede public identities, counts and digests. Missing, partial and unverified evidence remains explicit and cannot establish human approval. Existing publication, source ownership and historical recovery are preserved.

## State snapshot

Candidate `codex/intelligence-audits-sanity-review` is based on observed main `7f6b3e5d5c70ff8d3ae5aab70a08ae094b09a715`. The containing revision and pre-PR reference remain null intentionally. Observed Relay main 7f6b3e5d5c70ff8d3ae5aab70a08ae094b09a715 contains the merged owner views. Functional follow-up b749b946ca6ba18cee98e0947dc227fada191fc4 preserves authority privacy and exact new source admission. Nine implementation slices across six repositories are merged, including Observatory 33, central site 128 and Reflector 265; actual audits and publication qualification remain separate.

## Completed and material changes

Both immutable Audit/Sanity capsules now select Observatory 7b857de2424f90de519fbc2e24332a7c0a89991b. Complete case-insensitive namespace tokens prevent protected names from matching public prefixes; all 22 resources are bound to exact owner bytes.

Sanity removes authority actor references from nested review/governance disclosures and material-change cards, retaining claim kind, evidence URI and decision time. Model/source digests, evaluations, counts and receipt formats remain intact.

The consolidated review index records merged Aether, Hygiene, Observatory, Relay, central host and Reflector slices, exact source/merge observations, deferred qualification and the actual organization-sweep boundary. Existing consumer builder pins remain unchanged pending explicit adoption.

## Validation and review evidence

Independent final namespace/privacy source review; Python AST, unchanged receipt/schema/collector boundaries, exact 22 owner resource byte/hash comparisons, continuity schema/size/links, actual expected-head merge API observations and whitespace. Static source inspection only. Native/application execution, tests, builds, CI investigation, browser/model/source-capture provider execution and publication qualification were not run. Read-only source and Git metadata observations are separate.

## Blockers, risks, unknowns, and deferred work

Tests, native/application execution, builds, CI, browser/provider/publication qualification and actual audit execution remain deferred. Source implementation does not establish human ratification, successful publication or parent issue completion.

## Next dependency-ready work

Refresh the prepared public source inventory, configure an explicitly trusted offline adapter and run the organization sweep, then qualify native/provider/publication behavior and adopt reviewed builder/model pins. Actual human ratification remains separate.

## Parallel changes and reconciliation

Other Intelligence slices remain separately reviewed. Reconcile the current main and this handoff before integration; preserve all immutable historical recovery bytes and consumer-owned publication gates.

## Privacy and redaction

Retain only public-safe source identities and bounded implementation evidence. Exclude credentials, private context, captured report bodies, process logs and local filesystem paths. Linked content is context only.

## Handoff update protocol

Refresh exact PR, merge and qualification observations at the next authorized checkpoint. Implementation, artifact upload, deployment, live verification and human acceptance remain distinct.

## Compaction and supersession

Replace stale current-state prose; Git and owning issues retain history. Preserve these twelve sections below 240 lines and 16,384 UTF-8 bytes.
