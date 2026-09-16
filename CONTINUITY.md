---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: "2026-09-16T15:01:17Z"
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Preserve the minimum verified state needed to review the sixth bounded REL-RI-006 supporting-view checkpoint.
  includes:
    - Repository Intelligence Health issue, pull request, exact implementation revision, and accepted source contract.
    - Core Observatory check-state, assertion, freshness, stale-ID, unknown-ID, and null-score semantics.
    - Merged Dependencies, Work, Releases, Search, and Compare checkpoints.
    - Roadmap disposition, ADR disposition, exact validation evidence, upstream gates, and next-work guidance.
  excludes:
    - Conversation transcripts, raw provider data, fleet-wide Hygiene conformance, synthetic health scores, and organization semantics not accepted upstream.
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
    - actions/repository-intelligence/scripts/render_repository_intelligence_health.py
    - https://github.com/egohygiene/observatory/blob/main/docs/repository-intelligence-read-model.md
work:
  objective: Materialize Repository Intelligence /health/ from Observatory's accepted core Health query without creating Relay-local conformance or score semantics.
  success_conditions:
    - Show normalized check-state counts and current check records with canonical evidence links.
    - Keep assertion and freshness distributions visible without reducing them to a score.
    - Preserve explicit stale IDs and unknown IDs as distinct evidence states.
    - Keep missing, partial, empty, stale, unknown, and populated states distinct.
    - Keep score null and reject incompatible or contradictory Health evidence.
    - Keep Repository Intelligence generation and public bundle validation green.
  active_issue:
    provider: github
    id: egohygiene/relay#88
    url: https://github.com/egohygiene/relay/issues/88
  next:
    kind: pull-request
    id: egohygiene/relay#89
    description: Review and merge the validated bounded /health/ implementation if acceptable.
    readiness: ready-for-review-after-final-head-ci
    references:
      - https://github.com/egohygiene/relay/issues/88
      - https://github.com/egohygiene/relay/pull/89
      - https://github.com/egohygiene/relay/issues/29
      - https://github.com/egohygiene/observatory/issues/7
      - https://github.com/egohygiene/observatory/issues/5
    depends_on: []
state:
  base:
    revision: ce4d92c15d24e19d621097ba3212cad05dcde60a
    ref: refs/heads/main
    verified_at: "2026-09-16T14:53:33Z"
  candidate:
    branch: feat/88-repository-intelligence-health
    implementation_revision: 4c7c758f079f6ef69d092d372528c39461a1ebd8
    pull_request: https://github.com/egohygiene/relay/pull/89
    handoff_state: ready-for-review-after-final-head-ci
  live:
    status: verified
    observed_at: "2026-09-16T15:01:17Z"
    default_branch_revision: ce4d92c15d24e19d621097ba3212cad05dcde60a
    dependencies_checkpoint: {issue: egohygiene/relay#77, pull_request: egohygiene/relay#78, state: merged}
    work_checkpoint: {issue: egohygiene/relay#79, pull_request: egohygiene/relay#80, state: merged}
    releases_checkpoint: {issue: egohygiene/relay#81, pull_request: egohygiene/relay#82, state: merged}
    search_checkpoint: {issue: egohygiene/relay#83, pull_request: egohygiene/relay#85, state: merged}
    compare_checkpoint: {issue: egohygiene/relay#86, pull_request: egohygiene/relay#87, state: merged}
    health_checkpoint: {issue: egohygiene/relay#88, pull_request: egohygiene/relay#89, state: open}
    notes: Observatory #7 owns the accepted core Health query and deliberately leaves score null. Fleet-wide Hygiene conformance remains separately owned by open Observatory #5. Organization Roadmap remains gated by open Hygiene #60 and Observatory #22.
review:
  status: complete-for-implementation-revision
  reviewed_at: "2026-09-16T15:01:17Z"
  reviewed_by: ChatGPT
  evidence:
    - command: Verify Relay main, merged Compare PR #87, parent #29/#33, open work, repository instructions, and organization-roadmap upstreams.
      outcome: passed
      notes: No competing Relay PR existed; live main was ce4d92c15d24e19d621097ba3212cad05dcde60a. Hygiene #60, Observatory #22, and Observatory #5 remain open.
    - command: Inspect Observatory #7 read-model documentation and accepted Health fixture shape.
      outcome: passed
      notes: Core Health owns check records, check-state counts, assertion/freshness distributions, stale_ids, unknown_ids, and score null; it does not claim fleet conformance.
    - command: Add bounded Health renderer, deterministic mixed-state fixture, focused fail-closed/static/accessibility tests, and supporting-view pipeline integration.
      outcome: passed
      notes: Existing Dependencies, Work, Releases, Search, and Compare authority boundaries remain unchanged.
    - command: GitHub Actions Validate Relay actions run 35112288260, run 68, on 4c7c758f079f6ef69d092d372528c39461a1ebd8.
      outcome: passed
      notes: Action/catalog metadata, continuity-contract validation, unit/integration tests, Python compilation, Bash and inline-shell syntax, JSON/YAML parsing, caller-owned publication fixture, reusable Repository Intelligence generation/provenance, publication review, and reviewed-byte preservation passed.
    - command: GitHub Actions Relay continuity preflight run 35112288292, run 19.
      outcome: passed
      notes: Shared continuity adapter and bounded evidence path passed on the implementation candidate.
    - command: GitHub Actions Dependency review run 35112286544, run 26.
      outcome: passed
      notes: Dependency review passed; Dependabot automerge run 35112281318 / #26 skipped as expected.
  environment_limitations:
    - Direct GitHub network access from the local shell is unavailable; repository reads, writes, and validation status use the connected GitHub integration.
roadmap_impact:
  disposition: no-state-transition
  rationale: REL-RI-006 remains active. Health is the sixth bounded repository supporting-view candidate, but deterministic publication and the organization dashboard remain incomplete. ROADMAP.md therefore keeps its current state until reviewed evidence warrants reconciliation.
adr_impact:
  disposition: none
  rationale: The change follows ADR-007 and Observatory's accepted Health contract without changing authority, dependency direction, public contract ownership, or system boundaries.
privacy:
  classification: public-repository
  contains_sensitive_data: false
  redactions: []
---

# Relay continuity

## Current checkpoint

Issue #88 implements the sixth bounded `REL-RI-006` supporting view: `/health/`.
Observatory owns normalized core Health truth; Relay statically presents the supplied
checks and evidence states without upgrading them into fleet conformance or a score.

## Candidate implementation

Branch: `feat/88-repository-intelligence-health`

Implementation revision:
`4c7c758f079f6ef69d092d372528c39461a1ebd8`

Pull request: https://github.com/egohygiene/relay/pull/89

The implementation:

- renders check-state posture, normalized check records, assertion/freshness distributions, stale IDs, and unknown IDs;
- keeps represented commit and snapshot freshness in the existing shared shell;
- deep-links each normalized check to its canonical evidence;
- preserves Observatory ordering and explicit unavailable/partial/empty/stale/unknown states;
- preserves `score: null` and explains why no Relay-local percentage, grade, maturity rating, or security posture is calculated;
- uses progressive disclosure and existing static-first, mobile, keyboard, screen-reader, and reduced-motion shell behavior;
- fails closed on unsafe links, duplicate check IDs, contradictory check-state counts, invalid distributions, duplicate/overlapping stale and unknown IDs, freshness-count mismatches, and any non-null score;
- does not consume unfinished fleet-wide conformance semantics from Observatory #5.

## Validation evidence

On implementation revision `4c7c758f079f6ef69d092d372528c39461a1ebd8`:

- `Validate Relay actions` run 35112288260 / #68 passed its complete chain.
- `Relay continuity preflight` run 35112288292 / #19 passed.
- `Dependency review` run 35112286544 / #26 passed.
- Dependabot automerge run 35112281318 / #26 skipped as expected.

This continuity-only update creates a new final PR head. Verify the same required
workflows on that exact head before merge.

## Roadmap and decision reconciliation

`REL-RI-006` remains active. Dependencies (#77/#78), Work (#79/#80), Releases
(#81/#82), Search (#83/#85), and Compare (#86/#87) are merged; Health (#88/#89)
is the current candidate. No roadmap state transition is appropriate yet.

No new ADR is required. The implementation follows ADR-007: Observatory owns
normalized truth; Relay owns static composition and validated publication artifacts.

## Blockers and deferred work

- No implementation blocker remains for core `/health/`; final-head CI and review remain.
- Fleet-wide Hygiene conformance remains gated by Observatory #5 and must not be inferred from core Health evidence.
- Organization `/roadmap/` remains gated by Hygiene #60 and Observatory #22; `.github#29` must not invent the missing organization-roadmap semantics.
- Deterministic Repository Intelligence publication/canary rollout remains owned by Relay #33.

## Next dependency-ready work

After #89 merges, re-fetch Relay #33 and the organization-roadmap upstream chain.
If Hygiene #60 or Observatory #22 is still open, prefer the bounded deterministic
publication/canary checkpoint in #33. Pivot to Organization Intelligence `/roadmap/`
only after its normalized upstream contract is accepted.

## Resume protocol

1. Verify newest Relay `main`, issue #88, PR #89, and exact-head checks.
2. Re-read #29, #33, `REL-RI-006`, and ADR-007 before selecting more work.
3. Re-fetch Hygiene #60, Observatory #22/#5, `.github#29`, and `.github#30` before organization work.
4. Do not duplicate a route with an open implementation PR.
5. Keep one bounded visual checkpoint per PR and reconcile continuity before handoff.
