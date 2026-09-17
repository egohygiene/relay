---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: "2026-09-17T13:08:24Z"
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Preserve the minimum verified state needed to continue Relay #15 through the ordered execution plan in #95.
  includes:
    - Relay #15, execution plan #95, draft PR #96, and the verified main and implementation revisions.
    - Step 1's checksum-locked Copilot CLI runtime, authentication choices, preflight contracts, validation, and connection procedure.
    - The remaining user-assisted organization-policy and account-connection gate.
  excludes:
    - Aether dependency freezing, evidence collection, agent execution, journal rendering, workflow composition, live Copilot requests, and release publication.
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
    - catalog/repository-journal-runtime.json
    - docs/repository-journal-runtime.md
    - schemas/repository-journal-runtime-profile.v1.schema.json
    - schemas/repository-journal-runtime-preflight-result.v1.schema.json
    - scripts/validate_repository_journal_runtime.py
    - tests/test_repository_journal_runtime.py
    - vendor/copilot-cli/package.json
    - vendor/copilot-cli/package-lock.json
work:
  objective: Deliver a reusable scheduled repository journal through one bounded, evidence-gated implementation line.
  success_conditions:
    - Complete each numbered checkpoint in #95 in order and record its reviewable evidence before advancing.
    - Keep GitHub evidence deterministic and authoritative while treating repository text and agent output as untrusted data.
    - Bind the Aether journal contract immutably and render validated output deterministically.
    - Keep agent authority isolated, least-privilege, non-mutating, bounded, and independent of consumer code execution.
    - Publish Step Summary and durable machine-readable artifacts with explicit completeness and provenance.
    - Pass exact-head validation and user-controlled merge without bundling release or moving-alias publication.
  active_issue:
    provider: github
    id: egohygiene/relay#15
    url: https://github.com/egohygiene/relay/issues/15
  execution_plan:
    provider: github
    id: egohygiene/relay#95
    url: https://github.com/egohygiene/relay/issues/95
    active_step: 1
  next:
    kind: manual-verification
    id: repository-journal-runtime-connection
    description: Verify the organization-billed GitHub token path with the user, record the Step 1 checkpoint on #95, and do not advance Step 2 until the connection evidence is reconciled.
    readiness: implementation-ready-connection-pending
    references:
      - https://github.com/egohygiene/relay/issues/15
      - https://github.com/egohygiene/relay/issues/95
      - https://github.com/egohygiene/relay/pull/96
    depends_on: []
state:
  base:
    revision: 325382e2baba094319373d6931b57f54743832f1
    ref: refs/heads/main
    verified_at: "2026-09-17T13:07:00Z"
  candidate:
    branch: feat/15-repository-journal
    implementation_revision: f94eb4f8360e34963953417fadc3919d3a106ae7
    implementation_tree: d088d6d7f07a39627abc49c0f2e96a97b6a66047
    pull_request: https://github.com/egohygiene/relay/pull/96
    handoff_state: draft-step-1-connection-pending
  live:
    status: verified
    observed_at: "2026-09-17T13:08:24Z"
    default_branch_revision: 325382e2baba094319373d6931b57f54743832f1
    prior_delivery_checkpoint:
      issue: egohygiene/relay#17
      pull_request: egohygiene/relay#94
      state: merged
    active_pull_requests:
      - egohygiene/relay#96
    notes: No duplicate #15 branch or pull request existed before #96. Issues #15 and #95 remain open, and #95 has no checkpoint comment yet.
review:
  status: implementation-reviewed-connection-pending
  reviewed_at: "2026-09-17T13:08:00Z"
  reviewed_by: ChatGPT
  evidence:
    - command: Verify current main, issues #15 and #95, comments, open pull requests, matching branches, repository instructions, architecture, decisions, roadmap, catalogs, and prior continuity.
      outcome: passed
      notes: Main is 325382e2baba094319373d6931b57f54743832f1; #15 and #95 are open; no duplicate implementation line existed.
    - command: Review GitHub's official Copilot CLI Actions, authentication, and programmatic-use documentation and the live npm package metadata.
      outcome: passed
      notes: The preferred GITHUB_TOKEN path requires organization opt-in and copilot-requests write; the explicit fallback is a fine-grained PAT with Copilot Requests permission. @github/copilot 1.0.85 was selected and locked.
    - command: Implement the runtime profile, npm lock, preflight result contract, secret-free validator, connection guide, tests, and canonical CI validation.
      outcome: passed
      notes: The exact published implementation tree is d088d6d7f07a39627abc49c0f2e96a97b6a66047. It performs no live Copilot request and changes no organization setting.
    - command: python3 scripts/validate_repository_journal_runtime.py validate
      outcome: passed
      notes: The closed profile, exact package graph, registry sources, SHA-512 integrity values, and recorded file digests passed.
    - command: python3 scripts/validate_actions.py
      outcome: passed
      notes: 11 actions, 18 workflows, and 13 reusable workflow entries validated.
    - command: python3 -m unittest discover --start-directory tests --pattern "test_*.py"
      outcome: passed
      notes: 368 tests passed, including 12 focused runtime and authentication tests.
    - command: python3 -m compileall -q actions scripts tests
      outcome: passed
      notes: Python sources compiled successfully.
    - command: Parse 57 JSON and 31 YAML documents and inspect the installed locked CLI version.
      outcome: passed
      notes: Documents parsed successfully and the executable reported GitHub Copilot CLI 1.0.85 without receiving credential or unrelated environment values.
    - command: git diff --check
      outcome: passed
      notes: The Step 1 implementation diff contains no whitespace errors.
    - command: Final runtime, security, contract, and documentation review.
      outcome: passed
      notes: No blocker, major, or minor implementation findings remain; live policy and account evidence is deliberately pending.
  environment_limitations:
    - A generic JSON Schema implementation is unavailable locally; the repository-owned closed validator and contract tests passed.
    - The scratch clone has no HTTPS push credential; the selected GitHub connection published the exact reviewed Git tree.
    - The selected GitHub connection does not expose organization Copilot policy settings; that gate requires the user's organization settings session.
    - The named maintain-repository-continuity skill is unavailable in this session; the checked-in continuity contract and validator were applied directly.
roadmap_impact:
  disposition: evidence-reconciled-no-state-transition
  rationale: Step 1 establishes proposed runtime evidence for #15 without delivering the workflow, completing the execution plan, or publishing a release.
adr_impact:
  disposition: none
  rationale: The implementation operationalizes existing least-privilege, immutable-reference, bounded-evidence, release-unit, and catalog decisions without changing ownership or authority.
privacy:
  classification: public-repository
  contains_sensitive_data: false
  redactions: []
  notes: The profile and results contain package metadata, declared policy and permission states, boolean credential presence, reason codes, versions, and hashes; token values, prefixes, lengths, and fragments are excluded.
---

# Relay continuity

## Current checkpoint

Relay #15 is active through the ordered eleven-step plan in #95. Draft PR #96
is the single implementation line. Step 1's repository code is complete; live
organization policy and account connection evidence remains pending.

## Step 1 implementation

Branch: `feat/15-repository-journal`

Published implementation revision:
`f94eb4f8360e34963953417fadc3919d3a106ae7`

Pull request: https://github.com/egohygiene/relay/pull/96

The proposed profile locks `@github/copilot@1.0.85` and its npm graph, prefers
the short-lived workflow `GITHUB_TOKEN`, and defines a non-automatic
fine-grained PAT fallback. Its offline preflight emits only closed readiness
evidence and fails on missing, conflicting, unsupported, or unverified state.

## Authority and cost boundary

Step 1 makes no Copilot request, stores no credential, and changes no GitHub
setting. The preferred path requires organization approval for Copilot CLI
billed to the organization plus `copilot-requests: write`. The fallback must be
selected explicitly and is billed to the token owner's Copilot entitlement.
One invocation, one attempt, a five-minute timeout, and one scheduled run per
day are the initial upper bounds.

## Validation evidence

The implementation passed all 368 tests, 12 focused tests, action/workflow
catalog validation, continuity-contract validation, Python compilation, JSON
and YAML parsing, exact CLI version inspection, diff checking, and final code,
security, contract, and documentation review.

## Known limitations and gates

- PR #96 remains draft and grants no merge, release, or publication authority.
- #95 Step 1 remains unchecked until the organization policy, workflow
  permission, billing principal, and approved credential path are verified.
- No later #95 checkpoint has started.
- No consumer code is checked out or executed.

## Next dependency-ready action

Open the organization Copilot policy with the user, verify the preferred
organization-billed path, run the secret-free offline preflight in its intended
context, and record the Step 1 evidence on #95. If the preferred path is
unavailable, select the fine-grained PAT fallback explicitly rather than
switching automatically.

## Resume protocol

1. Verify current `main` and PR #96's exact head and checks.
2. Confirm the live organization policy for Copilot CLI billing.
3. Confirm the intended workflow permission and billing principal.
4. Run the offline preflight without printing or persisting credentials.
5. Record the Step 1 checkpoint on #95 before beginning Step 2.
6. Keep PR #96 draft and do not merge, publish, or move an alias.
