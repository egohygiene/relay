---
schema: aether.architecture-document/v1
id: relay-architecture
title: Relay Architecture
kind: architecture-document
version: 0.1.0
status: provisional
owners:
  - egohygiene
created: 2026-08-19
updated: 2026-08-20
governed_by:
  - architecture-architecture
depends_on:
  - relay-foundations
  - relay-system
related:
  - relay-purpose
  - relay-vision
  - relay-principles
  - relay-pillars
supersedes: []
---

# Relay Architecture

## Purpose and scope

Relay uses a layered, contract-driven architecture. This document owns structural boundaries, dependency direction, integration rules, and current-to-target evolution. Logical responsibilities remain canonical in [SYSTEM.md](SYSTEM.md).

## Layer model

1. **Intent and contracts** — identity, policy, specifications, schemas, and accepted decisions.
2. **Domain** — canonical concepts and pure domain behavior.
3. **Application** — planning, orchestration, use cases, and state transitions.
4. **Adapters** — filesystems, providers, frameworks, renderers, and external tools.
5. **Interfaces** — CLI, library, site, reports, generated artifacts, and automation contracts.
6. **Evidence** — tests, diagnostics, provenance, manifests, and health projections.

Dependencies point inward toward stable contracts and domain behavior. External details do not become canonical domain truth.

## Structural view

```mermaid
flowchart LR
  S1[Composite-action library]
  S2[Reusable-workflow library]
  S3[Contract metadata]
  S4[Security and permission tests]
  S5[Release and versioning]
  S6[Consumer examples]
  S7[Migration adapters]
  S1 --> S2
  S2 --> S3
  S3 --> S4
  S4 --> S5
  S5 --> S6
  S6 --> S7
```

The diagram is conceptual. [SYSTEM.md](SYSTEM.md) remains authoritative for responsibilities and implementation evidence determines current availability.

## Implemented v1 package topology

```text
actions/
├── repository-intelligence/      # read-only collector and static renderer
├── normalize-repository-report/  # producer contract adapter
└── publish-report-snapshot/      # guarded default-branch writer

.github/workflows/
├── repository-intelligence.yml   # reusable artifact orchestration
├── validate.yml                  # pull-request and default-branch gate
└── release.yml                   # reviewed manifest or manual SemVer publication
```

The dashboard builder never deploys Pages. Consumers compose its output into
their one authoritative site artifact. The snapshot publisher is isolated as a
separate action because it requires `contents: write`; all other v1 action jobs
operate with read-only repository permissions.

## Dependency rules

- Sibling domain capabilities integrate through versioned public contracts, not direct access to internals.
- Generated artifacts never become the canonical source unless an accepted decision explicitly changes ownership.
- Provider and platform adapters depend on application ports; core behavior does not depend on a provider implementation.
- Read, plan, apply, verify, publish, and recover remain separate authority boundaries when consequential.
- Cross-repository references use releases, immutable commits, schemas, packages, or documented APIs rather than mutable default-branch assumptions.

## Ecosystem interfaces

- Empathy baseline
- Egolint
- Realm image publishing
- Hygiene policy
- Pace synchronization
- Observatory reports

## Deployment and portability

The architecture favors independently usable local and self-hosted operation. Optional managed services may add availability, collaboration, support, and hosted infrastructure without becoming the canonical holder of portable state.

## Evidence and uncertainty

- **Observed:** Relay contains a machine-readable action catalog, three
  independently consumable composite actions, a reusable artifact workflow,
  validation gates, and a `release.json`-driven release workflow with manual
  recovery. Empathy, Akashic, and Optiflow have existing Repository Intelligence
  integrations; their migrations remain planned pilots for the hardened package.
- **Decided for this draft:** The repository owns the bounded concern described here and participates through versioned contracts.
- **Proposed:** Target systems and later roadmap phases remain proposals until accepted and implemented.
- **Open question:** Which additional reusable producers should join the repository-wide release unit after v1?
