# Intelligence implementation review

This candidate set advances the source collection and composition required by
[organization acceptance #41](https://github.com/egohygiene/.github/issues/41).
It is implementation for review. Tests, native runtime replay, full builds, CI
investigation, browser verification, consumer canaries, publication and stable
release acceptance remain deferred. Existing automated repository workflows may
run on these branches; no result from them is claimed here.

## Repository-hosted product and fleet overview

The primary continuation is now
[`codex/repository-intelligence-completion`](https://github.com/egohygiene/relay/tree/codex/repository-intelligence-completion),
stacked on [Relay #166](https://github.com/egohygiene/relay/pull/166).
Read the [shared completion guide](repository-intelligence-completion.md) first:
each repository owns its Pages Intelligence subtree, and the organization site
provides the fleet overview and drill-down links. The existing ten repository
renderers have already shipped; this continuation addresses shared route,
graph, evidence-intake and consumer-adoption gaps.

The central endpoint exploration is preserved in
[site #125](https://github.com/egohygiene/egohygiene.io/pull/125), with independent
slices #119–#124. Those drafts are fleet exploration and do not establish
completion of repository-hosted views or unsupported upstream source models.
[Site #126](https://github.com/egohygiene/egohygiene.io/pull/126) makes declared
repository Pages destinations primary while retaining canonical GitHub evidence.

## Earlier sliced review queue

| Review | Draft | Scope and practical limit |
| --- | --- | --- |
| 1 | [Relay #158](https://github.com/egohygiene/relay/pull/158) | Native Roadmap + Decisions source composition, action/workflow opt-in, exact source plan and provenance. Initial native plan covers these two domains. |
| 2 | [Relay #159](https://github.com/egohygiene/relay/pull/159) | Captured Work/Now issue and PR evidence. Offline collection; canonical roadmap priority is not inferred. |
| 2 | [Relay #160](https://github.com/egohygiene/relay/pull/160) | Immutable Git Journey collection. Shallow/truncated scope stays explicit; parent topology and semantic reference enrichment remain unsupported. |
| 2 | [Relay #161](https://github.com/egohygiene/relay/pull/161) | Revision-bound Health report/check captures. Execution and findings remain separate; original capture times survive. |
| 2 | [Relay #162](https://github.com/egohygiene/relay/pull/162) | Captured Releases/deployment observations, public asset links and receipt matching. No release or deployment authority. |
| 3 | [Relay #164](https://github.com/egohygiene/relay/pull/164) | Declared Dependencies through exact public Hygiene catalog/context/boundaries. Initial profile accepts a fixed public owner corpus. |
| 3 | [Relay #165](https://github.com/egohygiene/relay/pull/165) | Public fleet assembly using the existing Observatory model. Reviewed production catalog/public selection remains Hygiene #36's acceptance. |
| 4 | [Relay #163](https://github.com/egohygiene/relay/pull/163) | Exact projection/snapshot retention and Compare, including leases and truthful failed refresh state. Hosted retention and real two-revision proof remain open. |
| 5 | [Site #118](https://github.com/egohygiene/egohygiene.io/pull/118) | Content-first `/intelligence/` host, build-time fleet admission, directory/Now/coverage/source drilldowns and canonical static routing. Stacked on the existing site #117 draft; no live artifact or publication. |

The source collector drafts retain publication-denied review artifacts. They are
not automatically admitted by #158's two-domain native build. Expanding that
source plan requires explicit source authority, scope and conflict rules rather
than copying generated views or promoting a review envelope.

## Combined Relay checkout

Branch `codex/intelligence-review-all` combines the reviewed implementation
commits for the Relay slices above, preserving their individual commits and
excluding their competing per-PR checkpoint refresh commits. It is a convenience
checkout for the deferred integration/validation pass, not an extra merge or
publication path. No combined runtime/build acceptance is claimed.

The independent drafts each update `CONTINUITY.md`. Reconcile that one handoff
semantically in the chosen merge order; do not concatenate eight current
objectives. The canonical guides remain with their owning code:

- [Native source composition](repository-source-composition.md).
- [Work collection](https://github.com/egohygiene/relay/blob/codex/intelligence-work-source/docs/repository-work-collector.md).
- [Journey collection](https://github.com/egohygiene/relay/blob/codex/intelligence-journey-source/docs/repository-journey-collector.md).
- [Health collection](https://github.com/egohygiene/relay/blob/codex/intelligence-health-evidence/docs/repository-health-collector.md).
- [Releases collection](https://github.com/egohygiene/relay/blob/codex/intelligence-release-source/docs/repository-release-collector.md).
- [Declared Dependencies](https://github.com/egohygiene/relay/blob/codex/intelligence-dependency-source/docs/repository-dependency-collector.md).
- [Public fleet assembly](https://github.com/egohygiene/relay/blob/codex/intelligence-public-fleet/docs/public-fleet-assembler.md).
- [Compare retention](https://github.com/egohygiene/relay/blob/codex/intelligence-compare-retention/docs/repository-intelligence-snapshot-retention.md).

The peer guides exist on their owning branches and the combined checkout; they
are intentionally not copied into #158's bounded source-composition patch.

## Organization host checkout

The ninth candidate is [egohygiene.io #118](https://github.com/egohygiene/egohygiene.io/pull/118),
branch `codex/organization-intelligence-host`, based on the existing
[#117](https://github.com/egohygiene/egohygiene.io/pull/117) head
`a7e15c7b1543dcba01647ec8ff358aab5126c817`. Its PR targets that draft branch,
`docs/sprint-closeout-roadmap-2026-11-09`, to preserve the active website stack.
It is a separate repository and is not part of the combined Relay checkout.

The [site operator guide](https://github.com/egohygiene/egohygiene.io/blob/codex/organization-intelligence-host/docs/development/organization-intelligence-27.md)
describes the reviewed standalone fleet artifact, checksum and explicit
observation boundary. No artifact is connected by default. The host does not
promote Relay's publication-denied review envelope into a deployment approval.
Future modules remain labeled navigation anchors, rather than claimed route
implementations. Existing store behavior stays in its owning stack.

## Validation boundary

Static peer review found and corrected contract, source-binding, capture-time,
URL, checksum and failure-isolation defects. Python/JSON syntax, applicable
YAML/bash syntax, site Node syntax, whitespace and continuity metadata were inspected. These are
source inspections, not native runtime, privacy regression, accessibility,
performance or end-to-end proof.

The next executable pass should cover the pinned native source paths, adversarial
and partially adopted inputs, matching/mismatched revisions, complete bundle
reproducibility across checkout paths, public projection invariance, retained
baseline recovery and consumer-owned composition. Browser, hosted, canary,
deployment and release evidence follow in their existing owning issues.

## Remaining owner and product gates

Hygiene #36 still owns accepted production catalog/public selection. Human ADR
approval or canonical source migration cannot be fabricated by collectors.
Upstream-dependent Search attribution, Diagnostics, Audits, Hygiene and Sanity
remain separate work; this set introduces no competing canonical models for them.

No parent or route acceptance issue is advanced to complete by this draft set.
The organization host's own runtime route, static rendering and deployment acceptance
remain distinct from a local fleet artifact. Consumer-owned rollback bytes and
historical receipts are preserved.
