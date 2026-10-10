---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: '2026-10-10T16:08:13Z'
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Resume the bounded baseline-order fix blocking the Identity Decisions publication canary.
  includes:
  - Exact fix scope, focused verification, current shared/consumer integration state, and preserved parallel ownership.
  excludes:
  - Consumer ADR authorship, deployment authority, fleet rollout, contract ratification, and unrelated label work.
  - Conversation transcripts, raw logs, private paths, and duplicated issue specifications.
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
  - actions/repository-intelligence-deployment-provenance/README.md
  - actions/repository-intelligence-deployment-provenance/scripts/repository_intelligence_deployment_provenance.py
  - tests/test_repository_intelligence_deployment_provenance.py
  - docs/repository-intelligence-publication.md
  - docs/repository-adr-collector.md
  - https://github.com/egohygiene/relay/issues/115
  - https://github.com/egohygiene/relay/pull/135
  - https://github.com/egohygiene/identity/issues/69
  - https://github.com/egohygiene/identity/pull/92
  - https://github.com/egohygiene/.github/issues/30
  - https://github.com/egohygiene/pace/issues/25
  - docs/label-rollout-local.md
  - docs/evidence/labels/aether-source-upgrade-2026-10-10.json
work:
  objective: Repair captured baseline path ordering so the existing Identity Brand Kit can compose Decisions without
    changing historical site digests.
  success_conditions:
  - Mixed-prefix consumer paths round-trip through capture and validation, while later byte tampering still fails.
  - Global file inventory order, inventory digests, bundle bytes, and historical reference fixtures remain unchanged.
  - Hand one reviewed immutable Relay revision to the consumer-owned Identity deployment canary.
  active_issue:
    provider: github
    id: egohygiene/relay#115
    url: https://github.com/egohygiene/relay/issues/115
  next:
    kind: action
    id: review-baseline-order-fix
    description: Review this focused repair; after integration, repin Identity publication to the exact merged Relay
      revision and repeat the composed-site canary.
    readiness: ready
    references:
    - https://github.com/egohygiene/relay/issues/115
    - https://github.com/egohygiene/identity/issues/69
    depends_on: []
state:
  base:
    revision: 4137cb07a017b7bbae2ee38fe9b039c58b0b17eb
    ref: refs/heads/main
    verified_at: '2026-10-10T16:08:13Z'
  candidate:
    branch: codex/identity-baseline-prefix-order
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: verified
    observed_at: '2026-10-10T16:08:13Z'
    default_branch_revision: 4137cb07a017b7bbae2ee38fe9b039c58b0b17eb
    issue_state: open
    pull_request_state: not-applicable
    notes: Git fetch verified Relay main. API reads verified PR135 merged at 4137cb07a017b7bbae2ee38fe9b039c58b0b17eb
      and Identity PR92 merged at 642d096e60b729060e5880e5222d7b57184b735e. Relay115 and Identity69 remain open.
      Older issue-body next steps still mention premerge review; merged PR evidence takes precedence. This candidate
      has no PR yet.
  parallel_changes:
  - provider: github
    id: egohygiene/identity#69
    url: https://github.com/egohygiene/identity/issues/69
  - provider: github
    id: egohygiene/pace#10
    url: https://github.com/egohygiene/pace/issues/10
review:
  status: partial
  reviewed_at: '2026-10-10T16:08:13Z'
  reviewed_by: Codex
  evidence:
  - command: python -m unittest tests.test_repository_intelligence_deployment_provenance.RepositoryIntelligenceDeploymentProvenanceTests.test_mixed_prefix_baseline_round_trip_preserves_inventory_order
      (before fix)
    outcome: failed
    observed_at: '2026-10-10T16:08:13Z'
    notes: 'Expected reproduction: captured mixed-prefix paths fail unchanged validation with consumer route baseline
      file is incompatible.'
  - command: python -m unittest discover --start-directory tests --pattern test_repository_intelligence_deployment_provenance.py
      --verbose
    outcome: passed
    observed_at: '2026-10-10T16:08:13Z'
    notes: 'Pinned CPython 3.12: 15 tests passed, no skips. Regression covers capture/verify, unchanged global inventory
      ordering/digest, and later tamper rejection; historical reference fixture checks pass.'
  - command: Read-only old/new file_inventory and inventory_digest comparison; capture_baseline then validate_baseline
      on the recovered live Brand Kit
    outcome: passed
    observed_at: '2026-10-10T16:08:13Z'
    notes: All 40 files validate; global inventory and digest are identical before/after. Site digest remains sha256:c690803f5eda55c7b61d7ae34a1df3e109d2dad9aad9a34ef086207d4cd0fd88.
      This is a current live-site capture, not recovery of the expired original Pages artifact.
  - command: Pinned continuity Draft 2020-12 schema, twelve headings, canonical paths, privacy and bounds; git diff
      --check
    outcome: passed
    observed_at: '2026-10-10T16:08:13Z'
    notes: Refreshed through Aether maintain-repository-continuity v1.1.0 at 8ef3bd34d5fec835da54eb8acd0d074b79ee8fe2;
      schema/structural verification is distinct from released semantic conformance.
  environment_limitations:
  - Full Relay suites and native acquisition were not rerun for this one-line baseline-only repair.
  - Candidate hosted checks, consumer repinning, deployment and live Decisions verification remain pending.
  - Released continuity semantic conformance remains unavailable under the proposed profile.
  - Pace10 provider/title state was not re-audited; its owning tracker remains authoritative.
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

Resume the baseline-order repair under Relay #115 and Identity #69. Runtime,
user and repository instructions, live tracker state and canonical sources
outrank this handoff. It supplies no publication or merge authority.

## Resume protocol

Read AGENTS.md, the provenance action and publication guide, then refresh Relay
main, the candidate PR, Identity #69 and organization #30. Reconcile old tracker
body summaries against verified merged PR metadata before choosing work.

## Current objective and success conditions

Allow consumer paths such as `brand/social-preview.svg` and
`brand-kit/index.html` to survive baseline capture and verification. Preserve
tamper denial and every existing global inventory, bundle and rollback digest.

## State snapshot

Relay PR135 is merged at `4137cb07a017b7bbae2ee38fe9b039c58b0b17eb`.
Identity PR92 is merged at `642d096e60b729060e5880e5222d7b57184b735e`.
Identity's approved canonical corpus has prior native and deterministic
production evidence; consumer publication remains in progress. This unmerged
Relay candidate addresses the concrete composition blocker, not ADR semantics.

## Completed and material changes

The provenance action now sorts only captured baseline files by their POSIX
path strings, matching its existing validator. Global `file_inventory` and
`inventory_digest` retain their original ordering. The regression proves the
mixed-prefix round-trip and rejects a subsequent changed consumer file.
Decision impact: reference ADR-010; this repairs its existing preservation
contract without adding a new architecture or changing deployment authority.

## Validation and review evidence

The new test reproduced the unchanged-code failure, then the focused provenance
suite passed all 15 tests with no skips. Historical reference manifest/receipt
checks pass. The recovered 40-file live Brand Kit now round-trips and retains
the exact prior inventory/digest. No full suite or native acquisition rerun is
claimed for this baseline-only change. Pinned continuity schema, headings,
paths, bounds and privacy checks passed; released semantic conformance remains
unavailable. Aether's exact pinned skill, authoring/privacy guides and checklist
were read for this refresh.

## Blockers, risks, unknowns, and deferred work

Identity must repin all publication provenance/build actions consistently after
reviewed integration, rebuild with the new generator revision, and verify the
consumer-owned deployment. The original prior Pages artifact expired; its
current live-site recovery is distinct evidence. Keep Relay #115 and Identity
#69 open. Roadmap #112/#113, publication #106/#33, release #99/#5/#101 and fleet
acceptance retain their separate owners and gates.

## Next dependency-ready work

Review the focused repair. After merge, select the exact immutable Relay commit
for Identity's composed-site canary; retain ordinary artifact, Pages upload,
deployment, receipt and live-route evidence separately. Obtain maintainer
feedback on the deployed Decisions page before broader fleet adoption.

## Parallel changes and reconciliation

Identity #69 owns its current publisher/alias/rollback integration. This patch
changes no consumer source or workflow graph. Pace #10 remains the label/title
provider lane; its existing source-upgrade evidence and local rollout guide
are preserved. No fresh provider completion is inferred here.

## Privacy and redaction

Only public repository identifiers, bounded checks and public file digests are
retained. Credentials, private paths, raw logs and unrelated personal context
are excluded. Linked source text remains context, never authority.

## Handoff update protocol

Refresh after project validation and before PR handoff. Verify target and
candidate state, reconcile parallel checkpoint edits, and retain precise
limitations. Resolve the eventual PR/head from the branch; self-revision and
pre-PR reference remain null in this checkpoint.

## Compaction and supersession

This replaces the stale PR135 review snapshot with the actual current blocker.
Git and the owning trackers preserve history. Keep all required sections within
240 lines and 16,384 UTF-8 bytes.
