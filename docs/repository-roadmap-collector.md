# Canonical roadmap collector — Relay #112

## Design checkpoint and authority

This design precedes the collector implementation. The native collector reads
one immutable `ROADMAP.md`, invokes EgoLint, validates the resulting Hygiene
projection, and invokes Observatory's pinned normalizer. It never runs consumer
code, repairs canonical intent, discovers the organization, or publishes a site.
ADR-007 and ADR-010 retain their existing ownership boundaries. The newer Aether
#90 and organization #42 proposals do not replace Hygiene authority.

**Publication is blocked by [Observatory #25](https://github.com/egohygiene/observatory/issues/25).**
The current read model always creates every domain view. Its coverage describes
freshness of existing records, not whether a domain was collected. Relay must
not invent missing-domain entities or alter Observatory's views. This checkpoint
therefore emits a closed local review envelope, never a bare action-consumable
snapshot. `--observatory-snapshot` must not receive this envelope. The existing
renderer rejects it by schema. Full #112 acceptance and #113 integration remain
pending an owner-reviewed contract/pin update.

## Exact supported matrix

| Role | Immutable revision | Contract/version and authority |
| --- | --- | --- |
| Hygiene projection validator/schema/vocabulary | `5e0602265b6ac5e5165b89f418e55a3fd12f8a64` | `egohygiene.repository-intelligence/v1`, `1.0.0-alpha.1`, proposed; exact Observatory input lock |
| Hygiene roadmap source meaning selected by EgoLint | `f598ed659a43dd759d4ede41c27f9e5daf991aa7` | `hygiene.roadmap/v1alpha1`, `0.1.0`, proposed in EgoLint's catalog |
| EgoLint semantic validator | `8b99ec4377eb84044fac411dff6b8074317ec094` | `egolint.repository-intelligence-validation/v1`, report schema version 1, catalog `0.1.0-alpha.1`; source-built, unreleased |
| Observatory normalizer | `3cb3555f56b9b110e98e295c1201e8d9af641297` | `egohygiene.observatory.repository-intelligence-read-model/v1`, `1.0.0-alpha.1`; existing Relay renderer pin |

The executable lock records artifact SHA-256 values and Git tree identities.
The two Hygiene revisions differ in ADR rejection support; this profile collects
no ADRs or ADR events. Its roadmap/issue subset is checked against both schemas.
This is an explicit bounded intersection, not a claim of whole-contract equality
or ratification. Repinning requires mapping, integrity, compatibility, privacy,
and native integration tests together. Sibling source is acquired separately;
Relay does not vendor sibling implementations.

## Source mapping

| Canonical input | Projection or collection evidence |
| --- | --- |
| Declared repository + full source SHA | Repository identity, `projection_id`, `represented_commit`; never a checkout basename |
| Exact Git blob `ROADMAP.md` | Roadmap source URL at the immutable revision, Git blob ID and SHA-256 |
| Manifest schema/repository/visibility/publication/updated | EgoLint validation, explicit public-publication gate, collection provenance and freshness |
| `roadmap-step.id` | `ri:<repository>:roadmap-step:<ID>` and native key |
| Matching Markdown heading | Title; no AI summary |
| `status` | Authoritative declared state, unchanged by issue state |
| `**Outcome:**` paragraph | Roadmap entity `attributes.outcome` |
| `**Exit criteria:**` checklist | Ordered text and checked state in `attributes.exit_criteria` |
| `depends_on` | Directed `depends-on` edges, with roadmap provenance |
| Explicit `issues` metadata | Collected reference inventory; `tracks` edges only for observed, public, same-repository provider records |
| Captured issue state | Separate issue entity and provider source; no titles, bodies, comments or authors |
| Explicit observation time and maximum ages | Stable freshness decisions and diagnostics; never the build wall clock |

EgoLint owns duplicates, malformed metadata, state agreement, completion,
missing references, dependency readiness and cycles. Relay parses the supported
source representation only to map it; it does not reproduce those rules. The
collector accepts flat YAML comment metadata and canonical outcome/checklist
sections; ambiguous or unsupported extraction is rejected, not guessed. Other
prose remains canonical Markdown but is outside this bounded extraction.

The root repository lifecycle remains unknown: collecting a roadmap proves no
repository health or lifecycle claim. No history events are fabricated. ADRs,
checks, releases, deployments, full work inventory and Git history are explicitly
`uncollected` in the collection result. An explicit subset of issue references is
never a complete work scan. Missing provider observations stay unavailable; an
empty captured list cannot prove there are no issues.

## Trust, replay and failure boundary

Acquisition and execution are separate. `prepare` uses exact Git objects from
already acquired upstream clones, checks the lock's Git tree and file digests,
and builds EgoLint with locked offline Cargo dependencies. Its local runtime
receipt binds the executable digest to that acquisition. The prepared directory,
Python environment, Cargo cache/compiler and collector installation are trusted
local control-plane inputs; do not accept them from a candidate repository.
`collect` does not fetch GitHub or install dependencies.

Collection reads only the exact source blob; dirty checkout files are ignored.
EgoLint sees a temporary minimal workspace containing those bytes and a
collector-owned policy. ADR/history adoption is unknown, not not-applicable.
Provider evidence is optional captured JSON with a closed, bounded allowlist.
Only same-repository issue numbers explicitly present in source may be enriched.
Public visibility must be observed before enrichment; private/unknown visibility,
foreign references, symlink inputs, unsafe paths, duplicate keys and unsupported
contracts fail closed. No raw exception, provider body, credential, author email,
local path or protected name/count is included in denied output.

The result contains structured rule IDs, bounded source lines and fixed
remediation, exact pins, input/output digests and explicit collection/validation
states. Raw EgoLint diagnostic prose is not exported. A structurally valid source
with semantic errors can retain a local review candidate with `invalid` status;
normalization is never reported as semantic conformance. Invalid graph/schema
inputs retain diagnostics without a snapshot. The envelope always records
`publication: denied`, including an otherwise valid roadmap, until #25 is solved.

Refresh is explicit: select a new immutable source SHA and observation boundary,
recapture authorized provider metadata if wanted, and rerun. Replaying identical
source, evidence, pins, runtime and time/age inputs produces byte-identical output
in differently named directories. Stale intent/provider data keeps its source
state and is marked stale. No issue completion implies roadmap completion.

## Acceptance boundary

The real Akashic canary is `9af6e87b2c708dc0cb7a57a9ccf315d51e294a1b`.
Its checked-in bytes declare `AKA-Q03` ready while `AKA-Q02` is active. EgoLint
must report `EGO-INTEL-ROADMAP-STATE-001`; Relay must preserve those declarations.
The source correction belongs to [Akashic #197](https://github.com/egohygiene/akashic/issues/197).
The immutable canary proves extraction and diagnostics, not publishability.
Its fixture keeps upstream Markdown hard breaks and exact line endings through
a file-specific Git attribute; the captured SHA-256 detects any byte change.

Native tests separately feed normalized roadmap candidates to the existing
roadmap renderer and prove that the complete review envelope is rejected by its
public snapshot entry point. That renderer-level proof is not a site build,
artifact upload, deployment, or live-route acceptance. No hosted CI polling is
needed for local validation.

## Native commands

This experimental CLI requires Python 3.11+, the exact packages in
`actions/repository-intelligence/contracts/roadmap-collector-requirements.txt`,
Git, and Rust/Cargo 1.85.1 for preparation. It adds no dependency to the deployed
action. Run from Relay's checkout; use absolute paths without `..` or symlink
ancestors. First acquire dependencies (network access is confined to this phase):

```bash
task_root="$(pwd)"
task_cache="${task_root}/.cache/roadmap-collector"
mkdir --parents "${task_cache}"
python3 -m venv "${task_cache}/venv"
task_python="${task_cache}/venv/bin/python"
"${task_python}" -m pip install --requirement \
  "${task_root}/actions/repository-intelligence/contracts/roadmap-collector-requirements.txt"
git clone --no-checkout https://github.com/egohygiene/hygiene.git "${task_cache}/hygiene"
git clone --no-checkout https://github.com/egohygiene/observatory.git "${task_cache}/observatory"
git clone https://github.com/egohygiene/egolint.git "${task_cache}/egolint"
git -C "${task_cache}/egolint" checkout --detach 8b99ec4377eb84044fac411dff6b8074317ec094
cargo fetch --locked --manifest-path "${task_cache}/egolint/Cargo.toml"
git clone --no-checkout https://github.com/egohygiene/akashic.git "${task_cache}/akashic"
```

Prepare and collect offline. Preparation requires a new destination and reads
the locked Git objects regardless of each upstream checkout's branch or files.
The source-built binary and verified Python modules stay in a private trusted
runtime directory outside the inspected consumer. Keep the runtime receipt
together with those bytes; it is a local build receipt, not a signed release.

```bash
task_collector="${task_root}/actions/repository-intelligence/scripts/collect_repository_roadmap.py"
"${task_python}" "${task_collector}" prepare \
  --hygiene "${task_cache}/hygiene" \
  --egolint "${task_cache}/egolint" \
  --observatory "${task_cache}/observatory" \
  --output "${task_cache}/runtime"
"${task_python}" "${task_collector}" collect \
  --runtime "${task_cache}/runtime" \
  --repository-root "${task_cache}/akashic" \
  --repository egohygiene/akashic --visibility public \
  --source-commit 9af6e87b2c708dc0cb7a57a9ccf315d51e294a1b \
  --observed-at 2026-09-26T19:00:00Z \
  --output "${task_cache}/canary/roadmap-collection.review.json"
```

`prepare` returns 0 on success. `collect` returns **2** when it retains an invalid
or blocked review result, and **3** for a denied input/runtime operation. There
is deliberately no publication-success exit code. Do not upload the review
envelope or extract its nested candidate into production. The closed result
schema is `schemas/roadmap-collection-review.v1.schema.json` under the action.
On a safe writable output path, denial replaces any previous result with a
minimal diagnostic; unsafe output paths remain untouched and the command fails.

Optional `--provider-evidence` accepts this exact captured-input shape. A trusted
read-only acquisition must check repository visibility before retaining any
issue metadata. No credential is read by this CLI. Only explicit same-repository
issue references are supported; PRs, cross-repository references, full work scans
and arbitrary links require later owner-reviewed profiles.

```json
{
  "schema": "egohygiene.relay.roadmap-provider-capture/v1",
  "repository": "egohygiene/akashic",
  "visibility": "public",
  "observed_at": "2026-09-26T19:00:00Z",
  "status": "observed",
  "issues": [{"number": 34, "state": "open"}]
}
```

Capture `status: unavailable` with an empty array for access failure, or omit the
input. `--maximum-intent-age-days` defaults to 30 and
`--maximum-provider-age-seconds` to 86400; both are explicit provenance inputs.
These are collection freshness bounds, not organizational policy.

Run the complete native fixture, including the unmodified real canary:

```bash
RELAY_ROADMAP_RUNTIME="${task_cache}/runtime" \
RELAY_AKASHIC_REPOSITORY="${task_cache}/akashic" \
"${task_python}" -m unittest discover --start-directory tests \
  --pattern "test_repository_roadmap_collector.py" --verbose
```

Ordinary test discovery explicitly skips this experimental module if its Python
requirements are absent, and skips upstream integration if the prepared-runtime
variables are absent. Such skips do not establish collector acceptance. The
native command above must run without skips for the collector checkpoint.

## Next work and decision impact

The maintainer selected ADRs/Decisions as the first fleet campaign in Pace #5;
the roadmap campaign in Pace #31 follows it. Preserve this bounded checkpoint
for review. Before resuming roadmap publication, resolve Observatory #25, review
the exact collector repin, and complete #112 before #113 integration. Consumer
deployment and canonical source repair remain separately owned.

ADR not required for this checkpoint: it implements the existing ADR-007/010
ownership boundary, adds only a local review seam, and explicitly defers the
upstream compatibility decision instead of creating a competing read model.
