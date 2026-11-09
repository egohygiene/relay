# Repository Intelligence completion candidate

Refs [Relay #27](https://github.com/egohygiene/relay/issues/27),
[#33](https://github.com/egohygiene/relay/issues/33),
[#101](https://github.com/egohygiene/relay/issues/101), and
[organization #41](https://github.com/egohygiene/.github/issues/41).

Repository Intelligence is a portable subtree in **each consumer repository's
existing Pages artifact**. The organization site is a fleet overview, with
drill-down links into those independently owned publications. Relay builds;
the consumer retains its one Pages artifact and deployer. No central React
implementation is required by a repository dashboard.

## Review the shared product first

This candidate extends `codex/intelligence-source-domains` (Relay #166), which
already combines the earlier collector slices. Its commits keep route-profile
alignment, graph presentation, capture transport and bounded rendering fixes
separately reviewable. The existing ten focused renderers are retained: Now,
Roadmap, Decisions, Journey, Dependencies, Health, Releases, Work, Search and
Compare. Their closed feature issues are not reopened or reimplemented.

The [route handoff](repository-intelligence-routes.md) consumes the already
pinned Hygiene registry. All eighteen subtree routes, including overview and
the compatibility dashboard, are recorded in deterministic `routes.json`.
Six registered domains have explicit unsupported-source pages; that supplies
navigation and ownership, not completion of their upstream models. Consumer
Status and product Identity remain outside this subtree.

The [portable graph](repository-intelligence-navigation-graph.md) enhances the
overview and compatibility dashboard. It
distinguishes navigation/grouping connections from explicit directed owner
relationships. Static node and relationship directories retain source links,
assertion and freshness without JavaScript. Relative destinations preserve a
consumer's project Pages prefix. A missing semantic snapshot still permits
navigation and explicitly reports unavailable evidence.

The action runs the graph stage before creating its deterministic build
manifest. Bundle validation admits the exact registered route/asset inventory,
the exact pinned route handoff and canonical graph asset bytes. Duplicate
JSON members are rejected. Existing overview-only and ten-view inventories
remain structurally recognizable, but **historical recovery must continue
using its original pinned helper and bytes**. Current canonical asset checks
do not requalify an old recovery artifact.

The [Now blocker correction](repository-now-blockers.md) fixes an existing
shared renderer mismatch: enriched relationships previously appeared as
untitled entities. Blockers now retain directed endpoint labels, independent
endpoint/edge states, freshness, assertion, source links and relationship IDs.
Both endpoints must be public before their metadata enters a public card.

## Source collection and consumer upgrades

Canonical `collect-adrs` and `collect-roadmap` remain opt-in. Fresh Work/Health
capture composition uses an explicit evaluation boundary; transport must bind
the same repository and represented commit. A collector's publication-denied
review envelope is not an accepted snapshot. Missing evidence cannot become
an empty domain, conformance, human acceptance or publication success.

The [capture-artifact handoff](repository-capture-artifact-intake.md) accepts
only exact ordinary artifact IDs and archive digests from the same public
repository, head, run and attempt. A producer packs referenced JSON only;
the consumer verifies provider metadata, bounded ZIP contents and source
bindings before fresh collection. Private admission proof is retained with
the run report, outside deterministic site bytes. Missing proof fails the
capture run even if an ordinary site artifact was already uploaded.
`repository-intelligence-captures.yml` adds the required `actions: read` scope;
the original reusable workflow and its existing callers keep their permission
contract. This initial capture entrypoint supports push/manual events only.

Consumers adopt an exact reviewed Relay commit in their current builder and
matching provenance/source-binding helpers. Preserve their unrelated product
assets, canonical domain/base path, real source opt-ins, redirect ownership,
deployment permissions and scheduling. Preserve frozen rollback pins,
manifest digests, restore order and historical receipts byte-for-byte. A
candidate pin upgrade does not establish a new qualified rollback point.

Bounded adoption candidates target the existing Identity, Hygiene, Akashic,
Empathy and OptiFlow publishers. Identity already composes real ADR-backed
Intelligence with the Brand Kit; its active publication drafts overlap the
same workflow and must be reconciled during review. Hygiene still requires
real ADR metadata/human approval. Akashic's native roadmap remains blocked on
its canonical prerequisite-state defect. Existing source opt-ins are retained;
the generator must not rewrite those states or enable collection prematurely.

## Fleet overview and remaining work

The central site drafts remain optional fleet exploration.
[Site #126](https://github.com/egohygiene/egohygiene.io/pull/126) adds a publication
catalog supplying explicitly declared public consumer destinations and proof;
repository names cannot determine a custom Pages domain. Missing or invalid
destinations remain unavailable, and source-revision mismatches remain visible.
The directory and graph use consumer Pages as primary navigation and canonical
GitHub sources as secondary evidence.

Audits, Hygiene, Sanity, Diagnostics, Distribution and Identity adoption still
require their accepted owner projections. No public source migration, human
decision or parent issue disposition is supplied by this candidate. Broader
fleet adoption remains Pace #13's work.

Tests, native runtime execution, builds, CI investigation, browsers, canaries,
publication and release closeout were deferred for this implementation pass.
Static syntax and peer source review cannot establish those outcomes. The
next executable pass should exercise complete source composition, artifact
identity/hash denial, reproducible bundles, public/private projection,
project-path navigation and the existing consumer publication/recovery paths
before acceptance under #101 or organization #41.
