# Native Work and Health source composition — Relay #151

This checkpoint extends the existing Roadmap/Decisions source plan with fresh
Work and Health collection. The local CLI and composite action
select explicit transport captures, invoke the trusted collectors, and
normalize one repository/commit/evaluation-bound graph. They do not accept the
collectors' publication-denied review envelopes as build inputs.

## Capture plan and action use

The new optional composite `source-captures` input names a closed JSON
transport plan relative to the consumer repository. It can select either source
or both, with or without existing `collect-roadmap` and `collect-adrs` flags.

```json
{
  "schema": "egohygiene.relay.source-capture-plan/v1",
  "work": {
    "provider_evidence": ".captures/intelligence/work-provider.json",
    "maximum_age_seconds": 86400
  },
  "health": {
    "inventory": "partial",
    "expected_reports": ["osv"],
    "reports": {"osv": ".captures/intelligence/osv-summary.json"},
    "check_runs": {
      "state": "observed",
      "path": ".captures/intelligence/check-runs.json",
      "observed_at": "2026-11-09T04:00:00Z"
    },
    "maximum_age_seconds": 86400
  }
}
```

```yaml
with:
  collect-roadmap: true
  collect-adrs: true
  source-captures: .captures/intelligence/source-plan.json
  as-of: "2026-11-09T04:05:00Z"
```

This is a configuration example. Its referenced captures must actually exist
and match the selected public repository and represented commit. Use the exact
reviewed Relay revision for adoption. Produce these untracked transport captures
in preceding caller-owned steps after choosing the represented source commit.
The composite requires an explicit `as-of` evaluation boundary for capture plans;
it never substitutes the commit timestamp for later provider observations. The
consumer retains artifact composition and deployment.

The [plan schema](../actions/repository-intelligence/schemas/source-capture-plan.v1.schema.json)
and stdlib preflight reject duplicate/unknown keys, unsafe paths and ambiguous
source selections before runtime acquisition. Paths inside the plan are literal
repository-relative data files, not commands, modules or URLs. Runtime paths
cannot be supplied by that consumer-authored plan. Keep transport captures and
the plan outside the consumer's final public site tree.

Work data uses the existing closed
[Work provider capture](../actions/repository-intelligence/schemas/work-provider-capture.v1.schema.json).
It retains independent issue/PR inventory scopes, capture times and pagination.
Health report files use the pinned normalized report-summary contract; check
runs use the existing bounded REST capture seam. See the
[Work](repository-work-collector.md) and [Health](repository-health-collector.md)
guides for those inputs. No authenticated provider reads or consumer scripts are
added to the builder.

For an unavailable Health provider, use `"check_runs": {"state": "unavailable"}`
and omit its capture path/time. `not-requested` and `failed` are also explicit.
Expected report names may be present without a matching report file selection;
their missing evidence remains visible. `inventory: complete` is an explicit
owner-reviewed declaration of the producer inventory, not a result inferred
from an empty API page. `not-applicable` requires no expected reports, report
paths or requested check provider.

The same plan selects both source groups without requiring canonical files:

```sh
python3 -I actions/repository-intelligence/scripts/prepare_repository_sources_build.py \
  --repository-root /consumer --repository egohygiene/relay --visibility public \
  --source-commit "$SOURCE_COMMIT" --observed-at "$OBSERVED_AT" \
  --capture-plan /consumer/.captures/intelligence/source-plan.json
```

Add `--collect-roadmap` and/or `--collect-adrs` for sources that actually exist
at that same commit. External `--observatory-snapshot` and
`--observatory-comparison` remain mutually exclusive with native selection.

## Explicit local captures and prepared runtimes

Local callers may select source inputs directly instead of using a plan:

```sh
python3 -I actions/repository-intelligence/scripts/prepare_repository_sources_build.py \
  --repository-root /consumer --repository egohygiene/relay --visibility public \
  --source-commit "$SOURCE_COMMIT" --observed-at "$OBSERVED_AT" \
  --collect-work --work-capture /captures/work-provider.json --work-runtime /trusted/work-runtime \
  --collect-health --health-runtime /trusted/health-runtime \
  --health-inventory partial --health-expect-report osv \
  --health-report osv=/captures/osv-summary.json \
  --health-check-runs-state unavailable
```

`--work-maximum-age-seconds` and `--health-maximum-age-seconds` independently
accept 1–2,678,400 seconds. Direct capture paths can be absolute or relative to
the invoking directory. Plan paths are relative to the consumer root. Paths are
normalized before an acquisition subprocess changes directories.

Each explicitly selected prepared runtime remains outside the consumer. When
every selected source has a supplied runtime, collection stays offline and
does not acquire an unrelated runtime. Canonical sources use the existing
`--runtime` ADR profile. Work and Health can use their separate `--work-runtime`
and `--health-runtime` profiles.

Alternatively, a trusted ADR `--runtime` serves the shared source plan. Work and
Health currently pin exact subsets of its identical Hygiene/EgoLint/Observatory
owner artifacts. The wrapper verifies that compatibility and copies only the
required checked files and already-verified executable into private temporary
profile directories. Each derived runtime receives its own matching profile
receipt and is reverified. No lock, source artifact, compiler output or original
prepared runtime is modified. Different core pins fail closed.

Without sufficient prepared runtimes, acquisition reuses the existing immutable
ADR acquisition path before offline execution. Its Linux x86_64/Python 3.12
constraints remain. The composite `source-runtime` input can supply the trusted
shared profile for capture plans.

## Composition and uncertainty

All fresh collectors bind the same public repository, full commit and UTC
evaluation time. Their original source/capture clocks remain independent:
re-evaluating an old captured page or report never relabels it current. The
composer unions canonical graph records before owner normalization and
preserves each exact collection claim. It never unions route views.

`source_collection.domains` groups build receipts by source: `decisions`,
`roadmap`, `work` and `health`. These names are not additions to canonical
coverage. Work owns only the existing `issues` and `pull_requests` claims;
Health owns only `checks`. The alpha.2 coverage object keeps exactly its nine
defined keys. Every other domain remains uncollected, and overlapping sources
cannot silently upgrade or overwrite one another's claims.

Normalized partial, stale, unavailable, failed, uncollected and explicitly
not-applicable captures can therefore render their honest state alongside
unrelated valid sources. No activity, PR merge or completed build supplies human
ADR approval, roadmap acceptance, producer applicability or a passing Health
result. A malformed Work capture, incompatible native result, record conflict
or invalid composed graph denies the selected build. Health's existing producer
isolation preserves rejected/missing reports as failed/partial evidence where
its owner contract permits normalization.

## Outputs, provenance and failure

The existing private `sources` directory receives `projection.json`,
`snapshot.json` and `receipt.json` only after source and aggregate admission.
The snapshot can feed the existing route renderer; its canonical projection
remains available for exact Compare input. Neither work files nor raw captures
are copied into the public bundle.

The new
[captured-source receipt](../actions/repository-intelligence/schemas/source-capture-build.v1.schema.json)
binds each raw capture digest, source status, original observation/expiry times,
input contract hashes, exact runtime profile and executable digest, collector
implementation hashes, collection claims and normalized candidate digests.
Public diagnostics contain only fixed owner codes and bounded producer IDs.
The aggregate receipt adds the capture plan digest when used. Attachment verifies
the actual composed snapshot bytes and matches the evaluation time to public
provenance's generation time. The bundle verifier uses stdlib receipt checks and
does not execute collectors while validating a finished artifact.

Before retrying, the wrapper removes prior candidate files. A denied invocation
writes a closed `failure.json` where its private output namespace is usable;
it contains only a fixed code, stage and selected source identifier. No candidate
receipt survives a failed build. Retained Compare baselines and consumer-owned
last-known publications are separate and untouched. This adds bounded local
failure evidence for caller-owned generation; it does not
create a deployment, approval or recovery authority.

## Review and remaining acceptance

This checkpoint implements the next source-plan slice under #151. Static
source/peer review and Python/JSON/YAML/bash syntax inspection are the only
verification in this pass. Native acquisition, collectors, renderers, tests, CI,
real canaries and publication were not executed, as requested.

Next, review the source plan and run its deferred exact-pin cases: canonical
sources plus Work/Health; captured-only sources; complete/partial/empty/stale
and unavailable inventories; mismatched reports; duplicate/conflicting inputs;
mixed pins; retained failure evidence; deterministic checkout-independent
bundles; and consumer-owned artifact preservation. Then adopt through the
consumer's reviewed preview/publication path. The parent acceptance issues stay
open until that evidence exists.


## Reusable capture handoff — next #151 checkpoint

The reusable workflow deliberately retains its existing canonical-source and
external-snapshot surface. It does not expose `source-captures` in this slice:
a file committed at the represented head cannot embed that same head's final
SHA, and a later Health capture cannot use a commit-time evaluation clock.

The next bounded #151 checkpoint needs an ordinary immutable capture artifact
from the caller's same-revision producer job, an explicit matching evaluation
boundary, private extraction that preserves consumer files, input digests and
failure reporting. It must validate artifact/run/revision identity before fresh
collection. This is a concrete transport/integration gap, not CI evidence debt
or permission to relabel captured commits and timestamps.
