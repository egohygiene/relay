---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: "2026-09-16T15:23:03Z"
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Preserve the minimum verified state needed to review the bounded Relay #33 reusable Repository Intelligence publication-workflow checkpoint.
  includes:
    - Relay #90, PR #91, verified base revision, independently green implementation revision, and exact CI evidence.
    - Reusable Repository Intelligence workflow input/catalog parity for Observatory snapshot and structural comparison evidence.
    - Consumer-owned publication boundary, current Empathy/Akashic adoption evidence, roadmap and ADR disposition, and remaining #33 canary work.
  excludes:
    - Consumer repository migrations, Pages deployment authority changes, Observatory semantic changes, organization-roadmap implementation, and conversation transcripts.
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
    - workflow-catalog.json
    - .github/workflows/repository-intelligence.yml
    - actions/repository-intelligence/action.yml
    - docs/repository-intelligence-publication.md
    - tests/test_repository_intelligence_workflow.py
work:
  objective: Restore the reusable Repository Intelligence artifact workflow to the complete current Observatory evidence-input boundary without changing consumer-owned deployment authority.
  success_conditions:
    - Expose optional observatory-snapshot and observatory-comparison on workflow_call and workflow_dispatch.
    - Forward both paths unchanged to the Repository Intelligence action resolved from the exact called Relay revision.
    - Keep the reusable workflow contents-read and artifact-only, with no Pages or repository-write authority.
    - Keep workflow-catalog.json synchronized with the executable input contract.
    - Preserve the existing no-snapshot reusable-workflow smoke as an explicit partial-adoption canary.
    - Document direct-action site composition separately from reusable artifact generation.
    - Keep the complete Relay validation/publication review chain green.
  active_issue:
    provider: github
    id: egohygiene/relay#90
    url: https://github.com/egohygiene/relay/issues/90
  parent_issue:
    provider: github
    id: egohygiene/relay#33
    url: https://github.com/egohygiene/relay/issues/33
  next:
    kind: pull-request
    id: egohygiene/relay#91
    description: Review and merge the validated reusable-workflow parity checkpoint if acceptable.
    readiness: ready-for-review-after-final-head-ci
    references:
      - https://github.com/egohygiene/relay/issues/90
      - https://github.com/egohygiene/relay/pull/91
      - https://github.com/egohygiene/relay/issues/33
    depends_on: []
state:
  base:
    revision: 1c5f059c934782babebfcec2ec0b7958c778fd54
    ref: refs/heads/main
    verified_at: "2026-09-16T15:12:55Z"
  candidate:
    branch: feat/90-repository-intelligence-workflow-parity
    implementation_revision: 470b83a64b0e35c0f383b9e3a314161347a5087f
    pull_request: https://github.com/egohygiene/relay/pull/91
    handoff_state: ready-for-review-after-final-head-ci
  live:
    status: verified
    observed_at: "2026-09-16T15:23:03Z"
    default_branch_revision: 1c5f059c934782babebfcec2ec0b7958c778fd54
    dependencies_checkpoint: {issue: egohygiene/relay#77, pull_request: egohygiene/relay#78, state: merged}
    work_checkpoint: {issue: egohygiene/relay#79, pull_request: egohygiene/relay#80, state: merged}
    releases_checkpoint: {issue: egohygiene/relay#81, pull_request: egohygiene/relay#82, state: merged}
    search_checkpoint: {issue: egohygiene/relay#83, pull_request: egohygiene/relay#85, state: merged}
    compare_checkpoint: {issue: egohygiene/relay#86, pull_request: egohygiene/relay#87, state: merged}
    health_checkpoint: {issue: egohygiene/relay#88, pull_request: egohygiene/relay#89, state: merged}
    publication_checkpoint: {issue: egohygiene/relay#90, pull_request: egohygiene/relay#91, state: open}
    organization_roadmap_gate: {hygiene_60: open, observatory_22: open, github_29: open}
    fleet_conformance_gate: {observatory_5: open}
review:
  status: complete-for-implementation-revision
  reviewed_at: "2026-09-16T15:23:03Z"
  reviewed_by: ChatGPT
  evidence:
    - command: Verify newest Relay main, #33, open PRs, repository architecture/decision/roadmap guidance, reusable workflow, workflow catalog, validation workflow, and consumer integrations.
      outcome: passed
      notes: Main is merge of PR #89 at 1c5f059c934782babebfcec2ec0b7958c778fd54; no competing Relay PR existed. Empathy and Akashic pin the Repository Intelligence action in consumer-owned Pages pipelines.
    - command: Compare reusable Repository Intelligence workflow inputs to the current composite action boundary.
      outcome: passed
      notes: The action already accepted observatory-comparison, but the reusable workflow exposed only observatory-snapshot; #90 owns that bounded parity defect.
    - command: Add workflow_call/workflow_dispatch comparison input, exact forwarding, catalog synchronization, publication-boundary documentation, immutable example guidance, and executable workflow-parity tests.
      outcome: passed
      notes: No Pages deployment or write authority was added; comparison semantics remain owned by Observatory and validated by the underlying action.
    - command: GitHub Actions Validate Relay actions run 35114787480, run 71, on 470b83a64b0e35c0f383b9e3a314161347a5087f.
      outcome: passed
      notes: Action/catalog metadata, continuity-contract validation, complete unit/integration tests, Python compilation, Bash and inline-shell syntax, JSON/YAML parsing, caller-owned publication fixture, reusable Repository Intelligence generation/provenance, publication review, exact reviewed-byte preservation, and review-only output confirmation passed.
    - command: GitHub Actions Relay continuity preflight run 35114787533, run 21.
      outcome: passed
      notes: Shared continuity adapter and bounded evidence path passed on the implementation candidate.
    - command: GitHub Actions Dependency review run 35114783148, run 28.
      outcome: passed
      notes: Dependency review passed; Dependabot automerge run 35114783119 / #28 skipped as expected.
  environment_limitations:
    - Direct GitHub network access from the local shell is unavailable; repository reads, writes, and validation evidence use the connected GitHub integration and GitHub Actions.
roadmap_impact:
  disposition: evidence-reconciled-no-state-transition
  rationale: REL-RI-006 remains active. All six bounded supporting views are merged and #90 restores reusable workflow evidence parity, but parent #33 still requires representative hardened consumer migrations and public-route/canary proof before deterministic publication is complete.
adr_impact:
  disposition: none
  rationale: No authority or dependency direction changed. The checkpoint reinforces ADR-003 immutable consumer references, ADR-006 workflow catalog authority, and ADR-007 Observatory truth / Relay static composition / consumer-owned deployment.
privacy:
  classification: public-repository
  contains_sensitive_data: false
  redactions: []
---

# Relay continuity

## Current checkpoint

Issue #90 is the current bounded child of `relay#33` and `REL-RI-006`. It fixes
one concrete orchestration drift: the Repository Intelligence composite action
already supported Observatory snapshot plus structural comparison evidence, but
the reusable artifact workflow could forward only the snapshot.

## Candidate implementation

Branch: `feat/90-repository-intelligence-workflow-parity`

Implementation revision:
`470b83a64b0e35c0f383b9e3a314161347a5087f`

Pull request: https://github.com/egohygiene/relay/pull/91

The implementation:

- exposes optional `observatory-comparison` beside `observatory-snapshot` on both reusable invocation surfaces;
- forwards both evidence paths unchanged to `$/actions/repository-intelligence` from the exact called Relay revision;
- leaves malformed/mismatched comparison fail-closed behavior in the underlying action where it already belongs;
- synchronizes the workflow catalog and adds a dedicated drift test across YAML, catalog, permissions, forwarding, and smoke behavior;
- keeps the workflow statically `contents: read`, ordinary-artifact-only, and free of Pages deployment authority;
- documents that direct action use is correct for caller-owned site composition while the reusable workflow is a standalone review-artifact boundary;
- records Empathy and Akashic as live direct-action/consumer-owned Pages integrations without claiming they have completed the hardened reusable-workflow migration;
- preserves the no-snapshot Relay smoke path as explicit partial-adoption coverage.

## Validation evidence

On implementation revision `470b83a64b0e35c0f383b9e3a314161347a5087f`:

- `Validate Relay actions` run 35114787480 / #71 passed its complete chain.
- `Relay continuity preflight` run 35114787533 / #21 passed.
- `Dependency review` run 35114783148 / #28 passed.
- Dependabot automerge run 35114783119 / #28 skipped as expected.

This continuity-only update creates a new final PR head. The diff from the
independently green implementation revision must contain only `CONTINUITY.md`,
and the same required workflows must pass on that exact final head before merge.

## Architecture boundary

```text
canonical repository + authorized evidence
        ↓
Relay reusable artifact workflow
        ↓
Relay Repository Intelligence builder
        ↓
validated static /intelligence/ artifact
        ↓
consumer-owned site composition / deployment
```

The reusable workflow does not become a deployer. Observatory still owns
normalized snapshot/comparison truth; Relay validates/composes static artifacts;
the consumer remains the only owner of its authoritative site deployment.

## Roadmap and decision reconciliation

`REL-RI-006` remains active. Dependencies, Work, Releases, Search, Compare, and
core Health are merged. `ROADMAP.md` now records #90 as the current #33 child
and preserves representative consumer migrations/public-route verification as
the remaining deterministic-publication proof.

No new ADR is required. This checkpoint follows ADR-003, ADR-006, and ADR-007.

## Known limitations and gates

- Parent #33 remains open; this PR restores orchestration parity but does not prove the required real consumer migrations by itself.
- Empathy and Akashic currently prove immutable-pinned direct-action composition and public Pages integration, not the final hardened workflow migration target.
- The reusable workflow cannot inject files dynamically produced by another job into its checkout; callers needing generated evidence and site composition should use the composite action in the owning job until a reviewed artifact-transfer contract exists.
- Organization `/roadmap/` remains gated by open Hygiene #60 and Observatory #22; `.github#29` must not invent those semantics.
- Fleet-wide Hygiene conformance remains separately gated by open Observatory #5.

## Next dependency-ready work

After PR #91 merges, continue `relay#33` with the first real representative
consumer canary. Prefer an already-public Repository Intelligence consumer such
as Empathy: pin one reviewed current Relay revision, verify deterministic
`/intelligence/` publication and route preservation in its existing Pages build,
and capture failure/rollback behavior without adding a second deployment owner.
Then repeat on a materially different second consumer (Akashic is an existing
candidate) before considering #33 complete.

## Resume protocol

1. Verify newest Relay `main`, issue #90, PR #91, and exact final-head checks.
2. Verify that the implementation-to-final diff is continuity-only.
3. Keep #33 and REL-RI-006 open after #91 unless representative consumer canary acceptance is separately satisfied.
4. Re-fetch live Empathy/Akashic integration state before selecting the next canary; do not overwrite parallel consumer work.
5. Preserve Observatory truth, Relay static composition, and consumer-owned deployment in every canary.
