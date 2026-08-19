---
schema: aether.architecture-document/v1
id: relay-ontology
title: Relay Ontology
kind: architecture-document
version: 0.1.0
status: provisional
owners:
  - egohygiene
created: 2026-08-19
updated: 2026-08-19
governed_by:
  - architecture-ontology
depends_on:
  - relay-purpose
  - relay-vision
  - relay-principles
  - relay-epistemology
related:
  - relay-pillars
  - relay-manifesto
  - relay-ai-constitution
  - relay-personal-model
supersedes: []
---

# Relay Ontology

## Domain scope

Relay models the concepts needed for package repeatable automation behavior so repository templates can compose stable actions instead of copying workflow implementation. The ontology names conceptual entities and relationships; it is not a source-code class model, API schema, or database design.

## Canonical concepts

| Concept | Meaning |
| --- | --- |
| Action | A canonical concept in the Relay domain whose exact fields belong to specifications or schemas, not this ontology. |
| Reusable workflow | A canonical concept in the Relay domain whose exact fields belong to specifications or schemas, not this ontology. |
| Input | A canonical concept in the Relay domain whose exact fields belong to specifications or schemas, not this ontology. |
| Output | A canonical concept in the Relay domain whose exact fields belong to specifications or schemas, not this ontology. |
| Permission | A canonical concept in the Relay domain whose exact fields belong to specifications or schemas, not this ontology. |
| Runner | A canonical concept in the Relay domain whose exact fields belong to specifications or schemas, not this ontology. |
| Artifact | A canonical concept in the Relay domain whose exact fields belong to specifications or schemas, not this ontology. |
| Job summary | A canonical concept in the Relay domain whose exact fields belong to specifications or schemas, not this ontology. |
| Version pin | A canonical concept in the Relay domain whose exact fields belong to specifications or schemas, not this ontology. |
| Consumer | A canonical concept in the Relay domain whose exact fields belong to specifications or schemas, not this ontology. |

## Core relationships

- A repository or person provides source context to one or more domain artifacts.
- A specification constrains how an artifact is interpreted or produced.
- A plan separates proposed action from execution.
- Evidence supports a claim; a decision authorizes a durable direction.
- Provenance connects derived artifacts to their inputs and processing context.
- A consumer integrates through an explicit interface rather than internal structure.

## Boundaries

- Conceptual identity is distinct from filesystem path, database identifier, or display label.
- Observed state is distinct from desired state.
- Proposed relationships are not accepted facts.
- Neighboring repositories retain ownership of their domain concepts.

## Evidence and uncertainty

- **Observed:** The repository README establishes the intended boundary as the reusable GitHub Actions, workflows, automation components, and CI orchestration library for the organization; significant implementation remains incomplete.
- **Decided for this draft:** The repository owns the bounded concern described here and participates through versioned contracts.
- **Proposed:** Target systems and later roadmap phases remain proposals until accepted and implemented.
- **Open question:** Which parts of this draft should become active in the first independently versioned release?
