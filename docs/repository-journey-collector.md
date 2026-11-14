# Immutable Git Journey collection — Relay #147

The local collector reads one explicitly public repository at a full immutable
commit, emits existing Hygiene commit entities and `commit.created` events,
validates through the existing pinned native runtime, and asks Observatory to
build the current Journey read model. It does not execute consumer code or
change the inspected checkout. Every review result retains `publication: denied`.

## Mapping and current scope

| Captured input | Existing owner representation |
| --- | --- |
| Explicit repository and represented commit | Stable repository root, projection identity and immutable source URL |
| Reachable bounded Git commit object | `commit` entity with native SHA key, `recorded` state and `attributes.sha` |
| Committer's Unix instant | UTC `commit.created.occurred_at`; the identity portion is never exported |
| Explicit capture time | Source observation and event recording time; separate from historical occurrence |
| Explicit public-subject opt-in | Bounded sanitized entity title; default title is `Commit <short SHA>` |
| Original commit messages | Native EgoLint trailer syntax validation in a fresh temporary Git corpus; bodies, names, emails and signatures stay local |
| Bounded ancestry, shallow checkout, time window | Independent scope flags and conservative Git coverage |
| Commit-only events | `history: partial/incomplete`; other semantic/provider domains stay `uncollected` |

The immutable sources and source-object SHA-256 receipts bind exactly what was
inspected. No tag, branch, working directory name, current checkout file or
runtime clock becomes evidence. Commits are ordered by timestamp and stable
event ID through Observatory, which supplies existing unreleased Journey
chapters. Commit events do not declare roadmap completion, ADR acceptance,
release publication or causality.

No versioned owner contract currently maps public parent topology into Journey.
Parents are inspected only to construct the bounded native validation corpus;
they are not exported. Native `Roadmap-Step` and `ADR-Ref` trailer checks preserve
syntax diagnostics, with canonical ADR/roadmap adoption explicitly unknown.
Reference resolution remains unavailable; missing or external targets are never
fabricated. Enrichment from an admitted same-revision canonical domain needs a
separate reviewed mapping. Provider lifecycle acquisition is not attempted.

## Exact supported native inputs

This slice uses the existing
[`adr-collector.v1.lock.json`](../actions/repository-intelligence/contracts/adr-collector.v1.lock.json)
without changing any pin: Hygiene alpha.2 projection at
`639a003d5ddc4d242c2cf190eeb59a9fc522d199`, native EgoLint at
`d917ea524962639494e5bb4b3196192238ba57d9`, and Observatory alpha.2 at
`f411b83398dd07aa3d5e6e2c89d1e8dfff746085`. The existing lock additionally binds
the accepted ADR policy and full artifact/tree hashes. An already prepared ADR
runtime is compatible; roadmap's older review-only runtime is not.

EgoLint validates original trailer syntax and explicit nine-domain coverage.
Hygiene validates projection structure and vocabulary. Observatory validates and
normalizes the projection and read model. Uncollected canonical ADR/roadmap
surfaces keep the native source report `incomplete`; this is preserved separately
from successful bounded Git collection. Native messages and paths are not
copied into public diagnostics: only a stable owner rule, checked commit location
and generic remediation survive.

## Local usage

Use the dependencies and offline acquisition instructions in the
[ADR collector guide](repository-adr-collector.md#native-commands-and-reproducible-checks).
Preparation reads locked upstream Git objects and builds only trusted owner code.

```bash
python actions/repository-intelligence/scripts/collect_repository_journey.py prepare \
  --hygiene /trusted/hygiene --egolint /trusted/egolint \
  --observatory /trusted/observatory --output /trusted/journey-runtime

python actions/repository-intelligence/scripts/collect_repository_journey.py collect \
  --runtime /trusted/journey-runtime --repository-root /sources/relay \
  --repository egohygiene/relay --visibility public \
  --source-commit b4a88db20bc26f9ddefbee174baa8162cbe94ff2 \
  --observed-at 2026-11-09T00:00:00Z \
  --maximum-commits 256 \
  --output /review/relay/journey-collection.review.json
```

Paths are caller-selected absolute locations. The fixed output filename must be
outside the consumer checkout. Output writes are bounded, validated against the
closed review-envelope schema and replaced atomically. The supported snapshot
candidate is embedded for inspection; the review envelope itself is not a
production build input.

`--since` and `--until` are inclusive UTC timestamps selecting the presentation
window within the bounded ancestry. Each explicit window keeps Git coverage
partial, even when no selected record falls outside it. `--maximum-commits`
accepts 1–256; reaching the bound with older ancestry, a shallow checkout, or
withheld malformed/future timestamps also keeps Git coverage partial. No
filtered empty set proves that the repository has no commits. The Git scan
remains bounded independently of the time window.

Every captured object must be inspected by native EgoLint. At a truncated merge,
Git's shallow marker also hides selected parents of that merge. The adapter
partitions the **unchanged logical selection** into disjoint native-reachable
corpora. The first native root is the represented source; supplemental roots
are original selected branch heads, authenticated through original parent
headers and exact object hashes. No commit is dropped, duplicated, rewritten or
invented to fit the native traversal.

For every pass, the exact reachable SHA set must equal that corpus; the native
report must match its real original root, repository, catalog, contracts, schema
and exact inspected count. The unique union and summed counts must both equal
the original selection. A mismatch still denies admission. The caller's 1–256
logical-commit cap and 2 MiB source-object bound are unchanged. All passes share
one 60-second deadline rather than receiving separate 60-second allowances.

These are multiple genuine native reports, composed internally by Relay, not a
synthetic native report claiming the original source was inspected in one pass.
Any native invalid result remains invalid; native incomplete ADR/roadmap domains
remain incomplete. Diagnostics stay bounded and sanitized. Private inspection
details never enter the public envelope, whose source, clocks, records and
truthful truncated coverage remain unchanged.

`--collected-at` defaults to the explicit observation time. Replaying a previous
capture must keep its capture time; `--maximum-age-seconds` defaults to 86,400
and accepts 1–2,678,400. Capture freshness remains separate from the immutable
historical event's `not_applicable` freshness.

`--public-subjects` explicitly opts into first-line subjects from the authorized
public corpus. Control characters and formatting controls are removed; URLs and
repository/path references are omitted; credential-, email- and local-path-shaped
subjects use the generic SHA title. Bodies and actor identities are never
exported. This bounded sanitization is not semantic review: use generic default
titles for sources whose subject text has not been reviewed for disclosure.

Exit 0 means the bounded requested Git inventory is ready for local review; its
cross-domain history still remains partial. Exit 2 preserves partial or invalid
collection. Exit 3 retains a fixed-code denial when the safe output location is
usable. Raw exception text, source prose, process logs and local paths never
enter failure artifacts. Bounds are 256 KiB per object, 2 MiB of captured commit
objects and 8 MiB per review envelope.

## Review and remaining acceptance

This checkpoint contains implementation and operator instructions. Per the
maintainer's current direction, automated tests, native runtime execution,
real-source rendering, reproducibility replay and CI were deferred. Syntax and
diff inspection do not prove those gates.

Before admission to consumer builds, execute real pinned native validation,
complete and shallow/time-filtered/large/malformed histories, public-text and
failure-path checks, equal-envelope replay across differently named checkouts,
and actual Journey rendering. Then review source-plan composition, immutable
consumer adoption, ordinary preview artifact, consumer-owned publication and
live output separately. No action/workflow, permission, deployment, rollback or
consumer source is changed by this local collector.
