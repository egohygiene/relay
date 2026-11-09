# Production Journey and Releases source composition — Relay #151

The existing immutable Git Journey collector (#147) and public release/deployment
collector (#149) now join the same production source plan as Decisions, Roadmap,
Work and Health. The builder freshly invokes each selected collector, checks its
closed receipt, composes owner-defined graphs and normalizes the result through
the unchanged exact Hygiene/EgoLint/Observatory selections. It never promotes a
saved publication-denied review envelope into production evidence.

## Git Journey selection

The composite and both reusable workflows accept these optional inputs:

| Input | Default | Boundary |
| --- | --- | --- |
| `collect-journey` | `false` | Read immutable Git objects at the represented source revision |
| `journey-maximum-commits` | `256` | Integer from 1 through 256; truncation remains partial |
| `journey-since` | empty | Inclusive UTC lower event bound, to whole seconds |
| `journey-until` | empty | Inclusive UTC upper event bound, no later than `as-of` |
| `as-of` | represented commit time | Explicit evaluation clock when the caller selects one |

Bounds require Journey selection. Relative Git date expressions are not accepted
for these evidence windows. `activity-since` remains a separate diagnostic and
analytics input. The public production path always uses generic `Commit <sha>`
titles; commit bodies, subjects, author identities, emails, signatures, paths and
trailers do not enter these receipts or public graph records.

```yaml
with:
  collect-adrs: true
  collect-journey: true
  journey-maximum-commits: "256"
```

This input fragment belongs on the caller's existing immutable Relay selection;
it is not an independently executable workflow. Select ADRs or Roadmap only when
those canonical sources exist and pass their own admission at the same commit.
Journey may also run alone. All native selections exclude external snapshot and
comparison inputs, preserving the prior external-snapshot path when no native
source is selected.

Git inventory describes only the declared ancestry, count and time boundary.
Shallow, truncated, filtered and withheld-timestamp scopes remain independent
receipt flags. Semantic history is always partial. Provider lifecycle events,
parent topology and declared-reference resolution remain uncollected/unavailable;
Git collection does not supply them. Native inspection must cover every captured
commit before the projection is admitted. The existing collector guide records
the [mapping and remaining acceptance](repository-journey-collector.md).

## Public Releases and deployment capture selection

Extend the existing closed `source-capture-plan/v1` with an optional `releases`
selection. Its paths are data-only and relative to the consumer root for local
captures, or the private artifact root for same-run artifact intake:

```json
{
  "schema": "egohygiene.relay.source-capture-plan/v1",
  "releases": {
    "capture": "release-provider.json",
    "public_environments": ["github-pages"],
    "deployment_receipts": [],
    "maximum_age_seconds": 86400
  }
}
```

The referenced capture must be an actual public-only
[`release-provider-capture/v1`](../actions/repository-intelligence/schemas/release-provider-capture.v1.schema.json)
for the represented repository and commit. It retains independent release and
deployment inventory status, original observation times, pages and pagination.
`capture: null` explicitly selects unavailable provider evidence; it cannot select
receipt files. An empty complete inventory is different from unavailable or
uncollected evidence. The builder never infers complete scope from an empty page.

Declare public deployment environments before supplying deployment records or
receipt files. At most 64 unique environments and eight receipt files can be
selected by a transport plan. Exact deployment receipts retain their original
source revision, generator revision, run/attempt, environment, time and hashes;
their content must match the captured deployment observation. Historical
deployment and release target commits must actually exist in the inspected
repository. No capture or receipt SHA/time is rewritten to the current head.

Local/composite calls use `source-captures` with an explicit `as-of`. Reusable
calls use the existing exact same-run artifact handoff, through
`repository-intelligence-captures.yml`. Both invoke fresh collection after
transport admission. The ordinary reusable workflow supports Git Journey and
canonical sources; it retains its existing `contents: read` ceiling. Captures
remain in the separate `actions: read` entrypoint, limited to the existing trusted
push/manual event seam. No checkout file must embed its own containing SHA.

The artifact pack/admit/reverification path also checks release public-only
declarations and the explicit public environment allowlist. The closed bundle
allows fifteen payload files, 1 MiB per capture, 64 KiB per plan/manifest,
16 MiB expanded and 20 MiB archived; all prior path, hash, duplicate, compression
and executable-file denials remain. Raw JSON never enters site bytes or the
ordinary retained run report. See the [artifact guide](repository-capture-artifact-intake.md).

Release publication, prerelease, retraction, deployment conclusion, receipt proof
and installation remain different facts. The release collector's existing
supported mapping is unchanged; it does not infer installation, asset availability
from build success, or successful publication from a merged change. Distribution
and installation source models remain separate owner work.

## Local preparation and immutable generator proof

The direct CLI accepts `--collect-journey`, `--journey-maximum-commits`, optional
`--journey-since`/`--journey-until`, and `--collect-releases` with
`--release-capture`, repeatable `--release-public-environment` and
`--release-deployment-receipt`, plus `--release-maximum-age-seconds`. A release
selection also requires the real immutable `--generator-commit`.

The release collector verifies every executed helper and owner-selection file
against Git objects at that exact Relay generator commit. Installed Actions are
archives without `.git`, so automatic runtime acquisition separately fetches a
bare proof from the fixed public `egohygiene/relay` origin at the resolved full
generator SHA. It performs no Relay checkout or source-code execution. The
capture plan cannot select that origin, revision, executable or proof directory.
The final release receipt must match the site's actual generator identity.

`--runtime` and typed runtimes remain offline selections. Offline release calls
must run from a matching real Relay Git source or supply a trusted
`--generator-repository-root` containing that exact commit. An installed archive
plus an explicit prepared runtime does not silently enable a network fetch or
manufacture a source proof. Only the automatic acquisition path fetches it.

All selected source runtimes retain exact compatible core pins. The release
profile is a verified subset of the existing ADR runtime; only already verified
files and the exact executable are copied into a private per-domain profile.
Historical review locks remain unchanged.

## Coverage, commit identity and review artifacts

Journey and Releases can independently mention the same commit. Composition
merges only identical repository/SHA/canonical-URL identities. An independently
inspected Journey commit retains its generic title, recorded state and immutable
freshness; release/deployment provenance is added while every release source,
edge, event, assertion and capture clock stays unchanged. Other record conflicts
fail closed. Release-only targeted commits remain marked as targeted observations.

Journey's Git coverage survives unchanged only when every release target SHA is
already in its projected Git inventory. Extra targets downgrade the union to
partial scope; two partial sources never create a complete inventory. Combined
history remains partial, retaining conservative staleness and the oldest admitted
observation boundary. Each original domain receipt remains independently
inspectable, including raw-object hashes, projected commit identities, target
counts, inventory scope and per-source validation/pins.

Successful preparation still writes the same private `projection.json`,
`snapshot.json` and completion `receipt.json`. A denied invocation removes its
candidate triple and writes bounded `failure.json`; no prior candidate is reused.
All site renderers and the graph receive the selected combined snapshot before
the final deterministic build manifest is created. Public provenance binds
source receipts and exact implementation hashes; run-specific artifact proof
stays in ordinary private evidence.

Only source/schema/syntax/diff inspection and independent static peer review are
included in this slice. No native collectors, tests, builds, CI, provider calls,
consumer capture, publication or rollback rehearsal was executed. Real-source
replay, equal complete bundles across checkout names, privacy denial cases,
consumer route preservation and hosted acceptance remain explicitly deferred.
Refs #147, #149 and #151; no source or human disposition is inferred.
