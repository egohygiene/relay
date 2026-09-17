# Artifact-size budget adoption

The reusable workflow consumes ordinary caller-produced artifacts. It never
checks out the consumer repository, installs its dependencies, or runs its
build. Replace every placeholder with a reviewed full commit SHA.

## JavaScript bundle comparison with Size Limit

The consumer pins Size Limit and its selected plugins in `package.json` and the
package-manager lockfile. Separate producer jobs build the pull-request and
trusted base revisions, preserve each `size-limit --json` result, and then hand
both artifacts to Relay.

```yaml
---
name: Bundle budget

on:
  pull_request:

permissions:
  contents: read

jobs:
  current_bundle:
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@<full-checkout-commit-sha>
        with:
          persist-credentials: false
      - uses: actions/setup-node@<full-setup-node-commit-sha>
        with:
          node-version-file: ".node-version"
          cache: "pnpm"
      - run: corepack enable
      - run: pnpm install --frozen-lockfile
      - run: pnpm run build
      - name: Produce project-pinned Size Limit JSON
        continue-on-error: true
        run: |
          mkdir -p ".relay"
          pnpm exec size-limit --json > ".relay/size-limit.json"
      - name: Preserve current measurement
        if: "${{ always() }}"
        uses: actions/upload-artifact@<full-upload-artifact-commit-sha>
        with:
          name: "size-limit-current-${{ github.sha }}"
          path: ".relay/size-limit.json"
          include-hidden-files: true
          if-no-files-found: error

  baseline_bundle:
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@<full-checkout-commit-sha>
        with:
          ref: "${{ github.event.pull_request.base.sha }}"
          persist-credentials: false
      - uses: actions/setup-node@<full-setup-node-commit-sha>
        with:
          node-version-file: ".node-version"
          cache: "pnpm"
      - run: corepack enable
      - run: pnpm install --frozen-lockfile
      - run: pnpm run build
      - name: Produce baseline Size Limit JSON
        continue-on-error: true
        run: |
          mkdir -p ".relay"
          pnpm exec size-limit --json > ".relay/size-limit.json"
      - name: Preserve baseline measurement
        if: "${{ always() }}"
        uses: actions/upload-artifact@<full-upload-artifact-commit-sha>
        with:
          name: "size-limit-baseline-${{ github.event.pull_request.base.sha }}"
          path: ".relay/size-limit.json"
          include-hidden-files: true
          if-no-files-found: error

  budget:
    needs: [current_bundle, baseline_bundle]
    permissions:
      contents: read
    uses: egohygiene/relay/.github/workflows/artifact-budget.yml@<full-relay-commit-sha>
    with:
      current-artifact-name: "size-limit-current-${{ github.sha }}"
      baseline-artifact-name: "size-limit-baseline-${{ github.event.pull_request.base.sha }}"
      artifact-path: "size-limit.json"
      baseline-artifact-path: "size-limit.json"
      adapter: "size-limit-json"
      artifact-kind: "javascript-bundle"
      subject: "web-bundles"
      current-revision: "${{ github.sha }}"
      baseline-revision: "${{ github.event.pull_request.base.sha }}"
      mode: "blocking"
      maximum-increase-percent: "5"
      artifact-retention-days: 30
```

Size Limit's own per-check `sizeLimit` and `passed` values remain authoritative
inputs. Relay adds the shared baseline delta and state contract. A budget
exceedance still produces JSON and a report artifact; a Size Limit execution
error produces an error object that Relay rejects as invalid evidence.

## Native or package archive

A non-JavaScript producer uploads its already-built archive. Relay measures the
raw archive bytes without interpreting language, package, or compression
semantics:

```yaml
jobs:
  build_archive:
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@<full-checkout-commit-sha>
        with:
          persist-credentials: false
      - run: task build:archive
      - uses: actions/upload-artifact@<full-upload-artifact-commit-sha>
        with:
          name: "linux-amd64-${{ github.sha }}"
          path: "dist/tool-linux-amd64.tar.gz"
          if-no-files-found: error

  archive_budget:
    needs: build_archive
    permissions:
      contents: read
    uses: egohygiene/relay/.github/workflows/artifact-budget.yml@<full-relay-commit-sha>
    with:
      current-artifact-name: "linux-amd64-${{ github.sha }}"
      artifact-path: "tool-linux-amd64.tar.gz"
      adapter: "filesystem"
      artifact-kind: "archive"
      subject: "linux-amd64"
      current-revision: "${{ github.sha }}"
      mode: "blocking"
      maximum-bytes: "52428800"
```

For regression enforcement, add a trusted baseline producer and pass the
matching artifact name, relative path, immutable revision, and delta budgets.
If a delta budget is configured without matching baseline evidence, Relay
reports `missing-baseline`; blocking mode fails closed.
