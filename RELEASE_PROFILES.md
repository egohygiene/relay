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
| `github-action` | action, workflow library | GitHub Release | action/workflow catalogs, packaged archive, checksum, provenance, SBOM, signature |

All profiles require a root `SHA256SUMS` that covers every regular file in the
bundle except itself, using sorted `<sha256><two spaces><path>` records. Relay
copies neither raw source nor mutable registry state into the profile catalog.

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
