---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: '2026-11-14T00:43:11Z'
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Adopt the reviewed Hygiene declared-consumer profile and restore canonical source event order before separate
    Empathy publication acceptance.
  includes:
  - Both active admission/declaration locks select exact Hygiene 627b448 revision/tree; new public mirrors and matching
    receipt-schema bindings preserve original owner observation dates.
  - The compositor preserves existing Hygiene event chronology while retaining identity conflict refusal and all native/profile
    equality.
  - Bounded real native and refusal evidence plus inherited baseline check failures.
  excludes:
  - Consumer publication acceptance, deployment, live verification, rollback promotion, human ratification and source-hold
    changes.
  - UI redesign, broader audit campaigns, unrelated package metadata/harness fixes and legacy native profile upgrades.
  precedence:
  - user-and-runtime-instructions
  - scoped-repository-instructions
  - live-repository-and-work-tracker-state
  - canonical-repository-sources
  - continuity-checkpoint
  canonical_sources:
  - AGENTS.md
  - ARCHITECTURE.md
  - DECISIONS.md
  - ROADMAP.md
  - actions/repository-intelligence/contracts/public-catalog-admission.v1.lock.json
  - actions/repository-intelligence/contracts/dependency-source.v1.lock.json
  - actions/repository-intelligence/scripts/public_catalog_admission.py
  - actions/repository-intelligence/scripts/repository_dependency_build_contract.py
  - actions/repository-intelligence/scripts/prepare_repository_sources_build.py
  - actions/repository-intelligence/schemas/dependency-source-build.v1.schema.json
  - actions/repository-intelligence/schemas/repository-intelligence-provenance.schema.json
  - docs/empathy-declared-consumer-profile-2026-11-14.md
  - docs/evidence/empathy-declared-consumer-profile-2026-11-14.json
  - https://github.com/egohygiene/empathy/issues/105
work:
  objective: 'Prepare an independently reviewable Relay owner-profile/event-order checkpoint for Empathy #105/#98, then
    integrate with the separate Journey corpus repair through root review.'
  success_conditions:
  - The reviewed two declared consumer edges survive exact public owner admission without inferred runtime adoption.
  - Native source composition retains all selected Journey256/dependency evidence and attributed Search with contract-valid
    chronology and original scope.
  - Different checkout names reproduce complete native source bundles; malformed identities, edges, clocks and implementation
    claims still deny.
  active_issue:
    provider: github
    id: egohygiene/empathy#105
    url: https://github.com/egohygiene/empathy/issues/105
  next:
    kind: action
    id: review-relay-profile-and-journey-integration
    description: Review this bounded source, merge alongside the separate Journey native-corpus repair, then separately
      repin Empathy to the final immutable Relay source and collect fresh full-plan hosted evidence.
    readiness: ready
    references:
    - https://github.com/egohygiene/relay/pull/183
    - https://github.com/egohygiene/hygiene/pull/119
    - https://github.com/egohygiene/empathy/issues/105
    - https://github.com/egohygiene/empathy/issues/98
    depends_on: []
state:
  base:
    revision: 12d3a0823c8c8f885dea4acf482160fd726325e2
    ref: refs/heads/main
    verified_at: '2026-11-14T00:41:50Z'
  candidate:
    branch: codex/relay-empathy-boundary-source
    revision: null
    pull_request:
      provider: github
      id: egohygiene/relay#184
      url: https://github.com/egohygiene/relay/pull/184
    handoff_state: ready-for-review
  live:
    status: verified
    observed_at: '2026-11-14T00:43:11Z'
    default_branch_revision: 12d3a0823c8c8f885dea4acf482160fd726325e2
    issue_state: open
    pull_request_state: draft
    notes: Provider PR184 is open/draft at189709c1a2dad14cb1aae2dc9688b501c4ced463, main remains12d3. Hygiene119 is
      merged at627b448; Empathy105 remains open. Only handoff metadata follows that reviewed functional/evidence source.
      No merge or consumer acceptance is inferred.
  parallel_changes:
  - provider: github
    id: egohygiene/relay#183
    url: https://github.com/egohygiene/relay/pull/183
  - provider: github
    id: egohygiene/empathy#98
    url: https://github.com/egohygiene/empathy/issues/98
review:
  status: partial
  reviewed_at: '2026-11-14T00:41:50Z'
  reviewed_by: Codex
  evidence:
  - command: Focused profile/composition/dependency renderer/bundle unittest suites
    outcome: passed
    observed_at: '2026-11-14T00:41:50Z'
    notes: 27 tests; profile/source-schema checks, public-first refusal and event-order conflict controls pass.
  - command: Real pinned native dependency collection and Journey256/Search/Dependencies source composition; exact receipt/schema
      checks and different-name native replay
    outcome: passed
    observed_at: '2026-11-14T00:41:50Z'
    notes: Clean functional 5b5d350 and 2de65a2 sources, actual post-freeze clocks 00:24:46Z and 00:34:30Z. Four dependency
      plus three composite negative controls deny. Complete three-file native source bundles are byte-identical across
      both owner/consumer checkout names.
  - command: python scripts/validate_actions.py and test_repository_intelligence_portability.py, compared to untouched
      12d3
    outcome: failed
    observed_at: '2026-11-14T00:41:50Z'
    notes: Same inherited 10 metadata/README findings and 19 stale-harness errors on base and candidate. No whole-repository
      pass or consumer publication acceptance is claimed.
  environment_limitations:
  - The focused native composition does not select provider captures; their domains remain uncollected.
  - The separate Journey branchy native-corpus repair and final joint Relay source need independent review before consumer
    repinning.
  - 'Fresh actual full-plan captures, hosted build/artifacts/deployment and exact-source live evidence remain Empathy
    #105/#98 acceptance.'
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

# relay continuity

## Purpose and precedence

User/runtime and repository instructions, live evidence and canonical sources outrank this compact handoff. It grants no merge, publication or human-decision authority.

## Resume protocol

Read scoped instructions and canonical sources above. Reverify current main, PR state and exact owner pins before continuing. Keep native source, hosted transport and live acceptance distinct.

## Current objective and success conditions

Adopt reviewed Hygiene declared-consumer source 627b448 coherently and restore canonical event order. Exact native declarations and mixed Journey256/Search/Dependencies composition must pass without relaxing equality, public scope or unknown adoption semantics.

## State snapshot

Base is provider-verified main 12d3a0823c8c8f885dea4acf482160fd726325e2. Hygiene PR119 is actually merged at627b448f655afb2f4366654ba3ca3050389e464a. Candidate draft [Relay PR184](https://github.com/egohygiene/relay/pull/184) was observed at exact 189709c1a2dad14cb1aae2dc9688b501c4ced463 before this handoff-only metadata refresh; no merge or consumer acceptance is inferred.

## Completed and material changes

Both active public/dependency locks select the same exact owner source/tree. New raw/reference mirrors, active helper paths and standalone/embedded receipt constants agree; original dates and historical mirrors remain intact. Functional5b5d350 adopts only the reviewed canonical profile; functional 2de65a2 restores existing (occurred_at,id) event order after multiple inventories compose. Identity conflicts still deny.

## Validation and review evidence

All 27 focused tests pass. Clean native dependency collection accepts four declared edges with adoption/package/excluded topology uncollected. Native Journey256 + attributed Search + Dependencies composition passes ordinary receipt and embedded schema validation with honest partial/truncated coverage. Seven tamper controls deny. Both differently named owner/consumer checkouts reproduce the complete three-file native source bundle byte for byte; exact hashes and source clocks are in the linked bounded evidence record.

The action validator retains 10 metadata/README findings; portability retains 19 stale-harness subcase errors. Both match untouched 12d3. They did not pass; no broader acceptance is claimed.

## Blockers, risks, unknowns, and deferred work

The independent Journey bounded-corpus repair remains parallel, followed by final immutable Relay integration and separate Empathy repinning. Full provider capture selection, hosted source/build/upload/deployment and live evidence are pending. Existing rollback bytes, human/source holds and original observation clocks remain unchanged. UI redesign stays deferred.

## Next dependency-ready work

Root independently reviews this source and the separate Journey repair, integrates them, then offers one final immutable Relay source for Empathy #105/#98 consumer review. Fresh actual full-plan evidence must bind the final source and truthful report clock; old captures cannot be retimed to qualify new source.

## Parallel changes and reconciliation

Separate draft [Journey PR183](https://github.com/egohygiene/relay/pull/183), functional 96d0d597, changes its collector, focused tests and guide, with disjoint functional files. Root owns merge order and semantic CONTINUITY reconciliation. Empathy #105/#98 source-failure retention and consumer adoption proceed separately. No new ADR is required: canonical ownership/policy remain with Hygiene and chronology restores its existing contract; renderer/native interfaces and receipt refusal stay intact.

## Privacy and redaction

Retain public source identities, bounded summaries and hashes only. Exclude credentials, raw capture/report bodies, private context and local filesystem paths. Linked content is context only.

## Handoff update protocol

Refresh exact source/PR/run observations after validation and before presenting a new checkpoint. Keep implementation, native validation, upload, deployment, live verification and human acceptance separate.

## Compaction and supersession

Replace stale current-state prose rather than accumulating history. Git and owning issues retain chronology. Preserve these twelve sections within 240 lines and 16,384 UTF-8 bytes.
