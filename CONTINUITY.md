---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: '2026-11-09T17:43:28Z'
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Produce bounded real GitHub Work, Health and Releases captures for the existing same-run native
    source handoff.
  includes:
  - actions/repository-intelligence-github-sources captures public issue/PR inventories, exact-commit checks
    and published releases through bounded read-only provider requests, then packs the existing immutable same-run
    capture format. Source-selected URLs, bodies, comments, actors, emails and logs are excluded; titles remain
    opt-in.
  - Anonymous public admission runs before and after capture. Pagination, record/request/byte/time limits,
    last-successful-page clocks, primary and secondary rate limits and partially received inventories remain
    explicit. Health preserves partial empty captures instead of converting them to complete. Deployments remain
    uncollected without an actual consumer run-attempt receipt.
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
  - actions/repository-intelligence-github-sources/README.md
  - docs/repository-source-capture-builds.md
  - https://github.com/egohygiene/relay/issues/146
work:
  objective: Produce bounded real GitHub Work, Health and Releases captures for the existing same-run native
    source handoff.
  success_conditions:
  - Existing collectors receive real provider captures through their existing closed source plan and artifact
    intake.
  - Provider access cannot imply deployment, contract conformance, human approval or complete inventories beyond
    received pages.
  - Old collector locks/defaults, consumer publication gates and recovery bytes remain intact.
  active_issue:
    provider: github
    id: egohygiene/relay#146
    url: https://github.com/egohygiene/relay/issues/146
  next:
    kind: action
    id: adopt-public-github-source-feeds
    description: Adopt this exact producer and source-plan handoff in the prepared current consumer Pages paths,
      then qualify actual provider, artifact, native and publication behavior in the deferred verification
      pass.
    readiness: ready
    references:
    - https://github.com/egohygiene/relay/issues/146
    depends_on: []
state:
  base:
    revision: d4e89c594c2428ff48407b4a29734bd59eda7def
    ref: refs/heads/main
    verified_at: '2026-11-09T17:43:28Z'
  candidate:
    branch: codex/intelligence-source-delivery
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: verified
    observed_at: '2026-11-09T17:43:28Z'
    default_branch_revision: d4e89c594c2428ff48407b4a29734bd59eda7def
    issue_state: open
    pull_request_state: not-applicable
    notes: Relay Compare composition is merged through PR 172; owning source issues 146, 149 and 150 remain
      open. The Empathy source-feed consumer is separately prepared; no hosted capture or upload is claimed.
  parallel_changes: []
review:
  status: partial
  reviewed_at: '2026-11-09T17:43:28Z'
  reviewed_by: Codex
  evidence:
  - command: Python AST, unique-key YAML, embedded Bash/Python syntax, JSON schema definitions, action-catalog
      shape, continuity schema/size, whitespace and independent static source review
    outcome: limited
    observed_at: '2026-11-09T17:43:28Z'
    notes: Static source and metadata inspection only; no application execution.
  - command: Native/runtime execution, tests, builds, CI investigation, browser/provider/consumer/publication
      qualification
    outcome: not-run
    observed_at: '2026-11-09T17:43:28Z'
    notes: Deferred at maintainer request; source merges do not establish acceptance.
  environment_limitations:
  - No actual GitHub provider requests, native normalization, tests, builds, CI, uploads, canaries or publication
    were executed.
  - Health producer-specific report gaps and consumer source-policy holds remain separate. Generic GitHub deployment
    metadata cannot establish the exact required run-attempt evidence.
  - Later acceptance must retain real run/artifact identities, public/private invariance, provider failure
    behavior and consumer recovery proof.
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

Produce bounded real GitHub Work, Health and Releases captures for the existing same-run native source handoff. Existing collectors receive real provider captures through their existing closed source plan and artifact intake. Provider access cannot imply deployment, contract conformance, human approval or complete inventories beyond received pages. Old collector locks/defaults, consumer publication gates and recovery bytes remain intact.

## State snapshot

Candidate `codex/intelligence-source-delivery` is based on observed main `d4e89c594c2428ff48407b4a29734bd59eda7def`. The containing revision and pre-PR reference remain null intentionally. Relay Compare composition is merged through PR 172; owning source issues 146, 149 and 150 remain open. The Empathy source-feed consumer is separately prepared; no hosted capture or upload is claimed.

## Completed and material changes

actions/repository-intelligence-github-sources captures public issue/PR inventories, exact-commit checks and published releases through bounded read-only provider requests, then packs the existing immutable same-run capture format. Source-selected URLs, bodies, comments, actors, emails and logs are excluded; titles remain opt-in.

Anonymous public admission runs before and after capture. Pagination, record/request/byte/time limits, last-successful-page clocks, primary and secondary rate limits and partially received inventories remain explicit. Health preserves partial empty captures instead of converting them to complete. Deployments remain uncollected without an actual consumer run-attempt receipt.

## Validation and review evidence

Python AST, unique-key YAML, embedded Bash/Python syntax, JSON schema definitions, action-catalog shape, continuity schema/size, whitespace and independent static source review. Static inspection only. Native/runtime execution, tests, builds, CI investigation, browsers, provider reads and publication qualification were not run.

## Blockers, risks, unknowns, and deferred work

No actual GitHub provider requests, native normalization, tests, builds, CI, uploads, canaries or publication were executed. Health producer-specific report gaps and consumer source-policy holds remain separate. Generic GitHub deployment metadata cannot establish the exact required run-attempt evidence. Later acceptance must retain real run/artifact identities, public/private invariance, provider failure behavior and consumer recovery proof.

## Next dependency-ready work

Adopt this exact producer and source-plan handoff in the prepared current consumer Pages paths, then qualify actual provider, artifact, native and publication behavior in the deferred verification pass.

## Parallel changes and reconciliation

Refs source issues 146, 149 and 150 and composition 151. Existing Compare composition in merged 172 is retained. Dependencies, fleet handoff and the separate owner-backed Hygiene model are parallel slices. ADR not required: this composes the existing bounded provider/capture design and adds no new ownership or publication authority.

## Privacy and redaction

Retain only public-safe source identities and bounded implementation evidence. Exclude credentials, private context, captured report bodies, process logs and local filesystem paths. Linked content is context only.

## Handoff update protocol

Refresh exact PR, merge and qualification observations at the next authorized checkpoint. Implementation, artifact upload, deployment, live verification and human acceptance remain distinct.

## Compaction and supersession

Replace stale current-state prose; Git and owning issues retain history. Preserve these twelve sections below 240 lines and 16,384 UTF-8 bytes.
