# Repository Intelligence production data paths

Refs Relay #148, #153, #146, #149, #150, #152, #75 and
[the organization parent](https://github.com/egohygiene/.github/issues/41).
These implementation slices do not close the later qualification gates.

## Repository Pages and fleet overview

Each repository owns one Pages publication containing its Intelligence subtree.
The shared action collects and renders evidence without deploying it. The
organization site aggregates public repository snapshots and links into those
repository-owned destinations; it is not a replacement publisher.

The existing native action and both reusable workflows expose
`collect-dependencies: true`. This collects only bounded declared consumption
from the exact reviewed Hygiene public catalog and authored declarations.
Runtime/package adoption and excluded topology remain uncollected. Dependencies
add no new key to the closed nine-domain coverage model.

Native preparation accepts `--collect-dependencies` and an optional trusted
`--dependency-catalog` Git source outside the consumer checkout. Without that
source it acquires the exact owner revision privately; a prepared normalizer
alone does not make catalog acquisition offline. The existing old runtime and
review-only collector remain unchanged. See [the source guide](dependency-source-build.md).

Use a fresh explicit evaluation clock at or after the public admission capture.
Current push/manual consumers obtain that clock from the actual GitHub source
producer. Historical replay, release recovery and paths without fresh captures
retain their prior selections; a new catalog observation is not backdated to an
old commit timestamp.

The [GitHub Sources action](../actions/repository-intelligence-github-sources/README.md)
feeds Work/Now, exact-commit Health and published Releases through the existing
same-run immutable artifact intake. Its captured inventories remain bounded,
partial, unavailable or failed as observed. Deployment evidence requires a real
consumer run-attempt receipt and remains uncollected without one.

The [fleet artifact handoff](public-fleet-artifact-delivery.md) consumes explicit
successful retained repository artifact identities. It provides no discovery,
latest-run selection, mutable baseline pointer or second publisher. The central
host binds exact fleet and manifest bytes, freshness, expiry and partial state.
Real provider runs and artifact identities must be supplied during qualification.

## Optional owner-backed Hygiene input

`observatory-hygiene` names a repository-relative normalized owner conformance
JSON file outside the published subtree. It requires explicit `as-of`; the
owner model must match that evaluation clock, repository and represented commit.
It can accompany the native source plan or a compatible external core snapshot.
The owner query and input format are documented in
[the Hygiene view guide](repository-intelligence-hygiene.md).

The builder executes the exact owner validator, retains a closed
`provenance.hygiene_conformance` receipt and renders the existing Hygiene route.
Only that validated receipt enables the route's implemented state. The same
receipt binds page identity and navigation freshness without inserting an
unsupported domain into the core snapshot or adding another published asset.
The complete bundle inventory stays at 30 files.

The page shows supplied contract/version, required/advisory severity, reported
and effective status, revision, observation/expiry and source evidence. Whole
applicability and contract inventory remain unknown even when every supplied
assessment passes. Owner-admitted links outside the host's narrower URL policy
remain complete escaped text instead of broadening global link authority.
Absent owner input preserves the explicit source-unsupported page.

## Compare and integration review

The [Compare action](repository-intelligence-compare-artifact.md) can compose an
admitted comparison after the native build, preserving the fresh source receipt
and all payload bytes outside Compare. Its final manifest and bundle digest
replace the earlier builder outputs for downstream composition. Manual consumer
selection defaults off; seed supplies the first real pair without inventing a
baseline, and compare requires the complete exact retained prior selection.

The original review drafts Relay #158–#166 and site #118–#125 are closed as
superseded by merged Relay #167 and site #126. Their original branches remain
available. Unrelated website draft ancestry was not imported or marked merged.
Current functional source and consumer PRs are the review entry points.

Static source, schema and metadata review is distinct from running the code.
Tests, builds, native normalization, actual API/artifact transport, CI, browsers,
consumer publication and rollback qualification remain deferred at the
maintainer's request. Implementation merges do not establish successful uploads,
deployments, human ratification or parent issue completion.

## Organization sanity sweep after the owner foundations

The next owner-backed chain is Audits:
[Aether #86](https://github.com/egohygiene/aether/issues/86) →
[Observatory #20](https://github.com/egohygiene/observatory/issues/20) →
[Relay #74](https://github.com/egohygiene/relay/issues/74).
Sanity depends on [Hygiene #59](https://github.com/egohygiene/hygiene/issues/59),
[Aether #87](https://github.com/egohygiene/aether/issues/87),
[Observatory #21](https://github.com/egohygiene/observatory/issues/21) and
[Relay #76](https://github.com/egohygiene/relay/issues/76).

Once those structured owner contracts and pages exist, run a separate
organization sweep over the reviewed public repository roster. Retain each
repository's exact source revision, audit profile/version, structured findings,
applicability gaps, explicit review dispositions and evidence references.
Aggregate findings and coverage without turning absent audits into passes or
passing checks into architectural acceptance. Actual human ratification remains
its own evidence; the sweep cannot create it. No sweep was executed by these
implementation changes.
