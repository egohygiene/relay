# Reusable workflows

The complete current and internal workflow inventory lives in
[`workflow-catalog.json`](../../workflow-catalog.json); its security and caller
contract is explained in [`WORKFLOW_CATALOG.md`](../../WORKFLOW_CATALOG.md).

Relay workflows are opinionated orchestration layers over the smaller actions
in [`actions/`](../../actions/). The repository-intelligence workflow checks
out complete caller history, invokes the action from the exact called Relay
revision through GitHub's `$/` syntax, builds the routed site, and uploads it as
an ordinary workflow artifact.

The continuity preflight checks out the exact caller candidate without
credentials, acquires the pinned EgoLint source and checksum-locked Cargo
dependencies, then runs the shared adapter offline. It emits at most twenty
privacy-safe annotations and one retention-governed result artifact. Cancelled
or retried runs have no repository effects; missing history, unsupported
contracts, and unavailable validation remain explicit, while private output
stays allowlisted.

## Default branch compatibility

`main` remains the preferred default branch for new Ego Hygiene repositories,
but Relay reusable workflows are compatible with consumers whose configured
default branch is `master`.

For normal GitHub-hosted reusable workflow and composite-action calls, omit the
`default-branch` input and allow Relay to use
`github.event.repository.default_branch`. The explicit input is for local,
synthetic, or otherwise metadata-limited contexts; Repository Intelligence uses
`main` only as its final conventional fallback when neither source is available.
A pull-request head, fork branch, release branch, or other current ref must not
be treated as evidence of the repository's default branch.

When GitHub requires a static conventional-primary-branch trigger, support both
names at the trigger boundary:

```yaml
on:
  push:
    branches:
      - main
      - master
```

That compatibility list is not a deployment authorization. Workflows that may
publish releases or deployments must still gate execution against the
repository's configured default branch, for example:

```yaml
if: "${{ github.ref_name == github.event.repository.default_branch }}"
```

If a workflow intentionally targets a different release or deployment branch,
configure that branch explicitly instead of adding `main` and `master`.
Repositories that still use `master` may migrate their actual default branch to
`main` as a separate governance change; Relay compatibility does not perform or
require that migration.

```yaml
jobs:
  intelligence:
    # egohygiene/relay repository-intelligence v1.1.0
    uses: egohygiene/relay/.github/workflows/repository-intelligence.yml@<full-commit-sha>
```

The workflow uploads exactly the validated generated subtree as a regular
Actions artifact. Its provenance classifies GitHub-public repositories as
`public-safe` and all other visibility states as `internal-only`. It never
deploys Pages and never uploads the private work directory. The caller may
override retention, output layout, or canonical input settings, but the
defaults require no configuration.

When an Observatory materialization is already present in the checkout, pass
its repository-relative path through `observatory-snapshot`. Relay requires the
read model to match both the caller repository and represented commit. Without
that input, `/now/` remains useful as a truthful shell and displays operational
state as unavailable rather than deriving it from unrelated metrics.

Use the composite action directly when the dashboard must be composed into an
existing Pages build. Workflow artifacts live in another job and cannot mutate
the caller's site directory:

```yaml
- name: Add repository intelligence to the site build
  # egohygiene/relay repository-intelligence v1.1.0
  uses: egohygiene/relay/actions/repository-intelligence@<full-commit-sha>
  with:
    output-directory: dist/intelligence
    observatory-snapshot: .cache/observatory/repository-intelligence.json
```

Production callers pin the full Relay commit SHA. The moving `v1` alias is a
discovery and controlled-update target, not an immutable consumer reference.
See the [complete pinned caller](../../examples/workflows/repository-intelligence.yml)
for an adoption-ready workflow.

## Semantic release

`release-prepare.yml` is the read-only entry point for Aether-declared release
planning and verification. It preserves success or failure evidence and has no
tag, release, registry, or deployment authority. `semantic-release.yml` is the
separate default-branch publication handoff: it reuses preparation in `verify`
mode, then passes the exact caller-built bundle to `release-artifact.yml`.

Consumer repositories own the manual-dispatch wrapper, artifact construction,
and every external registry or deployment adapter. Ordinary pull requests call
only the preparation workflow; they cannot reach the write-capable handoff.

## Publication review and Pages deployment

`publication-review.yml` accepts an ordinary artifact containing a complete,
caller-built static publication site. It never checks out the caller repository
or invokes a renderer. Under a static `actions: read` and `contents: read`
ceiling, it validates the `beacon.publication-hub/v1` catalog and complete
checksum inventory, then uploads the exact reviewed bytes under a unique
artifact name.

`publication-pages.yml` is a separate deployment-only surface. The request must
be a push or manual run on the caller's configured default branch. It invokes
the review workflow with read-only permissions, then a job with scoped
`pages: write` and `id-token: write` downloads only that reviewed artifact,
revalidates its tree digest, checks all remote-proof inputs before Pages receives
the bytes, deploys through `github-pages`, and verifies every file and route.

Both workflows use non-cancelling concurrency so a nested review cannot collide
with deployment and a newer run cannot interrupt a provider mutation.
Pull-request review and default-branch deployment use separate caller jobs with
static permissions; see the
[Antidote](../../examples/workflows/publication-pages-antidote.md) and
[Reflector](../../examples/workflows/publication-pages-reflector.md) examples.
Production consumers pin the full v1.3.0 Relay commit. Refs #38.

## Stale pull-request lifecycle

`stale-pull-requests.yml` is caller-scheduled and advisory by default. Exactly
one conditional plan job reads provider metadata, applies explicit exemptions,
and uploads one checksum-bound lifecycle plan. The default pull-request-only
path has no Issues permission; the issue-enabled path exists only when
`process-issues: true`. Neither path checks out or executes consumer code. The
matching apply job is separately gated by `advisory: false`, downloads that
exact plan, revalidates live state, and holds the only label, comment, and close
authority. Its Issues write permission is likewise absent from the default
pull-request-only path.

No item can close on its first eligible run. Relay first applies the configured
stale label and posts a visible warning with a versioned marker. A later run may
close only if the complete warning window has elapsed, the marker and label are
still present, closure is explicitly enabled, and provider activity has not
advanced. Activity and reopen events instead clear Relay lifecycle labels.
Issues remain outside the scan unless `process-issues: true` is explicitly set.

The consumer owns the schedule, label creation, permission ceiling, and mode.
The apply job also rejects any request not running from the configured default
branch.
Start with the [read-only caller](../../examples/workflows/stale-pull-requests.md),
review the bounded plan, and grant write authority only when warnings or closure
are intentionally enabled.
