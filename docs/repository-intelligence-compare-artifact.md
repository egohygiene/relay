# Immutable Compare artifact handoff — Relay #152

The existing [offline retention CLI](repository-intelligence-snapshot-retention.md)
already admits exact original projection/snapshot pairs, computes the pinned
Observatory comparison and protects local pointer refresh with an explicit
digest lease. `repository-intelligence-compare-artifact` adds the ordinary
consumer artifact transport around that boundary. Existing builder/workflow
inputs, no-baseline behavior, token contracts and deployers are unchanged.

## Exact source and transport boundary

After a completed public source build, pass the directory containing its actual
original `projection.json` and matching `snapshot.json`. Combined source
preparation already retains both. Older ADR-only paths that emitted only a
snapshot must first retain their real original projection; never manufacture
one from a read model or substitute a review envelope.

The helper validates the current pair through the selected exact native
normalizer, requires repository/represented commit identity and bounds current
age at the explicit operational `as-of`. Explicitly stale or failed evidence
cannot establish a new baseline. It canonicalizes the admitted pair for
content-addressed retention without changing either JSON value.

The ordinary artifact contains exactly three regular, non-executable files:
`projection.json`, `snapshot.json` and closed `snapshot-bundle.json`. The
manifest binds public repository ID/name, source SHA, producer run/attempt/event,
original snapshot/capture boundary, native contract and upstream digest,
normalization profile, exact runtime lock, canonical pair byte hashes and the
separate retention clock. It does not carry a site, arbitrary paths, scripts,
logs, cache or mutable baseline pointer. ZIP traversal, extra entries,
duplicates, symlinks, encryption, unsupported compression and oversized or
excessively expanded input are denied before materialization.

Subsequent callers select the exact artifact ID and upload ZIP digest, source
SHA, producer run/attempt and canonical `snapshot:projection` digest lease.
Provider reads address those IDs directly. Both run and artifact must belong
to the same declared public repository and represented head; the prior run
must be a successful completed push/manual attempt. The immutable manifest's
clock must fall within that actual producer attempt. Expiry and download access
are inspected without name/list/latest lookup or signed URL retention. One
allowlisted CDN hop never receives the API authorization header.

The baseline manifest and original pair must revalidate under the exact current
profile/runtime lock. The default discriminator is `legacy-adr`. The closed
`search-attribution-v1` dispatch calls the separately reviewed Search helper's
`retention_adapter()` and uses its matching explicit runtime or closed trusted
`acquire(work)` path. An
absent helper, unknown profile, profile mismatch or changed lock fails closed;
old records are never silently normalized into a different historical model.

Each attempt creates fresh private output and local retention storage outside
the consumer checkout. An admitted baseline's exact objects, pointer digests
and original retention clock seed that isolated store. The existing CLI then
performs its whole-pointer locked lease check, source/domain completeness
checks, maximum age evaluation and comparison. Its exact `comparison.json`
remains separate from operational receipts. The original artifact is immutable
and untouched; there is no mutable cloud pointer or claim of cross-run global
compare-and-swap. Consumers serialize or deliberately select the next immutable
handoff using their existing orchestration.

## Consumer composition

Keep the existing capture, build and single deployment jobs. In an existing
read-only source/build job, after actual source preparation:

```yaml
# Pin both uses to the same exact reviewed Relay commit before adoption.
- id: compare
  uses: egohygiene/relay/actions/repository-intelligence-compare-artifact@FULL_REVIEWED_RELAY_SHA
  with:
    source-directory: ${{ runner.temp }}/current-public-source
    as-of: ${{ steps.source.outputs.as-of }}
    runtime: ${{ steps.runtime.outputs.path }}
    expected-baseline: none
    retention-days: 30
- name: Stage only admitted renderer inputs
  id: compare_inputs
  env:
    CURRENT_SNAPSHOT: ${{ steps.compare.outputs.snapshot-path }}
    COMPARISON: ${{ steps.compare.outputs.comparison-path }}
  shell: bash
  run: |
    set -euo pipefail
    stage="$(mktemp -d "${GITHUB_WORKSPACE}/.cache/intelligence-compare.XXXXXX")"
    relative="${stage#"${GITHUB_WORKSPACE}/"}"
    cp -- "${CURRENT_SNAPSHOT}" "${stage}/snapshot.json"
    printf 'snapshot=%s/snapshot.json\n' "${relative}" >> "${GITHUB_OUTPUT}"
    comparison=""
    if [[ -n "${COMPARISON}" ]]; then
      cp -- "${COMPARISON}" "${stage}/comparison.json"
      comparison="${relative}/comparison.json"
    fi
    printf 'comparison=%s\n' "${comparison}" >> "${GITHUB_OUTPUT}"
- uses: egohygiene/relay/actions/repository-intelligence@FULL_REVIEWED_RELAY_SHA
  with:
    observatory-snapshot: ${{ steps.compare_inputs.outputs.snapshot }}
    observatory-comparison: ${{ steps.compare_inputs.outputs.comparison }}
    as-of: ${{ steps.source.outputs.as-of }}
```

The stage example requires the consumer's existing `.cache` parent. The caller
must validate that private staging is untracked and remains outside its public
site. Use its resulting relative snapshot/comparison paths with the existing
builder inputs, preserve an explicit evaluation clock and retain the artifact
receipt through its existing always-run evidence handling. This deliberately
adds no second publication workflow or deployment/recovery dependency.

For the next attempt replace `none` with the exact previous
`next-baseline-lease` and supply **all** baseline inputs: `baseline-artifact-id`,
`baseline-artifact-digest`, `baseline-source-commit`, `baseline-run-id` and
`baseline-run-attempt`. Obtain them from the actual successful ordinary upload
and its represented source/run/attempt; do not synthesize outputs, reuse a
cancelled attempt or use an artifact's display name as selection authority.

The composite uploads eligible current pairs with the pinned ordinary
`upload-artifact`, `overwrite: false` and explicit retention1–90 days. It
does not upload Pages, publish source history or change deployment permissions.
Its final step records the actual upload result separately: comparison status
and local candidate eligibility cannot imply that retention or deployment ran.
The bounded operational receipt is independently retained for30 days, including
prepared failure/unavailable outcomes, through a separate ordinary artifact.

## Unavailable and failure behavior

- Explicit `none` seeds a valid current artifact while Compare remains
  unavailable. No historical snapshot is invented.
- Missing/inaccessible, expired transport, malformed, wrong-repository,
  redacted or incompatible selected baselines withhold comparison and new
  baseline upload. The validated current snapshot remains available for the
  existing no-comparison site path. The prior immutable artifact is unchanged.
- A downloaded valid baseline older than the explicit snapshot-age policy
  withholds comparison; the existing CLI can retain an otherwise eligible
  current pair after completeness checks. Artifact expiry without its original
  pair cannot prove compatibility and requires explicit recovery/new seeding.
- Current admission/freshness failure denies preparation, preserves a closed
  private failure receipt and creates no eligible upload. Loss of an adopted
  domain or complete-to-partial downgrade withholds promotion under existing
  retention policy. Cancellation cannot reuse another attempt's directory or
  turn its receipt into current success.
- Failed/cancelled upload reports retention as unknown when completion may
  have occurred. Inspect provider state before retrying. No overwrite or
  automatic lease substitution is performed.

Only the admitted snapshot and exact comparison belong in the site's normal
provenance/rendering path. Manifest, original projection, ZIP/provider hashes,
transport identity and operational receipts remain private ordinary evidence;
they never become public bundle freshness or redaction-sensitive digests.

## Review checkpoint

Prepared from Relay main `4071e92fb9c871ff724f6203a2fe45780eb30808` on
`codex/intelligence-compare-artifact`. This bounded slice owns only the new
helper/action/schema/docs and its independent action-catalog entry. Journey and
release source integration is parallel work; root reconciles shared continuity
and the optional Search helper. The continuity skill is unavailable in this
session's installed catalog; this dedicated handoff records the scoped result
instead of inventing a skill execution or competing aggregate checkpoint.

The user deferred tests, builds, CI, collectors/native replay, provider execution,
browser and publication. Only static syntax/schema/source/peer inspection is
performed here. Python AST, three JSON documents, two schema definitions,
unique-key action/example YAML, three embedded Bash blocks and whitespace
inspection passed. Independent source review found no concrete blocker in
provider/archive/pair admission, clock/lease handling or upload finalization.
Real two-revision domain capture, deterministic replay, provider
artifact expiry/access and failure/cancellation scheduling, consumer preview,
live Compare, upgrade and recoverable rollback remain acceptance under #152/#101.
Refs [organization #41](https://github.com/egohygiene/.github/issues/41).
