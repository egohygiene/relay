# Native Roadmap and Decisions composition

Refs Relay #112, #113 and #151; parent acceptance remains #101 and organization
`.github#41`. This candidate implements native build integration, not a completed
consumer adoption, release or deployment.

The source plan is explicit: one public repository, one full represented Git
commit, one UTC observation boundary, and `--collect-roadmap` and/or
`--collect-adrs`. Both collectors use the exact supported alpha.2 owner set in
`actions/repository-intelligence/contracts/adr-collector.v1.lock.json`.
The original roadmap review CLI and its historical alpha.1 lock remain unchanged.
No consumer code runs and no provider request occurs during offline collection.

## Local build preparation

Prepare the native ADR runtime using the existing
[ADR collector guide](repository-adr-collector.md), outside the consumer checkout,
with the locked Python dependencies. That same runtime serves both sources:

```sh
python3 -I actions/repository-intelligence/scripts/prepare_repository_sources_build.py \
  --runtime /trusted/runtime \
  --repository-root /consumer \
  --repository egohygiene/identity \
  --visibility public \
  --source-commit "$SOURCE_COMMIT" \
  --observed-at "$OBSERVED_AT" \
  --collect-roadmap --collect-adrs
```

The native canonical files must actually exist at `SOURCE_COMMIT`. An opt-in
cannot materialize or approve missing ADR metadata, accepted decisions, roadmap
intent, or a publication host. Canonical Hygiene owner mode and explicitly
declared external ADR references retain the existing `--policy-owner` and
`--known-external-decisions` selections. These require Decisions collection.

The command writes only the private, untracked
`.cache/repository-intelligence/sources/projection.json`, `snapshot.json` and
`receipt.json` paths
by default. A retry removes the previous candidate before collecting. Only a
successful complete source plan writes the receipt. Invalid sources never reuse
an earlier candidate. The canonical projection accompanies its normalized snapshot for exact offline
Compare admission; it is kept private rather than added to public output. This
scratch directory is distinct from a retained Compare baseline and must not be published wholesale.

Without `--runtime`, the same wrapper acquires the immutable owner sources,
locked wheels and Rust toolchain through the existing ADR acquisition path, then
re-executes offline. Automatic acquisition currently supports Linux x86_64 and
Python 3.12. Prepared-runtime use retains its existing pinned Python requirements.
This pass did not execute either runtime path.

For separate roadmap source review, `collect_repository_roadmap_source.py`
accepts the same identity/commit/time and `--runtime`, plus an explicit `--output`
file outside the inspected checkout. Its result remains publication-denied.

## Composite action and reusable workflow

The action and reusable workflow expose `collect-roadmap: true`. Consumers that
already collect Decisions set both `collect-roadmap` and `collect-adrs` to true.
Roadmap-only consumers leave `collect-adrs` false. Existing ADR-only and external
snapshot builds retain their original paths; native collection conflicts with
`observatory-snapshot` and `observatory-comparison`.

Use the exact reviewed Relay commit when adopting the candidate:

```yaml
with:
  collect-roadmap: true
  collect-adrs: true
```

The composite action additionally accepts a trusted `source-runtime` outside the
consumer checkout for offline roadmap/combined builds. It cannot be combined
with `adr-runtime`. The reusable workflow acquires its own immutable runtime;
it does not accept a caller-selected executable runtime.

The action resolves source identity/revision/time before collection, then passes
the validated snapshot to all existing route composers and the build manifest.
No write permission, secret inheritance, Pages uploader or second deployer is
added. Consumer-owned site composition, route preservation, deployment and
historical rollback remain separate gates.

## Source mapping and conflict rules

`ROADMAP.md` metadata, heading, outcome and exit criteria use the existing bounded
roadmap extractor and pinned EgoLint source validation. Authored status and
checked criteria remain canonical intent, not proof of issue closure or human
acceptance. Roadmap record freshness follows the declared manifest `updated`
date; a freshly captured old roadmap can therefore have current collection
coverage and stale intent records.

Supported same-repository issue references survive as the owner-defined
`attributes.issue_references` URLs. They are displayed with provider state
uncollected. No issue placeholder, issue inventory, lifecycle event or readiness
award is fabricated. Cross-repository issue references remain unsupported by this
bounded adapter rather than being looked up without a public allowlist.

Decisions collection retains its complete valid-inventory admission and native
policy validation. The canonical Decisions index is still `docs/decisions/README.md`
in a combined build. Unknown/partial or invalid ADR adoption does not disappear
when Roadmap is enabled.

Composition unions canonical graph records before the pinned owner normalization;
it never concatenates generated views. Repository identity records may merge only
identical metadata and their provenance IDs. Conflicting record IDs, overlapping
collected domains, mixed repositories, commits, boundaries, versions or runtimes
are denied. Uncollected domains remain uncollected; a union cannot promote partial
inventory to complete. The first supported native plan covers Roadmap and
Decisions. Other collector review artifacts are not automatically admitted by it.

## Provenance and failure behavior

`provenance.json.source_collection` binds the explicit domain receipts, represented
commit and observation boundary, exact runtime owner pins and executable digest,
collector/composer implementation hashes, canonical source hashes, nine-domain
coverage and composed snapshot/projection digests. The attachment path checks the
actual snapshot bytes before rendering. The deterministic bundle manifest covers
this provenance using the existing payload inventory. Deployment receipts and
observation clocks from a future refresh remain outside these bytes.

The public provenance schema and bundle validator both support this source plan;
legacy `adr_collection` remains supported and cannot coexist with a second native
source-plan receipt. The workflow preflight validates the new flag and protects
the private `sources` path in the same way as the existing `adr` path.

Parser, native and acquisition exceptions cross a fixed-text CLI boundary. The
existing workflow report retains the overall generation failure stage; richer
per-domain failure artifact retention remains follow-up work. One failed selected
native source denies this build rather than silently erasing the other source.
Failure isolation between public modules still belongs to final product
acceptance and does not authorize publishing incomplete source plans.

## Review and deferred acceptance

This implementation pass includes static source review and Python/JSON/YAML/shell
syntax inspection only. No tests, native runtime replay, cross-checkout build,
consumer canary, CI investigation, deployment, release or live page acceptance
has been performed. Keep #112/#113/#151/#101 open for their remaining evidence.

Next review: exercise valid Roadmap-only and Roadmap+Decisions sources at exact
pins, malformed and missing sources, stale intent, mixed-source denial, privacy,
equal complete bundles across checkout paths, and consumer-owned composition.
Then adopt through a reviewed consumer preview, preserving branding, existing
assets and rollback history. No acceptance checklist is advanced by this draft.
