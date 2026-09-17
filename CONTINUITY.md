---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: "2026-09-17T09:08:00Z"
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Preserve the minimum verified state needed to review Relay #17's reusable artifact-size budget contract and adapters.
  includes:
    - Relay #17, draft PR #94, verified base revision, implementation revision, and validation evidence.
    - The versioned report schema, composite action, read-only reusable workflow, catalogs, examples, and CI smoke path.
    - Size Limit JSON and bounded filesystem adapters for web, static-site, native, archive, and exported container-image artifacts.
    - Reconciliation of merged PR #93 and the deferred batched v1.6.0 publication gate.
  excludes:
    - Publishing v1.6.0 or moving v1, consumer migrations, Observatory ingestion, registry-native image inspection, and unrelated runtime-performance claims.
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
    - .github/workflows/artifact-budget.yml
    - actions/artifact-budget/action.yml
    - actions/artifact-budget/README.md
    - actions/artifact-budget/schemas/artifact-budget-report.schema.json
    - examples/workflows/artifact-budget.md
    - tests/test_artifact_budget.py
    - tests/test_artifact_budget_workflow.py
work:
  objective: Publish one common deterministic budget report and a least-privilege artifact handoff without executing consumer builds.
  success_conditions:
    - Normalize Size Limit JSON only for JavaScript/web use and prove at least one non-JavaScript filesystem adapter.
    - Record absolute bytes, optional baseline bytes and deltas, configured thresholds, warning bands, and explicit result states.
    - Support advisory and blocking modes while retaining machine-readable evidence before a blocking budget failure.
    - Bind current and optional baseline evidence to full immutable revisions and caller-produced artifact names.
    - Bound entry, byte, JSON parser, and item scans and reject traversal, symlinks, special files, duplicates, malformed data, and unsafe integers.
    - Keep the reusable workflow read-only, avoid checkout or consumer execution, and leave builds, lockfiles, thresholds, and artifact production with consumers.
    - Document maintained tool research, web and native adoption, partial evidence, unsupported measurements, and future Observatory ingestion.
    - Pass canonical Relay validation without publishing a release or claiming the later v1.6.0 gate is complete.
  active_issue:
    provider: github
    id: egohygiene/relay#17
    url: https://github.com/egohygiene/relay/issues/17
  next:
    kind: pull-request
    id: egohygiene/relay#94
    description: Validate the continuity-only final head, mark the draft ready, then leave merge authority to the user.
    readiness: draft-awaiting-final-head-ci
    references:
      - https://github.com/egohygiene/relay/issues/17
      - https://github.com/egohygiene/relay/pull/94
    depends_on: []
state:
  base:
    revision: 9c47f5eeff5fba86ab14be6b2ab59d187c820213
    ref: refs/heads/main
    verified_at: "2026-09-17T08:58:00Z"
  candidate:
    branch: feat/17-artifact-size-budgets
    implementation_revision: f016e9ec2d8d85a8b586ec7145ae707aa6d378ad
    implementation_tree: 79cb82264dbe8be5832025e52e72e2463260615d
    pull_request: https://github.com/egohygiene/relay/pull/94
    handoff_state: draft-awaiting-final-head-ci
  live:
    status: verified
    observed_at: "2026-09-17T09:07:21Z"
    default_branch_revision: 9c47f5eeff5fba86ab14be6b2ab59d187c820213
    prior_delivery_checkpoint:
      issue: egohygiene/relay#14
      pull_request: egohygiene/relay#93
      state: merged
    active_pull_requests:
      - egohygiene/relay#94
    notes: PR #93 is merged into current main. PR #94 is the bounded draft for #17; no release or consumer migration is included.
review:
  status: complete-for-implementation-revision
  reviewed_at: "2026-09-17T09:06:00Z"
  reviewed_by: ChatGPT
  evidence:
    - command: Verify newest Relay main, open work, issue #17 and dependency #1, repository instructions, architecture, decisions, roadmap, catalogs, and prior continuity state.
      outcome: passed
      notes: Main is 9c47f5eeff5fba86ab14be6b2ab59d187c820213, PR #93 is merged, dependency #1 is closed, and no duplicate implementation PR existed before #94.
    - command: Review the official Size Limit repository and documented JSON reporter at b1d4c43c6a92ea8b610898d342c9086c66d43ac3.
      outcome: passed
      notes: The repository was live and not archived; Relay uses the documented JSON boundary rather than a wrapper action and keeps non-JavaScript measurement separate.
    - command: Implement the report schema, adapters, action, reusable workflow, catalogs, documentation, examples, CI smoke path, and security-focused tests.
      outcome: passed
      notes: The exact published implementation tree is 79cb82264dbe8be5832025e52e72e2463260615d and no consumer code is checked out or executed.
    - command: python3 scripts/validate_actions.py
      outcome: passed
      notes: 11 actions, 18 workflows, and 13 reusable workflow entries validated.
    - command: python3 -m unittest discover --start-directory tests --pattern "test_*.py"
      outcome: passed
      notes: 356 tests passed, including 38 focused artifact-budget and catalog tests.
    - command: python3 -m compileall -q actions scripts tests
      outcome: passed
      notes: Python sources compiled successfully.
    - command: python3 scripts/validate_continuity_preflight_contract.py validate
      outcome: passed
      notes: The pinned continuity request/result contract and fixtures passed.
    - command: Parse 47 JSON and 29 YAML documents and run bash -n on 72 inline shell blocks plus repository shell files.
      outcome: passed
      notes: PyYAML and Bash syntax checks passed locally.
    - command: git diff --check
      outcome: passed
      notes: The implementation diff contains no whitespace errors.
    - command: Final code, security, and contract review.
      outcome: passed
      notes: No blocker, major, or minor findings remain after path, scan-bound, integer, partial-total, hidden-file, permission, failure-evidence, and consumer-authority review.
  environment_limitations:
    - Ruby/Psych is unavailable locally. Exact CI Psych parsing must pass on the final PR head.
    - The scratch clone has no HTTPS push credential; the selected GitHub connection published the exact reviewed Git tree.
    - The named maintain-repository-continuity skill is unavailable in this session; the checked-in continuity contract and validator were applied directly.
roadmap_impact:
  disposition: evidence-reconciled-no-state-transition
  rationale: Issue #17 adds to the staged v1.6.0 surface without publishing that immutable release or advancing a quest state.
adr_impact:
  disposition: none
  rationale: The implementation operationalizes ADR-001, ADR-002, ADR-003, ADR-005, and ADR-006 without changing ownership, dependency direction, release units, or authority.
privacy:
  classification: public-repository
  contains_sensitive_data: false
  redactions: []
  notes: Reports contain bounded identifiers, relative source paths, immutable revisions, numeric measurements, thresholds, reason codes, counts, and hashes; they omit file names, file bodies, tokens, manifests, and absolute runner paths.
---

# Relay continuity

## Current checkpoint

Issue #17 adds Relay's common artifact-size budget surface. Draft PR #94 is the
one bounded implementation. It starts from current main
`9c47f5eeff5fba86ab14be6b2ab59d187c820213`, where PR #93 is already merged.

## Candidate implementation

Branch: `feat/17-artifact-size-budgets`

Pre-continuity implementation revision:
`f016e9ec2d8d85a8b586ec7145ae707aa6d378ad`

Pull request: https://github.com/egohygiene/relay/pull/94

The implementation adds a versioned report, composite action, read-only
reusable workflow, web and native examples, machine catalogs, and a live CI
smoke handoff. Size Limit remains consumer-pinned and JavaScript-specific.
Filesystem adapters measure complete static sites, native binaries, archives,
and exported container-image archives without interpreting their contents.

## Contract and authority boundary

Consumer build -> caller-owned current/baseline artifacts -> read-only Relay
normalization -> deterministic hashed report -> advisory result or retained
blocking failure.

Relay never checks out or executes consumer code in the reusable workflow. The
consumer owns builds, dependency installation, Size Limit plugins and lockfile,
thresholds, reference revision, artifact production, and enforcement mode.
Relay accepts only full revision identities and traversal-safe, symlink-free,
bounded evidence.

## Validation evidence

The implementation tree passed all 356 tests, 38 focused tests, action/workflow
catalog validation, continuity-contract validation, Python compilation, JSON
and YAML parsing, Bash syntax checks, diff checking, and final code, security,
and contract review. GitHub Actions must pass on the continuity-only final head.

## Roadmap and decision reconciliation

The roadmap now includes artifact budgets in the additive v1.6.0 surface, but
there is no state transition because the release and moving alias remain
deferred. No new ADR is required; existing package, least-privilege,
immutable-reference, release-unit, and catalog decisions govern the work.

## Known limitations and gates

- PR #94 is not merge authority; the user reviews and merges it.
- Final-head GitHub Actions evidence is pending after this continuity update.
- Raw filesystem bytes do not establish runtime performance.
- Registry-native image semantics and credentials remain a future adapter.
- Runtime-only Size Limit checks remain explicit `unsupported` byte evidence.
- Issue #17 remains open for the later batched v1.6.0 and `v1` publication gate.

## Next dependency-ready action

Require validation, continuity preflight, and dependency review on PR #94's
exact final head. Mark it ready only when green, then leave merge to the user.

## Resume protocol

1. Verify newest Relay main and PR #94's exact head.
2. Confirm the diff after `f016e9ec2d8d85a8b586ec7145ae707aa6d378ad`
   is continuity-only.
3. Require all exact-head GitHub Actions checks to pass.
4. Mark the PR ready for review; do not merge it automatically.
5. Keep #17 open until the later immutable release and moving-alias gate.
