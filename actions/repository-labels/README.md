# Repository Label Automation

Plan and apply the label semantics owned by `egohygiene/.github` without
copying them into Relay. The action locks the exact merged organization
contract by commit and SHA-256, resolves the repository's canonical assignment,
and fails closed on drift, missing assignments, collisions, or incompatible
versions.

Relay owns execution only:

- deterministic label synchronization plans;
- checksum-bound, separately authorized apply;
- path and size label selection;
- first-contribution welcome planning;
- fork maintainer-edit checks;
- provider evidence and safe retry behavior.

The action never infers deletion from absence. A deletion must be named in
`sync.retire_labels`, appear in the reviewed plan, and receive the separate
`allow-deletions` apply input.

## Pull-request security model

Contributor pull requests use two workflows:

1. `pull-request-label-plan.yml` runs with read permissions, checks out only the
   trusted base SHA, reads changed-file metadata through the GitHub API, and
   uploads a checksum-bound plan. It never executes contributor code.
2. A consumer `workflow_run` invokes `pull-request-label-apply.yml`. The trusted
   stage verifies the producing workflow, repository, run-to-PR association,
   and candidate checksum; checks out the live base SHA; re-fetches all provider
   metadata; independently recomputes the plan; and requires an exact checksum
   match before granting bounded write access.

This design supports hostile forks without `pull_request_target`, secrets, or
write authority in the untrusted-event run. Only labels listed in the
repository configuration are managed; unrelated manually applied labels are
never removed.

## Repository configuration

Copy [`examples/label-automation/repository-labels.json`](../../examples/label-automation/repository-labels.json)
to `.github/relay-labels.json` and select only labels already present in the
canonical `.github` assignment for the repository. The example illustrates
configuration shape; its `size/*` labels must be added to that canonical
assignment before enabling size labeling.

Path rules use repository-relative glob patterns. Multiple matching rules add
multiple labels. `**/` also matches the repository root. Negation, absolute
paths, and parent traversal are intentionally unsupported.

Set `path_labels.preset` to `organization-v1` for Relay's conservative shared
mappings for documentation, automation, developer-experience, and security
paths. Those mappings use only universal labels from the canonical catalog.
Repository `rules` add overlay-specific mappings; a rule with the same label
replaces that shared label's paths, providing an explicit per-repository
override. Set the preset to `none` for a fully repository-owned mapping set.

When the configuration file is absent, pull-request planning emits an explicit
`not-configured` no-op rather than failing. Canonical label synchronization can
still operate because the organization assignment, not the repository file,
owns desired labels.

## Thin caller workflows

Plan and apply synchronization from explicit manual workflows. The apply call
must receive the exact SHA-256 exposed by the reviewed plan run:

```yaml
jobs:
  plan:
    permissions:
      contents: read
      issues: read
    uses: egohygiene/relay/.github/workflows/label-sync-plan.yml@<full-relay-commit-sha>
```

```yaml
jobs:
  apply:
    permissions:
      contents: read
      issues: write
    uses: egohygiene/relay/.github/workflows/label-sync-apply.yml@<full-relay-commit-sha>
    with:
      expected-plan-sha256: "<reviewed-plan-sha256>"
      allow-deletions: false
```

For pull requests, the caller plan workflow listens to `pull_request` and calls
the read-only planner. A second default-branch workflow listens to
`workflow_run` for the exact caller workflow name and calls the apply workflow:

```yaml
name: Pull Request Metadata Plan

on:
  pull_request:
    types: [opened, reopened, synchronize, ready_for_review]

permissions:
  contents: read

jobs:
  plan:
    permissions:
      contents: read
      issues: read
      pull-requests: read
    uses: egohygiene/relay/.github/workflows/pull-request-label-plan.yml@<full-relay-commit-sha>
```

```yaml
name: Pull Request Metadata Apply

on:
  workflow_run:
    workflows: ["Pull Request Metadata Plan"]
    types: [completed]

jobs:
  apply:
    permissions:
      actions: read
      contents: read
      issues: write
      pull-requests: write
    uses: egohygiene/relay/.github/workflows/pull-request-label-apply.yml@<full-relay-commit-sha>
    with:
      planner-workflow-name: "Pull Request Metadata Plan"
```

Production callers replace the placeholder with the reviewed full Relay commit
SHA and retain a human-readable release comment.

## Welcome and maintainer-edit behavior

Welcome comments are emitted only for `FIRST_TIMER` or
`FIRST_TIME_CONTRIBUTOR` authors, never for bots, and contain an idempotency
marker. Maintainer-edit checks apply only to forks and can warn or block.
Existing comments are checked both during planning and immediately before
write, so retries do not duplicate notices.

## Rollback

Revert the thin caller workflows or pin the preceding Relay commit. Label sync
rollback is additive by default: previously created labels remain until a new
explicit retirement plan is reviewed. Pull-request label changes are bounded
to configured managed labels; a fresh run reconciles them to the prior pinned
configuration without touching other labels.
