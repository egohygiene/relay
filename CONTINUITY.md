---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: "2026-09-20T14:35:07Z"
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: "Preserve the reviewed implementation state for Relay issue #6."
  includes:
    - "Workflow cancellation classes and their machine-checked mapping to every current Relay workflow."
    - "Bounded .reports producer directories, explicit retention, checksummed run manifests, and failure-safe artifact upload."
    - "The preserve-ci-report action, Relay disposable failure smoke, and immutable Empathy OSV adoption evidence."
  excludes:
    - "Release publication or movement of the v1 alias."
    - "Changes to Empathy or any other consumer repository."
    - "Repository snapshot commits, deployment, or other provider mutation."
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
    - catalog/ci-run-lifecycle.json
    - schemas/ci-run-lifecycle.schema.json
    - actions/preserve-ci-report/action.yml
    - actions/preserve-ci-report/scripts/preserve_ci_report.py
    - actions/preserve-ci-report/schemas/ci-report-manifest.schema.json
    - actions/preserve-ci-report/README.md
    - docs/ci-run-lifecycle.md
    - scripts/validate_ci_run_lifecycle.py
    - tests/test_ci_run_lifecycle.py
    - tests/test_preserve_ci_report.py
work:
  objective: "Complete #6 with enforceable cancellation classes and durable success/failure report preservation."
  success_conditions:
    - Every executable Relay workflow belongs to one cancellation class and catalog drift fails CI.
    - Supersedable checks cancel by stable work identity; evidence-preserving checks and provider writers do not cancel.
    - Immutable publication serializes by version and retains matching-evidence recovery semantics.
    - A producer writes only beneath .reports/<producer> and receives a unique run/attempt artifact identity.
    - Successful evidence is complete; failed evidence is partial or unavailable and never silently green.
    - File count, byte count, paths, links, revision identity, retention, manifests, and checksums are bounded and validated.
    - Empathy and disposable-consumer evidence satisfy the issue acceptance boundary without copying consumer implementation.
  active_issue:
    provider: github
    id: egohygiene/relay#6
    url: https://github.com/egohygiene/relay/issues/6
  next:
    kind: pull-request
    id: ci-report-lifecycle
    description: "Inspect PR #98 at its exact head, resolve any CI or review finding, and return merge authority to the user."
    readiness: published-exact-head-validation-pending
    references:
      - https://github.com/egohygiene/relay/issues/6
      - https://github.com/egohygiene/relay/pull/98
      - https://github.com/egohygiene/empathy/blob/98778e8442d3be3ea7a3d1f62b71f33969346ecc/.github/workflows/osv-scan.yml
    depends_on: []
state:
  base:
    revision: c1ff5e5230262048909b72afa83ef7ded4443072
    tree: 395100f6e27d307ece88204dc5aadc9d4924baad
    ref: refs/heads/main
    verified_at: "2026-09-20T14:18:00Z"
  candidate:
    branch: feat/6-ci-report-lifecycle
    implementation_revision: 03c05f8267e10da662d18389e3618442d55a964b
    implementation_tree: 54fb48321e453aa8d930267e7f640bf3905b222c
    pull_request: https://github.com/egohygiene/relay/pull/98
    handoff_state: published-exact-head-validation-pending
  live:
    status: pull-request-open
    observed_at: "2026-09-20T14:35:07Z"
    default_branch_revision: c1ff5e5230262048909b72afa83ef7ded4443072
    active_pull_requests:
      - egohygiene/relay#98
    issue_state: open
    notes: "PR #98 is open and ready for review at the exact implementation tree. REL-01 and Empathy #7 are complete; no duplicate pull request exists."
review:
  status: published-exact-head-validation-pending
  reviewed_at: "2026-09-20T14:35:07Z"
  reviewed_by: ChatGPT
  evidence:
    - command: "Verify current main, issue #6, open pull requests, dependencies, repository guidance, architecture, decisions, roadmap, and catalogs."
      outcome: passed
      notes: "Main is c1ff5e5230262048909b72afa83ef7ded4443072; #6 is open; no open Relay PR exists; both recorded dependencies are complete."
    - command: "Inspect Empathy OSV workflow, run 35354888576, and snapshot commit c9800ed19293e7c1b1d4a70c3bea006c1f2b64f5."
      outcome: passed
      notes: "The report upload succeeded before the severity gate failed; the publication job then succeeded, and its bot-authored snapshot binds the run and represented revision."
    - command: "python3 scripts/validate_actions.py and python3 scripts/validate_ci_run_lifecycle.py"
      outcome: passed
      notes: "13 actions, 21 workflows, 15 reusable workflows, all workflow classes, and the durable report policy validated."
    - command: "python3 scripts/validate_continuity_preflight_contract.py validate and python3 scripts/validate_repository_journal_runtime.py validate"
      outcome: passed
      notes: "The existing continuity and journal contracts remain valid."
    - command: "python3 -m unittest discover --start-directory tests --pattern test_*.py --verbose"
      outcome: passed
      notes: "409 tests passed, including bounded report provenance, failure evidence, symlink rejection, cancellation drift, and disposable smoke contract tests."
    - command: "Compile Python; parse JSON and YAML; validate inline and checked-in Bash; run git diff checks."
      outcome: passed
      notes: "61 JSON documents, 34 YAML documents, and 90 inline Bash blocks parsed or passed syntax checks."
  environment_limitations:
    - "A generic JSON Schema implementation is unavailable locally; closed validators, shape tests, fixtures, and JSON parsing passed."
    - "Ruby is unavailable locally; PyYAML parsed action/workflow YAML and Bash validated extracted inline shell blocks. Canonical CI repeats Ruby/Psych parsing."
    - "The maintain-repository-continuity skill is unavailable in this session; this checkpoint was refreshed directly under AGENTS.md."
    - "The disposable artifact upload requires GitHub Actions and remains pending PR #98 exact-head CI."
parallel_work:
  - id: egohygiene/relay#15
    state: waiting-scheduled-acceptance
    notes: "The merged repository journal remains queued for its first genuine scheduled-run acceptance together with #95."
roadmap_impact:
  disposition: evidence-reconciled-no-release-transition
  rationale: "Issue #6 adds the CI lifecycle/report contract to the pending additive release surface; no tag or moving alias changes in this task."
adr_impact:
  disposition: none
  rationale: "The implementation operationalizes ADR-001, ADR-002, ADR-003, ADR-005, and ADR-006 without changing authority or ownership."
privacy:
  classification: public-repository
  contains_sensitive_data: false
  redactions: []
  notes: "The report action records bounded paths, sizes, digests, run identity, and status only; it accepts no free-form failure text and grants no repository permission."
---

# Relay continuity

## Current checkpoint

Issue #6 is published in PR #98 on `feat/6-ci-report-lifecycle` from exact main
`c1ff5e5230262048909b72afa83ef7ded4443072`. No duplicate pull request exists.
The implementation assigns all current workflows to explicit cancellation
classes and adds a reusable action that preserves complete, partial, or
unavailable run-bound evidence beneath `.reports/<producer>/`.

## Evidence boundary

Empathy remains independently owned. Its immutable OSV workflow is recorded as
reviewed consumer evidence because it already demonstrates ref cancellation,
stable reports, always-on artifact upload, 30-day retention, and post-upload
failure enforcement. Relay's deliberately failing validation fixture is the
disposable executable consumer and uses one-day retention.

## Remaining gates

1. Inspect PR #98 exact-head GitHub Actions, reviews, and mergeability.
2. Resolve any blocking or substantive review finding in the same PR.
3. Return merge authority to the user; do not merge PR #98 in this session.
4. Keep release publication and the moving `v1` alias deferred for the later batched release.
5. Independently observe the first scheduled repository-journal run before closing #15 and #95.
