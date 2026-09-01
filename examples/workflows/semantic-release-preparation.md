# Semantic-release preparation caller

A consumer exposes its own event policy and pins Relay by full commit SHA. The
same read-only caller may run for pull-request review or explicit manual
planning; it never grants write permission.

```yaml
name: Review release preparation

on:
  pull_request:
    paths:
      - ".egohygiene/release.json"
      - "CHANGELOG.md"
      - "release.json"
  workflow_dispatch:
    inputs:
      version:
        required: true
        type: string

permissions:
  contents: read

jobs:
  plan:
    permissions:
      actions: read
      contents: read
    uses: egohygiene/relay/.github/workflows/release-prepare.yml@<full-relay-commit-sha>
    with:
      release-version: "${{ inputs.version }}"
      profile: "github-action"
      component-id: "example"
      expected-source-revision: "${{ github.sha }}"
      mode: "plan"
```

For a prepared default-branch candidate, the repository first uploads its
complete profile bundle and changes `mode` to `verify` with `artifact-name`.
Publication remains a separate manual workflow calling `semantic-release.yml`.
