# Public catalog admission

`validate_selection(rows, metadata)` also authenticates a serialized selected
subset without loading Git or native tools. It compares public rows to the exact
byte mirror `contracts/public-repositories.hygiene-49639c1.json`, whose SHA256 must
match the owner artifact pin. The mirror remains owner-authored data; updates
require a new reviewed source profile. Private wrappers are rejected before
identity access. Metadata alone does not authenticate membership.

`public_catalog_admission.acquire(work)` optionally fetches only the pinned public
Hygiene revision into a fresh bare Git directory at `work/public-catalog` and
returns that path. It uses only the standard library and Git, with an isolated
Git environment and fixed HTTPS source. It does not install tools, execute source
files, or change consumer/recovery configuration. Callers must place `work`
outside the consumer checkout and native runtime; `load()` still authenticates
the source and admits selected public rows after this transport completes.

`public_catalog_admission.py` reads the reviewed public projection delivered by
[Hygiene #97](https://github.com/egohygiene/hygiene/pull/97). It does not create a
registry, discover repositories, infer roles, or promote proposed policy. Refs
[Relay #148](https://github.com/egohygiene/relay/issues/148).

The independent `public-catalog-admission.v1.lock.json` selects Hygiene
`49639c1845cdfd08fbd5a768261a8b3cf515f80f`, tree
`f35e00f075ae5fa53bcf7734392f8d1443eb172d`. The public artifact, its closed owner
schema and its standard-library validation helper are verified as exact Git
blobs. The artifact SHA-256 is
`af9c7186ded0bb57b18741eaa5905314b96d6adb03736946c868e0fc4aa50b26`.
Existing collector, normalizer and recovery locks remain unchanged.

`load(catalog_root, requested=None)` returns `(selected_public_rows, metadata)`.
The caller supplies a Git repository containing the selected immutable owner
objects, never executable consumer code. No network request occurs. Omitting
the selector admits the complete reviewed public roster; an explicit selector
admits only matching canonical public names. Unknown, excluded or historical
alias selectors create no placeholders, diagnostics or guessed identities.

The loader executes only the hash-verified owner helper in a private temporary
directory. It uses the owner's ambiguity-preserving parser and selects public
visibility before identities, duplicates, schema validation, aliases, counts or
digest generation. The returned row shape remains the owner's public catalog
contract, including stable provider ID, role, explicit aliases and dated or
unknown next gate. Unknown lifecycle or gate evidence does not become success.

The metadata contains the closed schema ID, owner, exact revision, artifact
path/hash, owner schema/helper hashes, original UTC observation and selected
public-row digest. The selected digest is SHA-256 of UTF-8 JSON using sorted
object keys, two-space indentation, unescaped Unicode, no nonfinite numbers and
a trailing newline. Returned rows are sorted by canonical full repository name.
Only the reviewed public artifact and admitted canonical rows are hashed; the
mixed canonical catalog and excluded source data are not public receipt inputs.

`validate_metadata(metadata, selected=None)` checks the receipt shape and exact
current owner selection. When rows are supplied, it also checks their selected
digest. This is execution evidence, not an independent membership proof for an
untrusted serialized subset. Such a consumer must verify the exact full owner
public artifact and check its selected rows against that roster, or invoke the
trusted loader itself. A self-asserted digest cannot authorize a repository.

The profile supplies public identity admission. Canonical dependency declarations
and their permitted directions remain separate Hygiene-owned sources; public
identity alone never creates a dependency edge. Public fleet assembly and its
consumer-owned artifact/publication handoff remain separate operations too.

Source and schema review are the current validation boundary. Per the user,
native calls, tests, builds, CI and executable privacy/parity acceptance remain
deferred; implementation or a merge is not a public publication receipt.
