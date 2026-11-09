# Repository Intelligence GitHub Sources

Capture actual public GitHub issue/PR inventories, exact-commit check runs and
published releases into the existing Work/Health/Releases transport contracts.
Refs [#146](https://github.com/egohygiene/relay/issues/146),
[#149](https://github.com/egohygiene/relay/issues/149),
[#150](https://github.com/egohygiene/relay/issues/150).

This experimental producer performs bounded read-only API requests and safe Git
object reads. It executes no consumer scripts, scanners or transformations,
uploads no artifact, and publishes or deploys nothing. The consumer owns its
existing site build, publication and recovery gates.

## Consumer handoff

Use the exact reviewed full Relay commit for both producer and builder. Run this
after the existing checkout at the represented commit, with `fetch-depth: 0` if
historical release commits should be admitted. The existing capture artifact
seam supports public `push` and `workflow_dispatch` events; leave ordinary PR
builds on their current no-capture path.

```yaml
# Add these steps inside the consumer's existing build job. Preserve its gates.
- id: public_sources
  if: ${{ github.event_name == 'push' || github.event_name == 'workflow_dispatch' }}
  uses: egohygiene/relay/actions/repository-intelligence-github-sources@FULL_REVIEWED_RELAY_SHA
  with:
    github-token: ${{ github.token }}
    include-titles: true
- id: capture_upload
  if: ${{ steps.public_sources.outputs.artifact-directory != '' }}
  # actions/upload-artifact v7.0.1
  uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a
  with:
    name: ${{ steps.public_sources.outputs.artifact-name }}
    path: ${{ steps.public_sources.outputs.artifact-directory }}
    if-no-files-found: error
    retention-days: 7
- id: intelligence
  uses: egohygiene/relay/actions/repository-intelligence@FULL_REVIEWED_RELAY_SHA
  with:
    # Preserve the consumer's other existing native-source and output inputs.
    collect-journey: true
    search-attribution: true
    source-capture-artifact-id: ${{ steps.capture_upload.outputs.artifact-id }}
    source-capture-artifact-digest: ${{ steps.capture_upload.outputs.artifact-digest }}
    as-of: ${{ steps.public_sources.outputs.as-of }}
```

Use the capture-enabled reusable entrypoint instead when the existing consumer
uses a reusable workflow. Expose upload ID/digest and `as-of` as producer-job
outputs and pass them unchanged to `repository-intelligence-captures.yml`.
See [exact intake](../../docs/repository-capture-artifact-intake.md).

With a token, grant only the needed read permissions: `contents: read`,
`issues: read`, `pull-requests: read`, and `checks: read`. The builder's existing
artifact intake additionally needs `actions: read`. An empty token uses public
unauthenticated requests and their lower rate limit. Repository visibility is
always established through an unauthenticated request before inventory reads,
then rechecked before writing captures. Releases/assets/tag resolution always
use public unauthenticated reads, so a token cannot admit draft releases or
change public pagination by exposing drafts. Redirects are rejected; the token
is sent only to the fixed GitHub API origin.

## Inputs and outputs

`sources` is a closed comma-separated selection from `work,health,releases`.
`maximum-pages` defaults to 3 and accepts 1–20 per endpoint.
`maximum-work-records` defaults to 256 and accepts 1–2,000 independently for
issues and PRs. Check runs and releases are capped at 256 each; each release has
at most 64 assets. There are also hard limits of 128 requests, 2 MiB per response,
32 MiB total responses and a 240-second request deadline. Each request has a
15-second timeout; final public admission has a reserved request/time budget.
No retries or rate-limit sleeps run inside this action. Git object reads have
independent ten-second bounds. A capture file is capped at 1 MiB.

`maximum-age-seconds` defaults to 86,400 and accepts 1–2,678,400. This configures
later freshness evaluation; it never changes original observations.
`include-titles` defaults to false. Opting in retains only bounded safe public
titles/check names. Unsafe/oversized optional titles become null; check names
fall back to `GitHub check <provider-id>`. Bodies, comments, labels, actor/app
objects, emails, paths, arbitrary detail URLs, signed links and logs are absent.

Outputs are `artifact-name`, `artifact-directory`, `manifest-sha256`,
`producer-receipt` and `as-of`. All generated files live in new private
runner-temporary directories outside the consumer checkout. The existing packer
copies only the plan and selected JSON files into the exact same-run/head
artifact bundle. The separate producer receipt binds source/producer/file
hashes, original observation times, pagination, fixed outcomes and bounds; it
contains no raw responses or local paths. Its output path can be retained by a
caller-owned ordinary artifact upload, separate from the site and capture bundle.

## Mapping and incomplete evidence

This adds no canonical model and changes no existing collector lock. The owner
mapping remains the exact Hygiene/EgoLint/Observatory selections documented in
the [Work](../../docs/repository-work-collector.md),
[Health](../../docs/repository-health-collector.md), and
[Releases](../../docs/repository-release-collector.md) guides. The existing
native source plan performs all schema, semantic and normalized admission.

- Work calls the mixed Issues endpoint and the dedicated PR endpoint. PRs are
  excluded from issue records before selecting IDs, counts or titles. Provider
  numbers/IDs, states, closure reasons and timestamps remain separate. No
  relationships are inferred from bodies, closure, merge or commit messages.
  Both inventories request all states in most-recently-updated order, keeping
  bounded captures useful for current work. Repeated records in a moving paged
  inventory are deduplicated and leave the inventory explicitly incomplete.
- Health calls `commits/<exact-sha>/check-runs?filter=all`, keeps each matching
  head SHA, execution state and conclusion, and admits only canonical
  same-repository GitHub run URLs. Its optional closed `relay_capture` receipt
  carries pagination/failure state: a truncated/failed empty capture cannot
  appear complete merely because its provider total equals retained length.
  The overall producer inventory stays `partial`; complete check pagination
  cannot establish applicability of OSV, MegaLinter, Scorecard or other checks.
  Existing normalized report inputs remain separately selectable through the
  source plan; the producer does not relabel them to the current commit.
- Releases resolves the exact public tag ref and peels annotated tags. It never
  uses `target_commitish` as an alleged released commit. Missing/malformed refs,
  uninspected historical Git objects, incomplete assets and unsupported values
  leave inventory incomplete. Assets retain only public name, size and supplied
  SHA-256 (or null); no digest is invented. Tag resolution is an observation of
  that ref at capture time, without a claim that tags are immutable.
- Deployments remain explicitly `uncollected`. Generic GitHub deployment
  metadata does not independently bind an Actions run attempt, canonical
  consumer receipt or install verification. The existing reviewed release
  transport can still receive explicit public-environment/run-bound receipts
  through caller-owned producers; this action invents no deployment identity.

Received pages and their original capture boundaries survive endpoint rate
limits, permission loss, bounds or provider failure as partial evidence. With
no usable page, the selected domain remains unavailable/failed. Exhausted
pagination describes the provider's current inventory, without claiming an
atomic historical snapshot. Collection never awards progress or completion.
Failure of final public admission produces no usable source handoff. A malformed
or oversized transport fails closed before output. No prior capture directory
is reused or overwritten.

Static syntax/schema/source review is the implementation evidence for this
checkpoint. Tests, native collection/builds, actual API/artifact canaries,
publication, deterministic replay and recovery qualification remain deferred.
An implementation merge does not establish these acceptance outcomes.
