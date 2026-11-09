# Declared dependency collection — Relay #148

This bounded local collector projects Hygiene's current versioned declarations
into the existing Repository Intelligence graph and Dependencies read model.
It reads no consumer package manifests, performs no provider discovery, executes
no consumer code, and always retains `publication: denied` for local review.

## Mapping and ownership

Hygiene's catalog records repository identities and authored `consumes` inputs.
Its `catalog/repository-context.json` maps those exact input strings to stable
producer repository IDs; the owner context generator already derives direct
upstream dependencies from that mapping. Relay reuses this declaration seam.
The boundary register describes **permitted integration direction**, so its
wildcards never create graph edges or prove actual adoption.

| Owner input | Existing graph / review evidence |
| --- | --- |
| Catalog public identity | `repository` entity with stable `ri:<repository>:repository:<repository>` ID and canonical GitHub URL |
| Catalog `lifecycle`, `maturity`, `plane` | Declared lifecycle state and same named attributes, authoritative and visibly fresh/stale |
| Catalog `consumes` plus the exact context `dependency_sources` mapping | One direct `depends-on` edge, consumer → producer; duplicate declarations of the same pair collapse deterministically |
| Matching boundary producer and exact/wildcard consumer | Admission check for that already declared pair; no wildcard enumeration and no extra adopted edge |
| Boundary `contract_status`, `contract`, `pinning` | Same named review evidence; `required` remains a contract delivery gap, never a passed adoption check or fabricated `blocks` relationship |
| Immutable owner files and revision | Separate catalog, context and boundary provenance sources |
| Explicit consumer commit | Root projection identity; existence checked from Git objects without evaluating checkout content |
| Explicit public allowlist | Authorization before endpoint indexing, graph expansion, boundary lookup, rendered counts or links |

No relationship is inferred from a package manifest, source import, prose name,
activity, contract permission or version expectation. Transitive paths consist
of their direct edges; the collector does not create shortcut closure edges.
Lifecycle is architecture intent, independent of operational Health, provider
Status, release availability and runtime adoption. These remain uncollected.

The closed alpha.2 coverage object keeps its existing **nine** domains. This
collector adds no dependency domain and claims none of the other inventories.
Repository entities and declared dependency edges can exist while all nine
collection claims remain `uncollected`; the review scope explicitly identifies
this bounded declared graph. Existing Dependencies rendering retains that
uncertainty alongside source-linked edges.

## Supported source profile

[`dependency-collector.v1.lock.json`](../actions/repository-intelligence/contracts/dependency-collector.v1.lock.json)
binds the existing native alpha.2 owner set, plus the complete public
catalog/context/boundary artifacts and their owner validators at Hygiene
`fa41ccc95d0cd0365b38008e02bdc67b928c5ed2`. This source contains accepted catalog
output-handling repairs, but its registry observation is still August 21 and
its `website` identity remains unresolved. No alias is guessed.

Hygiene's schema and reference tools validate the exact locked public corpus.
The existing pinned EgoLint coverage validator and Hygiene/Observatory adapter
then validate and normalize the projected graph. The runtime lock retains
EgoLint `d917ea524962639494e5bb4b3196192238ba57d9`, Hygiene graph alpha.2
`639a003d5ddc4d242c2cf190eeb59a9fc522d199`, and Observatory alpha.2
`f411b83398dd07aa3d5e6e2c89d1e8dfff746085`. Full trees, artifact hashes, prepared
runtime/executable receipts and collector adapter digests remain inspectable.

This initial profile admits **only those immutable public source artifacts**.
It does not accept arbitrary mixed-visibility catalog files, current GitHub
inventory, a replacement registry, approved boundary exceptions, or a new
namespace model. The exact pinned corpus is checked public before its owning
validators run; operational allowlisting applies again before any graph lookup.
This supports a useful versioned source slice while preserving Hygiene #36's
separate catalog-minimum/public-allowlist acceptance gate.

## Local commands

Use the native dependencies and offline acquisition preparation described in the
[ADR collector guide](repository-adr-collector.md#native-commands-and-reproducible-checks).
This profile requires its own newly prepared runtime because it includes the
additional checksum-bound owner corpus and validators. Existing ADR runtimes
do not contain those artifacts and are rejected.

```bash
python actions/repository-intelligence/scripts/collect_repository_dependencies.py prepare \
  --hygiene /trusted/hygiene --egolint /trusted/egolint \
  --observatory /trusted/observatory --output /trusted/dependency-runtime

python actions/repository-intelligence/scripts/collect_repository_dependencies.py collect \
  --runtime /trusted/dependency-runtime --repository-root /sources/relay \
  --repository egohygiene/relay --visibility public \
  --source-commit b4a88db20bc26f9ddefbee174baa8162cbe94ff2 \
  --observed-at 2026-11-09T00:00:00Z \
  --public-repositories '["egohygiene/relay","egohygiene/egolint"]' \
  --maximum-depth 2 \
  --output /review/relay/dependency-collection.review.json
```

The JSON array is a caller-selected public projection allowlist for review,
not a new canonical catalog or a claim that Hygiene #36 is accepted. Root and
every reached endpoint must resolve to public entries in the selected source;
unknown and renamed endpoints yield a fixed owner diagnostic. Unvisited
allowlist entries are inert. Excluded endpoints
are ignored before lookup and create no names, counts, placeholders, inferred
gaps or diagnostics. Their original prose is never copied into output.

The same profile can express the public declaration chain Observatory → Relay
→ EgoLint by selecting those three identities and an existing immutable
Observatory consumer revision. This is a source mapping example, not a claim
that a native run, rendered canary or public deployment has been executed.

`--maximum-depth` accepts 1–8 and bounds upstream expansion. Output always
identifies its graph as bounded; it never reports whether excluded or deeper
topology exists. The captured public-only dependency representation is hashed;
there is no raw mixed-catalog payload hash or excluded-entry count. Limits are
256 visible nodes, 2,048 direct edges, 16 KiB of allowlist text and 8 MiB per
closed review artifact. Output must use the fixed filename outside the consumer
checkout; runtime execution must also remain outside it.

`--collected-at` defaults to the explicit observation boundary. A retained
capture keeps its original time; `--maximum-age-seconds` defaults to 86,400.
`--maximum-catalog-age-days` defaults to 30 and accepts 1–3,650. The catalog's
historical owner observation and capture age both affect freshness; fetching
the same outdated registry again does not make its intent current.

Forbidden or unsupported declared pairs fail with bounded Hygiene remediation;
the collector does not silently approve a source inconsistency. Cycles are
delegated to Hygiene's existing graph validator. Fixed diagnostics retain no
provider text, private topology, raw paths, process logs or exception excerpts.
Ready and invalid candidates preserve their normalized evidence; a denied
invocation writes only the closed denial artifact at a verified safe location.

Exit 0 means the supported bounded declared graph is ready for local review,
including visibly stale intent. Exit 2 retains an invalid graph. Exit 3 records
an input, identity, boundary or runtime denial. Publication remains denied for
all exits. No action/workflow, permission, provider, site or consumer-owned
publication boundary changes in this checkpoint.

## Deferred acceptance

Per the maintainer's direction, tests, actual native preparation/collection,
real-source rendering, replay, private-boundary fixtures and CI were deferred.
Only static syntax, JSON and diff inspection and peer review were performed.

Before build admission, verify native source and graph validation, real Relay
and multi-step public canaries, malformed/unknown/renamed/disallowed endpoints,
cycles, stale catalog behavior, deterministic cross-checkout replay, and output
invariance under excluded-data changes. Hygiene #36 still owns current
inventory, renames and the accepted public allowlist. Broader mixed/private
catalog support needs an owner-approved public projection contract before this
profile can expand; it cannot be supplied by a Relay-local coverage field.
