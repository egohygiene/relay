# Relay workflow catalog

[`workflow-catalog.json`](workflow-catalog.json) is the authoritative,
machine-readable inventory of Relay-owned GitHub workflows. Its checked-in
[JSON Schema](schemas/workflow-catalog.schema.json) closes the v1 vocabulary for
ownership, purpose, caller contracts, authority, runtime bounds, concurrency,
and failure semantics.

## Inventory snapshot

| Workflow | Audience | Owner | Purpose | Maximum authority | Timeout |
| --- | --- | --- | --- | --- | --- |
| `relay-validation` | Internal | `egohygiene/relay` | Validate packages, contracts, metadata, and the reusable smoke path | `contents: read` | 15 minutes |
| `relay-release` | Internal | `egohygiene/relay` | Publish a verified immutable release and optional major alias | job-scoped `contents: write` | 20 minutes |
| `publication-pages` | Reusable | `egohygiene/relay` | Review, conditionally deploy, and remotely prove caller-built publication bytes | review: read-only; deploy: job-scoped `pages: write` and `id-token: write` | 20 minutes |
| `repository-intelligence` | Reusable | `egohygiene/relay` | Build, verify, and upload one bounded intelligence artifact | `contents: read` | 15 minutes |

There are no staged workflow implementations in this repository at this
snapshot. All four files under `.github/workflows/` are current and cataloged.
A future staged candidate must first receive an owner, purpose, explicit
contract, and `experimental` catalog state; an uncataloged workflow fails CI.

## Security contract

- Workflow defaults grant only `contents: read`.
- Write permission is job-scoped and bound to release or Pages deployment.
- `write-all` and `pull_request_target` are prohibited.
- Every remote action or reusable workflow is pinned to a full 40-character
  commit SHA. The human-readable release remains in an adjacent comment.
- Relay-local calls from a reusable workflow use `$/`, which resolves the
  implementation from the exact called Relay revision instead of the caller's
  checkout.
- Every job that selects a runner declares a timeout.
- Concurrency and cancellation behavior are explicit and cataloged.

The catalog records maximum workflow authority. For example, release defaults
to `contents: read` and grants `contents: write` only to its single publishing
job, so validation changes cannot silently inherit write access.

## Failure contract

Validation and artifact workflows fail closed: they publish no successful
result when validation, provenance, output existence, or upload fails. A newer
run on the same validation or intelligence ref cancels stale work.

Publication Pages runs never cancel in progress. Every call performs a
read-only review and stores the exact reviewed artifact. Deployment is a
separate job authorized only for a push or manual run on the configured default
branch. It revalidates that reviewed artifact before Pages receives it and fails
closed on configuration, provider, HTTPS, route, or byte-proof disagreement.

Release runs are serialized and never cancel in progress. A retry may resume a
partial provider-side release only when the immutable tag still points to the
same validated default-branch commit; contradictory state fails closed.

## Reusable caller contract

`repository-intelligence` and `publication-pages` are the reusable workflows in
v1. Their inputs, defaults, outputs, permission ceilings, timeouts, concurrency
keys, and failure semantics are recorded in the catalog and checked against
their workflow sources.

Production callers pin an immutable Relay commit. See the
[complete adoption example](examples/workflows/repository-intelligence.yml) and
[example guidance](examples/workflows/README.md). Publication consumers use
separate static-permission review and deployment calls; the Antidote and
Reflector patterns remain migration documentation until v1.3.0 is released and
the product repositories pin it. Refs #38.

## Versioning

Relay releases its complete action and workflow surface as one repository unit:

- exact `vMAJOR.MINOR.PATCH` tags are immutable;
- the matching `vMAJOR` alias is a moving discovery target;
- production callers use a reviewed full commit SHA;
- additive catalog fields require a new schema version when they cannot remain
  compatible with `egohygiene.relay-workflow-catalog/v1`.

Pace may consume this catalog to compare desired workflow identities and pins,
but Relay remains the source of truth for workflow behavior and contracts.
