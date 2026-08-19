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
updated: 2026-08-19
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
| Composite-action library | Target | Owns its bounded portion of the reusable GitHub Actions, workflows, automation components, and CI orchestration library for the organization; exposes explicit inputs, outputs, failure states, and evidence. |
| Reusable-workflow library | Target | Owns its bounded portion of the reusable GitHub Actions, workflows, automation components, and CI orchestration library for the organization; exposes explicit inputs, outputs, failure states, and evidence. |
| Contract metadata | Target | Owns its bounded portion of the reusable GitHub Actions, workflows, automation components, and CI orchestration library for the organization; exposes explicit inputs, outputs, failure states, and evidence. |
| Security and permission tests | Target | Owns its bounded portion of the reusable GitHub Actions, workflows, automation components, and CI orchestration library for the organization; exposes explicit inputs, outputs, failure states, and evidence. |
| Release and versioning | Target | Owns its bounded portion of the reusable GitHub Actions, workflows, automation components, and CI orchestration library for the organization; exposes explicit inputs, outputs, failure states, and evidence. |
| Consumer examples | Target | Owns its bounded portion of the reusable GitHub Actions, workflows, automation components, and CI orchestration library for the organization; exposes explicit inputs, outputs, failure states, and evidence. |
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
