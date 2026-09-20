# Repository architecture validation contract

Relay issue [#5](https://github.com/egohygiene/relay/issues/5) is delivered
through the ordered checkpoints in
[#99](https://github.com/egohygiene/relay/issues/99). This document describes
checkpoint 1: the versioned boundary that later local and CI adapters must
implement. It does not introduce an action or reusable workflow.

## Responsibility boundary

Relay orchestrates validators and normalizes bounded evidence. It does not
become the authority for organization policy, validation semantics, consumer
architecture records, or materialization.

| Concern | Authority | Checkpoint 1 treatment |
| --- | --- | --- |
| Organization architecture policy | Hygiene | Pinned input only |
| Repository and ADR validation semantics | EgoLint | Pinned input only |
| Architecture-decision scaffolding | Holon | Pinned input only |
| Consumer records and diagrams | Consumer repository | Read-only input |
| Orchestration and normalized evidence | Relay | Versioned contract |
| Fleet rollout | Pace | Outside this task |
| Aggregated read models | Observatory | Outside this task |

The profile operationalizes ADR-001, ADR-002, ADR-003, ADR-005, and ADR-006.
It does not change ownership, so it requires no new architecture decision.

## Immutable source profile

[`catalog/repository-architecture-validation.json`](../catalog/repository-architecture-validation.json)
binds the reviewed source artifacts by full commit SHA and SHA-256 digest:

| Source | Revision | Lifecycle |
| --- | --- | --- |
| `egohygiene/hygiene` | `c589587395750cd1c79c6fa0bef010189c547249` | Accepted policy, not release-included |
| `egohygiene/egolint` | `8b99ec4377eb84044fac411dff6b8074317ec094` | Proposed validator, not release-included |
| `egohygiene/holon` | `660b941f99618806fcadd589bcdae61c519f96e4` | Accepted materializer, not release-included |

Repository-contract and architecture-record validation are available through
EgoLint rule families. Diagram discovery and evidence remain explicitly
`planned`: none of the reviewed upstream sources owns a released diagram
semantic validator, so Relay must not fabricate one.

Because the complete source set is not released, the profile is `proposed`,
defaults to `advisory`, and caps activation at `advisory`. A future required
mode needs all three recorded gates: an immutable EgoLint release, a reviewed
adapter/workflow fixture matrix, and explicit consumer opt-in.
The checked-in required-mode fixture exercises that future contract shape; it
does not activate required enforcement in this checkpoint.

## Request and result seam

The request contract records:

- repository identity, visibility, and represented revision;
- explicit adoption state for repository contracts, architecture records, and
  diagram sources;
- bounded repository-relative input paths;
- advisory or required intent;
- file, byte, and finding ceilings; and
- one JSON output path under `.reports/architecture-validation/`.

The result contract records:

- semantic status separately from execution outcome;
- per-surface coverage, including `partial`, `unavailable`, and
  `not-applicable`;
- all three exact upstream revisions;
- bounded diagnostics and exact retained-finding counts;
- scan and truncation evidence;
- repository-relative report paths; and
- a visibility-matched privacy classification.

An unavailable validator produces an explicit unavailable result. Missing,
partial, legacy, or truncated evidence cannot silently become conformance.
Advisory mode reports nonconformance without blocking; required mode may fail
only after its release and opt-in gates are satisfied.

## Execution and information safety

Future adapters are constrained by the profile even though checkpoint 1 does
not execute them:

- Network access is denied after explicit dependency acquisition.
- Consumer code is never executed.
- Consumer semantic records are never authored or rewritten.
- Writes are limited to temporary work and `.reports/` output.
- Stage, commit, push, pull-request, comment, merge, release, deploy, and
  publish authority are forbidden.
- Evidence excludes secrets, credentials, environment values, provider tokens,
  workflow logs, absolute local paths, raw source content, and private
  cross-repository content.

Repository text is untrusted data. It cannot grant authority or change the
validation plan.

## Validation

Validate the profile, schemas, and publish-safe fixture corpus offline:

```bash
python3 scripts/validate_repository_architecture_contract.py validate
```

Maintainers can separately verify the pinned bytes against already-acquired
local checkouts. This command performs no network access and does not run code
from those repositories:

```bash
python3 scripts/validate_repository_architecture_contract.py verify-sources \
  --hygiene-source /path/to/hygiene \
  --egolint-source /path/to/egolint \
  --holon-source /path/to/holon
```

The checked-in fixture corpus covers present, legacy, unknown, conformant,
nonconformant, and unavailable states across public, private, and internal
repositories. Mutation tests reject mutable revisions, ownership drift,
invented diagram semantics, path traversal, contradictory adoption evidence,
unsafe bounds, source-content leakage, and result-count contradictions.

## Next checkpoints

Checkpoint 2 implements the offline adapter against this seam. Later
checkpoints add honest diagram evidence, reusable workflow orchestration,
consumer fixtures and dogfood, then immutable release and live adoption proof.
Until those checkpoints land, this contract is a reviewed design boundary—not
a released or callable validation capability.
