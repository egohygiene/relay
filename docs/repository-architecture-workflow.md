# Reusable repository architecture validation

This is Relay #99 checkpoint 4. The experimental workflow is
`.github/workflows/repository-architecture-validation.yml`. It composes the
[existing local adapter](repository-architecture-validation.md) and
[diagram collector](repository-architecture-diagrams.md); it adds no sibling
validation rules. The [checkpoint-5 acceptance suite](repository-architecture-acceptance.md)
adds native fixtures, local recovery evidence and a manual dogfood caller;
checkpoint 6 owns live GitHub acceptance. The current profile remains advisory-only.

## Caller contract

Call the workflow at a reviewed **full Relay commit SHA containing this file**.
The catalog's `@v1` string is a discovery convention, not evidence that this
unreleased workflow is included in that alias. Mutable called references are
rejected. This example is deliberately a migration template, not a claim of
released adoption:

```yaml
name: Architecture evidence
on:
  pull_request:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  architecture:
    uses: egohygiene/relay/.github/workflows/repository-architecture-validation.yml@<reviewed-full-commit-sha>
    with:
      check-id: architecture
      mode: advisory
      repository-contract-adoption: unknown
      repository-contracts: "[]"
      adr-adoption: legacy
      adr-policy: ".config/repository-intelligence.toml"
      diagram-adoption: present
      diagram-roots: '["ARCHITECTURE.md", "SYSTEM.md"]'
      artifact-retention-days: 30
```

The policy path must refer to an existing caller-owned EgoLint policy compatible
with the request. The workflow never authors one. `present` and `legacy`
adoption require paths; `unknown` and `not-applicable` forbid them. Defaults are
`unknown` with no paths, so absence is never silently declared exempt.
Use `not-applicable` only for an explicitly reviewed exemption. Each contract
or diagram list accepts at most 16 normalized relative paths. The shared request
fixes ceilings at 256 findings, 10,000 files, and 100 MiB.

`check-id` is a lowercase kebab-case identifier of at most 48 characters,
defaulting to `architecture`. Separate calls or matrix entries in the same
caller workflow must use distinct IDs. Retention accepts integer days 1–90,
default 30. Invalid preflight input receives a fixed 30-day failure report when
provider identity is sufficient; input text is not reflected into that report.

Supported caller events are ordinary same-repository or fork `pull_request`,
branch `push`, branch `workflow_dispatch`, and `schedule`. Both PR classes have
the same read-only authority. The represented revision is **`github.sha`**—the
merge candidate on an ordinary PR—not an inferred head revision. The generic
report manifest binds that same SHA. Identity and visibility come from GitHub;
they cannot be overridden by workflow inputs. Privileged handoff events such
as `pull_request_target` and `workflow_run` are rejected before checkout.

## Trusted execution and dependencies

The only permission is `contents: read`, at workflow and job scope. There are
no caller secrets, persisted checkout credentials, caches, containers, consumer
commands, AI services, repository mutations, or publication steps. The caller
checkout lives at `caller/`. Source paths are data, never executable controls.

Relay helpers use `$/` to resolve from the exact called Relay revision. All
external actions and three sibling checkouts use full commit SHAs. The internal
helper invokes Python with `-I`, adds only the trusted Relay scripts directory,
and does not import packages from the caller checkout. Its control state,
dependency caches, runtime and report staging are outside that checkout in
new unpredictable runner-temporary directories.

The helper binds `job.workflow_*` in its composite operation's step-level `env`.
GitHub does not expose `job` in job-level `env`. Each operation resolves its own
identity, so failure reporting does not depend on successful preflight or a
prior environment-file write. The [acceptance guide](repository-architecture-acceptance.md#checkpoint-6-observation--2026-09-28)
records the provider parsing failure that established this regression.

The workflow targets `ubuntu-24.04`, Linux x86_64 and CPython 3.12. Acquisition
uses hash-locked binary Python wheels and Rust/Cargo **1.85.1** installed by
rustup's verified distribution mechanism into isolated storage. Cargo fetches
the pinned source's lockfile dependencies separately. Runtime preparation then
verifies all profile artifacts and builds with `--frozen --offline`; native
validation uses `--network none --pull-policy never` and a sanitized environment.
This is the reviewed tool path, not an OS sandbox for arbitrary executables.
The runner image itself is provider-managed, not a reproducible image digest.

Source/dependency acquisition and native build are skipped if both native
surfaces are explicitly not applicable, or required mode is requested. Diagram
discovery can still run when native acquisition/build fails; its evidence stays
distinct from unavailable native validation. A required request receives the
shared adapter's explicit unavailable result and fails after retention.

## Evidence, presentation and failure semantics

The helper accepts only evidence returned by the current adapter invocation.
It copies those bounded result/sidecar bytes into isolated staging and records
a run-bound checksum receipt. Finalization verifies that receipt and identity
before copying files to a new retention directory. It never scans caller report
directories, uploads raw logs, or accepts an old file after an early failure.
The normalized local result and sidecars are byte-identical to retained CI
files. Workflow metadata is a separate envelope.

| Retained file | Meaning |
| --- | --- |
| `workflow.json` | Closed identity, raw stage outcomes, result availability, planned enforcement and file digests |
| `.reports/architecture-validation/result.json` | Fresh shared adapter result, when available |
| Referenced evidence sidecars | Native projections/SARIF and diagram metadata actually returned by that invocation |
| `relay-report-manifest.json`, `SHA256SUMS` | Generic #6 report lifecycle binding and checksums |

The [workflow schema](../schemas/architecture-workflow-evidence.v1.schema.json)
excludes source prose, logs, environment contents and absolute paths. Private
and internal repositories retain their visibility classification. Artifact
access remains GitHub's repository/run access boundary; this workflow does not
publish reports to a site or organization aggregator.

Before generic metadata, a bundle contains at most six files and 6 MiB. Each
validation file is capped at 1 MiB; `workflow.json` is capped at 32 KiB. At most
20 escaped annotations are emitted, with source locations preserved and message
text capped at 2,048 characters. The Step Summary uses fixed labels and enums,
records each stage, and distinguishes actual upload outcome from semantic state.

Advisory nonconformance, legacy and incomplete results remain warnings.
Invalid input, failed/skipped required stages, unavailable execution, rejected
required mode, evidence tampering and failed retention fail the job. Stages use
raw `outcome`, never a success `conclusion` produced by `continue-on-error`.
Finalization and preservation run with `always()` before final enforcement.
The retained report says upload is `pending`: it was created before upload and
cannot certify its own upload. Inspect `report-upload-outcome` and a nonempty
`report-artifact-digest`, plus the job result. An artifact name alone is not proof.
The generic manifest's completeness describes the **report bundle**, not ADR
or diagram semantic conformance.

Artifact names are
`relay-report-architecture-<check-id>-<caller-workflow-hash>-<run-id>-<attempt>`.
Outputs expose semantic status, adapter outcome, planned workflow outcome,
artifact name/digest, manifest digest and observed preservation outcome.
The planned workflow outcome excludes later upload/presentation failures; the
actual job fails if those occur. Failed jobs may not expose all reusable outputs;
inspect retained artifacts and the run summary directly.

## Cancellation, retry and acceptance

Concurrency partitions by contract, repository, caller workflow path/ref,
target ref and check ID. Newer runs cancel only the same work identity. Caller
wrappers must use a different concurrency prefix to avoid self-cancellation.
The job has a 20-minute timeout, with tighter bounded subprocess timeouts.
Cancellation, runner loss, unavailable job context or an artifact-service outage
can prevent preservation. `always()` does not guarantee delivery after runner
termination. Retry in a new attempt; no previous evidence is reused.

GitHub.com job workflow identity and `$/` support are required. No Enterprise
Server or local Actions emulator support is claimed. Local helper/adapter tests
establish behavior without asserting GitHub scheduling, upload, or deployment.

The refreshed profile consumes the merged EgoLint #73 fix; consumers still need
reviewed policy migration and fixture evidence before fleet conformance. Existing
runtime receipts must be rebuilt against the new profile. Diagram semantics
remain unavailable pending EgoLint #74. Broader
consumer/recovery fixtures are documented in the
[acceptance guide](repository-architecture-acceptance.md). Hosted acceptance,
release publication and caller rollout remain separately tracked; implementation
does not complete #99/#5.
