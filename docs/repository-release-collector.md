# Captured release and deployment collection — Relay #149

This is a local, offline review adapter. It consumes an explicitly public,
closed provider capture at one represented repository revision and observation
boundary. It never contacts a provider, executes consumer code, publishes a
release, deploys a site, or treats a build as publication. Refs #149.

## Mapping and owner selections

Hygiene owns the existing graph and nine-domain coverage semantics, EgoLint
owns coverage validation, and Observatory owns normalized Releases and Journey
views. Relay owns this bounded capture interface and execution only.

The independent `release-collector.v1.lock.json` selects the same graph-compatible
sources as the current ADR collector: Hygiene projection
`639a003d5ddc4d242c2cf190eeb59a9fc522d199`, EgoLint
`d917ea524962639494e5bb4b3196192238ba57d9`, Observatory
`f411b83398dd07aa3d5e6e2c89d1e8dfff746085`. Full Git trees and owner-file hashes
bind preparation. There is no new canonical release or asset schema in Relay.

| Captured input | Existing projection |
| --- | --- |
| Repository identity, represented full commit, observation UTC | Root identity; exact Git commit must exist; no checkout-path identity |
| Public release ID, tag, published time, target full commit, prerelease/retracted state | Existing `release` entity keyed by stable provider ID; tag retained in title/attributes; canonical GitHub release URL; exact source revision retained separately |
| Explicit released commit | Existing `commit` entity and `release → releases → commit`; no inferred issue/PR membership |
| Release publication observation | Existing `release.published` event from the explicit publication timestamp, including a formerly published release now retracted; no retraction event or inferred transition is created; historical event time differs from capture time |
| Public asset name, size, optional SHA-256 | Closed release attributes; canonical unsigned download URL derived from repository/tag/name; no invented asset entity kind |
| Public deployment ID, run/attempt, revision, environment, status | Existing `deployment` entity; run URL and explicit status; only allowlisted public environments enter output |
| Explicit deployment release ID | Existing `deployment → deploys → release`; represented release/deployment commits must match; missing targets stay unlinked with a generic partial diagnostic |
| Optional selected deployment receipt | Existing Relay receipt schema validated; consumer/run/attempt/revision/environment/status must match; selected digests retained, raw receipt is never embedded |
| Complete/truncated/filtered/incomplete/denied/unavailable/failed inventory | Existing per-domain collection claims, independent of individual record freshness |

The alpha.2 release entity requires a publication timestamp. Drafts therefore
cannot enter this public collector. The capture producer must filter visibility
before acquiring public fields and certify the public-only root. Nonpublic
records are inadmissible and denied without names, asset URLs, counts or raw
error text. No redacted placeholders or hidden-record totals are emitted.
Private/local collection requires a separately reviewed path.

A `complete` inventory certifies the entire public scope and completed pagination,
not one empty API page. Partial captures retain their admitted public records;
empty partial captures remain partial. Explicit inapplicability is a caller
assertion and cannot coexist with records. Staleness uses the supplied capture
and observation times. Historical publication dates do not make a fresh capture
stale. Targeted Git identities and release/deployment events have explicit partial
coverage when present. They never claim complete reachable Git inventory or
whole-domain event history. Without those records, these domains stay uncollected.

## Local commands

Prepare dependencies separately using the locked Python requirements and
EgoLint toolchain, then acquire the pinned sources before offline preparation:

```bash
python actions/repository-intelligence/scripts/collect_repository_releases.py prepare \
  --hygiene /trusted/hygiene --egolint /trusted/egolint \
  --observatory /trusted/observatory --output /trusted/release-runtime

python actions/repository-intelligence/scripts/collect_repository_releases.py collect \
  --runtime /trusted/release-runtime --repository-root /sources/consumer \
  --repository egohygiene/relay --visibility public \
  --source-commit FULL_COMMIT_SHA --generator-commit FULL_RELAY_SHA \
  --observed-at 2026-11-09T03:00:00Z --capture /captures/releases.json \
  --public-environment github-pages \
  --output /review/release-collection.review.json
```

Deployment statuses use the current owner vocabulary. A cancelled receipt has no
lossless status mapping in that vocabulary and is rejected rather than relabeled
successful or silently dropped. A later owner-reviewed status extension can add it.

`--deployment-receipt` may be repeated with caller-selected bounded receipt files.
The capture references them by SHA-256, never filesystem path. Each supplied
receipt must be referenced exactly once. `--maximum-age-seconds` defaults to
86,400 and accepts 1 through 2,678,400. Omit `--capture` to retain explicit
unavailable release/deployment evidence. Capture shape is defined by
`schemas/release-provider-capture.v1.schema.json`.

The output is always `publication: denied`. Its candidate snapshot can be
reviewed or passed to a separately authorized composition adapter after checking
status, source binding, compatibility, and coverage. It is not itself a direct
production snapshot input. Output must be outside the inspected checkout and
use the fixed review filename. Inputs, collector/helpers, exact owner pins,
source commit, generator commit and candidate digests are retained without local
paths, current clocks, provider bodies, emails, credentials or signed URLs.

Exit 0 means ready or explicitly inapplicable local review, 2 means retained
partial/stale/unavailable/uncollected evidence, and 3 means denied input/runtime.
A safely writable output is replaced by a generic denial envelope on failure,
so a previous successful candidate cannot be mistaken for a new result.

## Remaining acceptance

This checkpoint implements captured-input replay and graph normalization. No
provider acquisition, real consumer publication, action/workflow wiring, native
runtime replay, tests, CI, browser review, cross-checkout equality or release
acceptance was performed here. Those checks are deferred by the current user
instruction. Existing rollback bytes and consumer sources remain untouched.
