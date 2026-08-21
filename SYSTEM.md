---
schema: aether.architecture-document/v1
id: relay-system
title: Relay System
kind: architecture-document
version: 0.1.0
status: provisional
owners:
  - egohygiene
created: 2026-08-19
updated: 2026-08-21
governed_by:
  - architecture-system
depends_on:
  - relay-foundations
  - relay-ontology
related:
  - relay-purpose
  - relay-vision
  - relay-principles
  - relay-pillars
supersedes: []
---

# Relay System

## Purpose and scope

This document identifies Relay's logical systems and responsibilities. It answers what the major systems do; [ARCHITECTURE.md](ARCHITECTURE.md) owns their structural organization and dependency rules.

## System inventory

| System | State | Responsibility |
| --- | --- | --- |
| Composite-action library | Active | Publishes three independently consumable, repository-versioned composite actions. |
| Reusable-workflow library | Active | Publishes bounded orchestration with explicit caller inputs, outputs, authority, and failure states. |
| Contract metadata | Active | Owns versioned action, workflow, release, artifact, and provenance schemas and catalogs. |
| Security and permission tests | Active | Rejects uncataloged workflows, mutable dependencies, broad authority, unsafe triggers, and unbounded runner jobs. |
| Release and versioning | Active | Publishes verified immutable repository releases and a controlled moving major alias. |
| Consumer examples | Active | Demonstrates complete caller-owned workflows with least privilege and immutable Relay pins. |
| Migration adapters | Target | Owns its bounded portion of the reusable GitHub Actions, workflows, automation components, and CI orchestration library for the organization; exposes explicit inputs, outputs, failure states, and evidence. |

## External systems

- Empathy baseline
- Egolint
- Realm image publishing
- Hygiene policy
- Pace synchronization
- Observatory reports

External systems are integrations, not hidden implementation units. Each requires version, authentication, availability, data, error, and replacement boundaries appropriate to its risk.

## System interactions

Inputs enter through an adapter or validated contract, move through domain systems, produce artifacts and diagnostics, and leave through a stable interface. Evidence flows back to validation, review, and future decisions.

## Failure model

Systems fail closed at destructive, publication, privacy, and security boundaries. Partial results identify coverage and remain distinguishable from complete success.

## Evidence and uncertainty

- **Observed:** The repository README establishes the intended boundary as the reusable GitHub Actions, workflows, automation components, and CI orchestration library for the organization; significant implementation remains incomplete.
- **Decided for this draft:** The repository owns the bounded concern described here and participates through versioned contracts.
- **Proposed:** Target systems and later roadmap phases remain proposals until accepted and implemented.
- **Open question:** Which parts of this draft should become active in the first independently versioned release?
