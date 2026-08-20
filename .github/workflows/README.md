# Reusable workflows

Relay workflows are opinionated orchestration layers over the smaller actions
in [`actions/`](../../actions/). The repository-intelligence workflow checks
out complete caller history, invokes the action from the exact called Relay
revision through GitHub's `$/` syntax, builds the dashboard, and uploads it as
an ordinary workflow artifact.

```yaml
jobs:
  intelligence:
    uses: egohygiene/relay/.github/workflows/repository-intelligence.yml@v1
    with:
      default-branch: main
```

Use the composite action directly when the dashboard must be composed into an
existing Pages build. Workflow artifacts live in another job and cannot mutate
the caller's site directory:

```yaml
- uses: egohygiene/relay/actions/repository-intelligence@<full-commit-sha>
  with:
    output-directory: dist/intelligence
```
