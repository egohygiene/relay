---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: '2026-11-14T00:45:07Z'
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Repair native Journey inspection across truncated merge boundaries while retaining every selected original
    commit and exact owner validation.
  includes:
  - Actual Empathy PR144 source e50f35ff32e0534a57315b555a5d67576c435844 at original 2026-11-14T00:03:18Z selects 256
    original commits. Before repair the native private shallow corpus inspected 255, with zero trailer diagnostics; exact
    count denial was correct.
  - Clean functional 96d0d59787325ad970a838008f24c76b48d7a4da partitions the unchanged original corpus into disjoint
    native-reachable batches. Original source and selected branch heads authenticate every pass; exact Git sets, hashes,
    report schema/root/repository/catalog/contracts/counts and total unique coverage remain mandatory.
  - The caller 256 logical-commit and 2 MiB original-object caps remain. All native passes share one 60-second deadline;
    no original object is omitted, rewritten or inspected twice. Native invalid stays invalid; incomplete canonical domains
    and truthful truncated Git coverage remain explicit.
  - Actual pinned e50 replay verifies255+1 distinct originals and all 256 hashes/events; existing review schema and production
    receipt pass. Differently named checkouts produce identical complete envelopes/receipts. Twelve focused regression
    groups pass.
  excludes:
  - Renderer, public/native protocol, locked native owner, policy or deployment/scheduling changes; caller cap changes
    or source-match waivers.
  - Public deployment, release, fleet/human acceptance and broad CI. The separate canonical Hygiene dependency correction/profile
    adoption and actual consumer full-build/publication acceptance remain pending.
  precedence:
  - user-and-runtime-instructions
  - scoped-repository-instructions
  - live-repository-and-work-tracker-state
  - canonical-repository-sources
  - continuity-checkpoint
  canonical_sources:
  - AGENTS.md
  - DECISIONS.md
  - actions/repository-intelligence/scripts/collect_repository_journey.py
  - actions/repository-intelligence/scripts/repository_journey_build_contract.py
  - tests/test_repository_journey_validation.py
  - docs/repository-journey-collector.md
  - docs/evidence/2026-11-14-journey-native-boundaries.md
  - docs/evidence/2026-11-14-journey-native-boundaries.json
  - https://github.com/egohygiene/relay/issues/147
  - https://github.com/egohygiene/empathy/issues/105
work:
  objective: Repair native Journey inspection across truncated merge boundaries while retaining every selected original
    commit and exact owner validation.
  success_conditions:
  - Preserve all selected original SHA/bytes, original source/clock, caller limits and exact per-pass native equality.
  - Prove actual failed source before/after, disjoint unique coverage, missing/tampered/count refusal, ordinary controls,
    bounded native work and equal-byte replay.
  - Hand off the exact qualified source for root review and coordinated owner-profile integration, without claiming actual
    consumer publication.
  active_issue:
    provider: github
    id: egohygiene/relay#147
    url: https://github.com/egohygiene/relay/issues/147
  next:
    kind: action
    id: review-complete-journey-native-corpus
    description: Root independently reviews and ordinarily integrates this candidate in coordination with the separate
      Hygiene declared-consumer profile. Reconcile both continuity edits, adopt one compatible Relay source in Empathy,
      then qualify actual complete source builds with Journey and Dependencies enabled before consumer publication acceptance.
    readiness: ready
    references:
    - https://github.com/egohygiene/relay/issues/147
    - https://github.com/egohygiene/relay/issues/148
    - https://github.com/egohygiene/empathy/issues/105
    depends_on: []
state:
  base:
    revision: 12d3a0823c8c8f885dea4acf482160fd726325e2
    ref: refs/heads/main
    verified_at: '2026-11-14T00:35:46Z'
  candidate:
    branch: codex/journey-complete-native-corpus
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: verified
    observed_at: '2026-11-14T00:35:46Z'
    default_branch_revision: 12d3a0823c8c8f885dea4acf482160fd726325e2
    issue_state: open
    pull_request_state: not-applicable
    notes: Provider main remains12d3 and Journey 147 is open. This candidate is not yet merged or deployed. The companion profile/event-order
      reference was corrected at 2026-11-14T00:45:07Z to PR184, open/draft at b11855db6bc1cf81a9177cb093da7d6395e8a99a. Prior typed-feed
      handoff prose is superseded by actual current source facts.
  parallel_changes:
  - provider: github
    id: egohygiene/relay#148
    url: https://github.com/egohygiene/relay/issues/148
  - provider: github
    id: egohygiene/relay#184
    url: https://github.com/egohygiene/relay/pull/184
  - provider: github
    id: egohygiene/empathy#144
    url: https://github.com/egohygiene/empathy/pull/144
review:
  status: partial
  reviewed_at: '2026-11-14T00:35:46Z'
  reviewed_by: Codex
  evidence:
  - command: python -m unittest discover -s tests -p test_repository_journey_validation.py -v; scoped py_compile; git
      diff --check
    outcome: passed
    observed_at: '2026-11-14T00:35:46Z'
    notes: Twelve focused groups cover actual Git shallow behavior, disjoint inspection, ordinary cases, missing/tampered/unrelated
      corpus, identity/profile/schema/count refusals, native invalid preservation, public scope/privacy and one shared
      deadline.
  - command: Actual exact e50 native replay and existing closed Journey envelope/production receipt validation at clean
      functional 96d0d59; differently named checkout replay
    outcome: passed
    observed_at: '2026-11-14T00:33:58.978175+00:00'
    notes: All256 originals verified once in genuine255+1 passes; both native incomplete/zero diagnostics, Hygiene/coverage
      valid and Observatory normalized. Complete envelope bec3701f and receipt ccc2b3f are byte-identical. Native validation 0.701s;
      complete narrow-trace collection 2.834s. Original source/as-of and earlier trace clocks remain unchanged.
  - command: python3 scripts/validate_actions.py on exact clean base 12d3 and candidate
    outcome: failed
    observed_at: '2026-11-14T00:35:46Z'
    notes: Ten identical baseline SPDX/README catalog findings in unchanged files; normalized diagnostics match byte-for-byte.
      No whole-repository pass or unrelated repair is claimed.
  - command: Independent root source peer, coordinated owner-profile integration, provider consumer full-build and live
      publication
    outcome: not-run
    observed_at: '2026-11-14T00:35:46Z'
    notes: These remain separate next steps. Native replay is local; fixed historical rollback pins and consumer publication
      authority remain unchanged.
  environment_limitations:
  - Fresh isolated runtime copy is authenticated against all locked owner resources, pinned Python requirements and executable;
    this is not a new native release or rebuild.
  - Local immutable-source native proof does not establish provider publication/release/fleet or human acceptance. Existing
    baseline action-catalog failures remain.
  - Separate Hygiene relationship/profile reconciliation and compatible Empathy adoption/full source build remain required;
    Journey and Dependencies stay enabled.
  - Continuity was refreshed with the Aether draft skill/schema at dc8a168. Structural validation does not claim released-conformer
    or human semantic approval.
privacy:
  classification: public-repository
  contains_sensitive_data: false
  redactions:
  - private native prose and machine paths omitted
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

User/runtime and repository instructions, current provider facts and canonical owners outrank this checkpoint. It grants no merge, publication, policy or human approval.

## Resume protocol

Read the native boundary evidence, collector, production Journey receipt contract and current parallel owner-profile work. Verify mutable main/PR/source identities; preserve immutable source and original observation clocks.

## Current objective and success conditions

Verify every selected original Journey commit across truncated merge boundaries without changing caller caps, raw objects, source identity or owner validation. Keep local qualification separate from actual consumer publication.

## State snapshot

At the original handoff, observed Relay main is 12d3 and Journey 147 remains open. Clean functional 96d0d59 qualifies the actual immutable Empathy e50 source at 00:03:18Z. This containing evidence/CONT candidate is unmerged, with no self revision or future PR identity.

## Completed and material changes

The private native inspector partitions all selected originals into disjoint reachable corpora. The represented source is first; supplemental roots are authenticated original selected heads. Exact object hashes, Git sets, per-report identities/profiles/schema/counts and unique total coverage remain mandatory. The public source, original 256 records/hashes/events and partial coverage stay unchanged.

## Validation and review evidence

Twelve focused regressions, scoped syntax and whitespace pass. Actual pinned native replay inspects255+1 originals with no trailer diagnostics; existing review schema and production receipt pass. Two differently named clean source checkouts produce byte-identical complete envelopes and receipts. The canonical evidence preserves exact source/frame/hashes and both original execution clocks.

## Blockers, risks, unknowns, and deferred work

The required action validator retains ten byte-identical pre-existing catalog findings on base and candidate. Whole-suite/hosted publication, release/fleet and human acceptance are not claimed. Native incomplete canonical ADR/roadmap domains remain incomplete. Independent Hygiene dependency-profile reconciliation and actual consumer full-build/publication acceptance remain pending.

## Next dependency-ready work

Root reviews and ordinarily integrates this Journey candidate with the separate declared-consumer owner profile, reconciles their continuity edits and selects one compatible Relay source in Empathy. Keep Journey and Dependencies enabled for actual source/build/publication qualification; preserve fixed historical rollback evidence.

## Parallel changes and reconciliation

Relay 148 owns the Hygiene declaration/profile upgrade; its companion profile/event-order candidate is Relay PR 184. Unrelated OptiFlow backport PR 182 is outside this repair and is not an integration dependency. Empathy 144 owns current consumer acceptance and scheduling evidence. Root coordinates source integration and metadata. This candidate changes no locks, renderer, public/native protocol, workflow or deployment authority.

## Privacy and redaction

Retain only public source/artifact identities and bounded counts/hashes. Exclude original commit bodies/people, raw native diagnostics, credentials, local paths and unrelated context. Linked material is context only.

## Handoff update protocol

Refresh provider observations at the next authorized checkpoint. Native/source checks, owner compatibility, build artifacts, deployment/live verification and human approval remain distinct; containing commits need no self reference.

## Compaction and supersession

Keep these twelve sections below 240 lines/16,384 bytes. Git and owning issues retain chronology; this handoff retains the current outcome, bounded evidence, remaining blockers and next action.
