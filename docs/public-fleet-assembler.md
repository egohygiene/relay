# Offline public fleet artifact assembly

Refs [Relay #153](https://github.com/egohygiene/relay/issues/153).
This bounded adapter assembles existing repository evidence through
Observatory's existing fleet model. It does not create another repository
registry, infer missing inventory, collect over the network, execute consumer
code, build a site, or grant publication authority.

Every result is `egohygiene.relay.public-fleet-review/v1` with
`publication: denied`. An explicitly reviewed extraction of
`fleet_snapshot_candidate` is the host handoff; the wrapper must never be
mistaken for an approved production artifact.

## Current dependency boundary

Hygiene #36 still owns the reviewed catalog-minimum and public allowlist. Its
October 20 checkpoint records a historical 27-record catalog, the legacy
`website` identity and an August observation boundary. This implementation does
not fix that catalog, rename a repository, assert a fresh organization total,
or certify that an arbitrary review URL approves a selection. The plan's
`review_reference` is caller-supplied evidence for human inspection, not an
automatically verified approval. Production acceptance still needs the owner
review, a real compatible repository artifact, the site-owned integration, and
live refresh/recovery proof.

## Exact owner intersection

`actions/repository-intelligence/contracts/public-fleet.v1.lock.json` binds source
trees and selected file hashes:

| Owner | Immutable source | Responsibility |
| --- | --- | --- |
| Hygiene graph/coverage | `639a003d5ddc4d242c2cf190eeb59a9fc522d199` | Existing proposed alpha.2 graph, vocabulary and nine-domain coverage |
| Hygiene catalog | `fa41ccc95d0cd0365b38008e02bdc67b928c5ed2` | Existing catalog schema and semantic validator, including repaired identity handling |
| EgoLint | `d917ea524962639494e5bb4b3196192238ba57d9` | Native coverage validation against its exact compatible Hygiene set |
| Observatory | `f411b83398dd07aa3d5e6e2c89d1e8dfff746085` | Repository normalization, fleet assembly and exact alpha.2 schemas |

These two independent Hygiene source selections preserve ownership: the catalog
does not redefine graph contracts, and an old graph pin does not substitute an
older catalog identity validator. The existing ADR runtime adapter performs
Hygiene graph validation → native EgoLint coverage validation → Observatory
normalization. Fleet assembly calls the pinned `build_fleet_snapshot` and
validates its existing fleet schema, whose SHA-256 is
`743e2e1eb52d6182ad401d5d32881360315e873a082f8fde37c1002949cfe793`.

## Public selection and isolation

The versioned `public-fleet-plan.v1.schema.json` is a local artifact transport
plan, not canonical identity policy. It supplies an exact catalog revision, a
Hygiene review reference, selected repository identities, requested consumer
commits, and candidate/last-known artifact paths, kinds and checksums. Identity
and public visibility must exist in the canonical catalog at that revision.

The assembler reads the exact `catalog/repositories.yaml` Git blob, filters
visibility, and only then admits requested public records. Unknown, private and
unselected records are ignored before their artifact paths, source claims or
checksums are inspected. No excluded identities, original totals, hidden counts,
placeholders or source diagnostics enter output. Only the selected public slice
is validated; Hygiene's fixed public canonical owner is added as validation
context without creating a fleet row. Catalog role/relationship prose and
proposed repository records are not exported.

At fixed public catalog revision, metadata and selection, changing excluded
records or their artifact plans cannot change public lookups, rows, digests or
diagnostics. Raw whole-catalog/plan hashes are deliberately absent. Public hashes
cover minimal selected catalog metadata and admitted canonical public input.
The catalog commit identifies the selected public Hygiene source; it is not a
fingerprint of an otherwise hidden discovery inventory.

Each admitted repository is processed independently. Missing files, wrong
hashes, malformed/unsupported snapshots, mismatched revisions and privacy
boundary failures produce fixed public diagnostic codes attached only to an
already-selected public repository. No raw exception, path, rejected name,
provider message or rejected artifact checksum is emitted. Other valid public
repositories still reach Observatory's fleet model.

No snapshot is fabricated for an unavailable repository. That repository remains
in the wrapper's public availability directory; it is absent from the normalized
fleet candidate. This distinction keeps fleet counts scoped to actual admitted
evidence rather than turning unavailable input into observed-empty coverage.
When nothing is admitted, the candidate is null: Observatory requires a nonempty
fleet, so a synthetic empty successful fleet is not produced.

## Repository input modes

- `projection` admits an original Hygiene alpha.2 projection and preserves its
  declared generator while running the owner validation/normalization boundary.
- `snapshot` admits the public graph/coverage portion of an Observatory alpha.2
  repository snapshot. It creates a new adapter-authored projection with
  `egohygiene/relay:public-fleet-replay` as generator. The snapshot does not retain
  its original projection generator; this mode therefore **does not verify or
  claim equivalence to the original upstream digest**. The receipt explicitly
  labels it `snapshot_graph_replay`.

Raw snapshot views, Search indexes, aggregate counts, upstream digest and
unrelated metadata are discarded. Every view and count is recomputed through
the pinned normalizer from admitted graph data. Acquisition checksums verify
local selected files but never enter public receipts. Only canonical admitted
public input and rebuilt snapshot digests are retained. Consequently, changing
discarded view text or a rejected/unused artifact does not perturb public hashes.

Inputs must already be public-safe owner projections. The assembler is a strict
guard, not a private-to-public redaction engine. All graph sources/entities/events
must be public; entity/source repositories and relationship/event endpoints must
be selected. Evidence URLs allow only exact selected GitHub repositories or
known public control owners, with encoded traversal and credential/query
ambiguities rejected. Restricted counts, unrestricted extensions, raw payload
fields, known credentials, emails and runner paths are rejected. Arbitrary prose
still requires source-owner privacy review; structural validation cannot certify
that a public title contains no sensitive meaning. Separate authorized private
builds, cross-organization namespaces and privacy-policy expansion remain owner
work, not flags on this assembler.

## Freshness and last-known evidence

All evaluation uses explicit `--observed-at`, never the wall clock. Capture times
and represented revisions are preserved. Aging source/domain observations become
stale; uncollected, unavailable and not-applicable claims do not become success.

If a candidate fails, an explicitly selected compatible last-known artifact may
be used within the recovery age. Its original commit/time remains visible, its
current evidence becomes stale, and the row is `last_known` with the candidate's
fixed failure reason. Failed refresh never overwrites a baseline or relabels it
current. Expired last-known evidence remains unavailable. Inputs, source/runtime
directories and the plan are protected against output replacement.

Default ages are one day for repository observations, 31 days for last-known
recovery and 31 days for catalog freshness. A stale historical catalog makes the
overall review partial even when selected repository evidence is usable.
Completeness of the selection does not imply fleet adoption or conformance.

## Local commands and host handoff

Use the existing exact collector Python requirements. Prepare runtime trust
separately from consumer input:

```bash
python actions/repository-intelligence/scripts/assemble_public_fleet.py prepare \
  --hygiene /sources/hygiene --egolint /sources/egolint \
  --observatory /sources/observatory --output /review/fleet-runtime

python actions/repository-intelligence/scripts/assemble_public_fleet.py assemble \
  --runtime /review/fleet-runtime --catalog-root /sources/hygiene \
  --artifact-root /review/repository-artifacts --plan /review/public-plan.json \
  --observed-at 2026-11-09T00:00:00Z \
  --output /review/results/public-fleet.review.json
```

Paths in the plan are bounded, relative, traversal-free regular files inside
`artifact-root`. Symlink ancestors are denied. Up to 64 selected public
repositories and 8 MiB per repository artifact are supported; review output is
bounded at 64 MiB. No paths appear in that output. Exit 0 means current assembly
with fresh catalog evidence, 2 means a partial/unavailable review, and 3 means a
closed admission denial. Every exit retains publication denial.

`fleet_snapshot_candidate` is exactly
`egohygiene.observatory.repository-intelligence-fleet/v1`, alpha.2. Its existing
`repositories[*].coverage.domains` contains all nine coverage entries; each
`views.NAME.repositories[*].data` retains that view's owner-defined
`collection_coverage`. Search uses the existing fleet Search records/coverage
shape. `views.now` retains canonical focus/blockers/ready/recent-event semantics;
the assembler invents no priorities.

Wrapper rows expose `repository`, `requested_commit`, `represented_commit`,
`status` (`current/stale/last_known/unavailable`), fixed `reason`,
`public_input_sha256`, rebuilt `snapshot_sha256`, `admission` mode and nine-domain
coverage. `candidate_sha256` is the SHA-256 of the candidate serialized as sorted,
indented UTF-8 JSON with a trailing newline, matching the shared runtime's
`json_bytes`. Observatory's own `sha256:` digest fields retain its compact JSON
digest convention. The host must review/extract these exact bytes and retain its
own deployment provenance; neither wrapper readiness nor local output establishes
publication.

## Deferred qualification

The user deferred tests, CI and polish. No native execution, synthetic privacy
matrix, real-source canary, cross-checkout replay, large-fleet performance,
provider refresh, workflow integration, site publication or recovery exercise is
claimed. Static syntax and source inspection are separate from those acceptance
gates. Hygiene #36, the first real compatible public source, and the consumer
host's reviewed artifact admission remain explicit dependencies.
