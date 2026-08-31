# Relay workflow catalog

[`workflow-catalog.json`](workflow-catalog.json) is the authoritative,
machine-readable inventory of Relay-owned GitHub workflows. Its checked-in
[JSON Schema](schemas/workflow-catalog.schema.json) closes the v1 vocabulary for
ownership, purpose, caller contracts, authority, runtime bounds, concurrency,
and failure semantics.

## Inventory snapshot

| Workflow | Audience | Owner | Purpose | Maximum authority | Timeout |
| --- | --- | --- | --- | --- | --- |
| `relay-validation` | Internal | `egohygiene/relay` | Validate packages, contracts, metadata, and the reusable smoke path | `actions: read`, `contents: read` | 15 minutes |
| `relay-release` | Internal | `egohygiene/relay` | Publish a verified immutable release and optional major alias | job-scoped `contents: write` | 20 minutes |
| `release-artifact` | Reusable | `egohygiene/relay` | Validate a profile-bound caller artifact and publish immutable release evidence | job-scoped `contents: write` | 15 minutes |
| `publication-review` | Reusable | `egohygiene/relay` | Validate and preserve exact caller-built publication bytes | `actions: read`, `contents: read` | 10 minutes |
| `publication-pages` | Reusable | `egohygiene/relay` | Deploy the exact read-only reviewed artifact and remotely prove it | job-scoped `pages: write` and `id-token: write` | 20 minutes |
| `repository-intelligence` | Reusable | `egohygiene/relay` | Build, verify, and upload one bounded intelligence artifact | `contents: read` | 15 minutes |
| `dependency-review` | Internal | `egohygiene/relay` | Analyse dependency changes on every pull request and fail on high-severity or denied-license packages | `contents: read` | 10 minutes |
| `automerge-dependabot` | Internal | `egohygiene/relay` | Classify then auto-approve and merge allowlisted low-risk Dependabot updates after all required checks | job-scoped `contents: write` and `pull-requests: write` | 5 minutes |

All eight files under `.github/workflows/` are current and cataloged.
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

Publication review and Pages runs never cancel in progress. The review workflow
has no Pages or OIDC authority and stores the exact accepted artifact. The
deployment-only workflow is callable only with explicit write permissions,
invokes review through a read-restricted nested call, and is authorized only for
a push or manual run on the configured default branch. It revalidates that
reviewed artifact before Pages receives it and fails closed on configuration,
provider, HTTPS, route, or byte-proof disagreement.

Release runs are serialized and never cancel in progress. A retry may resume a
partial provider-side release only when the immutable tag still points to the
same validated default-branch commit; contradictory state fails closed.

Dependency review runs cancel stale analysis on the same ref. Any
high-severity finding or denied-license package fails the workflow and blocks
the pull request. A fresh run on the corrected PR resolves the failure; there
is no partial-success state.

Automerge classification and approval runs never cancel in progress to avoid
orphaned approvals. The classify job skips non-Dependabot actors entirely. The
approve-and-merge job is skipped when the update does not meet the allowlist
policy. A failed merge attempt leaves the PR open for human review; no
partially-applied state exists because auto-merge is a GitHub-side setting that
only activates after all required checks pass.

**Emergency disable**: remove the `automerge-dependabot` workflow file or set
`if: false` on the `approve-and-merge` job to immediately stop automated
merges without affecting dependency-review analysis. Disable
`dependency-review` by removing that workflow file; existing open PRs will
lose the blocking check until a fresh commit re-triggers the workflow.

**Rollback**: revert the workflow file to a previous cataloged revision and
push to the default branch. The prior behavior takes effect on the next
pull-request event. No provider-side state accumulates.

## Reusable caller contract

`repository-intelligence`, `publication-review`, `publication-pages`, and
`release-artifact` are the
reusable workflows in v1. Their inputs, defaults, outputs, permission ceilings,
timeouts, concurrency keys, and failure semantics are recorded in the catalog
and checked against their workflow sources.

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
