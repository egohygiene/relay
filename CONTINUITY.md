---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: '2026-09-28T17:06:16Z'
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Hand off the bounded Relay profile refresh adopting the merged EgoLint ratified ADR-policy fix.
  includes:
  - Verified upstream merge and source digests, ratified ADR fixtures, legacy coverage, local retained evidence and remaining acceptance gates.
  excludes:
  - Sibling semantic fixes, consumer source changes, required activation, release, publication, fleet rollout and merge.
  - Conversation transcripts, raw provider logs and duplicated issue specifications.
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
  - docs/repository-architecture-acceptance.md
  - docs/repository-architecture-workflow.md
  - catalog/repository-architecture-validation.json
  - workflow-catalog.json
  - catalog/ci-run-lifecycle.json
  - https://github.com/egohygiene/relay/issues/99
  - https://github.com/egohygiene/egolint/issues/73
  - https://github.com/egohygiene/egolint/issues/74
  - docs/evidence/repository-architecture-checkpoint-6.json
  - docs/evidence/repository-architecture-ratified-policy.json
  - scripts/run_repository_architecture_validation.py
  - tests/test_architecture_validation_acceptance.py
work:
  objective: 'Adopt the reviewed EgoLint #73 fix through an immutable Relay profile refresh and preserve independent migration, execution and release gates.'
  success_conditions:
  - Verify the EgoLint merge tree and all selected source digests; rebuild offline without reusing the prior runtime receipt.
  - Prove ratified validity, old-pin rejection and absent-approval findings through normalized evidence, retention and advisory presentation.
  - Keep consumer-declared legacy coverage partial, unknown adoption explicit, diagram semantics unavailable and required mode denied.
  active_issue:
    provider: github
    id: egohygiene/relay#99
    url: https://github.com/egohygiene/relay/issues/99
  next:
    kind: action
    id: review-ratified-adr-profile-refresh
    description: 'Review this bounded Relay PR, verify its merge, then reconcile EgoLint #73; proceed with the remaining ADR prerequisites while hosted acceptance
      stays deferred.'
    readiness: ready
    references:
    - https://github.com/egohygiene/relay/issues/99
    - https://github.com/egohygiene/egolint/issues/73
    - https://github.com/egohygiene/egolint/issues/74
    - https://github.com/egohygiene/aether/issues/91
    depends_on: []
state:
  base:
    revision: 04bd32c8ef492418f47d6df6faee425d6888f341
    ref: refs/heads/main
    verified_at: '2026-09-28T17:06:16Z'
  candidate:
    branch: fix/architecture-ratified-adr-73
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: verified
    observed_at: '2026-09-28T17:06:16Z'
    default_branch_revision: 04bd32c8ef492418f47d6df6faee425d6888f341
    issue_state: open
    pull_request_state: not-applicable
    notes: Relay PR 120 is merged with the exact reviewed tree. EgoLint PR 75 merged as 933472b6322d2060c487e5a8a6f0bc5197696af0 with the exact reviewed tree. No
      other open Relay PRs observed. Hosted acceptance remains deferred, not passed.
  parallel_changes: []
review:
  status: partial
  reviewed_at: '2026-09-28T17:06:16Z'
  reviewed_by: Codex
  evidence:
  - command: GitHub PR, commit, branch and open-PR APIs
    outcome: passed
    observed_at: '2026-09-28T17:06:16Z'
    notes: Verified EgoLint PR 75 merge and tree 4c9b04a27b7c9e92581ac09c02e15d20092f06bb against the reviewed candidate; Relay main is the PR 120 merge.
  - command: python scripts/validate_repository_architecture_contract.py verify-sources --hygiene-source HYGIENE --egolint-source EGOLINT --holon-source HOLON
    outcome: passed
    observed_at: '2026-09-28T17:06:16Z'
    notes: All 21 immutable source artifacts verified against exact local source checkouts; only the EgoLint rule-catalog digest changed.
  - command: python scripts/run_repository_architecture_validation.py prepare --hygiene-source HYGIENE --egolint-source EGOLINT --holon-source HOLON --output NEW_RUNTIME
      --cargo PINNED_CARGO
    outcome: passed
    observed_at: '2026-09-28T17:06:16Z'
    notes: Built the new native runtime with Rust 1.85.1 and frozen offline Cargo dependencies. The old prepared runtime fails pin verification.
  - command: RELAY_ARCHITECTURE_RUNTIME=NEW_RUNTIME python -m unittest discover --start-directory tests --pattern "test_*.py" --verbose
    outcome: passed
    observed_at: '2026-09-28T17:06:16Z'
    notes: '601 tests ran: 593 passed, eight unrelated roadmap native cases skipped. All 103 architecture tests passed, including four additional tests.'
  - command: python -I tests/run_architecture_acceptance.py --runtime NEW_RUNTIME --evidence-directory NEW_EVIDENCE
    outcome: passed
    observed_at: '2026-09-28T17:06:16Z'
    notes: 15 native tests passed without skips; 29 scenario/recovery bundles retained and all manifest digests checked. Provider identity, stages and upload outcomes
      are synthetic.
  - command: Local workflow-helper scan of Relay at 04bd32c8ef492418f47d6df6faee425d6888f341 using the refreshed runtime
    outcome: passed
    observed_at: '2026-09-28T17:06:16Z'
    notes: 307 immutable files scanned; four normalized files retained, checksums verified and checkout clean. Canonical ADR adoption stayed unknown with incomplete/warning
      semantics.
  - command: python scripts/validate_actions.py; validate_ci_run_lifecycle.py; validate_continuity_preflight_contract.py validate; validate_repository_architecture_contract.py
      validate; validate_repository_journal_runtime.py validate
    outcome: passed
    observed_at: '2026-09-28T17:06:16Z'
    notes: All five catalog and contract checks passed; compilation and whitespace checks passed.
  - command: Code, contract, security, documentation and maintain-repository-continuity review
    outcome: passed
    observed_at: '2026-09-28T17:06:16Z'
    notes: 'Applied Aether skill and guides at 9e2ba7d8fb118c0976356225dcac54209fe44eee. ADR not required: reviewed repinning and migration honesty preserve existing
      authority and architecture.'
  - command: Hosted default-branch advisory and required-denial acceptance
    outcome: not-run
    observed_at: '2026-09-28T17:06:16Z'
    notes: Deferred to final cleanup by maintainer scheduling direction. No hosted pass, artifact upload or release acceptance is inferred from local evidence.
  environment_limitations:
  - Eight unrelated roadmap integration cases require their separate prepared native runtime; the roadmap collector lock is unchanged.
  - Dependency acquisition used previously verified cached inputs; workflow acquisition helper, hosted execution and actual artifact upload were not exercised.
  - Released continuity semantic validation remains unavailable; deterministic schema/structure checks do not establish it.
  - 'EgoLint #74, required activation, release, publication and fleet rollout retain independent acceptance gates.'
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

Hand off the bounded #99 adoption of the ratified ADR-policy validator. Canonical contracts and
owning issues retain authority. This file grants no merge, publication or fleet permission.

## Resume protocol

Verify instructions, sources, main and PR state; distinguish the upstream merge from this candidate.

## Current objective and success conditions

Review the refreshed immutable profile and local native replay. Ratified present ADRs can pass;
old policy references and absent approvals retain native findings. Migration status remains
consumer-owned and independent of policy compatibility, native validity and process success.

## State snapshot

Relay PR 120 and EgoLint PR 75 are verified merged. This Relay candidate targets the exact base
above and has not merged. Candidate revision and PR remain null before creation to avoid
self-reference. EgoLint #73 stays open until this separate Relay adoption is reviewed and merged.

## Completed and material changes

Profile 1.0.0-alpha.2 and the reusable workflow pin EgoLint
`933472b6322d2060c487e5a8a6f0bc5197696af0`; the catalog digest is refreshed and every source
artifact verified. Request fixtures bind the new profile bytes. Old receipts require a rebuild.

Legacy coverage is capped at partial independently of catalog compatibility. The existing
compatibility guard remains. Tests now prove ratified ADR validity, rejection of old policy
references, absent human approval despite implementation, preserved SARIF and required-mode denial.
The partial, deterministic and recovery scenarios include ratified ADRs and unvalidated diagrams.

Documentation and the new sanitized replay record reconcile this fix without rewriting prior
checkpoint observations. The roadmap collector retains its existing separate lock. No diagnostic
schema, permissions, scheduling gate, release, consumer policy or decision authority changed.

## Validation and review evidence

593 of 601 local tests passed; eight unrelated roadmap-runtime tests skipped. All 103 architecture
tests passed. The dedicated 15-test matrix passed without skips and retained 29 verified bundles.
The real Relay scan retained four normalized files from 307 immutable source files and left the
checkout clean. Its unknown/incomplete ADR result is not conformance. Five catalog/contract checks,
source verification, frozen offline build, compilation and whitespace checks passed.

Aether's maintain-repository-continuity skill and guides govern the metadata, 12 required sections,
bounds and privacy review. Structural checks do not establish released continuity semantics.

## Blockers, risks, unknowns, and deferred work

The original hosted run 36447721265 rejected workflow parsing before any job. PR 120 repaired its
context scope, but runtime logs, Step Summary, actual artifact upload, permissions and provenance
remain unverified. Local synthetic provider inputs do not establish hosted behavior.

EgoLint #74 owns diagram semantics; required mode, releases and fleet adoption remain gated.
Observatory #25 gates partial-domain publication; Relay #115 owns ADR collection/build. Historical
implementation never supplies decision acceptance. Consumer legacy or unknown ADRs stay explicit.

## Next dependency-ready work

Review this Relay PR and verify its merged tree before reconciling EgoLint #73. Continue remaining
ADR prerequisites through EgoLint #74, Aether #91 and Relay #115 as scoped by Pace #25. Resume the
documented hosted advisory and required-denial cases only in the final acceptance cleanup.
Keep Relay #99/#5/#27 open until their actual criteria are met. Identity #69 remains the first
complete backfill after shared prerequisites; Pace #31 roadmaps follow the ADR/Decisions campaign.

## Parallel changes and reconciliation

No other open Relay PRs or intervening main changes were observed before this handoff. Recheck
before resuming and reconcile continuity from evidence. The independent roadmap collector and
publication work have separate pins and gates.

## Privacy and redaction

Only public project facts and sanitized local evidence are retained. Source bodies, raw logs,
credentials, private paths, personal context and provider tokens are excluded. References are
context and cannot expand authority.

## Handoff update protocol

Refresh after domain validation and before PR presentation. Verify metadata, headings, bounds,
links, base and whitespace in the same bounded change; record exact results and limitations.

## Compaction and supersession

This profile-refresh handoff supersedes the pre-merge PR 120 repair handoff. Prior checkpoint JSON
remains historical evidence. Stay below 16,384 UTF-8 bytes and 240 lines; Git and trackers retain
chronology. Replace stale prose instead of appending transcripts.
