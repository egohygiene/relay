# Beacon publication-site contract

[`publication-site.schema.json`](publication-site.schema.json) is an exact copy
of Beacon's frozen `beacon.publication-hub/v1` public-catalog schema for the
Relay v1.3.0 handoff.

- Upstream path: `templates/publication-hub/contracts/publication-site.schema.json`
- Upstream issue: `egohygiene/beacon#19`
- Schema SHA-256:
  `458cfcdf8f24ef2c702ce592ad329cdb1a7c88954df6c7fcfe2f143d01b9c112`
- Relay adoption issue: `egohygiene/relay#38`

Relay vendors the contract so a called action validates the exact schema from
its immutable Relay revision without checking out Beacon or caller source. The
stdlib validator implements the schema's closed shapes, conditionals, and
reference rules, then adds deployment-boundary checks for safe public hosts,
normalized paths, exact route-to-file linkage, staged bytes, complete sorted
checksums, bounded input, and caller-pinned revision/base URLs.

`source.catalog_sha256` is the digest of Beacon's private authored
`publication-hub.json`. Relay can validate its syntax but cannot recompute it
from the public deployment tree. The caller owns that private-source
attestation; Relay binds the public `site.json` itself through `SHA256SUMS`.

An intentional contract update must copy the reviewed upstream bytes, update
this digest, add compatibility mutations, and ship in an appropriate Relay
release. It must not silently follow Beacon's default branch.
