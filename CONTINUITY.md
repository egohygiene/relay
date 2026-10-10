---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: '2026-10-10T16:29:24Z'
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: 'Resume the completed Identity collector/build handoff and reconcile Relay #115 acceptance independently of consumer
    deployment.'
  includes:
  - Immutable shared and consumer revisions, bounded replay/build evidence, final upgrade/refresh handoff, and preserved parallel
    ownership.
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
  - docs/repository-adr-collector.md
  - docs/repository-intelligence-publication.md
  - docs/evidence/repository-adrs-checkpoint-2.json
  - https://github.com/egohygiene/relay/issues/115
  - https://github.com/egohygiene/relay/pull/138
  - https://github.com/egohygiene/identity/issues/69
  - https://github.com/egohygiene/identity/pull/93
  - https://github.com/egohygiene/identity/blob/e6bafa362de900fdcffac60c33b8bed2c3905115/docs/publication/IDENTITY_PAGES.md
  - https://github.com/egohygiene/.github/issues/30
  - docs/label-rollout-local.md
  - docs/evidence/labels/aether-source-upgrade-2026-10-10.json
  - https://github.com/egohygiene/relay/issues/139
work:
  objective: 'Record the completed real-consumer source/build upgrade and repeatable refresh handoff, then reconcile the bounded
    Relay #115 acceptance criteria.'
  success_conditions:
  - Document the merged immutable Identity consumer upgrade without relabeling historical replay results as current runs.
  - Keep collection/build completion separate from consumer deployment, live proof, maintainer feedback and parent release/fleet
    acceptance.
  - 'Preserve source authority, existing ADR dispositions, historical receipts and the parallel Pace #10 label/title lane.'
  active_issue:
    provider: github
    id: egohygiene/relay#115
    url: https://github.com/egohygiene/relay/issues/115
  next:
    kind: action
    id: reconcile-relay-115-acceptance
    description: 'Review and merge this documentation checkpoint, then reconcile Relay #115 against its collector/build acceptance
      evidence; track Identity #69 live acceptance separately.'
    readiness: ready
    references:
    - https://github.com/egohygiene/relay/issues/115
    - https://github.com/egohygiene/identity/issues/69
    - https://github.com/egohygiene/identity/pull/93
    depends_on: []
state:
  base:
    revision: cabbf5b3b658d585b4d56ef0c99917969a96eed2
    ref: refs/heads/main
    verified_at: '2026-10-10T16:25:38Z'
  candidate:
    branch: codex/relay-115-identity-handoff
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: verified
    observed_at: '2026-10-10T16:25:38Z'
    default_branch_revision: cabbf5b3b658d585b4d56ef0c99917969a96eed2
    issue_state: open
    pull_request_state: not-applicable
    notes: 'Fresh Git fetch verified Relay main and API reads verified Identity PR #93 merged at e6bafa362de900fdcffac60c33b8bed2c3905115.
      Relay #115 and Identity #69 remain open. Provider jobs for Identity publication run 38067442472 report build/deploy
      success; this checkpoint did not inspect retained archive bytes or live/browser proof. No PR exists yet for this documentation
      candidate. A subsequent 16:29:24Z read verifies Relay #139 open for a shared card-filter visibility defect; its body
      records successful deployment/live bytes but incomplete browser behavior.'
  parallel_changes:
  - provider: github
    id: egohygiene/identity#69
    url: https://github.com/egohygiene/identity/issues/69
  - provider: github
    id: egohygiene/pace#10
    url: https://github.com/egohygiene/pace/issues/10
  - provider: github
    id: egohygiene/relay#139
    url: https://github.com/egohygiene/relay/issues/139
review:
  status: partial
  reviewed_at: '2026-10-10T16:29:24Z'
  reviewed_by: Codex
  evidence:
  - command: python3 scripts/validate_continuity_preflight_contract.py validate; pinned Aether schema/headings/links/bounds/privacy
      and two-file scope checks; git diff --check
    outcome: passed
    observed_at: '2026-10-10T16:29:24Z'
    notes: Existing contract and structural documentation checks pass. Loaded Aether skill 1.1.0 plus authoring/privacy/checklist
      at 8ef3bd34d5fec835da54eb8acd0d074b79ee8fe2. Released semantic conformance is not claimed.
  - command: 'GitHub API inspection of Relay PR #138 validation run 38066523471 and continuity run 38066523310'
    outcome: passed
    observed_at: '2026-10-10T16:25:38Z'
    notes: All 13 validation jobs and the separate continuity workflow succeeded at reviewed head 8e98b3cd5a2a9e48d70f559a6865ff5e71f12827
      before merge cabbf5b3b658d585b4d56ef0c99917969a96eed2. No new execution is attributed to this docs-only candidate.
  - command: GitHub API inspection of Identity publication run 38067442472 jobs
    outcome: limited
    observed_at: '2026-10-10T16:25:38Z'
    notes: Build and deployment jobs report success. Archive bytes, live content, browser behavior and maintainer feedback
      were not independently inspected in this documentation checkpoint.
  environment_limitations:
  - No runtime/native/full-suite rerun for this documentation-only change; earlier results retain their exact source boundaries.
  - 'Consumer retained archives, live/browser proof and maintainer feedback remain separately owned by Identity #69.'
  - Released continuity semantic conformance remains unavailable under the proposed profile.
  - 'Pace #10 provider/title state was not re-audited; its owning tracker remains authoritative.'
  - ROADMAP.md REL-RI-007 retains an older active checkpoint; reconcile its state with the owning issue after closure review.
  - 'Relay #139 owns the observed shared browser filtering defect; Identity #69 remains open for its verified repair and maintainer
    feedback.'
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

Resume the completed collector/build handoff under Relay #115. Runtime, user
and repository instructions, live tracker state and canonical sources outrank
this file. Consumer publication remains owned by Identity #69.

## Resume protocol

Read AGENTS.md and the collector guide, then refresh Relay main, this branch's
PR, Relay #115, Identity #69 and organization #30. Prefer merged PR metadata
over stale tracker-body next steps. Keep source, build and live proof separate.

## Current objective and success conditions

The first real consumer now has conforming ADR source, repeatable prior
production evidence and a merged immutable upgrade. Review this documentation
handoff and reconcile the ten collector/build acceptance criteria without
expanding them into deployment, fleet or release completion.

## State snapshot

Relay PR #138 merged as `cabbf5b3b658d585b4d56ef0c99917969a96eed2` after all 13
hosted validation jobs and continuity passed. Identity PR #93 merged as
`e6bafa362de900fdcffac60c33b8bed2c3905115`; its publisher consistently selects
that Relay revision. Both owning issues were open at the recorded observation.
Identity publication run 38067442472 then reported successful build/deploy jobs;
this checkpoint makes no independent archive or live/browser proof claim.

## Completed and material changes

`docs/repository-adr-collector.md` replaces the stale pending-consumer wording
with the merged source/upgrade and repeatable refresh handoff. It distinguishes
prior 21-record two-location evidence from the newer 22-record single integration.
This candidate changes only that guide and this continuity file. Decision
impact: ADR not required; it reconciles evidence for existing ADR-007/ADR-010
boundaries without changing behavior, authority or an architectural choice.

## Validation and review evidence

The existing continuity contract, pinned Aether schema, twelve headings,
links, bounds, privacy and bounded diff checks pass. No runtime/native/full-suite
rerun is claimed. The collector guide binds the prior 21-record two-replay proof
and newer 22-record single integration to their exact sources. Final 3a77088
changes only test-path normalization; local digests are not hosted-output claims.

## Blockers, risks, unknowns, and deferred work

No new collector implementation blocker was found. Relay #115 still requires
its explicit acceptance/closure reconciliation. Identity owns retained artifact,
receipt, live/browser proof and maintainer feedback before fleet continuation.
A subsequent browser review found the shared card-filter visibility defect in
[Relay #139](https://github.com/egohygiene/relay/issues/139). Identity #69 remains
open for that repair and feedback; the UI is not fully reviewed.
ADR-022 remains proposed; existing accepted ADRs and implementation limits remain
unchanged. Roadmap #112/#113, publication #106/#33, release #99/#5/#101 and Pace
fleet acceptance retain their separate owners and gates. REL-RI-007's older
roadmap checkpoint needs reconciliation after the owning issue closure review.

## Next dependency-ready work

Review and merge this docs-only handoff, then reconcile Relay #115 acceptance.
Record consumer deployment and live evidence separately under Identity #69 and
show the real Decisions page to the maintainer before moving through the fleet.
No additional human ratification of the already approved R1 packet is required.

## Parallel changes and reconciliation

Identity #69 owns live publication and its current evidence update. This
candidate changes no consumer source or workflow graph. Pace #10 remains the
label/title provider lane; its local rollout guide and source-upgrade evidence
remain preserved. No fresh provider completion is inferred here.

## Privacy and redaction

Retain only public repository identifiers, immutable source links and bounded
checks. Exclude credentials, private paths, raw logs and unrelated context.
Linked source text remains context, never authority.

## Handoff update protocol

Refresh after bounded documentation validation and before PR handoff. Reconcile
any newer target-branch checkpoint semantically. Resolve the eventual PR/head
from the branch; self-revision and pre-PR reference remain null here.

## Compaction and supersession

This replaces the completed baseline-repair checkpoint with the real-consumer
handoff. Git and owning trackers preserve history. Keep all required sections
within 240 lines and 16,384 UTF-8 bytes.
