# Antidote publication Pages caller

This is the target two-job authority pattern for Antidote after Relay v1.3.0 is
released. Keep Antidote's existing pinned dependency-install and native
`task check-site` steps in the producer job; replace only the duplicated Pages
review/deploy/remote-proof implementation with the pinned Relay call.

```yaml
name: Antidote publication hub

on:
  pull_request:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  build_site:
    name: Build product-owned publication site
    permissions:
      contents: read
    runs-on: ubuntu-24.04
    timeout-minutes: 30
    steps:
      - name: Checkout Antidote
        uses: actions/checkout@<full-actions-checkout-sha>
        with:
          persist-credentials: false

      # Preserve Antidote's existing pinned Task/LaTeX/Pandoc installation.
      - name: Build and validate Antidote publication site
        run: task check-site THEME="egohygiene" BUILD_DIR="build/egohygiene"

      - name: Upload caller-built static site
        uses: actions/upload-artifact@<full-actions-upload-artifact-sha>
        with:
          name: "antidote-publication-site-${{ github.sha }}"
          path: "_site"
          include-hidden-files: true
          if-no-files-found: error
          retention-days: 7

  review_site:
    name: Review publication bytes
    if: "${{ github.event_name == 'pull_request' }}"
    needs: build_site
    permissions:
      actions: read
      contents: read
    # egohygiene/relay publication-pages v1.3.0
    uses: egohygiene/relay/.github/workflows/publication-pages.yml@<full-relay-v1.3-commit-sha>
    with:
      artifact-name: "antidote-publication-site-${{ github.sha }}"
      expected-base-url: "https://antidote.egohygiene.io/"
      expected-source-revision: "${{ github.sha }}"
      fallback-base-url: "https://egohygiene.github.io/antidote/"
      required-routes: '["", "paper/", "magazine/", "downloads/"]'
      deploy-enabled: false

  deploy_site:
    name: Deploy reviewed publication bytes
    if: >-
      ${{
        (github.event_name == 'push' || github.event_name == 'workflow_dispatch') &&
        github.ref_type == 'branch' &&
        github.ref_name == github.event.repository.default_branch
      }}
    needs: build_site
    permissions:
      actions: read
      contents: read
      id-token: write
      pages: write
    # egohygiene/relay publication-pages v1.3.0
    uses: egohygiene/relay/.github/workflows/publication-pages.yml@<full-relay-v1.3-commit-sha>
    with:
      artifact-name: "antidote-publication-site-${{ github.sha }}"
      expected-base-url: "https://antidote.egohygiene.io/"
      expected-source-revision: "${{ github.sha }}"
      fallback-base-url: "https://egohygiene.github.io/antidote/"
      required-routes: '["", "paper/", "magazine/", "downloads/"]'
      verify-fallback: true
      deploy-enabled: true
```

The public catalog keeps the magazine slot truthful while it is planned or
draft: its landing page exists, but it has no version, artifact, release, DOI,
or checksum claims. Antidote remains independently buildable through Make and
Task if Relay is unavailable.

Refs egohygiene/relay#38.
