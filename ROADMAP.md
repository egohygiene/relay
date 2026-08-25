---
schema: aether.architecture-document/v1
id: relay-roadmap
title: Relay Roadmap
kind: architecture-document
version: 0.1.0
status: provisional
owners:
  - egohygiene
created: 2026-08-19
updated: 2026-08-24
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
updated: 2026-08-24
-->
## 2026-08-24 execution snapshot

> This evidence-reconciled snapshot is the issue-generation and visual-roadmap handoff. The longer-horizon strategy below remains canonical context; generated HTML, JSON, progress, issue plans, and commit lists are projections.

**Lifecycle:** active released product  
**Current gate:** Reconcile the stale roadmap with shipped v1.0-v1.2 behavior, then define and prove the reusable roadmap build workflow.  
**North-star outcome:** Immutable, reusable CI building blocks that repositories can pin, verify, and upgrade safely.

### Visual roadmap publication

**Mode:** `central`  
**Route:** `/roadmap/relay/`  
**Current publication evidence:** Versioned GitHub releases and reusable workflow distribution; v1.0 through v1.2 observed.

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

**Status:** `v1.0.0` and `v1.1.0` are published immutably. The current release
manifest requests the additive `v1.2.0` workflow-catalog release.

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
