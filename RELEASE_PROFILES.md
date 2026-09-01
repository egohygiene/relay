# Relay release profiles

Relay publishes a small, versioned release-profile catalog in
[`release-profiles.json`](release-profiles.json). A profile defines the minimum
artifact evidence Relay can validate and preserve; it does not transfer the
consumer's registry, container, site, package-manager, or signing authority to
Relay.

| Profile | Repository classes | Release delivery | Required payload evidence |
| --- | --- | --- | --- |
| `npm-specification` | npm package, specification bundle | GitHub Release evidence | package metadata, `.tgz`, checksum, provenance, SBOM, signature |
| `container-image` | container image, development environment | GitHub Release evidence | image digest, checksum, provenance, SBOM, signature |
| `binary` | CLI, desktop application, library | GitHub Release | binary archive, checksum, provenance, SBOM, signature |
| `static-site` | GitHub Pages site, static site | GitHub Release evidence | `index.html`, site catalog, checksum, provenance, SBOM, signature |
| `pdfa-document` | publication, research document | GitHub Release | PDF, PDF/A validation, checksum, provenance, SBOM, signature |
| `python-package` | Python package, Python workspace component | GitHub Release evidence | package record, sdist, wheel(s), checksums, provenance, SBOM, signature |
| `github-action` | action, workflow library | GitHub Release | action/workflow catalogs, packaged archive, checksum, provenance, SBOM, signature |

All profiles require a root `SHA256SUMS` that covers every regular file in the
bundle except itself, using sorted `<sha256><two spaces><path>` records. Relay
copies neither raw source nor mutable registry state into the profile catalog.

### Python package evidence

The `python-package` profile requires a schema-governed
`python-package.json` record alongside exactly one source distribution and one
or more wheels. The record names one component, its distribution name, its
exact semantic version, and one `pyproject-project` authority ending in
`pyproject.toml`. Its requested version must equal the repository release tag.

Every declared distribution path and digest must match both the bundle bytes
and `SHA256SUMS`; undeclared wheels or source distributions fail closed. A
workspace publishes independently versioned components as separate bundles,
each with its own authority record, rather than asking Relay to infer a shared
version.

The registry state is intentionally limited to `external` or `unavailable`.
Relay's pre-publication evidence cannot claim that PyPI accepted a package.
PyPI publication, credentials, receipts, and yanking remain in a separately
authorized repository-owned adapter.

```json
{
  "$schema": "https://egohygiene.github.io/relay/contracts/python-package-release/v1/schema.json",
  "schema": "egohygiene.relay-python-package-release/v1",
  "component": {
    "id": "example-package",
    "distribution": "example-package",
    "version": "1.4.0",
    "version_authority": {
      "kind": "pyproject-project",
      "path": "packages/example/pyproject.toml"
    }
  },
  "artifacts": {
    "sdist": {
      "path": "example_package-1.4.0.tar.gz",
      "sha256": "<lowercase-sha256>"
    },
    "wheels": [
      {
        "path": "example_package-1.4.0-py3-none-any.whl",
        "sha256": "<lowercase-sha256>"
      }
    ]
  },
  "registry": {"provider": "pypi", "state": "external"}
}
```

## Reusable publication workflow

`release-artifact.yml` validates a caller-built artifact, creates deterministic
release evidence, and publishes exactly three GitHub Release assets:

1. a reproducible archive of the validated bundle;
2. `release-asset.sha256` for that archive; and
3. `release-evidence.json` that binds profile, version, source revision,
   complete file hashes, provenance/SBOM/signature records, and rollback
   instructions.

The caller must upload the bundle before invoking Relay and grants only the
permissions the release needs. Production callers pin a full Relay commit SHA;
the adjacent version comment is discovery metadata, not the trust boundary.

```yaml
jobs:
  publish_release:
    permissions:
      actions: read
      contents: write
    # Replace with the reviewed Relay release commit.
    uses: egohygiene/relay/.github/workflows/release-artifact.yml@<full-commit-sha>
    with:
      artifact-name: "aether-v1.4.0"
      expected-source-revision: "${{ github.sha }}"
      profile: "npm-specification"
      release-version: "v1.4.0"
      update-major-alias: false
```

The reusable workflow only accepts push or manual-dispatch calls from the
caller’s default branch. It creates an annotated immutable tag only after the
checked-out commit still equals the current remote default-branch head. A
rerun may resume an interrupted release only when the existing immutable tag
already resolves to that same commit and its evidence assets exactly match;
contradictory state fails closed. Relay never overwrites a published evidence
asset.

## Rollback and external publication

GitHub Release assets, registry packages, container digests, and PDF editions
are immutable historical records. Relay never deletes or replaces them. The
validated `rollback` object identifies the recovery strategy for each profile:
revoke a mutable distribution channel when relevant, redeploy a prior verified
site artifact, or publish a corrected release at a new version.

Registry publication, image signing, PDF distribution, package deprecation,
and site deployment remain consumer-owned adapter steps. A caller records their
result as the required profile evidence and can use its own scoped credentials;
Relay does not request or forward those credentials.

The v1 validator verifies the complete checksum inventory and records the
hashes of signature evidence; cryptographic signature verification remains an
owner-specific adapter step until its signer and trust roots are explicitly
contracted.
