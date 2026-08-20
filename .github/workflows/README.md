# Reusable workflows

Relay workflows are opinionated orchestration layers over the smaller actions
in [`actions/`](../../actions/). The repository-intelligence workflow checks
out complete caller history, invokes the action from the exact called Relay
revision through GitHub's `$/` syntax, builds the dashboard, and uploads it as
an ordinary workflow artifact.

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

Use the composite action directly when the dashboard must be composed into an
existing Pages build. Workflow artifacts live in another job and cannot mutate
the caller's site directory:

```yaml
- name: Add repository intelligence to the site build
  # egohygiene/relay repository-intelligence v1.1.0
  uses: egohygiene/relay/actions/repository-intelligence@<full-commit-sha>
  with:
    output-directory: dist/intelligence
```

Production callers pin the full Relay commit SHA. The moving `v1` alias is a
discovery and controlled-update target, not an immutable consumer reference.
