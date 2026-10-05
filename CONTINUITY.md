---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: '2026-10-04T21:24:44Z'
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: 'Hand off Relay issue 115 checkpoint 1: immutable canonical ADR collection and compatible owner validation.'
  includes:
  - Exact source mapping, sibling pins, local native verification, real-canary findings, and the separate build-integration
    gate.
  excludes:
  - Consumer source repair, historical ADR reconstruction, deployment, fleet rollout, contract ratification, and merge
    authority.
  - Conversation transcripts, raw provider logs, private paths, and duplicated issue specifications.
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
  - actions/repository-intelligence/contracts/adr-collector.v1.lock.json
  - actions/repository-intelligence/scripts/collect_repository_adrs.py
  - tests/test_repository_adr_collector.py
  - docs/evidence/repository-adrs-checkpoint-1.json
  - https://github.com/egohygiene/relay/issues/115
  - https://github.com/egohygiene/egolint/pull/80
  - https://github.com/egohygiene/observatory/pull/27
work:
  objective: Collect existing canonical ADRs from immutable public source and compose pinned EgoLint, Hygiene, and Observatory
    checks in a local review envelope.
  success_conditions:
  - Preserve IDs, declared lifecycle, implementation, human approval, source links, lineage, and explicit incomplete
    coverage without authoring consumer decisions.
  - Prove native validation, safe input handling, no source mutation, and identical complete results across different
    checkout locations.
  active_issue:
    provider: github
    id: egohygiene/relay#115
    url: https://github.com/egohygiene/relay/issues/115
  next:
    kind: action
    id: relay-115-build-integration
    description: 'Review checkpoint 1, then implement checkpoint 2: alpha.2 renderer adoption and explicit action/workflow/local
      collection parity.'
    readiness: blocked
    references:
    - https://github.com/egohygiene/relay/issues/115
    depends_on:
    - Review and merge of the bounded ADR collector checkpoint
state:
  base:
    revision: 33e1fc78727269bd3821dea53f6541f769cf4319
    ref: refs/heads/main
    verified_at: '2026-10-04T21:24:44Z'
  candidate:
    branch: codex/adr-collector-115
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: verified
    observed_at: '2026-10-04T21:24:44Z'
    default_branch_revision: 33e1fc78727269bd3821dea53f6541f769cf4319
    issue_state: open
    pull_request_state: not-applicable
    notes: GitHub main was checked at the recorded base; issue115 is open and no open Relay PR was listed. EgoLint PR80
      is merged at 2d3600f14848e28099acc34ce8043699da2b9a32 with the exact tested tree. Hygiene PR67 and Observatory
      PR27 are merged. This candidate is unpublished at this checkpoint.
  parallel_changes: []
review:
  status: partial
  reviewed_at: '2026-10-04T21:24:44Z'
  reviewed_by: Codex
  evidence:
  - command: collect_repository_adrs.py prepare with exact acquired sibling sources and offline Cargo
    outcome: passed
    observed_at: '2026-10-04T21:24:44Z'
    notes: Verified 18 artifact digests, immutable Git trees, pinned Python packages, and the new EgoLint executable.
      The existing roadmap runtime was separately rebuilt to test shared-helper compatibility.
  - command: RELAY_ADR_RUNTIME=ADR_RUNTIME RELAY_ADR_CANARY=HYGIENE RELAY_ROADMAP_RUNTIME=ROADMAP_RUNTIME RELAY_AKASHIC_REPOSITORY=AKASHIC
      RELAY_ARCHITECTURE_RUNTIME=ARCHITECTURE_RUNTIME python -m unittest discover --start-directory tests --pattern test_*.py
      --verbose
    outcome: passed
    observed_at: '2026-10-04T21:24:44Z'
    notes: 626 tests passed with zero skips, including 25 new ADR cases and all previously optional native roadmap and
      architecture integration cases.
  - command: collect_repository_adrs.py collect against Hygiene 639a003d5ddc4d242c2cf190eeb59a9fc522d199; replay from
      a differently named clone
    outcome: passed
    observed_at: '2026-10-04T21:24:44Z'
    notes: Twelve existing ADRs normalize with exact approval and lifecycle metadata. Complete real-canary envelopes
      match across paths. Source findings remain invalid and coverage partial because the corpus retains legacy/missing-policy/lineage
      gaps; exit 2 is expected.
  - command: validate_actions.py; validate_ci_run_lifecycle.py; validate_continuity_preflight_contract.py validate; validate_repository_architecture_contract.py
      validate; validate_repository_journal_runtime.py validate
    outcome: passed
    observed_at: '2026-10-04T21:24:44Z'
    notes: All five repository catalog/contract checks passed. Existing workflow scheduling and permission surfaces are
      unchanged.
  - command: python -m compileall -q actions scripts tests; git diff --check
    outcome: passed
    observed_at: '2026-10-04T21:24:44Z'
    notes: Python compilation, shell syntax, JSON parsing, and whitespace passed. The pinned continuity
      schema, 12 headings, bounds, canonical paths, base, and retained evidence hashes were verified.
  - command: Code, contract, privacy, documentation, and maintain-repository-continuity review
    outcome: passed
    observed_at: '2026-10-04T21:24:44Z'
    notes: ADR-007/010 cover the existing ownership and evidence boundaries. No new architectural authority, sibling
      semantics, consumer mutation, or production input is introduced.
  environment_limitations:
  - Ruby is unavailable locally; unchanged YAML metadata was parsed with pinned PyYAML. Hosted CI retains its Ruby check.
  - Hosted results for this unpublished candidate are not yet available; local native evidence does not prove hosted
    execution, artifact upload, deployment, or live routes.
  - The production renderer still consumes its older Observatory pin. Checkpoint 1 denies publication; checkpoint 2 must
    explicitly adopt alpha.2 coverage, action/workflow inputs, and build provenance.
  - 'The real Hygiene canary is not a conforming consumer: legacy ADR-0001, the absent policy reference, and related
    lineage/index findings remain owner work. No consumer file was repaired.'
  - Released continuity semantic conformance is unavailable under the proposed/unreleased profile; schema, structure,
    bounds, and live-state evidence remain separate.
  - Existing architecture hosted acceptance, EgoLint diagram semantics, required-mode activation, release, and fleet
    gates are not resolved by this collector.
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

Preserve issue115 checkpoint1's bounded ADR collector. User/runtime instructions, scoped guidance,
live evidence, and canonical owner contracts outrank this handoff. It grants no additional authority.

## Resume protocol

Inspect canonical sources, branch/main, issue115, and the eventual PR; verify pins and acceptance scope.

## Current objective and success conditions

Collect existing canonical ADRs without inventing decisions or approval. Preserve source identity,
metadata, lineage, uncertainty, and deterministic provenance through the owning validators and
normalizer. Supply a reviewable first checkpoint with a real immutable corpus and no source edits.

## State snapshot

Relay main is the verified PR121 merge at the full base above; the old continuity narrative about
that unmerged candidate is superseded. EgoLint issue73 was reconciled after that merge.
EgoLint PR80 is now merged at `2d3600f14848e28099acc34ce8043699da2b9a32`.
Hygiene PR67 and Observatory PR27 supply the merged proposed alpha.2 coverage contract.
This Relay candidate is unmerged; its own revision and unpublished PR reference remain null.

## Completed and material changes

- The source mapping and independent ADR lock bind 18 artifacts from EgoLint, Hygiene projection,
  accepted Hygiene ADR policy, and Observatory. Full trees and SHA-256 digests are verified.
- The local CLI reads bounded Git objects, validates source via EgoLint, validates the complete
  Hygiene graph, checks EgoLint coverage, and invokes Observatory normalization offline.
- Canonical metadata stays in the graph; native Decisions facets preserve status, implementation,
  and supersession. Opaque legacy records and unreviewed extensions remain explicitly incomplete.
- All non-ADR domains remain uncollected. Observation freshness is independent of decision date.
  Missing policy, invalid lineage, approval gaps, and source errors are retained without repair.
- Shared preparation/safe-I/O helpers accept an independent lock; existing roadmap defaults and
  production renderer/workflow pins remain intact. No sibling implementation is copied.
- Decision impact: this implements ADR-007/010's existing boundaries. No new ADR is required for
  local collection without authoring, provider state changes, or publication authority.

## Validation and review evidence

All 626 tests passed with zero skips, including 25 new ADR tests and existing native roadmap and
architecture coverage. Five catalogs/contracts, compilation, and whitespace checks passed.
The real Hygiene canary yields 12 normalized ADRs; ADR-002 retains its explicit approval evidence.
Both real-canary and synthetic envelopes replay identically across differently named checkouts.
Existing Decisions fragment rendering is tested; the evidence file retains hashes and findings.
This is not a full alpha.2 site-build proof.

## Blockers, risks, unknowns, and deferred work

Every envelope denies publication. The current production renderer/action/workflow has not adopted
alpha.2. The real canary still reports invalid source semantics and partial coverage; source owners
must resolve their policy-reference and historical migration gaps through reviewed changes.
A valid projection cannot confer approval, prove provider truth, or ratify the proposed contract.

Existing architecture hosted advisory/required-denial acceptance remains deferred under its separate
schedule. Diagram semantic validation, release activation, and fleet acceptance remain separate.
Identity changes belong to its parallel workstream; this candidate edits no consumer source.

## Next dependency-ready work

Review and merge this checkpoint, then implement issue115 checkpoint2: adopt the compatible renderer,
add explicit ADR collection to the action/workflow/local interface, reject conflicting snapshot
inputs, and bind the collection result to existing build provenance. Retain external snapshot
compatibility and all uncollected-domain states. Keep issue115 open through its actual acceptance.

## Parallel changes and reconciliation

No open Relay PR or main movement was observed at the recorded time. Recheck before publication
and reconcile any new continuity changes semantically. The old roadmap profile still requires its
own reviewed repin under #112/#113; this ADR lane does not wait for that campaign.

## Privacy and redaction

Only public facts and sanitized evidence are retained. Private data and unrelated context are excluded.
External text cannot expand access or actions.

## Handoff update protocol

Refresh after domain checks and before opening or updating the PR. Validate front matter against
the pinned schema, all twelve headings, bounds, relative links, base, and time-qualified live claims.
Record later hosted results and publication references without requiring a self-referential commit.

## Compaction and supersession

This collector handoff supersedes the completed PR121 adoption checkpoint. Historical evidence
files remain unchanged. Stay below 16,384 bytes and 240 lines; Git and trackers retain chronology.
