---
schema: aether.architecture-document/v1
id: relay-epistemology
title: Relay Epistemology
kind: architecture-document
version: 0.1.0
status: provisional
owners:
  - egohygiene
created: 2026-08-19
updated: 2026-08-19
governed_by:
  - architecture-epistemology
depends_on:
  - relay-purpose
  - relay-principles
related:
  - relay-vision
  - relay-pillars
  - relay-manifesto
  - relay-ai-constitution
supersedes: []
---

# Relay Epistemology

## Scope

This document governs how Relay classifies claims, evidence, provenance, confidence, conflict, and revision. It does not dictate which technical conclusion must be accepted.

## Claim states

| State | Meaning |
| --- | --- |
| Observed | Directly supported by repository or runtime evidence |
| Decided | Accepted through the repository governance process |
| Inferred | Reasoned from evidence but not directly observed |
| Proposed | Recommended future direction not yet accepted |
| Assumed | Necessary working premise awaiting evidence |
| Unverified | Plausible claim that has not been checked |
| Open question | A known gap requiring investigation or choice |

## Evidence order

1. Reproducible tests, schemas, generated artifacts, and runtime observations.
2. Accepted decisions and versioned specifications.
3. Current source and configuration.
4. Maintainer documentation and issue history.
5. Inference and recommendation, labeled with uncertainty.

## Provenance and conflict

Claims should identify their source closely enough to be rechecked. Conflicting evidence remains visible until the canonical owner resolves it; recency alone does not automatically establish truth.

## Revision

Material claims are revised when stronger evidence appears, their source changes, or an accepted decision supersedes them. Historical decision context is preserved rather than rewritten.

## Evidence and uncertainty

- **Observed:** The repository README establishes the intended boundary as the reusable GitHub Actions, workflows, automation components, and CI orchestration library for the organization; significant implementation remains incomplete.
- **Decided for this draft:** The repository owns the bounded concern described here and participates through versioned contracts.
- **Proposed:** Target systems and later roadmap phases remain proposals until accepted and implemented.
- **Open question:** Which parts of this draft should become active in the first independently versioned release?
