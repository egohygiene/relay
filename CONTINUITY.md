---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: "2026-09-17T07:53:03Z"
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Preserve the minimum verified state needed to review Relay #14's warning-first stale pull-request lifecycle.
  includes:
    - Relay #14, draft PR #93, verified base revision, pre-continuity implementation revision, and validation evidence.
    - The composite action, reusable workflow, conditional permission modes, catalogs, examples, recovery contract, and focused tests.
    - Reconciliation of merged PR #92 and stale action/workflow inventory wording.
  excludes:
    - Publishing v1.6.0 or the v1 alias, activating a consumer schedule, running mutation against current Relay pull requests, and unrelated issue lifecycle changes.
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
    - WORKFLOW_CATALOG.md
    - workflow-catalog.json
    - action-catalog.json
    - .github/workflows/stale-pull-requests.yml
    - actions/stale-pull-requests/action.yml
    - actions/stale-pull-requests/README.md
    - examples/workflows/stale-pull-requests.md
    - tests/test_stale_pull_requests.py
    - tests/test_stale_pull_request_workflow.py
work:
  objective: Publish a reusable advisory-first stale lifecycle that cannot silently close work and remains least-privilege in PR-only mode.
  success_conditions:
    - Default to advisory planning, disabled closure, PR-only evaluation, draft and bot exemptions, and protected security/dependency/critical labels.
    - Separate read-only planning from checksum-bound apply authority and require a visible warning from an earlier run before closure.
    - Revalidate exact live state, warning provenance, activity, labels, reviewers, exemptions, and PR head before each mutation.
    - Keep PR-only jobs free of Issues permission while granting it explicitly to issue-enabled jobs.
    - Bound provider scans, require stable unique identities, fail on incomplete issue-search evidence, and emit body-redacted summaries.
    - Document partial writes, reopen recovery, shared Actions-bot trust, provider races, emergency disable, and immutable consumer adoption.
    - Pass canonical Relay validation without publishing a release or claiming the issue's publication gate is complete.
  active_issue:
    provider: github
    id: egohygiene/relay#14
    url: https://github.com/egohygiene/relay/issues/14
  next:
    kind: pull-request
    id: egohygiene/relay#93
    description: Review and merge the validated stale lifecycle implementation if exact final-head CI remains green.
    readiness: ready-for-review-after-final-head-ci
    references:
      - https://github.com/egohygiene/relay/issues/14
      - https://github.com/egohygiene/relay/pull/93
    depends_on: []
state:
  base:
    revision: 14788f6de909164cc0763eab513bb16adc1f11fe
    ref: refs/heads/main
    verified_at: "2026-09-17T07:51:00Z"
  candidate:
    branch: feat/14-stale-pr-lifecycle
    implementation_revision: 2eb26e69fc0ade39f71fa031e60b79cbd980dba0
    pull_request: https://github.com/egohygiene/relay/pull/93
    handoff_state: ready-for-review-after-final-head-ci
  live:
    status: verified
    observed_at: "2026-09-17T07:52:00Z"
    default_branch_revision: 14788f6de909164cc0763eab513bb16adc1f11fe
    prior_delivery_checkpoint:
      issue: egohygiene/relay#59
      pull_request: egohygiene/relay#92
      state: merged
    active_pull_requests:
      - egohygiene/relay#93
    cleanup_audit:
      relay_29: open-unmet-search-and-health-acceptance
      relay_58: deferred-until-optiflow-v1-and-flow-suite-stability
      relay_60: open-upstream-gates
      relay_71: open-v1.6.0-publication-gate
    notes: PR #92 is merged into current main. PR #93 is the only open Relay pull request and is intentionally draft until this continuity-only final head is validated.
review:
  status: complete-for-implementation-revision
  reviewed_at: "2026-09-17T07:52:00Z"
  reviewed_by: ChatGPT
  evidence:
    - command: Verify newest Relay main, open pull requests, issue #14, dependency #1, repository instructions, architecture, decisions, roadmap, catalogs, and prior continuity state.
      outcome: passed
      notes: Main remains 14788f6de909164cc0763eab513bb16adc1f11fe; dependency #1 is closed and PR #93 is the only open Relay pull request.
    - command: Implement the stale lifecycle action, workflow, catalogs, documentation, example, and security-focused tests.
      outcome: passed
      notes: Advisory and closure default off; PR-only and issue-enabled authority are separated; no consumer code is checked out or executed.
    - command: python3 scripts/validate_actions.py
      outcome: passed
      notes: 10 actions, 17 workflows, and 12 reusable workflow entries validated.
    - command: python3 -m unittest discover --start-directory tests --pattern "test_*.py"
      outcome: passed
      notes: 333 tests passed, including 50 focused lifecycle and catalog tests.
    - command: python3 -m compileall -q actions scripts tests
      outcome: passed
      notes: Python sources compiled successfully.
    - command: python3 scripts/validate_continuity_preflight_contract.py validate
      outcome: passed
      notes: The pinned continuity request/result contract and fixtures passed.
    - command: Parse changed JSON and YAML and run bash -n on every new inline shell.
      outcome: passed
      notes: Catalogs, manifests, workflow YAML, and inline Bash passed local syntax checks.
    - command: git diff --check
      outcome: passed
      notes: The implementation diff contains no whitespace errors.
    - command: Independent code, security, and contract review.
      outcome: passed
      notes: No blocker, major, or minor findings remain after permission, timing, pagination, path, warning-visibility, and recovery hardening.
  environment_limitations:
    - Ruby, Task, and gh are unavailable locally. Exact CI Psych parsing and provider-side checks must pass on the final PR head.
    - The named maintain-repository-continuity skill is unavailable in this session; the checked-in continuity contract and validator were applied directly.
roadmap_impact:
  disposition: evidence-reconciled-no-state-transition
  rationale: Issue #14 adds the staged v1.6.0 surface and corrects roadmap evidence without completing publication or advancing a quest state.
adr_impact:
  disposition: none
  rationale: The implementation operationalizes ADR-001, ADR-002, ADR-003, ADR-005, and ADR-006 without changing ownership, dependency direction, release units, or authority.
privacy:
  classification: public-repository
  contains_sensitive_data: false
  redactions: []
  notes: Plans omit titles, bodies, tokens, raw provider payloads, and configured comment bodies; summaries expose only bounded item IDs, kinds, transitions, reasons, counts, and hashes.
---

# Relay continuity

## Current checkpoint

Issue #14 adds Relay's warning-first stale pull-request lifecycle. Draft PR #93
is the one bounded implementation. It starts from current main
`14788f6de909164cc0763eab513bb16adc1f11fe`; prior PR #92 is merged, so the
old #59 checkpoint is superseded.

## Candidate implementation

Branch: `feat/14-stale-pr-lifecycle`

Pre-continuity implementation revision:
`2eb26e69fc0ade39f71fa031e60b79cbd980dba0`

Pull request: https://github.com/egohygiene/relay/pull/93

The implementation:

- adds one composite action and one reusable workflow with advisory defaults;
- separates PR-only and issue-enabled permissions into conditional jobs;
- requires a checksum-bound plan, default-branch apply, trusted warning marker,
  stale label, unchanged activity/head, and an elapsed warning window;
- protects drafts, bots, users, requested teams, and exact exempt labels;
- resets managed labels after activity, exemptions, or reopen recovery;
- rejects future evaluation times, incomplete or unstable provider scans,
  symlinked paths, hidden custom warnings, and changed live snapshots; and
- records bounded partial-write recovery without claiming transactionality.

## Validation evidence

The implementation tree passed catalog validation, all 333 tests, 50 focused
lifecycle/catalog tests, Python compilation, continuity-contract validation,
JSON/YAML and inline Bash syntax checks, diff checking, and three independent
reviews. This continuity-only update creates a new final PR head. Required
GitHub workflows must pass on that exact head before merge.

## Authority boundary

Read-only provider scan -> checksum-bound advisory plan -> explicitly authorized
default-branch apply -> visible warning -> later unchanged-state closure ->
maintainer reopen recovery.

The caller owns scheduling and the permission ceiling. PR-only mode never asks
for Issues permission. Issue processing, provider mutation, and closure each
require explicit opt-in. No branch is deleted and no consumer code is checked
out or executed.

## Roadmap and decision reconciliation

The roadmap evidence now names the additive v1.6.0 stale lifecycle surface, but
there is no state transition because neither v1.6.0 nor the `v1` alias is
published.

No new ADR is required. The implementation follows existing externalized
package, least-privilege, immutable-reference, repository-release-unit, and
workflow-catalog decisions.

## Known limitations and gates

- PR #93 is not merge authority; the user reviews and merges it.
- Final-head GitHub Actions evidence is pending after this continuity-only commit.
- GitHub's Actions-bot identity is repository-wide, not unique workflow proof.
- Provider timestamps have second precision and a final-read-to-write race is irreducible.
- Multi-item provider writes are not transactional; documented fresh-run or reopen recovery applies.
- Issue #14 remains open until v1.6.0 and its moving `v1` alias are published.
- Issue #58 remains deferred until OptiFlow v1.0.0 and Flow suite stability.

## Next dependency-ready action

Review PR #93. Merge it only after exact final-head validation passes. Do not
close #14 on merge; immutable v1.6.0 and `v1` publication remain a separate
release gate.

## Resume protocol

1. Verify newest Relay main and PR #93's exact head.
2. Confirm the diff after `2eb26e69fc0ade39f71fa031e60b79cbd980dba0`
   is continuity-only.
3. Require validation, continuity preflight, and dependency review to pass.
4. Merge only through the user's normal review path; do not auto-merge.
5. Keep #14 open until immutable release and moving-alias evidence exist.
