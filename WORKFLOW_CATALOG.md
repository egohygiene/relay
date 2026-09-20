# Relay workflow catalog

[`workflow-catalog.json`](workflow-catalog.json) is the authoritative,
machine-readable inventory of Relay-owned GitHub workflows. Its checked-in
[JSON Schema](schemas/workflow-catalog.schema.json) closes the v1 vocabulary for
ownership, purpose, caller contracts, authority, runtime bounds, concurrency,
and failure semantics.

## Inventory snapshot

| Workflow | Audience | Owner | Purpose | Maximum authority | Timeout |
| --- | --- | --- | --- | --- | --- |
| `artifact-budget` | Reusable | `egohygiene/relay` | Normalize caller-produced artifact size evidence and enforce advisory or blocking budgets | `contents: read` | 10 minutes |
| `relay-validation` | Internal | `egohygiene/relay` | Validate packages, contracts, metadata, and the reusable smoke path | `actions: read`, `contents: read` | 15 minutes |
| `relay-release` | Internal | `egohygiene/relay` | Dogfood the reviewed semantic-release handoff | job-scoped `contents: write` | 15 minutes |
| `release-artifact` | Reusable | `egohygiene/relay` | Validate a profile-bound caller artifact and publish immutable release evidence | job-scoped `contents: write` | 15 minutes |
| `release-prepare` | Reusable | `egohygiene/relay` | Plan or verify Aether-declared release intent and retain evidence | `actions: read`, `contents: read` | 10 minutes |
| `semantic-release` | Reusable | `egohygiene/relay` | Verify a prepared candidate and hand off exact immutable publication | job-scoped `contents: write` | 5 minutes |
| `publication-review` | Reusable | `egohygiene/relay` | Validate and preserve exact caller-built publication bytes | `actions: read`, `contents: read` | 10 minutes |
| `publication-pages` | Reusable | `egohygiene/relay` | Deploy the exact read-only reviewed artifact and remotely prove it | job-scoped `pages: write` and `id-token: write` | 20 minutes |
| `repository-intelligence` | Reusable | `egohygiene/relay` | Build, verify, and upload one bounded intelligence artifact | `contents: read` | 15 minutes |
| `repository-journal` | Reusable | `egohygiene/relay` | Render validated deterministic or reviewed-manual journal evidence without AI billing | `actions: read`, provider metadata reads | 10 minutes |
| `repository-journal-copilot` | Reusable | `egohygiene/relay` | Generate one no-tool candidate behind explicit account preflight | read permissions plus job-scoped `copilot-requests: write` | 10 minutes |
| `repository-journal-dogfood` | Internal | `egohygiene/relay` | Schedule and manually dispatch Relay's deterministic no-billing canary | read-only provider metadata | reusable caller |
| `label-sync-plan` | Reusable | `egohygiene/relay` | Preview canonical label synchronization | `contents: read`, `issues: read` | 10 minutes |
| `label-sync-apply` | Reusable | `egohygiene/relay` | Recompute and apply an approved label plan | job-scoped `issues: write` | 10 minutes |
| `pull-request-label-plan` | Reusable | `egohygiene/relay` | Plan PR labels and contributor checks without executing PR code | `contents: read`, `issues: read`, `pull-requests: read` | 10 minutes |
| `pull-request-label-apply` | Reusable | `egohygiene/relay` | Validate the trusted plan handoff and apply managed metadata | job-scoped `issues: write` and `pull-requests: write` | 10 minutes |
| `stale-pull-requests` | Reusable | `egohygiene/relay` | Plan inactivity and exemptions, then optionally apply a warning-first stale lifecycle | conditional read-only plan; `pull-requests: write` apply, plus `issues: write` only when issues are opted in | 10 minutes |
| `dependency-review` | Internal | `egohygiene/relay` | Analyse dependency changes on every pull request and fail on high-severity or denied-license packages | `contents: read` | 10 minutes |
| `automerge-dependabot` | Internal | `egohygiene/relay` | Classify then auto-approve and merge allowlisted low-risk Dependabot updates after all required checks | job-scoped `contents: write` and `pull-requests: write` | 5 minutes |

Every executable workflow file under `.github/workflows/` is current and
cataloged; an uncataloged workflow fails CI.

## Legacy candidates

Historical workflows enter Relay through the
[legacy workflow quarantine and graduation policy](docs/legacy-workflow-lifecycle.md).
Candidate bytes remain disabled outside `.github/workflows/` and absent from
both machine-readable catalogs. Manual-only triggers and `experimental` catalog
status are not quarantine: both describe executable automation. A normalized
implementation enters the catalogs only when its permissions, contract,
failure behavior, isolated tests, documentation, and release path are ready for
review together.

## Security contract

- Workflow defaults grant only `contents: read`.
- Repository and deployment write permissions are job-scoped and purpose-bound.
- Copilot request permission exists only in the separately callable Copilot
  journal workflow; the default journal and dogfood schedule cannot receive it.
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

Label synchronization separates review from mutation. The planning workflow
reads the canonical `.github` contract and current repository labels; the apply
workflow recomputes the same plan from live state and requires its exact reviewed
checksum. Unmanaged labels are preserved, and deletion is impossible unless the
configuration explicitly retires a label and the caller grants deletion authority.

Pull-request metadata uses a two-workflow trust boundary. The `pull_request`
planner checks out only the trusted base revision, reads provider metadata, and
uploads a checksum-bound plan with no write permission. A caller-owned
`workflow_run` wrapper invokes the apply workflow, which verifies the triggering
workflow identity, event, run, repository, artifact count, and live head/base SHAs
before writing. Neither stage uses `pull_request_target` or executes contributor
code with a token.

Stale pull-request management uses a read/plan/apply boundary inside one
non-cancelling reusable workflow. Its advisory default runs exactly one of two
statically scoped read-only plan jobs and preserves a checksum-bound artifact
plus bounded summary. The pull-request-only path has no Issues permission. Only
`process-issues: true` selects the alternate plan and apply jobs that add Issues
authority. The matching conditional apply job must receive explicit caller
write authority, consumes that exact artifact, and revalidates live item state
before changing labels, posting comments, or closing. A failure reports no
successful result; a fresh run converges earlier open-item idempotent mutations.
GitHub does not provide a transaction across multiple items, so the catalog
declares bounded partial success: an earlier item may already be updated when a
later provider call fails, while that run still fails overall. Fresh runs
reconcile open warnings and resets. If optional metadata fails after the
provider has already closed an item, a maintainer reviews that closed item or
reopens it; open-item scans do not pretend that post-close metadata was repaired.

Closure requires the configured stale label and Relay's trusted visible warning
marker from an earlier run. A manually added label, missing marker, incomplete
warning window, later activity, exemption, or reopen event cannot authorize
closure. A partial warning that applied only the label is repaired with a
visible warning on the next run and still cannot close. Issues are excluded by
default and enter the same explicit lifecycle only through `process-issues`.
The Lucide workflow and `actions/stale` v11 informed the lifecycle vocabulary
but are not runtime dependencies: the reference has divergent message/timing
settings and disabled closure, while the upstream action does not expose the
author/team exemptions or bounded candidate/exemption evidence required here.
The exact marker author is GitHub's repository-wide `github-actions[bot]`
identity, so every workflow with `issues: write` or `pull-requests: write` is
inside this trust boundary; the marker does not claim unique workflow-file
identity.

Artifact-budget evaluation consumes only caller-produced Actions artifacts.
The workflow does not check out or execute consumer code: JavaScript callers
run their own pinned Size Limit installation and upload its JSON, while static
sites, native binaries, archives, and container-image archives use bounded raw
filesystem measurement. Missing baselines and unsupported runtime-only Size
Limit checks remain explicit report states. Blocking mode uploads the completed
report before failing; advisory mode preserves the same evidence without
granting mutation authority.

Repository-journal generation separates deterministic provider evidence from
non-authoritative candidate prose and deterministic rendering. The default
reusable workflow supports deterministic, reviewed-manual, and intentionally
unavailable modes with read-only provider permissions and no AI account or
billing dependency. Each candidate statement cites an exact normalized record
ID; Relay validates identity, interval, bounds, references, and safe text, then
retains the candidate beside its evidence. Manual validation establishes that
provenance boundary but does not claim semantic proof of free-form prose.

The separately callable Copilot workflow is the only journal surface with
`copilot-requests: write`. It checks a checksum-bound, secret-free account
preflight before at most one no-tool invocation. Unknown policy, permission,
billing, credential, or runtime state makes no request and yields an explicit
unavailable result. Provider truncation or unavailability remains partial or
unavailable evidence; invalid input or rendering preserves bounded failure
evidence before the job fails. Neither path checks out consumer code, mutates a
repository, or owns an external delivery sink.

**Emergency disable**: remove the `automerge-dependabot` workflow file or set
`if: false` on the `approve-and-merge` job to immediately stop automated
merges without affecting dependency-review analysis. Disable
`dependency-review` by removing that workflow file; existing open PRs will
lose the blocking check until a fresh commit re-triggers the workflow.

**Rollback**: revert the workflow file to a previous cataloged revision and
push to the default branch. The prior behavior takes effect on the next
pull-request event. No provider-side state accumulates.

**Stale lifecycle emergency disable**: remove or disable the consumer-owned
schedule, or return its call to `advisory: true`. Existing labels and closed
items remain visible provider state. Maintainers may remove lifecycle labels or
reopen an item; a later enforcing run treats that activity as recovery rather
than closure authority.

## Reusable caller contract

`artifact-budget`, `repository-intelligence`, `repository-journal`,
`repository-journal-copilot`, `publication-review`, `publication-pages`,
`release-artifact`, `release-prepare`, `semantic-release`, `label-sync-plan`,
`label-sync-apply`, `pull-request-label-plan`, `pull-request-label-apply`, and
`stale-pull-requests` are the reusable workflows in v1. Their inputs, defaults,
outputs, permission ceilings,
timeouts, concurrency keys, and failure semantics are recorded in the catalog
and checked against their workflow sources.

`release-prepare` is statically read-only and can run for pull-request review or
manual planning. `semantic-release` is the default-branch-only write handoff:
it consumes exact preparation and profile evidence before delegating to
`release-artifact`. Registry and deployment adapters remain consumer-owned.

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
