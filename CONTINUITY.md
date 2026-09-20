---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: "2026-09-20T15:23:04Z"
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: "Preserve checkpoint 1 of Relay issue #5 and ordered plan #99."
  includes:
    - "The immutable Hygiene, EgoLint, and Holon architecture-validation source profile."
    - "Closed request/result schemas, bounded publish-safe fixtures, and offline contract validation."
    - "The authority, privacy, rollout, failure, and future local/CI parity boundaries."
  excludes:
    - "The offline adapter, diagram evidence implementation, reusable workflow, or consumer dogfood."
    - "Release publication or movement of the v1 alias."
    - "Changes to sibling or consumer repositories."
    - "Consumer code execution or repository/provider mutation."
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
    - README.md
    - catalog/repository-architecture-validation.json
    - schemas/repository-architecture-validation-profile.v1.schema.json
    - schemas/repository-architecture-validation-request.v1.schema.json
    - schemas/repository-architecture-validation-result.v1.schema.json
    - scripts/validate_repository_architecture_contract.py
    - tests/fixtures/repository-architecture-validation/cases.v1.json
    - tests/test_repository_architecture_contract.py
    - docs/repository-architecture-validation.md
work:
  objective: "Complete #99 checkpoint 1 by freezing the upstream profile and normalized evidence seam for parent #5."
  success_conditions:
    - Hygiene policy, EgoLint semantics, and Holon materialization inputs are pinned by full revision and SHA-256.
    - Relay remains orchestration/evidence authority and does not copy sibling semantics or author consumer state.
    - Local and future CI adapters share one closed, versioned request/result contract.
    - Advisory is the default and maximum mode while required upstream releases and implementation gates are incomplete.
    - Missing, partial, legacy, truncated, or unavailable evidence cannot silently become conformance.
    - Paths, findings, annotations, scans, bytes, results, and retained evidence are bounded.
    - Public, private, internal, present, legacy, unknown, nonconformant, and unavailable fixtures are covered.
  active_issue:
    provider: github
    id: egohygiene/relay#5
    url: https://github.com/egohygiene/relay/issues/5
  execution_plan:
    provider: github
    id: egohygiene/relay#99
    url: https://github.com/egohygiene/relay/issues/99
    checkpoint: 1
    checkpoint_name: freeze-upstream-profile-and-evidence-contracts
  next:
    kind: pull-request
    summary: "Publish checkpoint 1 from feat/5-architecture-validation, verify exact-head CI, and return merge authority to the user."
state:
  branch: feat/5-architecture-validation
  base_branch: main
  base_revision: b8c9cfbae7f74b8c7c6daf735a38a59ac72096d9
  base_tree: f4116c15ff34d9bd6af10287f1acb5141796ffac
  active_pull_requests: []
  issue_state: open
  plan_issue_state: open
  notes: "No duplicate #5 pull request existed at checkpoint start. PR #98 had merged cleanly and #6 was closed."
upstream_evidence:
  hygiene:
    revision: c589587395750cd1c79c6fa0bef010189c547249
    role: organization-policy
    release_included: false
  egolint:
    revision: 8b99ec4377eb84044fac411dff6b8074317ec094
    role: validation-semantics
    release_included: false
  holon:
    revision: 660b941f99618806fcadd589bcdae61c519f96e4
    role: materialization
    release_included: false
review:
  status: local-validation-passed
  reviewed_at: "2026-09-20T15:23:04Z"
  reviewed_by: ChatGPT
  evidence:
    - command: "Verify current main, issues #5/#99, open pull requests, dependencies, repository guidance, architecture, decisions, roadmap, catalogs, and current CI."
      outcome: passed
      notes: "Main is b8c9cfbae7f74b8c7c6daf735a38a59ac72096d9; #5 and #99 are open; no duplicate Relay pull request existed; prerequisite Hygiene, EgoLint, and Holon work is complete."
    - command: "Inspect exact current Hygiene, EgoLint, and Holon source artifacts and compute SHA-256 digests."
      outcome: passed
      notes: "The profile records exact commits and every reviewed policy, schema, rule, lock, blueprint, and template byte."
    - command: "python3 scripts/validate_repository_architecture_contract.py validate"
      outcome: passed
      notes: "The profile, schemas, fixture references, ownership, bounds, rollout, and privacy contracts passed."
    - command: "python3 scripts/validate_repository_architecture_contract.py verify-sources with explicit local Hygiene, EgoLint, and Holon checkouts"
      outcome: passed
      notes: "All three checkout revisions and all 21 pinned artifact digests matched without executing sibling code."
    - command: "python3 -m unittest tests.test_repository_architecture_contract -v"
      outcome: passed
      notes: "Nine focused tests cover valid fixtures plus immutable-pin, authority, path, bound, provenance, outcome, count, schema, malformed-type, and privacy mutations."
    - command: "Run all Relay contract/catalog validators and python3 -m unittest discover --start-directory tests --pattern test_*.py."
      outcome: passed
      notes: "All action, workflow, CI-lifecycle, continuity, architecture, and journal validators passed; 418 repository tests passed."
    - command: "Compile Python; parse JSON and YAML; validate inline and checked-in Bash; validate continuity structure and git diff whitespace."
      outcome: passed
      notes: "66 JSON documents, 34 YAML documents, and 91 inline Bash blocks parsed or passed syntax checks; CONTINUITY.md remained within its 240-line and 16-KiB bounds."
  environment_limitations:
    - "A generic JSON Schema implementation is unavailable locally; the dependency-free validator, schema-shape tests, fixture validation, and JSON parsing provide the local check."
    - "Ruby is unavailable locally; PyYAML parsed action/workflow YAML and Bash validated extracted inline shell blocks. Canonical CI repeats Ruby/Psych parsing."
    - "The maintain-repository-continuity skill is unavailable in this session; this checkpoint was refreshed directly under AGENTS.md."
parallel_work:
  - id: egohygiene/relay#15
    state: waiting-scheduled-acceptance
    notes: "The merged repository journal remains queued with #95 for the first genuine scheduled-run acceptance; it does not block #5 checkpoint 1."
roadmap_impact:
  disposition: evidence-reconciled-no-release-transition
  rationale: "REL-ARCH-001 is active and checkpoint 1 is complete locally; no action, reusable workflow, release, or moving alias is introduced."
adr_impact:
  disposition: none
  rationale: "The contract operationalizes ADR-001, ADR-002, ADR-003, ADR-005, and ADR-006 without changing authority or ownership."
privacy:
  classification: public-repository
  contains_sensitive_data: false
  redactions: []
  notes: "Contracts retain bounded repository-relative diagnostics and explicit classification only; raw source, secrets, environment values, provider tokens, logs, and private cross-repository content are excluded."
---

# Relay continuity

## Current checkpoint

Issue #99 decomposes parent #5 into six ordered checkpoints. Checkpoint 1 is
implemented on `feat/5-architecture-validation` from exact main
`b8c9cfbae7f74b8c7c6daf735a38a59ac72096d9`. It freezes the immutable upstream
profile and closed request/result seam only; it does not advertise a callable
action or workflow.

## Authority and availability

Hygiene owns policy, EgoLint owns validation semantics, Holon owns
materialization, and consumer repositories own their architecture records.
Relay owns orchestration and bounded evidence. Repository-contract and ADR
rules are available in the pinned EgoLint source. Diagram semantic validation
is honestly `planned`, so unavailable diagram coverage cannot become a passing
claim. The complete source set is unreleased, which caps this profile at
advisory mode.

## Remaining gates

1. Run the complete Relay validation suite and review the final diff.
2. Publish one checkpoint-1 pull request advancing #5 and #99.
3. Verify the exact PR head, reviews, mergeability, and all required checks.
4. Return merge authority to the user; do not merge in this session.
5. After the user merges, begin checkpoint 2 as a separate offline-adapter PR.
6. Keep release publication and the moving `v1` alias deferred for the later batched release.
