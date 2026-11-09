# Owner-defined Search attribution

Refs [Relay #102](https://github.com/egohygiene/relay/issues/102),
[source composition #151](https://github.com/egohygiene/relay/issues/151), and
[Observatory #24](https://github.com/egohygiene/observatory/issues/24).

Search consumes the versioned `search_fields` representation from Observatory
`49a8031f2a5124ff7ab09adbda50a9a5dbe6dec2`. Exact owner Python and browser
implementations are vendored with their hashes in `search-fields.v1.lock.json`.
The browser reference prefixes existing `site.js`; no extra published asset or
second index is created. Original license notices and bytes are preserved,
including non-semantic comment whitespace.

The owner admits only title, key, kind, state and repository, in that order.
Complete-query substring matching and participating field spans come from its
reference API, including overlapping and cross-field matches. Frozen Unicode
14 casing, final-sigma context and explicit outer whitespace avoid differences
between Python and browser tables. No ranking, casefold, token-AND behavior,
provider lookup or source-prose indexing is introduced.

Relay validates supplied attribution before rendering and checks public
visibility before identities, text and counts. The browser shows ordered
matched-field labels as text. Older records retain their opaque `search_text`
filter and explicitly unavailable attribution. Raw Search queries stay in URL
state so browser lowercasing cannot change a versioned query on reload. All
admitted records, facets and canonical sources remain static; query-specific
attribution is progressive enhancement.

## Native opt-in

The composite and both reusable entrypoints accept `search-attribution: true`
alongside a native source plan. It conflicts with external snapshot/comparison
selection and cannot select sources itself. The local source-preparation CLI
uses `--search-attribution`. External attributed snapshots need no native flag.

ADR-only opt-in builds use the same source composer as Roadmap, Journey and
captured domains. Collectors retain their original runtimes and domain
receipts. Final normalization selects `search-attribution-v1`. Its trusted
upgrade copies verified unchanged tools into a fresh private runtime and
acquires only pinned Observatory bytes. It does not rebuild the same Rust
toolchain or mutate the old runtime. Advanced local callers may provide a
prepared `--search-runtime` outside the consumer checkout. An all-typed local
plan without a shared ADR runtime requires that explicit Search runtime.
Caller defaults and historical lockfiles remain unchanged.

`provenance.source_collection.normalization_profile` binds the feature option,
new lock/pins, executable and implementation hashes. Source identity, clocks,
combined coverage and original projection/snapshot hashes stay bound by the
enclosing receipt. The closed schema and final admission verify the same
profile. There is no new source, human disposition or deployment authority.

## Compare and adoption

The [Compare artifact action](repository-intelligence-compare-artifact.md)
selects `normalization-profile: search-attribution-v1` for original pairs from
this pipeline. Both sides revalidate with the same exact profile; legacy and
attributed pairs cannot silently mix or rewrite history. Default Compare
selection remains legacy ADR. Missing baselines stay unavailable.

Consumer adoption selects one exact Relay revision and enables generic Git
Journey plus Search attribution on current paths. Existing ADR opt-ins, strict
source gates, product routes, deployment ordering and frozen recovery pins and
digests remain consumer-owned. No baseline, approval or publication is invented.

Static syntax/schema, input/catalog parity and independent source review are
the current evidence. Native execution, tests, builds, CI investigation,
cross-runtime fixtures, canaries and publication qualification remain deferred.
