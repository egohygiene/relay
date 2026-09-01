# Semantic release orchestration

Relay implements the execution layer of Aether's
`egohygiene.repository-release/v1` convention. It does not infer a version from
commit messages, modify a changelog, open a release pull request, publish a
registry package, deploy a site, mint a DOI, or hold product credentials.

## Lifecycle

1. The repository owns `.egohygiene/release.json`, `CHANGELOG.md`, component
   version sources, and the four standard Taskfile handoffs.
2. A pull-request or manual planning job calls `release-prepare.yml` in `plan`
   mode. The target remains under `Unreleased`; Relay emits read-only evidence.
3. A reviewed release change promotes the target to a dated changelog section
   and updates the selected component's sole version authority.
4. The repository builds its own Relay profile bundle and calls
   `release-prepare.yml` in `verify` mode. Relay requires a clean current
   default-branch commit, version/changelog agreement, unused or identical tag,
   and complete profile evidence.
5. Only a repository-owned explicit manual publication workflow calls
   `semantic-release.yml`. It repeats verification, delegates immutable GitHub
   Release evidence to `release-artifact.yml`, and retains an outcome report.
6. Repository-owned adapters may then publish registries or deploy providers.
   Their success must be recorded separately and is never inferred from the
   GitHub Release.

Ordinary pull requests stop at steps 2 or 4. They cannot grant the
`contents: write` permission required by step 5.

## Repository classes

| Aether repository shape | Typical Relay profile | Repository-owned work outside Relay |
| --- | --- | --- |
| Rust CLI or library | `binary`, `cargo-crate`, or both as separate bundles | crates.io publication and platform installers |
| Python package | `python-package` | PyPI trusted publication |
| npm/React package or specification | `npm-specification` | npm registry publication |
| Container or development environment | `container-image` | Registry login, push, and channel tags |
| Static site or application | `static-site` | Pages/cloud deployment and runtime configuration |
| Research paper or publication | `pdfa-document` | DOI, archive, journal, and index submission |
| Contract/action repository | `github-action` or `npm-specification` | Consumer pin upgrades and marketplace discovery |
| Multi-component workspace | One profile bundle per selected component/delivery | Component selection and independent version authorities |
| Internal-only repository | No publication handoff until a delivery profile is declared | Private distribution and access policy |

The declaration's delivery channel must name the selected Relay profile exactly
once with `configured` or `external` state. A multi-component repository passes
`component-id`; Relay never guesses which independent authority should move.

## Consumer workflow shape

A consumer owns the event trigger and artifact build. Production calls pin the
complete reviewed Relay commit SHA.

```yaml
name: Release

on:
  workflow_dispatch:
    inputs:
      version:
        required: true
        type: string

permissions:
  contents: read

jobs:
  build:
    permissions:
      contents: read
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@<full-commit-sha>
      - run: task release:bundle RELEASE_VERSION="${{ inputs.version }}"
      - uses: actions/upload-artifact@<full-commit-sha>
        with:
          name: "release-bundle-${{ github.sha }}"
          path: ".relay/release-bundle"

  publish:
    needs: build
    permissions:
      actions: read
      contents: write
    uses: egohygiene/relay/.github/workflows/semantic-release.yml@<full-relay-commit-sha>
    with:
      artifact-name: "release-bundle-${{ github.sha }}"
      release-version: "${{ inputs.version }}"
      profile: "cargo-crate"
      component-id: "example-crate"
      expected-source-revision: "${{ github.sha }}"
```

The caller may add a registry adapter only as a separate job with its own
environment, permissions, credentials, evidence, and retry semantics.

## Recovery

Exact semantic tags and release assets are immutable. A rerun resumes only if
the tag points to the represented commit and the existing assets match the
reviewed evidence. Contradictory state fails closed. Recovery follows the
declaration and profile rollback instructions: revert or revoke the affected
channel, retain the historical release, and publish a corrected successor.
