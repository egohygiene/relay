# Repository Intelligence consumer deployment provenance

This reference keeps site composition and Pages deployment in the consumer
repository. Replace every placeholder with a reviewed immutable action commit,
the consumer's canonical URL, and the rollback point from its last accepted
deployment receipt.

Before adopting a generator revision, prove identical complete bundles in
differently named full-history checkouts with the same canonical `owner/name`,
consumer/generator revisions, evidence bytes, and declared inputs. A corrected
generator can change old digests; preserve historical rollback pins and their
recorded environment constraints. Review corrected adoption and a new rollback
point separately.

Use the [publication evidence procedure](../../docs/repository-intelligence-publication.md#acceptance-evidence-by-stage)
to distinguish build, ordinary artifact upload, Pages upload, deployment, receipt,
and live verification. Changes to this example's job dependencies or
skip/failure/cancellation gates need a GitHub-executed read-only no-op scheduler
fixture, including skipped ancestors and denied PR/unsuccessful prerequisites.
That fixture must not deploy, upload Pages artifacts, use secrets or write
permissions, or enter a protected environment. A green run with required stages
skipped is insufficient. Keep deferred-acceptance PRs reference-only (`Refs #N`).

```yaml
---
name: Repository Intelligence Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    permissions:
      contents: read
    steps:
      - name: Checkout complete consumer history
        uses: actions/checkout@<full-actions-checkout-sha>
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Build consumer-owned site
        run: pnpm run build

      - name: Capture unrelated consumer routes
        # egohygiene/relay repository-intelligence-deployment-provenance v1.6.0
        uses: egohygiene/relay/actions/repository-intelligence-deployment-provenance@<full-relay-sha>
        with:
          operation: capture-baseline
          consumer-revision: "${{ github.sha }}"

      - name: Build deterministic Repository Intelligence subtree
        # egohygiene/relay repository-intelligence v1.6.0
        uses: egohygiene/relay/actions/repository-intelligence@<same-full-relay-sha>
        with:
          output-directory: dist/intelligence

      - name: Create consumer-owned redirect aliases
        run: pnpm run build:intelligence-aliases

      - name: Verify composition before deployment
        uses: egohygiene/relay/actions/repository-intelligence-deployment-provenance@<same-full-relay-sha>
        with:
          operation: verify-composition
          consumer-revision: "${{ github.sha }}"
          relay-revision: "<same-full-relay-sha>"
          required-routes: >-
            ["/","/intelligence/","/intelligence/now/","/intelligence/roadmap/",
            "/intelligence/decisions/","/intelligence/journey/"]
          aliases: >-
            [{"route":"/health/","target":"/intelligence/health/"},
            {"route":"/search/","target":"/intelligence/search/"}]

      - name: Upload the one consumer-owned Pages artifact
        uses: actions/upload-pages-artifact@<full-actions-upload-pages-artifact-sha>
        with:
          path: dist

      - name: Preserve receipt inputs for the deployment runner
        uses: actions/upload-artifact@<full-actions-upload-artifact-sha>
        with:
          name: "repository-intelligence-provenance-${{ github.sha }}-${{ github.run_attempt }}"
          path: |
            dist
            .relay/repository-intelligence-deployment/consumer-route-baseline.json
            .relay/repository-intelligence-deployment/composition-verification.json
          include-hidden-files: true
          if-no-files-found: error
          retention-days: 30

  deploy:
    needs: build
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    permissions:
      actions: read
      contents: read
      id-token: write
      pages: write
    environment:
      name: github-pages
      url: "${{ steps.deployment.outputs.page_url }}"
    steps:
      - name: Download exact composition and baseline
        id: download_provenance_inputs
        uses: actions/download-artifact@<full-actions-download-artifact-sha>
        with:
          name: "repository-intelligence-provenance-${{ github.sha }}-${{ github.run_attempt }}"
          path: .

      - name: Deploy the consumer-owned Pages artifact
        id: deployment
        continue-on-error: true
        uses: actions/deploy-pages@<full-actions-deploy-pages-sha>

      - name: Record the separate consumer deployment receipt
        id: receipt
        if: "${{ always() && steps.download_provenance_inputs.outcome == 'success' }}"
        uses: egohygiene/relay/actions/repository-intelligence-deployment-provenance@<same-full-relay-sha>
        with:
          operation: record-receipt
          consumer-revision: "${{ github.sha }}"
          relay-revision: "<same-full-relay-sha>"
          workflow-run-id: "${{ github.run_id }}"
          workflow-run-attempt: "${{ github.run_attempt }}"
          deployment-environment: github-pages
          deployment-url: "https://repository.example/"
          deployment-conclusion: "${{ steps.deployment.outcome }}"
          aliases: >-
            [{"route":"/health/","target":"/intelligence/health/"},
            {"route":"/search/","target":"/intelligence/search/"}]
          rollback-revision: "<previous-deployed-consumer-sha>"
          rollback-site-digest: "sha256:<previous-composed-site-digest>"
          rollback-url: "https://repository.example/"

      - name: Preserve the consumer deployment receipt
        if: "${{ always() && steps.receipt.outcome == 'success' }}"
        uses: actions/upload-artifact@<full-actions-upload-artifact-sha>
        with:
          name: "repository-intelligence-deployment-receipt-${{ github.run_id }}-${{ github.run_attempt }}"
          path: .relay/repository-intelligence-deployment/deployment-receipt.json
          include-hidden-files: true
          if-no-files-found: error
          retention-days: 30

      - name: Reassert deployment result after receipt preservation
        if: "${{ always() }}"
        shell: bash
        env:
          DEPLOYMENT_OUTCOME: "${{ steps.deployment.outcome }}"
          RECEIPT_OUTCOME: "${{ steps.receipt.outcome }}"
        run: |
          set -euo pipefail
          [[ "${DEPLOYMENT_OUTCOME}" == "success" ]]
          [[ "${RECEIPT_OUTCOME}" == "success" ]]
```

The reference shows the authority and data flow, but Relay's local fixture does
not claim that this workflow has deployed a production site. The consumer must
retain the real run URL, receipt artifact, environment history, and any remote
route or byte verification required by its publication policy.

Recovery uses the last accepted receipt: rebuild its exact
`rollback.consumer_revision`, require the same recorded
`rollback.site_digest`, deploy through the consumer workflow, and record a new
receipt for that rollback run. Relay never initiates the deployment.

Refs egohygiene/relay#105 and egohygiene/relay#33.
