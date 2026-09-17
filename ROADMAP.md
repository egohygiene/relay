---
schema: aether.architecture-document/v1
id: relay-roadmap
title: Relay Roadmap
kind: architecture-document
version: 0.2.0
status: provisional
owners:
  - egohygiene
created: 2026-08-19
updated: 2026-09-17
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
updated: 2026-09-17
-->
## 2026-08-25 execution snapshot

> This evidence-reconciled snapshot is the issue-generation and visual-roadmap handoff. The longer-horizon strategy below remains canonical context; generated HTML, JSON, progress, issue plans, and commit lists are projections.

**Lifecycle:** active released product  
**Current gate:** Reconcile the stale roadmap with shipped v1.0-v1.2 behavior, then define and prove the reusable roadmap build workflow.  
**North-star outcome:** Immutable, reusable CI building blocks that repositories can pin, verify, and upgrade safely.

### Visual roadmap publication

**Mode:** `central`  
**Route:** `/roadmap/relay/`  
**Current publication evidence:** Versioned GitHub releases and reusable workflow distribution; v1.0 through v1.5 observed.

Publish the public-safe projection through egohygiene.io at /roadmap/relay/. This repository owns intent and acceptance evidence; it does not add a second site deployment.

### Quest line

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

- Releases v1.0, v1.1, and v1.2 were observed.
- Latest audited commit 8837ab6862ab was associated with a healthy released repository.

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

- [ ] Shipped v1.0-v1.2 items are marked from acceptance evidence.
- [ ] Stale or duplicated future work is removed.

**Current evidence:**

- ROADMAP.md was stale relative to the released product.

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

- Existing dist and intelligence workflows provide a precedent; no roadmap workflow was observed.

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

- No cross-repository roadmap workflow pilot was observed.

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

- Current releases predate the proposed roadmap automation.

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
- [ ] Relay v1.3.0 is published from the accepted implementation commit.
- [ ] Antidote and Reflector pin that release and pass real default-branch
  deployment plus rollback checks without losing native build independence.

**Current evidence:**

- Relay issue #38 owns the implementation and release/adoption acceptance.
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
issues: [29, 33, 77, 79, 81, 83, 86, 88, 90]
-->
#### REL-RI-006 — Complete supporting views and the intelligence dashboard

**State:** `active`
**Depends on:** `REL-RI-005`

**Outcome:** Dependencies, Health, Releases, Work, Search, Compare, and the
organization dashboard form one consistent evidence-navigation system.

**Exit criteria:**

- [ ] Every supporting view preserves the shared shell and evidence vocabulary.
- [ ] Consumer publication refreshes deterministically through one pinned workflow.

**Current evidence:**

- Dependencies (#77/#78), Work (#79/#80), Releases (#81/#82), Search (#83/#85),
  Compare (#86/#87), and core Health (#88/#89) are merged as bounded supporting
  views over accepted Observatory evidence.
- Issue #90 is the current #33 child checkpoint to restore reusable-workflow
  parity with the complete snapshot/comparison evidence boundary and lock that
  parity with executable tests.
- Empathy and Akashic already compose immutable-pinned Repository Intelligence
  action output into consumer-owned Pages pipelines; representative migrations
  to one current hardened workflow revision and public-route verification remain
  required before #33 or REL-RI-006 can be considered complete.

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
timeouts, concurrency, parameters, and failure semantics.

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

**Status:** `v1.0.0` through `v1.5.0` are published immutably. The current
release declaration, changelog, and version authority prepare the additive
`v1.6.0` surface: product-facing release names, legacy-workflow intake policy,
advisory-first stale pull-request lifecycle automation, and reusable artifact
size/performance budgets. Publication remains an explicit manual dispatch after
review.

**Outcome:** A bounded capability advances from documented intent to validated, independently usable behavior.

**Exit signals:**

- The owning contract and acceptance criteria are versioned.
- Implementation and documentation agree.
- Relevant tests and safety checks pass.
- Downstream consumers and migration impact are understood.
- Remaining uncertainty is visible.

## Phase 5: Migrate repository consumers

**Status:** Empathy, Akashic, and Optiflow have existing immutable-SHA v1.0
consumer integrations. Their migrations to one approved hardened Relay SHA and
public-route verification remain planned, repository-specific pilot work.

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
  and validation suite. `v1.0.0` and `v1.1.0` are published; the additive
  `v1.2.0` catalog release and consumer pin migrations remain under review.
- **Decided for this draft:** The repository owns the bounded concern described here and participates through versioned contracts.
- **Proposed:** Target systems and later roadmap phases remain proposals until accepted and implemented.
- **Open question:** Which consumer-specific constraints will surface during the three hardened pilot migrations?
