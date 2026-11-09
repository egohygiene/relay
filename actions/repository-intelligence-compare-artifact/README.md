# Repository Intelligence Compare Artifact

This separate opt-in composite action supplies the existing Compare renderer
with an exact compatible retained baseline. It consumes a completed public
source build's **original** `projection.json` and `snapshot.json`; it never
reconstructs a projection, changes observation clocks or chooses a latest
artifact. See the [operator and composition guide](../../docs/repository-intelligence-compare-artifact.md).

Use the exact reviewed Relay commit. Callers require `contents: read` and
`actions: read`; existing Intelligence callers that do not select this action
keep their existing token contract. Only public `push`/`workflow_dispatch`
contexts are admitted. The action performs bounded reads, private temporary
writes and one eligible ordinary artifact upload. It has no Pages, deployment,
source-history, secret inheritance or provider mutation authority.

For a first baseline, supply `expected-baseline: none` with all baseline fields
empty. The comparison stays unavailable while an eligible current pair can be
retained. For subsequent runs, supply the prior upload's exact artifact ID and
ZIP digest, represented consumer SHA, successful run/attempt and the exact
`snapshot-sha256:projection-sha256` lease. All fields are mandatory together.
Preserve these immutable selection records separately; no shared cloud pointer
or automatic recovery is created.

The default `legacy-adr` profile uses the existing locked alpha.2 retention CLI.
`search-attribution-v1` is a closed integration seam for the separately reviewed
Search normalizer; it requires that helper and a matching prepared runtime or
its exact trusted acquisition path. It never falls back to legacy normalization. Profile or runtime-lock
mismatch makes the baseline incompatible. Historical profile migration requires
an explicit new lineage, preserving old artifacts and receipts.

`snapshot-path`, `projection-path` and an optional `comparison-path` are private
absolute paths. For an existing native source build, set the optional
`intelligence-directory` to its completed repository-relative subtree. The
action composes only the Compare route from its in-memory admitted evidence,
preserves every other payload byte including `source_collection`, refreshes
the build manifest, and validates the complete bundle. Both actions must use
the same full immutable Relay commit. Use the final `manifest-sha256` and
`bundle-digest` outputs after composition; the earlier builder outputs describe
the earlier bytes. Consumer composition checks and upload follow this step.

External-snapshot consumers can instead copy only the admitted snapshot and
comparison into a new untracked private consumer work directory before using
the builder's existing repository-relative inputs. Do not use that external
path to replace native collection receipts. Do not publish the artifact
manifest, source projection, operational receipts or whole temporary directory.
The caller still owns the one site composition, Pages artifact, deployer and
recovery procedure. See the [manual opt-in example](../../examples/workflows/repository-intelligence-native-compare.md)
for explicit seeding and complete baseline selection.

`status` describes comparison evidence separately from the upload. A successful
upload returns `artifact-id`/`artifact-digest`; select `next-baseline-lease` only
with those actual upload outputs and its exact source/run/attempt identity.
The private artifact receipt records upload outcome as uploaded, unchanged or
unknown; a possible failed upload is never described as confirmed unchanged.
Retain that receipt through the caller's existing always-run evidence path.

Native replay, two-revision consumer previews, hosted retention expiry,
failure/cancellation scheduling, live Compare, upgrade and rollback acceptance
remain deferred. Source/syntax inspection does not establish those outcomes.
