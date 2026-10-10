---
schema: aether.architecture-document/v1
id: relay-roadmap
title: Relay Roadmap
kind: architecture-document
version: 0.2.1
status: provisional
owners:
  - egohygiene
created: 2026-08-19
updated: 2026-10-10
governed_by:
  - architecture-roadmap
depends_on:
  - relay-vision
  - relay-pillars
  - relay-architecture
  - relay-decisions
related:
  - relay-purpose
  - relay-principles
  - relay-manifesto
  - relay-epistemology
supersedes: []
---

# Relay Roadmap

<!-- BEGIN ROADMAP EXECUTION SNAPSHOT -->
<!-- roadmap-manifest
schema: hygiene.roadmap/v1alpha1
repository: egohygiene/relay
visibility: public
publication: central
route: /roadmap/relay/
updated: 2026-10-10
-->
## 2026-10-10 execution snapshot

> This snapshot refreshes the Repository Intelligence execution order and its verified upstream gates on 2026-10-10. Unrelated tracks retain their separately dated evidence; this is not a new audit of every roadmap item. The longer-horizon strategy below remains canonical context; generated HTML, JSON, progress, issue plans, and commit lists are projections.

**Lifecycle:** active released product  
**Current gate:** Review and integrate the canonical ADR Decisions build in [#115](https://github.com/egohygiene/relay/issues/115) / [PR #135](https://github.com/egohygiene/relay/pull/135), then prove the owner-reviewed Identity #69 canary under Pace #5 before the roadmap campaign. Publication acceptance in [#106](https://github.com/egohygiene/relay/issues/106) remains separate. The checkout-directory repair for [#109](https://github.com/egohygiene/relay/issues/109) is merged; its outstanding work is acceptance evidence and reviewed consumer adoption.
**North-star outcome:** Immutable, reusable CI building blocks that repositories can pin, verify, and upgrade safely.

### Visual roadmap publication

**Mode:** `central`  
**Route:** `/roadmap/relay/`  
**Recorded publication evidence (2026-09-25):** Versioned GitHub releases and reusable workflow distribution; v1.0 through v1.5 observed. Release inventory was not refreshed for this Intelligence checkpoint.

Publish the public-safe projection through egohygiene.io at /roadmap/relay/. This repository owns intent and acceptance evidence; it does not add a second site deployment.

### Quest line

The original `REL-Q01`–`REL-Q05` IDs remain stable for existing links. Their
roadmap-publication goals now overlap the delivered `/roadmap/` renderer and
the Repository Intelligence publication track below; they are not requests to
build a second generator. Original wider pilot criteria remain unverified and
must be explicitly reconciled before any legacy step is declared complete.

<!-- roadmap-step
id: REL-Q01
status: complete
depends_on: []
issues: []
-->
#### REL-Q01 — Ship the reusable workflow foundation

**State:** `complete`
**Depends on:** None

**Outcome:** Relay provides released and green reusable CI behavior.

**Exit criteria:**

- [x] Tagged releases are available.
- [x] Default-branch validation is green.

**Current evidence:**

- Published releases `v1.0.0` through `v1.5.0` were observed on 2026-09-25.
- Default-branch [validation run 35780510787](https://github.com/egohygiene/relay/actions/runs/35780510787)
  passed at `9a6315978766c336566b9fa7139b800fa8789ba5`. This is recorded provider
  evidence, not a new execution or proof of every consumer's current health.

<!-- roadmap-step
id: REL-Q02
status: active
depends_on: [REL-Q01]
issues: []
-->
#### REL-Q02 — Reconcile roadmap and release history

**State:** `active`
**Depends on:** `REL-Q01`

**Outcome:** The roadmap describes current capabilities, remaining gaps, and supported upgrade paths.

**Exit criteria:**

- [ ] Shipped capabilities and outstanding acceptance are reconciled from current evidence.
- [ ] Stale or duplicated future work is removed.

**Current evidence:**

- The 2026-10-10 reconciliation updates the ADR-first Intelligence sequence,
  closed upstream gates, and merged implementation evidence. Review/merge and
  tracker synchronization remain distinct from #106 publication acceptance and
  #101 final release acceptance; unrelated tracks have not been re-audited and
  this edit does not mark those outcomes complete.

<!-- roadmap-step
id: REL-Q03
status: ready
depends_on: [REL-Q02]
issues: []
-->
#### REL-Q03 — Define the roadmap build contract

**State:** `ready`
**Depends on:** `REL-Q02`

**Outcome:** A reusable workflow validates canonical roadmap data and emits a static quest-site artifact.

**Exit criteria:**

- [ ] Inputs, permissions, outputs, and failure modes are versioned.
- [ ] The workflow emits both machine-readable validation evidence and a static artifact.

**Current evidence:**

- The `/roadmap/` renderer (#31) and reusable Intelligence artifact workflow
  (#90/#91) are already merged. Their final publication acceptance belongs to
  #33/#106. Canonical roadmap semantics remain upstream-owned; reconcile this
  legacy step against those interfaces rather than authoring another workflow.

<!-- roadmap-step
id: REL-Q04
status: planned
depends_on: [REL-Q03]
issues: []
-->
#### REL-Q04 — Pilot the roadmap workflow

**State:** `planned`  
**Depends on:** `REL-Q03`

**Outcome:** Representative docs-only, application, and private repositories consume one pinned Relay workflow.

**Exit criteria:**

- [ ] At least three repository classes pass the workflow.
- [ ] Private repositories publish only explicitly allowed evidence.

**Current evidence:**

- Akashic #185 and Empathy #94 record accepted public consumer proofs at the
  hardened Relay pin; see REL-RI-006. The original three-class/private-pilot
  scope is not established by those two canaries and is not a new #106 gate.
  #101 and Pace #13 retain their own acceptance and rollout scopes.

<!-- roadmap-step
id: REL-Q05
status: planned
depends_on: [REL-Q04]
issues: []
-->
#### REL-Q05 — Release the roadmap automation

**State:** `planned`  
**Depends on:** `REL-Q04`

**Outcome:** A tagged Relay release makes roadmap validation and publication safely reusable.

**Exit criteria:**

- [ ] Consumers pin an immutable release reference.
- [ ] Upgrade and rollback instructions are tested.

**Current evidence:**

- On 2026-09-25, releases through `v1.5.0` were observed. The hardened consumer
  pin recorded at that checkpoint includes source-declared `v1.6.0` work, but
  no published `v1.6.0` release was observed then.
  #101 owns final Intelligence release acceptance; release dispatch and fleet
  pin changes are outside this documentation checkpoint.

### Publication Pages lifecycle track

<!-- roadmap-step
id: REL-PAGES-001
status: active
depends_on: [REL-Q01]
issues: [38]
-->
#### REL-PAGES-001 — Ship the reviewed publication Pages lifecycle

**State:** `active`
**Depends on:** `REL-Q01`

**Outcome:** Product repositories can keep their native Make/Task publication
builds while pinned, statically separated Relay review and deployment workflows
prove and publish the exact caller-built static bytes.

**Exit criteria:**

- [x] Local validation enforces the Beacon public catalog, lifecycle honesty,
  route/resource linkage, complete checksums, path safety, and bounded input.
- [x] Read-only review and write-scoped Pages deployment are separate reusable
  workflow surfaces; deployment consumes only the exact reviewed artifact.
- [x] Canonical and explicitly authorized fallback endpoints use bounded HTTPS
  verification with deterministic, versioned evidence.
- [ ] Match the published Relay v1.3.0 release to this track's accepted implementation evidence.
- [ ] Antidote and Reflector pin that release and pass real default-branch
  deployment plus rollback checks without losing native build independence.

**Current evidence:**

- Relay issue #38 owns the implementation and release/adoption acceptance.
- `v1.3.0` is published; this checkpoint does not re-audit #38's complete
  release-to-consumer evidence or change its remaining acceptance state.
- The v1.3 implementation PR references rather than closes #38; the issue stays
  open through immutable release publication and product migrations.
- Antidote and Reflector static-permission caller patterns are documented under
  `examples/workflows/`.

### Repository Intelligence experience track

This track turns the validated organization read model into a low-cognitive-load
repository story. It is additive to the release-automation quest line above and
follows the dependency order defined in Relay issue #27.

<!-- roadmap-step
id: REL-RI-001
status: complete
depends_on: []
issues: [27]
-->
#### REL-RI-001 — Establish the experience and contract boundaries

**State:** `complete`
**Depends on:** None

**Outcome:** Observatory owns normalized truth, Holon owns visual primitives,
and Relay owns route composition and static publication artifacts.

**Exit criteria:**

- [x] The complete route map and interaction principles are captured.
- [x] The Observatory read model and Holon component package are versioned.
- [x] Relay records the sibling boundary and immutable contract evidence.

<!-- roadmap-step
id: REL-RI-002
status: complete
depends_on: [REL-RI-001]
issues: [28]
-->
#### REL-RI-002 — Ship the shared shell and operational Now view

**State:** `complete`
**Depends on:** `REL-RI-001`

**Outcome:** `/now/` immediately shows meaningful change, active quests,
blockers, newly broken checks, pending decisions, and the next grounded moves.

**Exit criteria:**

- [x] Desktop, mobile, keyboard, screen-reader, reduced-motion, and print contracts pass.
- [x] Repository identity, represented commit, freshness, build evidence, and canonical sources stay visible.
- [x] URL-backed filters and transparent browser-local resume behavior are verified.

<!-- roadmap-step
id: REL-RI-003
status: complete
depends_on: [REL-RI-002]
issues: [31]
-->
#### REL-RI-003 — Render the roadmap as an explorable quest line

**State:** `complete`
**Depends on:** `REL-RI-002`

**Outcome:** `/roadmap/` makes progress, dependencies, exit criteria, and linked
commit evidence legible without replacing `ROADMAP.md` as canonical intent.

**Exit criteria:**

- [x] Long quest lines remain scrollable, keyboard reachable, and printable.
- [x] Expanding a quest exposes its linked commits and other evidence.
- [x] The implementation is reviewed and merged as the current Relay contract.

<!-- roadmap-step
id: REL-RI-004
status: complete
depends_on: [REL-RI-002]
issues: [30]
-->
#### REL-RI-004 — Render ADR lineage as decision history

**State:** `complete`
**Depends on:** `REL-RI-002`

**Outcome:** `/decisions/` preserves proposal, acceptance, implementation, and
supersession as a navigable historical chain.

**Exit criteria:**

- [x] ADR status, scope, implementation, and supersession remain distinct.
- [x] Decision evidence links back to canonical records and affected quests.
- [x] The implementation is reviewed and merged as the current Relay contract.

<!-- roadmap-step
id: REL-RI-005
status: complete
depends_on: [REL-RI-003, REL-RI-004]
issues: [32]
-->
#### REL-RI-005 — Unify commits and delivery evidence as a journey

**State:** `complete`
**Depends on:** `REL-RI-003`, `REL-RI-004`

**Outcome:** `/journey/` relates commits to quests, decisions, issues, checks,
releases, and deployments across meaningful epochs.

**Exit criteria:**

- [x] Long histories virtualize interactively without truncating static output.
- [x] Time, state, and evidence filters remain URL-shareable.
- [x] Release chapters partition every event in deterministic chronological order.
- [x] Explicit quest and ADR context is linked while orphaned work stays unclassified.
- [x] Optional replay respects reduced-motion preferences and never changes evidence.
- [x] The implementation is reviewed and merged as the current Relay contract.

<!-- roadmap-step
id: REL-RI-006
status: active
depends_on: [REL-RI-005]
issues: [29, 33, 77, 79, 81, 83, 86, 88, 90, 102, 104, 105, 106, 109]
-->
#### REL-RI-006 — Complete supporting views and the intelligence dashboard

**State:** `active`
**Depends on:** `REL-RI-005`

**Outcome:** Dependencies, Health, Releases, Work, Search, Compare, and the
repository dashboard form one consistent evidence-navigation system.
Organization aggregation remains with Observatory and the organization host.

**Exit criteria:**

- [x] Every supporting view preserves the shared shell and evidence vocabulary.
- [ ] Search identifies the matched normalized field from accepted Observatory evidence.
- [ ] Consumer publication refreshes deterministically through one pinned workflow.

**Current evidence:**

- Dependencies (#77/#78), Work (#79/#80), Releases (#81/#82), Search (#83/#85),
  Compare (#86/#87), and core Health (#88/#89) are merged as bounded supporting
  views over accepted Observatory evidence.
- The #29 reconciliation pins Hygiene's repository route profile, separates the
  `/intelligence/` overview from `/intelligence/now/`, preserves cross-view URL
  context, exposes every route as an action output, and proves partial adoption
  plus aggregate supporting-view orchestration.
- Field-attributed Search matches remain an ordered contract follow-up in
  Observatory #24 and Relay #102; Relay will not infer them from opaque
  `search_text`. Observatory #5 still owns full conformance evidence; Relay #75
  renders that accepted evidence as the separate `/hygiene/` contract matrix.
- Workflow parity #90/#91 is merged. Issue #29 is closed; field attribution
  remains explicitly separate in Observatory #24 and Relay #102.
- Issue #33 remains open for #106's final evidence reconciliation and current
  canary verification. Its four preceding checkpoints are closed; migration
  implementation is no longer the next task.
- Checkpoint #104 is complete at Relay revision
  `ecdf1d9bd8eda0d1aa2388a7caffe867968578a7`: it owns the artifact-workflow
  trust matrix, read-only fork-safe execution, revision-scoped success
  artifacts, bounded sanitized run evidence, and same-target cancellation.
- Checkpoint #105 and PR #108 are merged at
  `9a6315978766c336566b9fa7139b800fa8789ba5`. Its
  [closeout](https://github.com/egohygiene/relay/issues/105#issuecomment-5783676953)
  records deterministic build manifests, separate consumer deployment receipts,
  and provider reference-pipeline proof. Fixture proof and consumer deployment
  proof retain distinct scopes.
- [Akashic #185](https://github.com/egohygiene/akashic/issues/185#issuecomment-5792866221)
  and [Empathy #94](https://github.com/egohygiene/empathy/issues/94#issuecomment-5796092734)
  are closed with recorded consumer-owned publication, failure, preservation,
  and rollback evidence at the same immutable Relay pin. Their recorded source
  revisions are respectively `cdf4959d573d36d4030c4e8e939ad0ea4df3d973` and
  `d160044e08f3377afdf14f4856bc470ddd53b769`.
- The preceding records were reread on 2026-09-25; this documentation mission
  did not re-run workflows, download retained deployment artifacts, or inspect
  live route bytes. #106 must reverify its own acceptance evidence before #33
  closes. #101 retains final integration/release acceptance; Pace #13 retains
  fleet adoption.
- #109's implementation merged in [PR #111](https://github.com/egohygiene/relay/pull/111)
  as `13f22cb67ae7f2b922e0c75de966610802201bdb` on 2026-09-26. Canonical repository
  identity now replaces checkout basenames, and the regression compares complete
  bundles across differently named checkouts. The issue remains open for its
  exact-head provider evidence and tracked consumer-guidance/adoption acceptance;
  do not schedule the implemented repair again. Historical pins and rollback
  bytes retain their documented constraints until separately upgraded.

<!-- roadmap-step
id: REL-RI-007
status: active
depends_on: [REL-RI-004]
issues: [115]
-->
#### REL-RI-007 — Connect canonical ADR evidence to Decisions builds

**State:** `active`
**Depends on:** `REL-RI-004`

**Outcome:** An explicit read-only collection path validates a consumer's
canonical ADR corpus through pinned owner contracts and populates the existing
Decisions renderer without inventing decisions or transferring publication
authority.

**Exit criteria:**

- [x] The first canonical ADR collection checkpoint is merged in PR #134.
- [ ] The opt-in native/action/workflow build integration is reviewed and merged.
- [ ] A real owner-reviewed immutable consumer corpus passes admission and
  reproduces complete bundles while retaining lifecycle, implementation,
  lineage, source links, and explicit uncollected-domain states.
- [ ] Identity #69 receives the reviewed immutable upgrade and repeatable
  refresh instructions; consumer deployment remains separately evidenced.

**Current evidence (2026-10-10):**

- EgoLint #73, Aether #91, and Observatory #25 are closed. Ratified-policy
  validation, continuous decision-capture guidance, and partial-domain coverage
  semantics are available from their owners; they are no longer unimplemented
  blockers for this lane.
- [PR #135](https://github.com/egohygiene/relay/pull/135) records the reviewed
  integration candidate at `9644eb8188827dccb88f4c856c1de7f236a79988`. Its recorded validation
  covers native/action/workflow admission, deterministic replay across checkout
  and runtime locations, existing external snapshots, and alpha.2 coverage.
  Review and integration into current `main` remain the immediate checkpoint.
- The recorded immutable Hygiene canary preserves 12 canonical records but has
  source-policy and migration gaps, so production admission remains denied.
  This is consumer source work, not proof that the shared Decisions renderer is
  missing. Identity #69 owns the first selected consumer migration; Pace #5
  owns the subsequent ADR capability campaign.
- Relay #5/#99 retain hosted acceptance, release and required-mode gates.
  Supported operational validation can serve this bounded ADR lane without
  claiming those parent issues or consumer publication complete.

### Bounded Intelligence completion sequence

1. Review and integrate #115 / PR #135 against current `main`, preserving the
   existing shared renderers and the distinct source-admission gate. Reconcile
   #115 against real consumer evidence before declaring its acceptance complete.
2. Complete Identity #69 as the first ADR/Decisions canary, including a reviewed
   corpus, immutable Relay upgrade, repeatable refresh and consumer-owned
   publication evidence; advance the capability through Pace #5 one repository
   at a time.
3. Resume #112's roadmap collector with the now-available Observatory #25
   coverage contract, review its separate runtime/profile repin, then complete
   #113's opt-in build integration. ADR integration does not silently upgrade
   the roadmap collector or clear its publication gate.
4. Reconcile Akashic #197's source-state inconsistency and prove its populated
   roadmap canary, then advance the second capability through Pace #31.
5. Close outstanding acceptance from recorded proof: #109's provider and
   consumer follow-up, #106's three-repository publication matrix, and #33's
   publication closeout. These are separate evidence gates, not renderer rebuilds.
6. Select required remaining route capabilities through #101's entry criteria;
   record any nonblocking/post-v1 disposition explicitly in the owning issues.
   Field-attributed Search remains Observatory #24 then Relay #102 even though
   the supporting-view parent #29 is closed.
7. Complete #101 integration/release acceptance, then the remaining Pace #13
   adoption waves without duplicating the ADR and roadmap campaigns.

For every route, track renderer delivery, connected normalized evidence, and
publication verified at a recorded revision separately. Missing Observatory
input remains unavailable; it is not evidence of a billing failure.
The organization focus order is coordinated in
[Pace #25](https://github.com/egohygiene/pace/issues/25); the Intelligence program
remains in [organization #30](https://github.com/egohygiene/.github/issues/30).
Product features and optional platform research are outside this infrastructure
focus. These links do not transfer organization roadmap authority into Relay.

### Repository architecture validation track

<!-- roadmap-step
id: REL-ARCH-001
status: active
depends_on: [REL-Q01]
issues: [5, 99]
-->
#### REL-ARCH-001 — Establish the architecture-validation evidence boundary

**State:** `active`
**Depends on:** `REL-Q01`

**Outcome:** Repositories can validate repository contracts, architecture
records, and diagram evidence through one immutable, privacy-safe local and CI
contract without moving sibling policy into Relay.

**Exit criteria:**

- [x] Hygiene policy, EgoLint semantics, and Holon materialization artifacts
  are pinned by full revision and digest in a versioned profile.
- [x] Closed request and result schemas preserve adoption, coverage,
  provenance, bounds, truncation, and privacy states.
- [x] An offline adapter normalizes pinned EgoLint evidence without executing
  consumer code or mutating the inspected checkout.
- [x] Diagram evidence is either validated by a reviewed owner or reported as
  explicitly planned or unavailable.
- [ ] A least-privilege reusable workflow proves local/CI parity across public,
  private, legacy, missing, and nonconformant fixtures.
- [ ] The capability is released immutably and adopted by representative
  consumers before required mode can be enabled.

**Current evidence:**

- Issue #99 decomposes parent #5 into six ordered, reviewable checkpoints.
- The checkpoint-1 profile and fixture corpus make the current boundary
  advisory-only because the complete upstream validator surface is not yet
  included in immutable releases.
- Repository-contract and architecture-record rules are present in the pinned
  EgoLint source. No reviewed diagram semantic validator was found, so Relay
  records that surface as planned instead of claiming conformance.
- Checkpoint 2 merged in PR #116 as `b3d27e61a86f347e0924da0c7eb56ad2f20b4e01`:
  offline native validation, bounded snapshots and sanitized JSON/SARIF evidence.
- Checkpoint 3 merged in PR #117 as `cf1413703160d4eac4ef66a10beb9415d40e42a2`,
  adding bounded diagram discovery and closed metadata.
  Format validation remains explicitly unavailable; EgoLint #74 tracks reviewed
  offline backends.
- Checkpoint 4 merged in PR #118 as `da172c64cbda4ae4a28434a065fbfa616c1d74c3`.
  Its reviewed tree was verified before checkpoint 5. It composes the adapter
  in a read-only reusable workflow
  with bounded presentation, fresh-evidence receipts and #6 retention.
- Checkpoint 5 merged in PR #119 as `ce7b9b4de823cdbfec84496398a2d89847a5d492`,
  verified on current main on 2026-09-28 with the exact reviewed tree. It adds
  a native end-to-end fixture matrix, no-skip
  local evidence runner, recovery/private-data checks and manual Relay dogfood.
  See the [acceptance guide](docs/repository-architecture-acceptance.md).
- Checkpoint 6 inspected default-branch run 36447721265: GitHub rejected
  job-level `job.workflow_*` expressions before any job started, with no artifacts.
  PR #120 merged the step-scoped repair as `04bd32c8ef492418f47d6df6faee425d6888f341`.
  Hosted advisory/required-denial acceptance is deferred to final cleanup;
  annotations, actual upload, runtime permissions/provenance and sanitized logs
  remain unverified. The local/CI exit criterion stays open.
- EgoLint PR #75 merged the #73 ratified-policy fix as
  `933472b6322d2060c487e5a8a6f0bc5197696af0`. Relay adopted that profile in
  [PR #121](https://github.com/egohygiene/relay/pull/121), merged on 2026-10-03 as
  `33e1fc78727269bd3821dea53f6541f769cf4319`; this is no longer an unmerged
  adoption candidate. Valid ratified ADR coverage may pass; old policy
  references fail and legacy adoption stays partial.
  [Local evidence](docs/evidence/repository-architecture-ratified-policy.json)
  remains separate from hosted acceptance, release and consumer rollout.
- ADR/Decisions adoption under Pace #5 is the current fleet priority. Relay
  #115 / PR #135 owns the current canonical collection/build checkpoint;
  Aether #91's continuous-capture guidance is closed. Identity #69 is the
  selected first canary, and roadmap rollout in Pace #31 follows the ADR
  campaign. See REL-RI-007 and the bounded completion sequence.

### Repository continuity preflight track

<!-- roadmap-step
id: REL-CONT-001
status: active
depends_on: [REL-Q01]
issues: [60, 61, 62, 63]
-->
#### REL-CONT-001 — Publish continuity preflight and CI evidence

**State:** `active`
**Depends on:** `REL-Q01`

**Outcome:** Consumers run one immutable, privacy-safe continuity contract
locally before pull-request presentation and through a read-only CI backstop.

**Exit criteria:**

- [x] The pinned contract and shared request/result schemas are reviewed.
- [x] The local adapter performs no implicit Git, provider, or semantic writes.
- [ ] The reusable pull-request workflow is least-privilege and fork-safe. Candidate implementation: #63.
- [ ] Local and CI evidence is byte-compatible and released immutably.

**Current evidence:**

- Parent issue #60 is decomposed into contract #61, local adapter #62, and
  reusable workflow/dogfood #63.
- All upstream inputs are immutable reviewed commits but remain unreleased;
  promotion is capped at `observe`.

### Repository journal track

<!-- roadmap-step
id: REL-JOURNAL-001
status: active
depends_on: [REL-Q01]
issues: [15, 95]
-->
#### REL-JOURNAL-001 — Ship the evidence-bound repository journal

**State:** `active`
**Depends on:** `REL-Q01`

**Outcome:** Repositories can schedule or manually dispatch an inspectable
Aether journal without requiring AI billing, while a separately permissioned
Copilot adapter remains available for explicit later activation.

**Exit criteria:**

- [x] The Aether 1.0.0 draft distribution and Copilot runtime are bound by
  immutable revisions, package locks, and checksums.
- [x] Bounded provider evidence, candidate, result, completeness, provenance,
  and deterministic-rendering contracts are implemented and tested.
- [x] Read-only no-billing and separately authorized Copilot reusable workflows
  are cataloged; Relay owns a scheduled/manual deterministic canary caller.
- [x] PR #96 is merged and the implementation is verified on current `main`.
- [ ] A default-branch manual canary and the first scheduled execution retain
  valid summaries, artifacts, provenance, permissions, and sanitized logs.

**Current evidence:**

- Issue #95 owns the ordered eleven-step evidence plan for parent #15.
- PR #96 merged as `d77ac85a73d5911e84d9a07719620f7ce70e71b8`; its tree exactly
  matches the reviewed head. Deterministic and reviewed-manual modes are the
  present no-billing path; organization Copilot connection is an optional later
  activation rather than an implementation prerequisite.
- Default-branch manual run 35485517452 retained sanitized failure evidence and
  exposed that valid live evidence could exceed the deterministic candidate
  item ceiling. A bounded follow-up selects across sections and reports the
  limit as partial before live acceptance is retried.
- Release publication and movement of the `v1` alias remain outside this track.

### Roadmap-to-issue handoff

- A step is complete only when its exit criteria and required evidence are satisfied; commit count never determines progress.
- Ready steps without an issue are candidates for the private, duplicate-aware roadmap.issue-plan.json dry run. Planned steps remain preview-only unless a reviewer explicitly opts them in with issue_policy: propose.
- Issue creation or reconciliation requires human approval or an explicitly authorized Pace operation and returns issue references through a reviewable roadmap pull request.
- Pull requests and commits should include Roadmap-Step: <ID>; historical evidence may be linked through existing issue and pull-request relationships.
- Public rendering uses only allowlisted build-time evidence and never places a GitHub token or private issue plan in the browser artifact.

<!-- END ROADMAP EXECUTION SNAPSHOT -->

## Strategic context

This roadmap describes capability evolution, not promised dates or an issue queue. Sequence follows architecture dependencies and may change when evidence or risk changes.

## Phase 1: Inventory proven Empathy actions

**Status:** Complete for the initial Repository Intelligence capability.

**Outcome:** A bounded capability advances from documented intent to validated, independently usable behavior.

**Exit signals:**

- The owning contract and acceptance criteria are versioned.
- Implementation and documentation agree.
- Relevant tests and safety checks pass.
- Downstream consumers and migration impact are understood.
- Remaining uncertainty is visible.

## Phase 2: Define action and workflow contracts

**Status:** Complete for the v1 action and workflow contracts. Every current
workflow is inventoried by owner and purpose with machine-checked permissions,
timeouts, concurrency, parameters, and failure semantics. Issue #6 added a
separate versioned lifecycle catalog for cancellation classes plus bounded,
run-bound success and failure report preservation without changing the workflow
catalog v1 schema.

**Outcome:** A bounded capability advances from documented intent to validated, independently usable behavior.

**Exit signals:**

- The owning contract and acceptance criteria are versioned.
- Implementation and documentation agree.
- Relevant tests and safety checks pass.
- Downstream consumers and migration impact are understood.
- Remaining uncertainty is visible.

## Phase 3: Extract and test reusable components

**Status:** Complete for the central implementation, fixtures, and test suite;
consumer evidence is tracked in Phase 5.

**Outcome:** A bounded capability advances from documented intent to validated, independently usable behavior.

**Exit signals:**

- The owning contract and acceptance criteria are versioned.
- Implementation and documentation agree.
- Relevant tests and safety checks pass.
- Downstream consumers and migration impact are understood.
- Remaining uncertainty is visible.

## Phase 4: Publish immutable releases

**Status (release evidence observed 2026-09-25):** `v1.0.0` through `v1.5.0`
were published immutably. The release declaration, changelog, and version
authority at that checkpoint prepared the additive `v1.6.0` surface:
product-facing release names, legacy-workflow intake policy,
advisory-first stale pull-request lifecycle automation, and reusable artifact
size/performance budgets, plus bounded CI report preservation. This Intelligence
refresh does not establish a newer published release; publication remains an
explicit manual dispatch after review.

**Outcome:** A bounded capability advances from documented intent to validated, independently usable behavior.

**Exit signals:**

- The owning contract and acceptance criteria are versioned.
- Implementation and documentation agree.
- Relevant tests and safety checks pass.
- Downstream consumers and migration impact are understood.
- Remaining uncertainty is visible.

## Phase 5: Migrate repository consumers

**Status:** Akashic #185 and Empathy #94 record completed hardened consumer
proofs at Relay `9a6315978766c336566b9fa7139b800fa8789ba5`. #106 owns current
cross-consumer reconciliation and verification before #33 closes. Optiflow and
broader consumer upgrades remain separately scoped adoption work; their current
acceptance was not re-audited in this checkpoint.

**Outcome:** A bounded capability advances from documented intent to validated, independently usable behavior.

**Exit signals:**

- The owning contract and acceptance criteria are versioned.
- Implementation and documentation agree.
- Relevant tests and safety checks pass.
- Downstream consumers and migration impact are understood.
- Remaining uncertainty is visible.

## Cross-cutting tracks

- Security, privacy, accessibility, licensing, and provenance.
- Documentation, architecture portals, examples, and onboarding.
- Packaging, release, compatibility, and self-hosting.
- Organization integration through explicit contracts.
- Observatory evidence and Pace conformance when those systems exist.

## Deferred direction

Optional managed services, enterprise controls, marketplaces, and the conversational organization compiler remain later architecture work. Current choices should preserve portability and avoid foreclosing them.

## Evidence and uncertainty

- **Observed:** Relay owns the reusable Repository Intelligence implementation,
  framework-free template, public contracts, reusable artifact workflow,
  complete workflow catalog, immutable-pin adoption example, privacy fixtures,
  and validation suite. Published releases through `v1.5.0`, closed #104/#105,
  and recorded Akashic/Empathy acceptance were observed on 2026-09-25.
  Source-declared `v1.6.0` was not observed as a published release at that
  checkpoint; release inventory was not re-audited on 2026-10-10.
- **Observed on 2026-10-10:** The core Intelligence renderers and supporting
  views are delivered. Relay PR #111's portability repair and PR #121's
  ratified-policy adoption are merged. EgoLint #73, Aether #91, and Observatory
  #25 are closed. Relay #115 / PR #135 remains the open ADR build integration
  checkpoint; real consumer source acceptance and deployment remain separate.
- **Decided for this draft:** The repository owns the bounded concern described here and participates through versioned contracts.
- **Proposed:** Target systems and later roadmap phases remain proposals until accepted and implemented.
- **Open work:** The selected execution path is #115 / PR #135 → Identity #69
  and Pace #5 → #112/#113 → Akashic #197 and Pace #31. #109 acceptance after its
  merged repair, #106 publication reconciliation, #101 final integration/release
  acceptance, and Pace #13 fleet rollout remain distinct. Historical acceptance
  does not prove present deployment freshness.
