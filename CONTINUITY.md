---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: "2026-09-17T06:49:00Z"
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Preserve the minimum verified state needed to review Relay #59's legacy-workflow quarantine and graduation policy.
  includes:
    - Relay #59, draft PR #92, verified base revision, implementation revision, and validation evidence.
    - The inert evidence boundary, lifecycle policy, public historical fixture, catalog exclusion, privacy rules, and executable guard tests.
    - Reconciliation of merged PR #91 and the stale prior continuity checkpoint.
  excludes:
    - Activating or adopting a legacy workflow, changing supported workflow contracts, publishing a Relay release, consumer rollout, and unrelated repository-intelligence work.
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
    - docs/legacy-workflow-lifecycle.md
    - tests/test_legacy_workflow_quarantine.py
work:
  objective: Define a non-executable intake, review, graduation, and terminal-archive path for workflows found in legacy or consolidation repositories.
  success_conditions:
    - Preserve imported workflow evidence outside .github/workflows with a non-runnable suffix and no active references.
    - Bind public evidence to immutable source provenance, exact Git blob identity, and artifact SHA-256.
    - Keep private or restricted sources metadata-only and reject sensitive identity or workflow-shaped bytes from public Relay.
    - Review triggers, permissions, credentials, dependencies, mutations, deployment, repository assumptions, and reusable suitability explicitly.
    - Require normalization, isolated validation, catalogs, documentation, merge, immutable release, and later consumer-owned adoption in the correct order.
    - Keep rejected, superseded, and graduated evidence disabled, unique, and absent from supported catalogs.
    - Pass canonical Relay validation without changing any active workflow, action, permission, trigger, or authority boundary.
  active_issue:
    provider: github
    id: egohygiene/relay#59
    url: https://github.com/egohygiene/relay/issues/59
  next:
    kind: pull-request
    id: egohygiene/relay#92
    description: Review and merge the validated legacy-workflow lifecycle policy if acceptable.
    readiness: ready-for-review-after-final-head-ci
    references:
      - https://github.com/egohygiene/relay/issues/59
      - https://github.com/egohygiene/relay/pull/92
    depends_on: []
state:
  base:
    revision: 56ae8adf411a60bee534a61b2d451ecb7132cbdb
    ref: refs/heads/main
    verified_at: "2026-09-17T06:46:00Z"
  candidate:
    branch: docs/59-legacy-workflow-quarantine
    implementation_revision: a8f1681839bef32dffcdb011e3fe372d7b49ad9d
    pull_request: https://github.com/egohygiene/relay/pull/92
    handoff_state: ready-for-review-after-final-head-ci
  live:
    status: verified
    observed_at: "2026-09-17T06:46:00Z"
    default_branch_revision: 56ae8adf411a60bee534a61b2d451ecb7132cbdb
    prior_publication_checkpoint:
      issue: egohygiene/relay#90
      pull_request: egohygiene/relay#91
      state: merged
    active_pull_requests:
      - egohygiene/relay#92
    cleanup_audit:
      relay_29: open-unmet-search-and-health-acceptance
      relay_60: open-upstream-gates
      relay_71: open-v1.6.0-publication-gate
    notes: PR #91 is merged into current main. The old checkpoint that described it as open was stale and is superseded by this #59 checkpoint.
review:
  status: complete-for-implementation-revision
  reviewed_at: "2026-09-17T06:46:00Z"
  reviewed_by: ChatGPT
  evidence:
    - command: Verify newest Relay main, open pull requests, issue #59, repository instructions, architecture, decisions, roadmap, catalogs, and stale continuity state.
      outcome: passed
      notes: Main remains 56ae8adf411a60bee534a61b2d451ecb7132cbdb; #59 has no sibling-repository dependency and PR #92 is the only open Relay pull request.
    - command: Add lifecycle policy, disabled public historical evidence, internal provenance manifest, catalog documentation, changelog entry, and executable guard tests.
      outcome: passed
      notes: No active workflow/action or machine-readable catalog changed. The fixture is byte-identical to public Relay blob 714465a3e91ddb54faee39394e37038218085d4f and is archived with a .yml.disabled suffix.
    - command: python3 scripts/validate_actions.py
      outcome: passed
      notes: 9 actions, 16 workflows, and 11 reusable workflow entries validated.
    - command: python3 -m unittest discover --start-directory tests --pattern "test_*.py" --verbose
      outcome: passed
      notes: 297 tests passed, including five legacy-workflow boundary tests.
    - command: python3 -m compileall -q actions scripts tests
      outcome: passed
      notes: Python sources compiled successfully.
    - command: python3 scripts/validate_continuity_preflight_contract.py validate
      outcome: passed
      notes: The pinned continuity request/result contract and fixtures passed.
    - command: git diff --check
      outcome: passed
      notes: The implementation diff contains no whitespace errors.
  environment_limitations:
    - Ruby, Task, and gh are unavailable locally. Exact CI Psych parsing and provider-side checks must pass on the final PR head.
    - The named maintain-repository-continuity skill is unavailable in this session; the checked-in continuity contract and validator were applied directly.
roadmap_impact:
  disposition: no-state-transition
  rationale: Issue #59 is cross-cutting workflow intake governance and does not honestly complete or advance one existing roadmap quest.
adr_impact:
  disposition: none
  rationale: The policy operationalizes ADR-001, ADR-002, ADR-003, ADR-005, and ADR-006 without changing ownership, dependency direction, release units, or authority.
privacy:
  classification: public-repository
  contains_sensitive_data: false
  redactions: []
  notes: Only immutable public Relay history is retained as workflow evidence. Restricted sources are represented by an opaque manifest and a fixed metadata-only stub, never raw workflow bytes or repository identity.
---

# Relay continuity

## Current checkpoint

Issue #59 defines how Relay can study workflows found in legacy or
consolidation repositories without activating them. Draft PR #92 is the one
bounded implementation. It starts from current main
`56ae8adf411a60bee534a61b2d451ecb7132cbdb`; prior PR #91 is already merged,
so the old continuity checkpoint is no longer authoritative.

## Candidate implementation

Branch: `docs/59-legacy-workflow-quarantine`

Implementation revision:
`a8f1681839bef32dffcdb011e3fe372d7b49ad9d`

Pull request: https://github.com/egohygiene/relay/pull/92

The implementation:

- documents inventory, quarantine, review, normalization, isolated validation,
  merge, immutable release, graduation, and consumer adoption as distinct steps;
- makes `.github/workflows/` the executable boundary and rejects manual-only
  workflows as a substitute for quarantine;
- keeps retained evidence disabled, uncataloged, unique, and outside active
  automation;
- binds public fixtures to exact revision, URL, Git blob, and SHA-256 evidence;
- permits restricted sources only as opaque metadata plus one fixed redaction
  stub, with no private identity or workflow body;
- records the old public Relay release workflow as superseded by the current
  split release surfaces; and
- adds tests that fail on misplaced lifecycle states, stray files, symlink/path
  escapes, provenance drift, catalog/reference drift, missing review gates, and
  unsupported replacement claims.

## Validation evidence

The implementation tree passed catalog validation, all 297 tests, Python
compilation, continuity-contract validation, and diff checking locally. This
continuity-only update creates a new final PR head. Required GitHub workflows
must pass on that exact head before merge.

## Authority boundary

```text
historical bytes + immutable provenance
        -> inert evidence outside .github/workflows
        -> security and contract review
        -> separately implemented Relay package
        -> reviewed merge + immutable Relay release
        -> consumer-owned, full-SHA-pinned adoption
```

A captured file never becomes executable by being moved or renamed. Graduation
requires a normalized Relay implementation and later immutable release
evidence. Consumers retain mutation, deployment, merge, and release authority.

## Roadmap and decision reconciliation

There is no roadmap state transition. This is cross-cutting intake governance,
not evidence that a product quest shipped.

No new ADR is required. The checkpoint enforces the existing externalized
package, least-privilege, immutable-reference, repository-release-unit, and
workflow-catalog decisions.

## Known limitations and gates

- PR #92 is not merge authority; the user reviews and merges it.
- Final-head GitHub Actions evidence is pending after this continuity-only commit.
- Issue #29 remains open because matched-field Search evidence and broader
  Health posture are not fully delivered or formally superseded.
- Issue #60 remains open on EgoLint #55 and Holon #42.
- Issue #71 remains open until Relay v1.6.0 and its moving alias are published.
- Issue #58 is deferred until OptiFlow v1.0.0 and the Flow suite definition of
  done are both satisfied.

## Next dependency-ready action

Review PR #92. Merge it only after exact final-head validation passes. The merge
will close #59 through its pull-request footer. Do not activate the archived
fixture or add it to either catalog.

## Resume protocol

1. Verify newest Relay main and PR #92's exact head.
2. Confirm the final-head diff after
   `a8f1681839bef32dffcdb011e3fe372d7b49ad9d` is continuity-only.
3. Require validation, continuity preflight, and dependency review to pass.
4. Merge only through the user's normal review path; do not auto-merge.
5. Keep #29, #58, #60, and #71 open until their explicit gates are satisfied.
