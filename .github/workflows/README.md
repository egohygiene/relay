# Reusable workflows

The complete current and internal workflow inventory lives in
[`workflow-catalog.json`](../../workflow-catalog.json); its security and caller
contract is explained in [`WORKFLOW_CATALOG.md`](../../WORKFLOW_CATALOG.md).

Relay workflows are opinionated orchestration layers over the smaller actions
in [`actions/`](../../actions/). The repository-intelligence workflow checks
out complete caller history, invokes the action from the exact called Relay
revision through GitHub's `$/` syntax, builds the routed site, and uploads it as
an ordinary workflow artifact.

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
