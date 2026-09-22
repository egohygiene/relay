---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: "2026-09-22T07:56:23Z"
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: "Implement Relay checkpoint #104's Repository Intelligence workflow trust boundary and durable failure evidence, then publish the exact review handoff."
  includes:
    - "The trusted/fork pull-request, default-push, reusable-call, and manual-rebuild event and authority contract."
    - "Revision-scoped site artifacts, sanitized fixed-retention run reports, workflow gates, schemas, fixtures, catalogs, and documentation."
    - "Review-only pull-request publication; merge authority remains with the user."
  excludes:
    - "Pages deployment, artifact-to-deployment provenance, deployment receipts, and rollback verification owned by #105."
    - "Akashic or Empathy consumer migration, final #33 reconciliation, product polish, or fleet rollout."
    - "Observatory #24, Relay #102, release publication, or movement of the v1 alias."
  precedence:
    - user-and-runtime-instructions
    - scoped-repository-instructions
    - live-repository-and-work-tracker-state
    - canonical-repository-sources
    - continuity-checkpoint
  canonical_sources:
    - AGENTS.md
    - AI_CONSTITUTION.md
    - ARCHITECTURE.md
    - SYSTEM.md
    - DECISIONS.md
    - ROADMAP.md
    - README.md
    - .github/workflows/repository-intelligence.yml
    - actions/repository-intelligence/action.yml
    - actions/repository-intelligence/workflow-evidence/action.yml
    - actions/repository-intelligence/workflow-evidence/schemas/repository-intelligence-workflow-report.schema.json
    - actions/preserve-ci-report/action.yml
    - docs/repository-intelligence-publication.md
    - workflow-catalog.json
work:
  objective: "Present one exact, locally validated #104 implementation PR while retaining post-merge provider evidence as open closeout work."
  success_conditions:
    - "Every supported event/invocation class has documented executable coverage under one explicit read-only authority ceiling."
    - "Fork input cannot access secrets or tokens, write state, use trusted caches, publish Pages, or execute consumer-owned control-plane code."
    - "All third-party actions are immutable-pinned and Relay-local helpers resolve from the exact called revision."
    - "Concurrency cancels only the same repository, caller-workflow-ref, target-ref, and contract identity."
    - "Success sites and success/failure reports have revision/run identities, digests, bounded retention, and fail-closed gates."
    - "Reports expose only closed stage, code, revision, version, artifact, and remediation metadata from an isolated runner-temporary path."
    - "Negative fixtures and mutation tests reject unsafe identity, input, path, permission, gate, schema, and diagnostic states."
  active_issue:
    provider: github
    id: egohygiene/relay#104
    url: https://github.com/egohygiene/relay/issues/104
  next:
    kind: issue
    id: egohygiene/relay#105
    description: "After #104 merges and its required provider evidence is recorded, bind deterministic Repository Intelligence artifacts to consumer-owned deployment provenance."
    readiness: blocked-by-104-merge-and-closeout
    references:
      - https://github.com/egohygiene/relay/issues/105
      - https://github.com/egohygiene/relay/issues/33
    depends_on:
      - egohygiene/relay#104
state:
  base:
    revision: 4a1f86acf570b9bc5b337f7ef3fbd00d951c2e85
    ref: refs/heads/main
    verified_at: "2026-09-22T07:48:49Z"
  candidate:
    branch: codex/relay-104-intelligence-trust-failures
    revision: 3556bfabbd55993a03a9a208d938e00013c9f0e0
    tree: eb5c6a053743c5e7df90e498a2c9f3fec986b7b6
    pull_request: https://github.com/egohygiene/relay/pull/107
    handoff_state: provider-validation-passed-ready-for-review
  live:
    status: verified
    observed_at: "2026-09-22T07:56:23Z"
    default_branch_revision: 4a1f86acf570b9bc5b337f7ef3fbd00d951c2e85
    issue_state: open
    pull_request_state: draft
    notes: "PR #107 contains the exact locally reviewed implementation tree; trusted-PR validation run 35701854093 passed with bound site and report artifacts. This continuity-only update still requires an exact-head recheck before the draft is marked ready. No merge, issue closure, default-branch run, deployment, or completed #33 evidence update is claimed."
  parallel_changes: []
review:
  status: passed-continuity-head-recheck-pending
  reviewed_at: "2026-09-22T07:56:23Z"
  reviewed_by: ChatGPT
  evidence:
    - command: "Verify live Relay #104, #105, #106, main, open pull-request state, repository guidance, architecture, decisions, roadmap, and catalogs."
      outcome: passed
      observed_at: "2026-09-22T07:48:49Z"
      notes: "Main remains 4a1f86acf570b9bc5b337f7ef3fbd00d951c2e85; #104-#106 are open and retain their ordered boundaries."
    - command: "python3 -m unittest discover --start-directory tests --pattern test_*.py --verbose"
      outcome: passed
      observed_at: "2026-09-22T07:48:49Z"
      notes: "All 474 unit and integration tests passed, including event/trust, hostile checkout, schema contradiction, stage-gate mutation, path/symlink, and sanitizer coverage."
    - command: "Run validate_actions.py, validate_ci_run_lifecycle.py, validate_continuity_preflight_contract.py, validate_repository_architecture_contract.py, and validate_repository_journal_runtime.py."
      outcome: passed
      observed_at: "2026-09-22T07:48:49Z"
      notes: "All five catalog and contract validators passed."
    - command: "Compile Python; parse 63 JSON and 35 YAML documents with duplicate-key checks; validate 94 inline Bash blocks, checked-in shell, both JavaScript assets, and git diff whitespace."
      outcome: passed
      observed_at: "2026-09-22T07:48:49Z"
      notes: "All deterministic syntax, metadata, and whitespace checks passed with PyYAML 6.0.3; Ruby/Psych remains a canonical-CI check."
    - command: "Independent read-only security, correctness, and #104 acceptance reviews."
      outcome: passed
      observed_at: "2026-09-22T07:48:49Z"
      notes: "The final reviews found no implementation blocker; one valid-ref portability edge was repaired and revalidated."
    - command: "Publish implementation commit through the connected GitHub API and compare its tree to the locally validated commit."
      outcome: passed
      observed_at: "2026-09-22T07:48:49Z"
      notes: "Remote commit 3556bfabbd55993a03a9a208d938e00013c9f0e0 and the local implementation have identical tree eb5c6a053743c5e7df90e498a2c9f3fec986b7b6."
    - command: "Inspect trusted-PR validation run https://github.com/egohygiene/relay/actions/runs/35701854093 and its retained Repository Intelligence artifacts."
      outcome: passed
      observed_at: "2026-09-22T07:56:23Z"
      notes: "The full workflow, Repository Intelligence job, and output consumer passed. Site artifact repository-intelligence-site-v1-1321918958-46989847c47c22311f3b7e6c8b765b67c1556dd8-35701854093-1 has digest sha256:e98bf71663bea5b097e01f05f40de211f03068e1414ed821b293d3df9fda1876 and 1-day smoke retention. Report artifact relay-report-repository-intelligence-v1-35701854093-1 has digest sha256:a9e37b2681084da09e3bb6c6435ebd06345c0c57a450ae257ea0b4bb1fe7cee5 and 30-day retention; its RIW-000 report and manifest bind the PR merge revision, run, site digest, and allowlisted authority."
  environment_limitations:
    - "The continuity-only head update must repeat required PR checks before the draft is marked ready."
    - "Exact merged revision plus default-push, fork, manual, retained artifact, and completed #33 evidence are necessarily post-merge closeout work; #104 remains open."
    - "Ruby is unavailable locally; PyYAML and duplicate-key traversal parsed metadata, while canonical CI repeats parsing with Ruby/Psych."
    - "The maintain-repository-continuity skill is unavailable in this session; this checkpoint was refreshed directly from the pinned local Aether template under AGENTS.md."
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

# Relay continuity

## Purpose and precedence

This checkpoint records #104's bounded workflow-trust and durable-evidence
implementation. It does not replace canonical architecture, roadmap, Git
history, live issues, or PR state. Resolve conflicts using the precedence above.

## Current state

- Base: live `main` at `4a1f86acf570b9bc5b337f7ef3fbd00d951c2e85`.
- Implementation: `3556bfabbd55993a03a9a208d938e00013c9f0e0`, exact tree
  `eb5c6a053743c5e7df90e498a2c9f3fec986b7b6`, in draft PR #107.
- Local verification: 474 tests, five contract validators, all static checks,
  three independent reviews, and trusted-PR run 35701854093 passed.
- Live: #104 and parent #33 remain open. No merge or deployment is claimed.

## Material changes

- Added a pre-checkout event, invocation, identity, input, and retention gate.
- Enforced explicit read-only/no-secret/no-cache/no-Pages authority and exact
  immutable third-party or revision-bound Relay-local resolution.
- Isolated site names by contract/repository/revision/run and cancellation by
  caller workflow ref plus target ref.
- Added a closed sanitized report schema, runner-temporary report creation,
  fixed 30-day preservation, and failure reassertion for every actionable stage.
- Hardened Python imports, CLI values, Git refs, path/symlink boundaries, stage
  sequencing, upload-digest claims, workflow gates, and mutation validation.
- Updated fixtures, catalogs, lifecycle docs, adoption guidance, changelog, and
  the roadmap without transferring deployment authority from consumers.

## Remaining evidence and next work

PR #107 must pass its continuity-only exact-head recheck and return to the user
for merge. Keep #104 open afterward until its exact merged revision and the
remaining representative event/trust run
URLs, success/failure artifact names and digests, retention, permission audit,
negative-fixture results, and completed-evidence update to #33 are recorded.
Only then is #105 dependency-ready; it owns build-to-deployment provenance.

## Resume protocol

1. Re-verify main, #104, #105, #33, PR #107, and the exact PR head.
2. Inspect every provider check and the Repository Intelligence site/report
   artifacts before marking the PR ready.
3. Resolve substantive review findings on this branch; do not merge for the user.
4. After user merge, collect the closeout evidence above before closing #104 or
   beginning #105.

## Privacy and compaction

This public checkpoint contains only public repository identifiers, revisions,
issue/PR URLs, contract names, and bounded validation outcomes. Keep it below
16,384 UTF-8 bytes and 240 lines; replace stale state instead of appending history.
