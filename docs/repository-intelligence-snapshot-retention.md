# Offline snapshot retention and Compare

Refs [Relay #152](https://github.com/egohygiene/relay/issues/152).

`retain_repository_intelligence_snapshots.py` supplies the existing Compare
renderer with the locked Observatory comparison, plus a separate operational
receipt. It accepts already reviewed public Observatory alpha.2 snapshots paired
with their exact original upstream projections.
It does not collect evidence, refresh a snapshot's observation time, publish a
site, choose a cloud retention provider, or change canonical source history.

## Contract and authority

The adapter reuses `adr-collector.v1.lock.json`, its prepared offline runtime,
and `collect_repository_adrs.normalize`. That boundary applies pinned Hygiene
schema/vocabulary validation, native EgoLint coverage validation and Observatory
normalization. Current selections are inspectable in that lock; no new graph,
history or comparison model is introduced here. The receipt records the exact
lock, upstream revisions, native executable and adapter digests.

Admission requires a public alpha.2 snapshot and alpha.2 upstream projection,
the declared repository and (for the current input) full source revision. The
adapter requires the original upstream projection, normalizes it with the
locked owners and requires exact structural equality with the supplied read
model, including its upstream digest. An edited view, contradictory coverage or
unsupported generator cannot become an accepted baseline. Alpha.1 comparison
rendering remains supported; this new retention adapter deliberately requires
the explicit alpha.2 domain boundary.

The snapshot graph intentionally does not retain its upstream generator. A
snapshot alone therefore cannot reconstruct the exact original projection or
prove its upstream digest. Preserve both collector outputs; do not fabricate a
generator from the read model's different Observatory generator. Existing local
collector review envelopes retain both `projection_candidate` and
`snapshot_candidate`; source-build preparation must retain its original
projection alongside its snapshot before using this adapter.

Snapshots must already have received their public projection review. This is
not a redaction engine: it rejects non-public records, redaction summaries,
graph/snapshot extension payloads and obvious credential/email/machine-path
strings. Public declarations do not independently establish that arbitrary
free text is safe. Keep private/local builds on their separately authorized
path; never upload their captures or this retention store to public hosting.

## Prepare once

Install the existing hash-locked ADR build requirements through the established
trusted acquisition procedure. Prepare the runtime from exact local owner
checkouts, outside the consumer's source checkout:

```sh
python actions/repository-intelligence/scripts/retain_repository_intelligence_snapshots.py prepare \
  --hygiene /trusted/hygiene \
  --egolint /trusted/egolint \
  --observatory /trusted/observatory \
  --output /artifacts/compare-runtime
```

Preparation uses the existing ADR runtime acquisition/build path. Subsequent
`compare` and `refresh` invocations operate offline and never run consumer
scripts. The current implementation requires a POSIX host for its advisory
baseline lock.

## Seed and refresh

Provide the actual source commit represented by the input and an explicit UTC
operational observation boundary. `--repository-root` identifies the consumer
checkout whose files must remain untouched. Retention and attempt output must
be separate and outside that checkout. The attempt directory must be new.

```sh
python actions/repository-intelligence/scripts/retain_repository_intelligence_snapshots.py refresh \
  --runtime /artifacts/compare-runtime \
  --repository-root /sources/consumer \
  --repository egohygiene/identity \
  --source-commit "$CONSUMER_SOURCE_COMMIT" \
  --snapshot /artifacts/current/observatory.snapshot.json \
  --projection /artifacts/current/repository.projection.json \
  --observed-at "$OBSERVED_AT" \
  --store /artifacts/retained-intelligence \
  --expected-baseline none \
  --output /artifacts/attempt-001
```

The first valid refresh seeds a baseline and produces an `unavailable`
comparison receipt because there is no historical evidence yet. For later
refreshes, inspect the existing pointer and supply its `snapshot_sha256` as
`--expected-baseline`. This is an explicit lease: an unexpected newer baseline
or a held concurrent lock denies replacement. No automatic retry changes the
expected digest.

The repository's local store contains:

```text
egohygiene--identity/
  snapshots/<canonical-snapshot-sha256>.json
  projections/<canonical-projection-sha256>.json
  baseline.json
  .baseline.lock
```

Snapshot and original projection objects contain canonical JSON bytes and are
immutable by digest. The pointer binds both digests, and admission always
validates the original pair together.
`baseline.json` is a local operational pointer, not a canonical source record.
Its retention clock stays outside the snapshot and rendered bundle. Existing
objects are never pruned by this tool, so operators can retain a previous
reviewed rollback point separately from the current pointer. Transport the
complete store as a consumer-owned ordinary artifact if desired; publication,
artifact expiry and access policy remain the consumer's decisions.

## Compare without advancing

Use `compare` with the same inputs and a new attempt directory to inspect the
retained baseline without updating it. Explicit `--baseline PATH` and
`--baseline-projection PATH` together can select a reviewed immutable pair
instead of the pointer; they are accepted only by `compare`, never by `refresh`.

Each attempt produces `retention.receipt.json`. When there is a compatible,
unexpired baseline with usable coverage it also produces `comparison.json`,
exactly the pinned `Observatory.compare_snapshots` result. Feed that file to
the builder's existing `--observatory-comparison` input together with the
matching `--observatory-snapshot`. The Compare route accepts alpha.1 and alpha.2
and binds its version, after revision, observation boundary and snapshot ID to
the supplied current snapshot. The comparison describes structural changes;
it does not infer causality, acceptance or semantic completion.

Input artifact SHA-256 and retained canonical SHA-256 are recorded separately
for both the snapshot and projection. Two differently formatted copies of equivalent input produce the
same retained bytes and normalized comparison; their receipt's input-byte hash
can differ. Operational receipt clocks and retention policy are never inserted
into the comparison or snapshot.

## Failure and freshness behavior

- Default maximum current age is one day; default maximum baseline age is 30
  days. Override the explicit seconds flags when the consumer has reviewed a
  different policy; each is bounded to one year.
- Snapshot observations later than the explicit operational boundary are
  rejected, as are operational clocks earlier than the last retention. Old current evidence or any
  explicitly stale current domain/record does not replace the baseline.
- Missing, inaccessible, expired, malformed, incompatible, wrong-repository and
  redacted baselines have distinct receipt states. Expiry withholds comparison
  but permits a valid current snapshot to establish the next baseline.
- Failed current collection, loss of a previously adopted domain and complete
  inventory becoming partial withhold comparison and baseline promotion. The
  prior retained object remains intact. Initially partial but valid inventories
  remain partial; uncollected domains never become observed-empty or success.
- A corrupt/missing retained object, unreadable pointer, mismatched digest or
  incompatible baseline requires explicit operator recovery; a refresh does
  not silently discard the recovery evidence.
- An automatic refresh requires the baseline's recorded runtime lock to match
  the current lock. Upgrading owners is an explicit migration: validate the old
  pair with `compare`, then seed a separately reviewed new store. Preserve the
  old store and rollback evidence.
- Each attempt has a new directory, so a failed retry cannot reuse a previous
  successful comparison file. Diagnostics use closed codes and omit captured
  text, exceptions and local paths.
- Promotion checks the complete pointer again under its lock, so a concurrent
  refresh of identical snapshot bytes cannot silently move a newer retention
  clock backwards. If output writing fails after a pointer write, a failure
  receipt reports retention as `retained` or `unknown`; it never asserts
  `unchanged` after a possible committed promotion. Inspect the pointer before
  retrying an interrupted attempt.

Exit `0` means a comparison is available and any requested promotion succeeded.
Exit `2` means there is useful operational evidence but comparison/promotion is
unavailable (including initial seeding); inspect `status`, `baseline_state` and
`retention`. Exit `3` means admission or execution was denied. Treat all three
outcomes explicitly in consumer orchestration.

To recover, restore a complete reviewed store artifact, or create a new empty
store and deliberately seed a reviewed current snapshot with the `none` lease.
Keep the old store for inspection. This tool never moves a cloud artifact,
changes a publisher or edits historical deployment rollback receipts.

## Remaining acceptance

This delivery is implementation for review. Tests and CI were explicitly
deferred for the program's later validation pass. Real two-revision consumer
captures, deterministic replay, adversarial/failure verification, hosted
retention expiry, preview/publication, upgrade and live rollback acceptance
remain open under #152 and #101. No live comparison or deployment is claimed.
