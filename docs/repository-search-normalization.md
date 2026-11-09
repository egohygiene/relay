# Opt-in Search normalization profile

Relay keeps existing canonical collectors and their runtime locks separate from
the final normalized Search presentation. The `search-attribution-v1` profile
selects Observatory's versioned field-attribution API for the final composed
graph. It does not reconstruct an index, add searchable fields, rank results,
collect new provider data, change canonical state, or authorize publication.

The owner contract and renderer follow-up are
[Observatory #24](https://github.com/egohygiene/observatory/issues/24) and
[Relay #102](https://github.com/egohygiene/relay/issues/102). Source composition
remains [Relay #151](https://github.com/egohygiene/relay/issues/151), while the
artifact retention handoff remains
[Relay #152](https://github.com/egohygiene/relay/issues/152).

## Separate immutable selection

`actions/repository-intelligence/contracts/search-attribution-normalizer.v1.lock.json`
owns this execution profile's exact source trees and file hashes. It retains the
current Hygiene graph, accepted ADR policy and EgoLint selections, and selects
the new Observatory implementation and its adjacent Search helper. Existing ADR,
Roadmap, Work, Health, Journey, Releases, dependency and fleet lockfiles are not
repinned by this profile.

The selected Observatory revision is
`49a8031f2a5124ff7ab09adbda50a9a5dbe6dec2`, tree
`8eaeb62a3ce58056093df77cc7a6327322aaeaf2`. The lock includes the standalone
engine and adjacent Python helper, Search contract descriptor/schema, four
read-model/view/fleet/comparison schemas, portable JavaScript reference and its
Unicode license. Attributed fields and queries use the owner's frozen Unicode
14.0.0 normalization; the legacy opaque default retains its earlier expression.

`repository_search_normalization.py prepare` accepts the same explicitly trusted
Hygiene, EgoLint, Observatory, Cargo and output paths as the current native
preparer. It reads immutable Git objects, verifies the locked file/tree bytes,
and compiles only the existing trusted EgoLint source using the existing offline
preparation boundary. Its `acquire(work)` adapter delegates to the existing
isolated acquisition path with a closed profile name. Arbitrary lock paths or
preparer code cannot be supplied through that interface.

With attribution disabled, existing owner calls receive no new keyword and keep
their previous normalized bytes. Existing runtime receipts retain their two-key
shape and existing lock bytes. Source-code hashes continue to identify the
actual selected Relay implementation. An attributed runtime cannot be passed
off as an old runtime: the exact lock digest and every selected file must agree.

## Trusted integration API

The helper is loaded only from the immutable Relay action directory:

- `normalize(runtime, projection)` first requires public source/entity/event
  classifications and no redacted topology, verifies the selected prepared
  runtime, and invokes the existing native validators. Final normalization uses
  Observatory `build_repository_snapshot(projection, search_attribution=True)`.
  Its return shape matches the existing `(snapshot, validation)` callback.
- `metadata(runtime)` returns the closed normalization profile, exact feature
  keyword, immutable owner pins, executable digest and trusted adapter hashes.
  `validate_metadata(value)` verifies that execution evidence without importing
  caller-selected code. Parent source receipts remain responsible for binding
  repository, represented commit, observation and final candidate hashes.
- `retention_adapter()` loads an independent instance of the existing retention
  implementation with this exact lock and normalizer. It reuses the existing
  storage, lease, failure, freshness and coverage rules; no process-global
  legacy adapter is changed.
- `upgrade(legacy_runtime, work)` returns a new runtime at `work/runtime`. It
  first verifies the legacy ADR runtime and requires every non-Observatory pin
  to match this profile exactly. Only verified required owner files and the
  verified EgoLint executable are copied. A private bare Git fetch acquires
  only the exact new public Observatory commit; its tree and every selected
  blob digest must match the lock. The new runtime is verified again before
  admission. The scratch directory must be fresh or empty, outside a Git
  checkout and separate from the legacy runtime. No old file, compiler,
  toolchain or Python environment is changed. Incompatible explicitly typed
  runtimes can use `acquire(work)` separately.

The helper performs no field attribution itself. Observatory's pinned schema
and semantic implementation remain authoritative. Malformed or incompatible
inputs fail rather than silently becoming opaque results under this profile.

Production opt-in wiring, its source receipt field and action/reusable workflow
inputs are integrated separately after the owner pin and this helper are
available. Merely including this helper does not enable any consumer source or
alter current source collection defaults.

## Retention compatibility

An artifact handoff must state `normalization_profile: search-attribution-v1`
and select its matching trusted runtime. The legacy `legacy-adr` profile retains
its existing runtime, schema and normalizer. The original Hygiene projection
must accompany each normalized snapshot: its generator contributes to the
upstream digest and cannot be reconstructed from the read model.

Both before and after pairs must reproduce exactly under the selected profile
before comparison. An old opaque snapshot and a new attributed snapshot are
incompatible under one retained-pair profile; absence of attribution is not an
implicit migration. The selected new Observatory implementation supplies
comparison semantics, including schema validation of the optional extension.
Failed admission cannot promote a baseline or replace a valid retention lease.

## Review limits

This change is source preparation. Tests, builds, native runtime acquisition or
execution, renderer runs, CI, browser checks and consumer publication are
deferred by the user. Static syntax and peer review do not prove normalization,
cross-runtime matching, complete bundle equality or retained artifact behavior.
No deployment, recovery, scheduling or human decision state changes here.
