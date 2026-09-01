# Verify Release Plan

`verify-release-plan` is Relay's read-only bridge to Aether's
`egohygiene.repository-release/v1` declaration. It never edits a version,
changelog, tag, release, registry, or deployment.

`mode: plan` requires a reviewable `Unreleased` entry and an unpromoted target
version. `mode: verify` additionally requires a clean checkout at the current
default-branch head, an exact dated changelog promotion, agreement with the
selected component's sole version authority, and a complete profile-bound
release bundle.

The action always writes `egohygiene.relay-release-plan-evidence/v1`, including
bounded failure evidence. A pre-existing immutable tag is accepted only when it
resolves to the represented source commit, enabling an identical interrupted
release to resume.

```yaml
- name: Verify reviewed release candidate
  uses: egohygiene/relay/actions/verify-release-plan@<full-commit-sha>
  with:
    repository-id: "${{ github.repository }}"
    component-id: "example"
    release-version: "v1.2.3"
    profile: "cargo-crate"
    source-revision: "${{ github.sha }}"
    default-branch: "${{ github.event.repository.default_branch }}"
    mode: "verify"
    bundle-directory: ".relay/release-bundle"
```

Production consumers pin the complete Relay commit SHA. The `v1` alias is only
a discovery and controlled-update reference.
