---
schema: aether.architecture-document/v1
id: relay-decisions
title: Relay Decisions
kind: architecture-document
version: 0.1.0
status: provisional
owners:
  - egohygiene
created: 2026-08-19
updated: 2026-08-21
governed_by:
  - architecture-decisions
depends_on:
  - relay-principles
  - relay-epistemology
  - relay-foundations
  - relay-system
  - relay-architecture
related:
  - relay-purpose
  - relay-vision
  - relay-pillars
  - relay-manifesto
supersedes: []
---

# Relay Decisions

## Purpose

This document preserves significant accepted architectural choices and their rationale. Issues coordinate work, proposals explore alternatives, and this file records decisions that constrain future implementation.

## Governance

Do not rewrite historical context to fit current understanding. Amend a record for corrections that do not change meaning; supersede it with a new record when the decision changes materially.

## Index

- ADR-001: Package reusable behavior outside templates
- ADR-002: Default to least-privilege permissions
- ADR-003: Require immutable references in consumer workflows
- ADR-004: Preserve extracted Intelligence contract identities
- ADR-005: Release the action catalog as one repository unit
- ADR-006: Catalog workflow authority and failure semantics

## ADR-001: Package reusable behavior outside templates

- **Status:** Accepted as the current architectural direction
- **Date:** 2026-08-19
- **Context:** Repository evidence and ecosystem ownership require an explicit durable boundary.
- **Decision:** Package reusable behavior outside templates.
- **Consequences:** The choice improves ownership and predictability while requiring maintained contracts, validation, and migration discipline.
- **Reconsider when:** New evidence shows that the boundary prevents standalone usefulness, safety, portability, or maintainability.

## ADR-002: Default to least-privilege permissions

- **Status:** Accepted as the current architectural direction
- **Date:** 2026-08-19
- **Context:** Repository evidence and ecosystem ownership require an explicit durable boundary.
- **Decision:** Default to least-privilege permissions.
- **Consequences:** The choice improves ownership and predictability while requiring maintained contracts, validation, and migration discipline.
- **Reconsider when:** New evidence shows that the boundary prevents standalone usefulness, safety, portability, or maintainability.

## ADR-003: Require immutable references in consumer workflows

- **Status:** Accepted as the current architectural direction
- **Date:** 2026-08-19
- **Context:** Repository evidence and ecosystem ownership require an explicit durable boundary.
- **Decision:** Require immutable references in consumer workflows.
- **Consequences:** The choice improves ownership and predictability while requiring maintained contracts, validation, and migration discipline.
- **Reconsider when:** New evidence shows that the boundary prevents standalone usefulness, safety, portability, or maintainability.

## ADR-004: Preserve extracted Intelligence contract identities

- **Status:** Accepted for Intelligence v1
- **Date:** 2026-08-19
- **Context:** Empathy already emitted four named public contracts before their implementation moved into Relay. Their JSON Schema `$id` values use two historical namespaces: `egohygiene.github.io/contracts` for repository analytics and tree data, and `egohygiene.dev/schemas` for normalized reports and the dashboard aggregate.
- **Decision:** Preserve those `$id` values and schema names byte-compatibly for v1. Implementation ownership moving to Relay does not rename the data contract. New Relay-only contracts use the `egohygiene.github.io/relay/contracts` namespace.
- **Consequences:** Existing snapshots and consumers remain compatible. The historical namespace split is explicit rather than accidental. A future unified namespace requires a versioned v2 contract and documented compatibility aliases.
- **Reconsider when:** The organization can publish permanent redirects and a deliberate v2 migration plan.

## ADR-005: Release the action catalog as one repository unit

- **Status:** Accepted for Relay v1
- **Date:** 2026-08-19
- **Context:** GitHub resolves a subdirectory action from a repository ref, so independent folder tags do not provide independent version graphs inside one repository.
- **Decision:** Validate and release every cataloged action at one immutable repository SemVer tag. Maintain an optional moving major alias for convenience while recommending full commit SHAs to consumers.
- **Consequences:** One release proves compatibility across actions and reusable workflows. A change to any public package advances the Relay repository version.
- **Reconsider when:** An action needs an incompatible cadence or trust boundary substantial enough to justify a separate repository.

## ADR-006: Catalog workflow authority and failure semantics

- **Status:** Accepted for Relay v1
- **Date:** 2026-08-21
- **Context:** Workflow YAML exposes executable behavior but does not provide one stable inventory for ownership, caller parameters, permission ceilings, runtime bounds, concurrency, or failure behavior. Security review and future Pace reconciliation need that contract without inferring intent from implementation text.
- **Decision:** Maintain `workflow-catalog.json` as the complete inventory of current internal and reusable workflows. Require explicit owner, purpose, audience, permissions, timeout, concurrency, inputs, outputs, and failure semantics. Reject uncataloged workflows, mutable remote dependencies, `write-all`, `pull_request_target`, and runnable jobs without timeouts.
- **Consequences:** Reviewers and automation can compare declared authority with implementation. Adding a workflow becomes an explicit contract change. The catalog duplicates a bounded amount of YAML metadata and therefore requires executable drift checks.
- **Reconsider when:** GitHub provides a portable native workflow manifest with equivalent closed, versioned semantics that Pace and offline validators can consume.

## Open decisions

- Exact self-hosted, managed, and organization-integrated deployment boundaries.
- Which target systems must exist before the architecture status may become active.

## Evidence and uncertainty

- **Observed:** The repository README establishes the intended boundary as the reusable GitHub Actions, workflows, automation components, and CI orchestration library for the organization; significant implementation remains incomplete.
- **Decided for this draft:** The repository owns the bounded concern described here and participates through versioned contracts.
- **Proposed:** Target systems and later roadmap phases remain proposals until accepted and implemented.
- **Open question:** Which parts of this draft should become active in the first independently versioned release?
