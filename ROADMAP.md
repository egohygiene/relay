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
updated: 2026-08-20
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

**Status:** Complete for the v1 contract; additive hardening continues within
the accepted compatibility boundary.

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

**Status:** `v1.0.0` is published immutably. The current release manifest
requests the additive `v1.1.0` hardening release.

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
  privacy fixtures, and validation suite. `v1.0.0` is published; the additive
  `v1.1.0` hardening release and consumer pin migrations remain under review.
- **Decided for this draft:** The repository owns the bounded concern described here and participates through versioned contracts.
- **Proposed:** Target systems and later roadmap phases remain proposals until accepted and implemented.
- **Open question:** Which consumer-specific constraints will surface during the three hardened pilot migrations?
