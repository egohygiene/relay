# Canonical ADR collection and Decisions builds — Relay #115

## Mapping and ownership

This mapping precedes implementation. The collector reads an explicit public
repository at one immutable Git revision. Hygiene owns ADR and graph semantics,
EgoLint owns source and coverage validation, Observatory owns normalization, and
Relay owns bounded acquisition and orchestration. ADR-007 and ADR-010 apply.
Canonical files remain unchanged. Collection never authors a decision, infers
human approval from a merge, or reconstructs intent from history.

| Input | Projection / retained evidence |
| --- | --- |
| Explicit repository, visibility, full commit, observation time | Root identity and revision; no checkout-name or wall-clock inference |
| Consumer policy reference and canonical index | Immutable source links and hashes; exact policy validation by EgoLint |
| Every Markdown file under the declared decision directory | Bounded inventory; canonical ADR records are selected by their owner schema; legacy/unrecognized files prevent complete coverage |
| ADR `id`, `title`, `status` | Stable `ri:<repository>:architecture-decision:<id>`, native key, title, declared lifecycle |
| `decision_scope`, `implementation_status` | Corresponding Hygiene entity attributes and Observatory Decisions facets |
| `date`, `owners`, `approval`, `evidence`, `exceptions`, affected repositories/contracts, issue and PR references | Same named canonical metadata in the graph entity's attributes; declared links are not fetched provider observations |
| Canonical source path and full commit | Entity URL and provenance source; Markdown rationale remains available at its immutable source |
| Local `supersedes` and `superseded_by` | Deduplicated, directed `supersedes` relationships; both original declarations remain preserved; EgoLint validates lifecycle and reciprocal consistency |
| `related` and external lineage | Preserve declared references as attributes; never fabricate missing/external entities or claim their visibility was observed |
| Legacy IDs already in conforming owner metadata | Preserve exact ID width and filename; EgoLint owns migration exceptions |
| Missing front matter or unsupported legacy metadata | Generic incomplete-inventory diagnostic, no guessed status, approval, rewritten ID, or invented graph node |
| No history acquisition | No invented lifecycle events; history and every non-ADR domain remain `uncollected` |

The graph's existing kind-specific `attributes` object retains canonical ADR
metadata; this introduces no Relay extension or alternative normalized model.
Optional local extension payloads are not projected: their privacy and meaning
need an explicitly supported owner contract. Their presence makes this bounded
projection partial. All supported fields survive in `snapshot_candidate.graph`;
the existing Decisions view continues to expose only Observatory-owned facets.

## Exact compatible inputs

| Owner | Revision | Selected contract |
| --- | --- | --- |
| EgoLint | `2d3600f14848e28099acc34ce8043699da2b9a32` | Source report v1, catalog `0.1.0-alpha.3`, coverage CLI/report v1 |
| Hygiene projection | `639a003d5ddc4d242c2cf190eeb59a9fc522d199` | Intelligence `1.0.0-alpha.2`, proposed |
| Hygiene ADR policy | `c589587395750cd1c79c6fa0bef010189c547249` | ADR `1.1.0` and policy reference `1.0.0`, accepted |
| Observatory | `f411b83398dd07aa3d5e6e2c89d1e8dfff746085` | Intelligence read model `1.0.0-alpha.2` |

The collector lock binds full Git trees and SHA-256 artifact digests. Preparation
reads those Git objects from separately acquired owner repositories and builds
EgoLint with frozen offline dependencies. It reuses the existing roadmap
collector's runtime and safe-I/O helpers with an explicit independent lock.
The old roadmap runtime retains its separate adoption gate; checkpoint 2
repins the production renderer to the same Observatory alpha.2 revision. No sibling implementation is copied into Relay.

## Uncertainty, privacy, and publication

Collection completeness, ADR conformance, and freshness are independent. A
complete valid inventory can be `observed` or `observed_empty`; legacy or omitted
extension data is `partial`. An absent directory/index is `unavailable`, an
explicit unknown adoption is `uncollected`, and a verified explicit
not-applicable selection must not conceal canonical records. Semantic source
errors remain invalid even when projection normalization succeeds.

The source validator also reports uncollected roadmap/history as `incomplete`;
Relay preserves that result and never promotes it to whole-repository validity.
Missing policy references remain missing and produce owner diagnostics. The
collector does not write a replacement reference into the consumer corpus.

Reject private/unknown repository visibility and nonpublic canonical records
before returning source identities, counts, or candidate data. Bound file count,
individual bytes, total source bytes, process time, and output bytes. Read Git
objects rather than dirty worktrees; reject path traversal, Git symlinks,
submodules, filesystem symlink ancestors, ambiguous YAML/JSON, and unsafe output
locations. Run no consumer configuration, hooks, scripts, or network operation.
Diagnostics use fixed codes and reviewed remediation, never source prose or raw
exceptions. A denial replaces a prior result only at a verified safe output path.

Checkpoint 1 emits an **ADR review envelope**, not a production snapshot input.
`publication: denied` remains unconditional on that review interface. Checkpoint 2's
separate build adapter invokes fresh collection and gates the normalized candidate
before attaching build provenance. Consumer publication review remains separate.
The existing `--observatory-snapshot` entry point must reject this envelope.

## Replay and remaining acceptance

Refresh by explicitly choosing another immutable consumer revision, public
visibility, source paths, and observation boundary. The same source, captured
inputs, collector, and prepared runtime must yield identical complete envelopes
across differently named checkouts. Hash all selected source bytes and both
projection/read-model candidates; never include local paths or runtime clocks.

Use a real immutable Hygiene ADR corpus as a read-only canary. Its legacy
ADR-0001 and absent consumer policy-reference file remain visible validation
gaps; collection must preserve the conforming records and their actual approval
evidence without claiming corpus conformance or publication. Identity's sources
and its parallel implementation work remain untouched.

Checkpoint 2 below supplies action/workflow/local parity, mutually exclusive external
snapshot inputs, reviewed renderer repinning, and build provenance. A real conforming
consumer corpus and the immutable Identity #69 upgrade remain acceptance work. Deployment and live-route acceptance remain separate.
Refs #115; this bounded checkpoint does not complete all issue acceptance.

## Native commands and reproducible checks

Use Python 3.11+ with the exact packages in
`actions/repository-intelligence/contracts/roadmap-collector-requirements.txt`,
Git, and the pinned Rust 1.85.1 toolchain. Keep acquired sibling clones, Cargo
dependencies, and the prepared runtime outside the inspected consumer. Network
acquisition happens before these commands; `prepare` compiles offline from the
locked Git objects, regardless of checkout branches. Never use a runtime or
collector supplied by an untrusted consumer.

```bash
python actions/repository-intelligence/scripts/collect_repository_adrs.py prepare \
  --hygiene /trusted/hygiene --egolint /trusted/egolint \
  --observatory /trusted/observatory --output /trusted/adr-runtime

python actions/repository-intelligence/scripts/collect_repository_adrs.py collect \
  --runtime /trusted/adr-runtime --repository-root /sources/hygiene \
  --repository egohygiene/hygiene --visibility public \
  --source-commit 639a003d5ddc4d242c2cf190eeb59a9fc522d199 \
  --observed-at 2026-10-04T21:00:00Z --adoption legacy \
  --output /review/hygiene/adr-collection.review.json
```

Paths in the example are caller-selected absolute paths, not bundled resources.
Acquire EgoLint at the locked revision and run `cargo fetch --locked` before
preparation. Preparation checks 18 owner artifacts, complete Git tree identities,
the Python package versions, and the built executable digest. Its destination
must be new. Receipts from the older roadmap or architecture runtime are not
compatible with this profile.

`--adoption` is explicit: `present`, `legacy`, `unknown`, or `not-applicable`.
Default inputs are `docs/decisions/policy-reference.json`, `docs/decisions`, and
`docs/decisions/README.md`; select other canonical paths with `--policy-reference`,
`--decision-directory`, and `--index`. EgoLint checks those paths against the
consumer reference. Root `DECISIONS.md` can remain a compatibility entry point;
the collector never treats its prose as a second canonical ledger.

`--collected-at` defaults to the supplied observation boundary. Set it explicitly
when replaying a previously captured inventory; `--maximum-age-seconds` defaults
to 86,400 and accepts 1 through 2,678,400. Older captures remain stale. An ADR's
historical decision date does not make a newly observed inventory stale. This is
capture freshness, not an assertion that maintainers recently reviewed each ADR.

Collection bounds are 256 selected Git entries, 256 KiB per source blob, 2 MiB
total selected source content, and 8 MiB per review envelope. Larger or ambiguous
inputs fail closed instead of being silently truncated. Output must use the
fixed filename `adr-collection.review.json` outside the consumer checkout.

Exit 0 means the requested bounded collection is ready for **local review** (or
explicitly inapplicable), 2 retains partial/invalid/unavailable/uncollected
evidence, and 3 denotes an input or runtime denial. Every result still says
`publication: denied`. The real Hygiene command above returns 2 because its
existing corpus has unresolved migration and source-validation findings.

```bash
RELAY_ADR_RUNTIME=/trusted/adr-runtime \
RELAY_ADR_CANARY=/sources/hygiene \
python -m unittest discover --start-directory tests \
  --pattern test_repository_adr_collector.py --verbose
```

Native tests exercise actual pinned validators and normalization, rendering of
the existing Decisions fragment, whole-envelope replay, unchanged source,
lineage/index/approval failures, unknown and empty collection, old IDs, extension
withholding, private input, file bounds, unsafe paths, and runtime integrity.
Ordinary discovery may skip these native cases when the explicit runtime or
canary clone is absent; those skips are not acceptance evidence. The documented
native run must finish without skips before reviewing this checkpoint.

Fixture provenance: the synthetic canonical corpus adapts EgoLint's public
`tests/fixtures/repository-intelligence/valid/docs/decisions` at
`2d3600f14848e28099acc34ce8043699da2b9a32` to Relay identity and local-only lineage.
The real canary is read directly from the immutable Hygiene clone, not rewritten
or vendored into Relay. Decision impact: this is implementation of ADR-007/010's
existing owner and evidence boundaries; no new architectural authority is added.

## Checkpoint 2: opt-in Decisions builds

`collect-adrs: true` now connects a fresh native collection to the existing
Intelligence action and reusable workflow. It reads the standard canonical paths
above with adoption `present`. A build requires complete `observed` or
`observed_empty` ADR coverage, current observation freshness, valid Hygiene and
coverage checks, successful Observatory normalization, and no invalid or
truncated EgoLint result. EgoLint's `incomplete` result remains visible because
roadmap/history were not requested; it is never relabeled whole-repository valid.
The local review command and its `publication: denied` envelope remain unchanged
in purpose. The builder does not accept saved review envelopes as site inputs.

The renderer accepts alpha.2 per-domain claims and keeps the established alpha.1
external-snapshot interface. Every affected view shows its collection state;
record freshness cannot stand in for collection completeness. Decisions retains
its existing route, fragments, lifecycle, implementation, and supersession
presentation. Date, owner, affected-contract facets, and declared human approval
come from the matching public graph attributes. Canonical Markdown stays the
source of narrative and approval authority.

The ADR mode conflicts with **both** `observatory-snapshot` and
`observatory-comparison`. There is no ADR/roadmap merge mode: the separate roadmap
review profile still needs #112/#113 adoption. Existing builds without ADR
collection keep their dependency-light behavior and unavailable-input states.

### Action and reusable workflow

After reviewing the integration PR, select its full immutable Relay revision.
The example deliberately uses a review placeholder: replacing a historical
consumer pin and establishing a new rollback point require consumer review.

```yaml
jobs:
  intelligence:
    permissions:
      contents: read
    uses: egohygiene/relay/.github/workflows/repository-intelligence.yml@<reviewed-full-relay-sha>
    with:
      collect-adrs: true
      artifact-retention-days: 30
```

For a composed workflow, use the same `collect-adrs: "true"` input on
`egohygiene/relay/actions/repository-intelligence@<reviewed-full-relay-sha>` after
a complete-history checkout. It produces an ordinary static artifact; the
consumer retains composition, aliases, deployment, and rollback authority.
The reusable workflow retains its existing trust, upload, reporting, and failure
gates. No Pages upload, deployment, protected environment, or write permission
is added.

With no `adr-runtime` input, the action acquires the four locked source revisions
from three public owner repositories into a private temporary directory. On
CPython 3.12/Linux x86_64 it installs hash-locked wheels, installs Rust 1.85.1
through rustup, fetches Cargo's locked dependencies, then prepares the verified
runtime and collects offline. Git, Python with venv, and rustup must already be
available; the reusable workflow and native acceptance job pin Ubuntu 24.04
to retain the CPython 3.12 wheel ABI. Acquisition preserves configured
proxy and CA trust. No consumer package manifest, configuration, hook, cache, or
executable enters that runtime. Native executable builds remove private build
paths so fresh runtime preparation can reproduce the bound executable digest.
Temporary acquisitions are removed at completion.

An independently trusted prepared runtime can be supplied as `adr-runtime` to
the composite action for offline use. It must be outside the consumer checkout;
the invoking Python must already have the exact collector requirements. This
input is intentionally absent from the reusable workflow so caller repository
content cannot select its executable runtime.

### Local collection and refresh

The action invokes this same native command. Run it from the reviewed Relay
checkout with the pinned Python environment; replace the example identity,
source directory, and revision with reviewed public consumer inputs:

```bash
python -I actions/repository-intelligence/scripts/prepare_repository_adr_build.py \
  --runtime /trusted/adr-runtime \
  --repository-root /sources/consumer --repository egohygiene/consumer \
  --visibility public --source-commit <full-consumer-sha> \
  --observed-at 2026-10-05T00:00:00Z \
  --work-directory .cache/repository-intelligence
```

Omit `--runtime` to use the identical fresh acquisition path. Generated
`snapshot.json` and `receipt.json` live under the private work directory's `adr/`
child, outside tracked source; tracked destinations and symlinks are refused.
Work roots for this mode are `.cache`, `.staging`, `build`, or `dist`, subject to
the action's existing separate-public-output and report layout checks. Do not
publish the work directory. A denied retry removes prior generated candidates
at a verified safe destination. Use the review-only collector when richer
sanitized source diagnostics are needed.

The action passes that snapshot to the existing site renderers and attaches the
receipt to `provenance.json.adr_collection` before creating the existing build
manifest. The receipt binds immutable source hashes, observation inputs, exact
upstream trees/artifacts, executable/collector/helper hashes, source-validation
state, all nine domain claims, and both candidate digests. The bundle validator
rechecks this optional closed provenance boundary. It contains no runner paths,
current wall clock, deployment identity, or self-referential Relay commit.
The build manifest's existing Relay revision binds the adapter and renderer.

For native composition with the existing render scripts, first generate the
normal dashboard/provenance, then attach the receipt before site rendering and
manifest creation:

```bash
python -I actions/repository-intelligence/scripts/repository_adr_build_contract.py \
  --provenance /sources/consumer/dist/intelligence/provenance.json \
  --receipt /sources/consumer/.cache/repository-intelligence/adr/receipt.json \
  --snapshot /sources/consumer/.cache/repository-intelligence/adr/snapshot.json
```

Use that same snapshot with the existing site, supporting-view, and comparison
renderers, followed by manifest creation and bundle validation, as ordered in
`action.yml`. Tests execute those exact Bash bodies and compare the entire
bundle across different checkouts and independently prepared runtimes.
Rendering errors remain in the existing generation failure stage; acquisition,
collection, source-validation, normalization, and provenance denials print only
bounded stage codes. No failed generation reaches the workflow's site upload.

### Acceptance and Identity #69 handoff

Run `python3 -I scripts/run_repository_adr_acceptance.py` for fresh acquisition,
offline runtime replay, the real immutable Hygiene canary, and owner-native ADR
build tests. The normal validation workflow runs this read-only acceptance path.
The complete suite with the documented ADR, roadmap, and architecture runtimes
also retains the old external-snapshot and no-snapshot regression cases.

Identity #69 should first review its standard-path corpus with the review CLI,
resolve source-policy and migration findings in Identity, then pin this reviewed
Relay integration and opt in. Refresh by selecting a new consumer commit and an
explicit observation instant locally, or rerunning the pinned workflow against
the intended commit (its default observation is the represented commit time).
Validate the ordinary artifact before composing it into the existing site;
preserve unrelated routes and the historical rollback point. Record artifact
upload, Pages upload, deployment, receipt, and live-route checks separately.
The Hygiene canary's 12 canonical records still have legacy/missing-policy source
gaps and therefore cannot pass the production build. No consumer source or
historical ADR is repaired by this integration, and #115 remains open for the
real conforming-consumer acceptance and immutable upgrade handoff.
