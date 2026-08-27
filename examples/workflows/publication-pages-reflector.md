# Reflector publication Pages caller

This is the incremental migration pattern for Reflector after Relay v1.3.0 is
released. Reflector's native `task pages:check`, manuscript, magazine, DOI,
release metadata, artifact names, and site staging remain authoritative. Relay
replaces only duplicated lifecycle validation, Pages deployment, and remote
byte proof.

```yaml
name: Reflector publication hub

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
    timeout-minutes: 45
    steps:
      - name: Checkout Reflector
        uses: actions/checkout@<full-actions-checkout-sha>
        with:
          fetch-depth: 0
          persist-credentials: false

      # Preserve Reflector's existing pinned native publication dependencies.
      - name: Build and validate Reflector publication site
        run: task pages:check PAGES_OUTPUT_DIR="_site"

      - name: Upload caller-built static site
        uses: actions/upload-artifact@<full-actions-upload-artifact-sha>
        with:
          name: "reflector-publication-site-${{ github.sha }}"
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
      artifact-name: "reflector-publication-site-${{ github.sha }}"
      expected-base-url: "https://reflector.egohygiene.io/"
      expected-source-revision: "${{ github.sha }}"
      fallback-base-url: "https://egohygiene.github.io/reflector/"
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
      artifact-name: "reflector-publication-site-${{ github.sha }}"
      expected-base-url: "https://reflector.egohygiene.io/"
      expected-source-revision: "${{ github.sha }}"
      fallback-base-url: "https://egohygiene.github.io/reflector/"
      required-routes: '["", "paper/", "magazine/", "downloads/"]'
      verify-fallback: true
      deploy-enabled: true
```

The migration must preserve Reflector's published URLs, DOI and release
history. Its current Pages workflow remains the rollback path until the pinned
Relay call passes a real default-branch deployment and both public endpoints.

Refs egohygiene/relay#38.
