# Captured Health evidence

Refs [Relay #150](https://github.com/egohygiene/relay/issues/150).

`collect_repository_health.py` is an offline, publication-denied admission path
for the existing Repository Intelligence Health view. It consumes normalized
producer reports or captured GitHub check runs, verifies their represented
revision, builds the existing Hygiene alpha.2 graph, invokes EgoLint coverage
validation, and delegates all read-model normalization to Observatory. It never
runs consumer scripts, reads console logs, calls GitHub, calculates a health
score, or publishes a site.

The review envelope is Relay execution evidence, not a new canonical check,
conformance, or Health model. `snapshot_candidate` uses the same upstream schema
already accepted by the renderer. Build adoption remains a separate checkpoint.

## Supported contracts and runtime

The independent [health lock](../actions/repository-intelligence/contracts/health-collector.v1.lock.json)
selects the existing alpha.2 source set:

| Owner | Immutable revision | Responsibility |
| --- | --- | --- |
| Hygiene | `639a003d5ddc4d242c2cf190eeb59a9fc522d199` | Graph vocabulary, alpha.2 schema and semantic checks |
| EgoLint | `d917ea524962639494e5bb4b3196192238ba57d9` | Native explicit-coverage validation |
| Observatory | `f411b83398dd07aa3d5e6e2c89d1e8dfff746085` | Public-safe Repository Intelligence normalization |
| Relay | `b4a88db20bc26f9ddefbee174baa8162cbe94ff2` | `repository-report-summary/v1` producer schema |

The lock retains exact source-tree and file hashes, including the accepted
report-summary schema. Runtime preparation reuses the existing immutable Git
acquisition and reproducible native build; collection verifies the resulting
receipt, selected source files, and native binary before normalization. Use the
exact Python dependency set in `contracts/roadmap-collector-requirements.txt`.
Acquire dependencies and Cargo caches before the offline preparation step.

```bash
python actions/repository-intelligence/scripts/collect_repository_health.py prepare \
  --hygiene /sources/hygiene --egolint /sources/egolint \
  --observatory /sources/observatory --output /review/health-runtime
```

## Producer reports

Accepted normalized producers are `osv`, `megalinter`, and `scorecard`. First use
Relay's existing `normalize-repository-report` adapter to produce their native
summary; this collector does not duplicate scanner parsing. Every supplied
report must also be named by `--expect-report`. A requested producer without a
file remains missing. Duplicate selections and unrequested files are denied.

Each schema-valid report must match the declared repository and full source
commit. Generation must precede the observation boundary and expiry must follow
generation. Source times use UTC timestamps with whole seconds. Expired evidence
stays stale; supplying an old report with a new expected commit never refreshes
or relabels it. Mismatches, malformed files, inaccessible files and missing
producer reports are isolated: other compatible producers can still normalize,
and the checks inventory remains incomplete.

Two stable check identities preserve independent facets:

| Graph key | Observed state | Meaning |
| --- | --- | --- |
| `report-PRODUCER-execution` | `success`, `failure`, `cancelled`, `unknown` | Did the native producer emit usable output? |
| `report-PRODUCER-findings` | `clear`, `attention`, `blocked`, `unknown` | What did the producer's policy findings say? |

These records represent a completed **summary observation**. Their required
Hygiene `attributes.status: completed` does not assert that a native check ran or
succeeded. Original facet states, generation, expiry and numeric finding counts
remain in the projection. The Health view shows each facet separately because
the pinned compact read model does not retain arbitrary check attributes.

Canonical links are derived from the same-repository numeric GitHub Actions run
ID. Raw producer messages, tool arrays, log excerpts, local paths, arbitrary
detail/security links, workflow text and actor information are excluded. The
retained inventory contains selected bounded state metadata and source hashes,
never source file paths or report bodies. Native EgoLint v1 run reports are not
accepted directly: their current generic report does not itself bind a consumer
commit. A future revision-bound adapter must be reviewed rather than assigning
the expected commit to an unbound old report.

```bash
python actions/repository-intelligence/scripts/collect_repository_health.py collect \
  --runtime /review/health-runtime --repository-root /sources/consumer \
  --repository egohygiene/consumer --visibility public \
  --source-commit 0123456789abcdef0123456789abcdef01234567 \
  --observed-at 2026-11-09T04:00:00Z \
  --expect-report osv --report osv=/captures/osv-summary.json \
  --expect-report megalinter --report megalinter=/captures/megalinter-summary.json \
  --output /review/health-collection.review.json
```

Use actual repository identity and full revision in place of the example.
Output must be outside the inspected consumer checkout and have exactly the
basename `health-collection.review.json`.

## Captured GitHub check runs

`--check-runs` accepts the existing GitHub REST response object with
`total_count` and `check_runs`. It requires `--check-runs-state observed` and an
explicit `--check-runs-observed-at`. Collection performs no provider requests.
Capture the public repository's commit-scoped check-runs endpoint separately,
retaining pagination outside the collector. At most 256 records and 1 MiB of
JSON are admitted; a greater total count than captured records stays partial.

Each check requires a unique positive numeric ID, bounded public-safe name,
matching `head_sha`, supported status/conclusion, chronological start/completion
times at or before capture, and a credential-free same-repository GitHub run
URL without query or fragment. Other provider fields, app metadata, details,
annotations, URLs, logs and actors are ignored. Status remains `queued`,
`in_progress` or the exact conclusion: success, failure, neutral, cancelled,
skipped, timed out, action required or unknown. Unsupported provider conclusions
remain rejected until their owner vocabulary has a reviewed mapping; they never
become success. A mismatched run is excluded and makes inventory partial.

For unavailable or failed provider collection use
`--check-runs-state unavailable` or `--check-runs-state failed` without a file or
capture timestamp. These remain explicit in the review inventory. Captures
older than `--maximum-age-seconds` (default 86,400) stay stale. Whole-second UTC
timestamps are required. A valid complete empty capture can prove observed-empty
only with the explicit complete-inventory declaration below.

```bash
python actions/repository-intelligence/scripts/collect_repository_health.py collect \
  --runtime /review/health-runtime --repository-root /sources/consumer \
  --repository egohygiene/consumer --visibility public \
  --source-commit 0123456789abcdef0123456789abcdef01234567 \
  --observed-at 2026-11-09T04:00:00Z \
  --check-runs-state observed --check-runs /captures/check-runs.json \
  --check-runs-observed-at 2026-11-09T03:30:00Z \
  --output /review/health-collection.review.json
```

## Coverage, precedence and failure

Default `--inventory partial` describes a selected producer set, even when every
supplied report is valid. `--inventory complete` is an explicit owner-reviewed
declaration that all applicable check producers are represented. A complete
report file or API page does not establish that declaration. Missing, rejected,
unavailable, failed or truncated captures prevent a complete claim even when the
flag is supplied. With no admitted records, failed admission remains failed and
missing/denied provider evidence remains unavailable rather than observed-empty.
With no requested source the domain is uncollected. An explicit owner declaration
`--inventory not-applicable` requires no requested captures and retains
`not_applicable` collection/freshness with its observation time; it does not claim
that a skipped native check is inapplicable.
All other eight alpha.2 collection domains remain uncollected.

Report and provider identities occupy separate namespaces; a native check run
does not replace its normalized findings or vice versa. Duplicate IDs within a
capture are denied. There is no latest-wins selection or aggregation into a
score. Staleness and execution/finding state remain independent. Health does not
become Hygiene conformance, runtime Status, audit acceptance or human architecture
ratification.

The collector writes a closed, atomically replaced review envelope and candidate
digests. Closed diagnostics identify the producer and remediation without echoing
raw exception text or source content. A failed producer cannot prevent another
compatible producer from being normalized. Invalid pins, root source binding or
normalization fail the collection; no candidate acquires publication authority.
Symlink and traversal paths are denied. Only explicitly public input is allowed;
the caller must authorize and verify every capture's public classification before
invocation. There is no private-to-public redaction or private-build mode here.

Exit codes: `0` means a complete structurally ready inventory or explicitly
not-applicable domain, `2` means partial, failed, unavailable, uncollected or
invalid review evidence, and `3` means admission or
runtime denial. None means every check passed, consumer CI passed, or a site was
published. `publication: denied` is invariant.

## Delivery limits

This implementation is unqualified draft work. At the user's request, no tests,
CI, native runtime preparation, real producer canary, cross-checkout replay,
renderer verification, composite/reusable workflow integration, publication,
rollback or Empathy #98 regression was run in this delivery. Review these before
adoption. The current consumer publisher remains the only deployment authority.
