# Public declared Dependencies source builds

Refs [Relay #148](https://github.com/egohygiene/relay/issues/148).

`collect_repository_dependency_source.py` admits Hygiene's reviewed public
repository projection and its separately authored consumption/context/boundary
declarations for a fresh native Repository Intelligence build. It reuses the
existing declared dependency collector's direct-edge mapper. The earlier review
CLI, publication-denied review envelopes, collector locks, default source plan,
consumer deployment gates and recovery pins are unchanged.

The source profile selects Hygiene commit
`49639c1845cdfd08fbd5a768261a8b3cf515f80f`, the reviewed head of
[Hygiene #97](https://github.com/egohygiene/hygiene/pull/97). That projection
provides public identities and authored role context. Its rows do not declare
dependency edges. Edges come only from that same revision's canonical
`consumes`, `dependency_sources` and matching permitted boundary declarations.
An empty mapping does not invent an external node. Historical aliases do not
become current identities. Private or unselected endpoints are omitted before
lookup, graph expansion, policy evidence, counts and public digests.

The adapter emits direct `depends-on` edges only; walking another depth selects
additional authored edges rather than creating transitive ones. The default
depth is one, with an explicit maximum of eight. Forbidden or unmatched
selected pairs fail admission. Selected exceptions require a separately
reviewed profile; the pinned owner register has none. A `required` contract or
immutable-pinning policy remains declared policy evidence. It does not prove
contract delivery, runtime adoption or architecture approval.

The projection uses the existing pinned ADR native runtime, Hygiene's alpha.2
graph contract and Observatory's normalizer. No native tool rebuild or owner
schema upgrade is required. The root repository entity keeps the same unknown
state and empty attributes as other source adapters for composition. Other
repository nodes retain authored role context in attributes, with unknown
execution state. All nine inventory coverage domains remain `uncollected`;
Dependencies contributes graph evidence without adding a coverage domain or
upgrading Git, Work, Health or any other source's inventory claims.

The supplied UTC observation is the fresh source-inspection boundary. The public
inventory timestamp and canonical catalog declaration date remain separate in
the receipt. `maximum_catalog_age_days` evaluates both source clocks, defaults
to 30 and can preserve a stale graph explicitly. An extraction cannot refresh
an old authored gate or imply a current conformance result.

## Trusted source API

```python
result = collector.collect(args)
projection, snapshot, receipt = (
    result["projection"], result["snapshot"], result["receipt"]
)
```

`args` is a namespace with `runtime`, `catalog_root`, `repository_root`,
`repository`, `visibility`, `source_commit` and `observed_at`. Optional fields
are `public_repositories` (a JSON array of explicit canonical public names),
`maximum_depth` and `maximum_catalog_age_days`. With no selector, the reviewed
public roster is the authorization boundary. The consumer itself must be an
admitted member. `runtime` and the exact-owner Git `catalog_root` must be outside
the consumer and separate from one another. The represented consumer commit
must exist as a Git object; no consumer code or provider inventory is executed.

`public_catalog_admission.acquire(work)` optionally fetches only the exact
Hygiene source into a fresh isolated bare Git. Existing native-build code can
reuse its already prepared ADR runtime. Offline callers pass an existing Git
source with the exact required objects. Neither path follows a mutable branch.

```sh
python -I actions/repository-intelligence/scripts/collect_repository_dependency_source.py \
  --runtime /trusted/adr-runtime \
  --catalog-root /trusted/hygiene-git \
  --repository-root /consumer \
  --repository egohygiene/relay --visibility public \
  --source-commit FULL_CONSUMER_COMMIT \
  --observed-at 2026-11-09T18:00:00Z \
  --maximum-depth 1 \
  --output-directory /private/new-dependency-build
```

The output directory must be new and outside the consumer, runtime and owner
source. It contains `projection.json`, `snapshot.json` and `receipt.json`.
The CLI does not publish or consume a prior review envelope. The shared native
composer can consume this fresh in-memory result and normalize the union once,
including its independently selected optional Search normalization profile.

## Receipt and remaining integration

`repository_dependency_build_contract.validate(receipt, repository,
source_commit, observed_at)` performs ordinary standard-library receipt
verification. The closed `dependency-source-build.v1.schema.json` describes
the transport. The receipt binds exact runtime pins, executed Relay helper
bytes, source clocks, scope/depth, authenticated visited public owner rows,
direct public edges, boundary policy evidence and both canonical candidates.
Serialized rows are compared to an exact byte mirror of the owner public
artifact; a self-declared subset digest cannot establish membership.

The receipt also declares its authorized public identity selection. Its direct
edges and policies must exactly match bounded traversal of
`contracts/public-dependency-declarations.hygiene-49639c1.json`. This public-only
reference mirrors the fixed owner's consumed-input mapping, permitted policies
and forbidden-pair flags. It is verification transport, with immutable Hygiene
authority, and introduces no canonical registry or dependency-inference rule.
Only the canonical collector reads the original declarations; the ordinary
bundle verifier can authenticate selected edges without reading mixed owner
data or executing native tools. The public reference, owner artifact, public
admission lock and receipt schema are included in the executed artifact binding.

The internal source lock authenticates immutable mixed canonical owner blobs
before selection. Their whole-file hashes, excluded records, private names,
excluded counts and raw validation diagnostics are absent from public receipts.
Public evidence hashes cover admitted visited rows, direct edges and selected
policy evidence only. The immutable source revision remains public provenance.

Shared action/composer/provenance wiring is a separate integration slice. This
adapter does not enable consumers, claim issue acceptance or change deployment
scheduling. Native execution, end-to-end qualification, tests and CI remain
deferred at the user's request. Hygiene's proposed catalog checkpoint policy
and unrelated ADR/human source decisions are not ratified by collection.
