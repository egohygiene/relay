---
schema: aether.architecture-document/v1
id: relay-design-system
title: Relay Design System
kind: architecture-document
version: 0.1.0
status: provisional
owners:
  - egohygiene
created: 2026-08-19
updated: 2026-08-19
governed_by:
  - architecture-design-system
depends_on:
  - relay-personal-model
  - relay-design
related:
  - relay-purpose
  - relay-vision
  - relay-principles
  - relay-pillars
supersedes: []
---

# Relay Design System

## Purpose and scope

This document defines reusable semantic language for Relay's documentation, terminal output, diagrams, reports, sites, and future interactive surfaces. It does not freeze a framework, component library, or final visual identity.

## Semantic roles

| Role | Meaning |
| --- | --- |
| Canvas | Primary quiet background or base surface |
| Surface | Grouped content or bounded interaction area |
| Primary | Main action or navigational emphasis |
| Information | Neutral context or observation |
| Success | Completed and verified state |
| Caution | Review required; safe to pause |
| Danger | Destructive, security, privacy, or irreversible risk |
| Unknown | Missing, unavailable, partial, or unverified state |

## Status vocabulary

Use the states observed, planned, running, partial, verified, failed, blocked, and unknown consistently. Never present partial or unknown as success.

## Content and interaction

- Use verbs that describe the actual operation.
- Put scope and consequence before confirmation.
- Keep destructive actions visually and textually distinct.
- Pair errors with recovery and evidence locations.
- Preserve stable identifiers in machine-readable output.
- Respect reduced-motion and no-color contexts.

## Components and projections

Canonical patterns include command help, progress state, evidence table, decision card, plan preview, validation summary, architecture node, and recovery prompt. Concrete tokens and components are downstream projections maintained by the owning surface.

## Visual direction

The expression should remain compact, status-oriented, actionable, and consistent in logs and summaries while allowing product-specific identity to vary inside Ego Hygiene's broader family.

## Evidence and uncertainty

- **Observed:** The repository README establishes the intended boundary as the reusable GitHub Actions, workflows, automation components, and CI orchestration library for the organization; significant implementation remains incomplete.
- **Decided for this draft:** The repository owns the bounded concern described here and participates through versioned contracts.
- **Proposed:** Target systems and later roadmap phases remain proposals until accepted and implemented.
- **Open question:** Which parts of this draft should become active in the first independently versioned release?
