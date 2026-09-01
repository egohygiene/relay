# Validate Release Bundle

`validate-release-bundle` validates a complete, caller-built release artifact
against one checked-in Relay release profile. It never publishes to a registry,
changes a Git ref, deploys a site, or receives consumer secrets.

The action requires a complete sorted `SHA256SUMS` inventory plus the profile's
provenance, SBOM, and signature evidence. It rejects symlinks, duplicate or
missing checksum entries, hash mismatches, unexpected path traversal, and
profile-specific missing files. On success it writes byte-stable
`egohygiene.relay-release-evidence/v1` JSON that records the exact release
version, represented commit, checked files, checksums, and profile rollback
instructions.

For the `cargo-crate` profile, validation binds one declared Cargo package and
`Cargo.toml` authority to the requested version, exact `.crate` filename and
digest, and an `external` or `unavailable` registry state. Undeclared crate
archives fail closed, and the action never contacts or publishes to crates.io.

For the `python-package` profile, validation additionally binds the requested
release version to one declared `pyproject.toml` authority, verifies the exact
sdist and wheel digests in `python-package.json`, rejects undeclared package
artifacts, and preserves an honest `external` or `unavailable` registry state.
It does not contact or publish to PyPI.

Use it directly in a caller-owned validation job, or through Relay's reusable
release workflow. Production callers pin Relay to a reviewed full commit SHA.

```yaml
- name: Validate release artifact
  # egohygiene/relay validate-release-bundle v1
  uses: egohygiene/relay/actions/validate-release-bundle@<full-commit-sha>
  with:
    bundle-directory: "dist/release"
    profile: "npm-specification"
    release-version: "v1.4.0"
    source-revision: "${{ github.sha }}"
    evidence-output: "dist/release/release-evidence.json"
```

The profile catalog is intentionally a validation contract, not an automatic
registry or deployment adapter. Package registries, container registries, and
site deployments remain consumer-owned authorization boundaries.
