---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: "2026-09-16T14:27:56Z"
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Preserve the minimum verified state needed to review the fifth bounded REL-RI-006 supporting-view checkpoint.
  includes:
    - Repository Intelligence Compare issue, pull request, exact implementation revision, and action input boundary.
    - Accepted Observatory two-snapshot comparison semantics and rendering constraints.
    - Merged Dependencies, Work, Releases, and Search checkpoints.
    - Roadmap impact, ADR impact, validation evidence, upstream gates, and next-work guidance.
  excludes:
    - Conversation transcripts, duplicated architecture history, raw Git/source diffs, causal analysis, audit-finding comparison, and organization semantics not accepted upstream.
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
    - actions/repository-intelligence/action.yml
    - actions/repository-intelligence/scripts/generate_repository_intelligence_site.py
    - actions/repository-intelligence/scripts/render_repository_intelligence_compare.py
    - https://github.com/egohygiene/observatory/blob/main/docs/repository-intelligence-read-model.md
    - https://github.com/egohygiene/observatory/blob/main/schemas/repository-intelligence-compare.v1.schema.json
work:
  objective: Materialize Repository Intelligence /compare/ from Observatory's accepted comparison artifact without creating Relay-local diff, causal, quality, or resolution semantics.
  success_conditions:
    - Bind Before and After boundaries to one repository and the rendered current commit.
    - Keep entity, relationship, and event additions, removals, and field changes distinct.
    - Expose exact Observatory-provided changed field paths and per-view digest differences.
    - Link current entity evidence only when stable IDs resolve against the matching after snapshot.
    - Keep missing comparison evidence distinct from a valid zero-change comparison.
    - Keep Repository Intelligence generation and public bundle validation green.
  active_issue:
    provider: github
    id: egohygiene/relay#86
    url: https://github.com/egohygiene/relay/issues/86
  next:
    kind: pull-request
    id: egohygiene/relay#87
    description: Review and merge the validated bounded /compare/ implementation if acceptable.
    readiness: ready-for-review-after-final-head-ci
    references:
      - https://github.com/egohygiene/relay/issues/86
      - https://github.com/egohygiene/relay/pull/87
      - https://github.com/egohygiene/relay/issues/29
      - https://github.com/egohygiene/observatory/issues/7
    depends_on: []
state:
  base:
    revision: 86ec7af2a01124d1d38872dc80f878e48a4f8568
    ref: refs/heads/main
    verified_at: "2026-09-16T14:14:51Z"
  candidate:
    branch: feat/86-repository-intelligence-compare
    implementation_revision: 470e3c8cbeac4fcea435f4740534e375ed137616
    pull_request: https://github.com/egohygiene/relay/pull/87
    handoff_state: ready-for-review-after-final-head-ci
  live:
    status: verified
    observed_at: "2026-09-16T14:27:56Z"
    default_branch_revision: 86ec7af2a01124d1d38872dc80f878e48a4f8568
    dependencies_checkpoint: {issue: egohygiene/relay#77, pull_request: egohygiene/relay#78, state: merged}
    work_checkpoint: {issue: egohygiene/relay#79, pull_request: egohygiene/relay#80, state: merged}
    releases_checkpoint: {issue: egohygiene/relay#81, pull_request: egohygiene/relay#82, state: merged}
    search_checkpoint: {issue: egohygiene/relay#83, pull_request: egohygiene/relay#85, state: merged}
    compare_checkpoint: {issue: egohygiene/relay#86, pull_request: egohygiene/relay#87, state: open}
    notes: Observatory #7 owns the accepted compare artifact and explicitly defines it as structural change without causality. Broader Health/Hygiene conformance remains owned by Observatory #5. Organization Roadmap remains gated by Hygiene #60 and Observatory #22 unless live state changes.
review:
  status: complete-for-implementation-revision
  reviewed_at: "2026-09-16T14:27:56Z"
  reviewed_by: ChatGPT
  evidence:
    - command: Verify Relay main, merged Search PR #85, parent #29, open compare work, repository instructions, and Observatory compare contract.
      outcome: passed
      notes: No competing Compare child or PR existed; live main was 86ec7af2a01124d1d38872dc80f878e48a4f8568.
    - command: Inspect Observatory compare schema, read-model documentation, compare_snapshots implementation, and CLI boundary.
      outcome: passed
      notes: Compare reports Before/After boundaries, added/removed/field-changed graph IDs, and per-view digests without causal claims.
    - command: Add bounded Compare renderer, explicit observatory-comparison action input, strict binding to the matching after snapshot, and focused tests.
      outcome: passed
      notes: Existing one-snapshot Dependencies/Work/Releases/Search composition remains unchanged; Compare is a separate two-snapshot adapter.
    - command: GitHub Actions Validate Relay actions run 35108717028, run 65, on 470e3c8cbeac4fcea435f4740534e375ed137616.
      outcome: passed
      notes: Full unit/integration tests, action/catalog and continuity-contract validation, Python compilation, Bash and inline-shell syntax, JSON/YAML parsing, caller-owned publication fixture, reusable Repository Intelligence generation/provenance, publication review, and reviewed-byte preservation all passed.
    - command: GitHub Actions Relay continuity preflight run 35108717120, run 17.
      outcome: passed
      notes: Shared continuity adapter and bounded evidence path passed on the implementation candidate.
    - command: GitHub Actions Dependency review run 35108716771, run 24.
      outcome: passed
      notes: Dependency review passed; Dependabot automerge run 35108716757 / #24 skipped as expected.
  environment_limitations:
    - Direct GitHub network access from the local shell is unavailable; repository reads, writes, and validation status use the connected GitHub integration.
roadmap_impact:
  disposition: no-state-transition
  rationale: REL-RI-006 remains active. Compare completes another bounded supporting view, but broader Health semantics, deterministic publication completion, and organization aggregation remain outside this candidate.
adr_impact:
  disposition: none
  rationale: The change implements ADR-007 and Observatory's accepted compare contract without changing authority or dependency direction.
privacy:
  classification: public-repository
  contains_sensitive_data: false
  redactions: []
---

# Relay continuity

## Current checkpoint

Issue #86 implements the fifth bounded `REL-RI-006` supporting view: `/compare/`.
Observatory owns the two-snapshot comparison and reports structural change only:
Before/After boundaries, added/removed IDs, changed field paths, and per-view
digests. Relay presents that artifact without explaining why the change happened.

## Candidate implementation

Branch: `feat/86-repository-intelligence-compare`

Implementation revision:
`470e3c8cbeac4fcea435f4740534e375ed137616`

Pull request: https://github.com/egohygiene/relay/pull/87

The implementation:

- adds optional `observatory-comparison` while requiring the matching `observatory-snapshot` when comparison evidence is supplied;
- binds comparison repository, `after.represented_commit`, and `after.snapshot_id` to the current rendered repository/snapshot;
- leaves the existing one-snapshot supporting-view composer unchanged;
- renders Compare through a separate adapter because Observatory Compare is a separate artifact, not `views.compare`;
- keeps entity, relationship, and event added/removed/changed categories distinct;
- shows exact changed field paths and per-view before/after SHA-256 digests;
- links only current entity IDs that resolve safely through the matching after Search projection;
- never treats additions as improvements, removals as resolutions/regressions, or structural deltas as causal evidence;
- distinguishes unavailable comparison evidence from a valid comparison with no normalized structural differences;
- fails closed on shape drift, duplicate/overlapping IDs, malformed field paths/digests, mismatched boundaries, and contradictory changed flags.

## Validation evidence

On implementation revision `470e3c8cbeac4fcea435f4740534e375ed137616`:

- `Validate Relay actions` run 35108717028 / #65 passed its complete chain.
- `Relay continuity preflight` run 35108717120 / #17 passed.
- `Dependency review` run 35108716771 / #24 passed.
- Dependabot automerge run 35108716757 / #24 skipped as expected.

This continuity-only update creates a new final PR head. Verify the same required
workflows on that exact head before merge.

## Roadmap and decision reconciliation

`REL-RI-006` remains active. Dependencies (#77/#78), Work (#79/#80), Releases
(#81/#82), and Search (#83/#85) are merged; Compare (#86/#87) is the current
candidate. No roadmap state transition is appropriate yet.

No new ADR is required. The implementation follows ADR-007: Observatory owns
normalized comparison truth; Relay owns static presentation and validated artifacts.

## Blockers and deferred work

- No implementation blocker remains for `/compare/`; only final-head CI and review remain.
- Compare is normalized structural comparison, not raw Git diffing or root-cause analysis.
- Audit-specific comparison remains owned by Relay #74 / Observatory #20.
- Broader `/health/` must not absorb unfinished fleet-conformance semantics from Observatory #5.
- `/audits/`, `/hygiene/`, and `/sanity/` remain gated by their normalized owner contracts unless live state changes.
- Organization `/roadmap/` remains gated by Hygiene #60 and Observatory #22 unless those dependencies have landed.

## Next dependency-ready work

After #87 merges, re-fetch Relay #29/#33 and the visual-control-plane upstream
contracts. Compare completes the accepted #7 supporting-view set except the
broader Health surface. Prefer the smallest truthful remaining dashboard slice:
a bounded core `/health/` check/freshness view if its ownership boundary is
still clear, deterministic publication completion if #33 is the remaining gate,
or organization `/roadmap/` immediately if Hygiene #60 and Observatory #22 have landed.

## Resume protocol

1. Verify newest Relay `main`, issue #86, PR #87, and exact-head checks.
2. Re-read parent #29, #33, and `REL-RI-006` before selecting another view.
3. Re-fetch Hygiene #60, Observatory #22/#5, and `.github#30` before choosing organization or Health work.
4. Do not duplicate a route with an open implementation PR.
5. Keep one bounded visual checkpoint per PR and reconcile continuity before handoff.
