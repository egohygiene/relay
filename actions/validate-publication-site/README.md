# Validate Publication Site

`validate-publication-site` verifies an already-built static publication tree.
It never checks out source, invokes a renderer, installs dependencies, changes
repository state, or deploys content.

The action accepts the host-neutral `beacon.publication-hub/v1` catalog and
proves that its canonical HTTPS base, source revision, routes, publication-slot
honesty, artifact metadata, and complete sorted `SHA256SUMS` inventory agree
with the bytes in the caller workspace. It rejects broad or protected output
directories, path traversal, symlinks, route collisions, empty files, missing
files, partial or mutable inventories, unsafe public hosts, and publication
claims on planned slots. Public fallback fields are present but may be `null`.
Available slots require a pinned source revision, version, and at least one
verified artifact.

The action applies the exact vendored
[`publication-site.schema.json`](contracts/publication-site.schema.json) before
Relay's byte, route, host, and lifecycle checks. Its pinned upstream provenance
and digest are recorded in the [contract README](contracts/README.md).

```yaml
- name: Validate the product-owned publication site
  # Relay v1.3.0; pin the released full commit SHA.
  uses: egohygiene/relay/actions/validate-publication-site@<full-commit-sha>
  with:
    site-directory: "_site"
    expected-base-url: "https://antidote.egohygiene.io/"
    expected-fallback-base-url: "https://egohygiene.github.io/antidote/"
    expected-source-revision: "${{ github.sha }}"
    required-routes: '["", "paper/", "magazine/", "downloads/"]'
```

The generated validation evidence is deterministic and contains no local
absolute paths. The default destination is
`.relay/publication-site-validation.json`; callers may upload it as ordinary
review evidence. Its successful and sanitized failure shapes are versioned by
[`publication-site-validation-evidence.schema.json`](schemas/publication-site-validation-evidence.schema.json).

An empty `expected-fallback-base-url` accepts nullable fallback metadata without
pinning it. When supplied, the value must exactly match the normalized catalog
fallback; the reusable workflow passes its fallback input during read-only
review so drift fails before deployment.

`site-tree-sha256` is the SHA-256 digest of the exact, sorted, complete
`SHA256SUMS` bytes. Because that inventory covers every public file except
itself, the digest is a stable identity for the reviewed site tree.

Relay caps the site at 20,000 files, 1 GiB total, and 256 MiB per file, with
tighter bounds for the catalog and checksum metadata. These are validation
limits, not permission to expose sensitive content: the caller remains
responsible for deciding which product-owned bytes are public.

The catalog's `source.catalog_sha256` identifies Beacon's private authored
`publication-hub.json`. Relay validates that digest's shape, but the private
source is deliberately outside a public static artifact. Relay instead proves
the public `site.json` bytes through the complete outer checksum inventory;
attesting the private authored source remains caller-owned evidence.
