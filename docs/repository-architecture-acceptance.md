# Architecture fixtures, dogfood, and recovery

This is [#99 checkpoint 5](https://github.com/egohygiene/relay/issues/99).
It proves local composition of the existing adapter, workflow helper and #6
report lifecycle. It does not establish hosted scheduling, upload, release,
required enforcement, fleet adoption or diagram semantic validity.

## Evidence boundary

The native acceptance suite reuses `AdapterFixture` and
`ArchitectureWorkflowFixture`; it does not duplicate EgoLint rules or create a
second validator. Each disposable Git repository goes through preflight, the
real pinned native executable where applicable, finalization, the real local
report packager, and presentation. Provider identity, stage outcomes and upload
outcomes are explicitly synthetic. No upload occurs in these tests.

The [recorded checkpoint observation](evidence/repository-architecture-checkpoint-5.json)
captures the 12-test native run, 23 locally retained scenario/recovery bundles,
toolchain and profile identity, and a real Relay scan at the verified checkpoint-4
merge. That Relay scan inspected 301 files, retained four normalized files and
one diagram source, verified manifest digests, and left its checkout clean. Its
incomplete/warning result is local evidence; provider inputs were synthetic.

Existing contract, adapter, diagram and workflow suites already cover pin
drift, unsupported policy, missing approvals, duplicate ADR IDs, missing indexes,
input bounds, path traversal, symlinks, dangerous Git helpers, source-content
exclusion, escaped annotations and receipt tampering. The new suite tests the
composition of those boundaries instead of repeating each individual check.

| Disposable case | Advisory semantics | Advisory execution | Required intent |
| --- | --- | --- | --- |
| Conformant repository contract; other surfaces explicitly not applicable | conformant / passed | success | denied; unavailable evidence retained |
| Invalid contract with missing required file | nonconformant / warning | success with warning annotation | denied; unavailable evidence retained |
| Declared legacy ADR corpus | legacy / warning; partial ADR coverage | success | denied; unavailable evidence retained |
| Unknown adoption | incomplete / warning | success | denied; unavailable evidence retained |
| Unavailable runtime with independent diagrams | unavailable | failure with complete diagram inventory retained | denied; unavailable evidence retained |
| Malicious source symlink | incomplete / warning; scan rejected | success with advisory diagnostic; no native conformance | denied; unavailable evidence retained |
| Conformant contract plus unvalidated diagrams | incomplete / warning | success; diagram semantics unavailable | denied; unavailable evidence retained |

The positive conformance case covers only the selected repository-contract
surface. It never claims ADR or diagram conformance. The legacy fixture uses
the existing native old-policy corpus solely to reproduce EgoLint #73, retains
`RELAY-ARCH-COMPAT-001`, and must stay legacy with partial coverage. Do not adopt
that older policy in consumers. An implemented or merged ADR still needs its
separate human decision evidence.

## Run and inspect locally

Prepare the hash-locked dependencies and pinned runtime using the
[adapter guide](repository-architecture-validation.md). Then run from trusted
Relay code, selecting a **new** evidence directory outside the checkout:

```bash
python3 -I tests/run_architecture_acceptance.py \
  --runtime /path/to/architecture-runtime \
  --evidence-directory /path/to/new-architecture-evidence
```

The command rejects a missing or tampered runtime before running and exits
nonzero on failures or skips. Omit `--evidence-directory` to discard temporary
bundles after the tests. Ordinary `unittest discover` still runs the suite when
`RELAY_ARCHITECTURE_RUNTIME` is supplied, and explicitly skips it otherwise.
The evidence directory contains:

- `acceptance.json`: test outcome, profile digest, and explicit synthetic/local
  evidence labels; never a hosted acceptance assertion.
- One directory per advisory/required scenario and recovery observation.
- `workflow.json`, the exact normalized result and referenced sidecars, and
  `relay-report-manifest.json` plus `SHA256SUMS` inside each report directory.

Inspect result `semantic_status`, `coverage` and `outcome` alongside the
request's declared adoption and the retained adoption diagnostics. The
generic manifest's completeness concerns packaging, not semantic coverage.
Its `generated_at` is the packaging wall clock: it and the manifest checksum
may differ between replays. Every validation file and `workflow.json` must be
byte-identical across differently named checkouts at the same revision and
captured provider inputs; every other manifest field must agree.

The suite checks all manifest sizes and digests, the exact file allowlist,
private/internal classification, and source/log/path canaries across retained
files and presentation. It verifies failed acquisition followed by a new
attempt succeeds without modifying the failed bundle, and that early checkout
failure or cancellation cannot import old caller reports. Upload outages fail
presentation even when the local manifest exists. Runner termination can still
prevent preservation; these local tests do not prove delivery after cancellation.

## Relay dogfood and checkpoint 6

`.github/workflows/repository-architecture-dogfood.yml` is a manually dispatched,
read-only caller of the same-revision reusable workflow. It has a separate
concurrency prefix, no scheduled or pull-request trigger, and no provider write
or deployment authority. The called job retains its 20-minute timeout.

Relay has inline legacy `DECISIONS.md` records and no canonical ADR policy for
this workflow. The caller therefore declares canonical adoption **unknown**,
with `ARCHITECTURE.md` as its sole diagram root. The expected advisory result
with a working native runtime is incomplete/warning, never conformant. Adding
a real policy or migrating Relay's ADR corpus belongs to its existing backfill
work, not this fixture checkpoint.

After checkpoint 5 is merged and its exact tree is verified on `main`, checkpoint
6 must inspect actual default-branch executions:

1. Dispatch the dogfood caller on `main` with `required-denial: false`; record
   the resolved source and Relay revisions, run ID and attempt.
2. Inspect job/step outcomes, read-only permissions, exact sibling pins,
   annotations and Step Summary. Retained `artifact_upload: pending` describes
   pre-upload state; inspect the actual preservation step and archive digest.
3. Download the ordinary report artifact; verify its identity, byte limits,
   checksums, normalized coverage and privacy. Inspect logs for sanitized output
   without copying source or credentials into acceptance notes.
4. Dispatch a separate `required-denial: true` run. Expect failure after retaining
   `RELAY-ARCH-MODE-001` / `AW-REQUIRED`; do not enable required enforcement or
   reinterpret the expected failure as conformance.
5. Record acquisition, cancellation/retry and artifact-service limitations from
   actual evidence. Never infer hosted behavior from synthetic stage inputs.

EgoLint [#73](https://github.com/egohygiene/egolint/issues/73) still owns ADR-policy
compatibility, and [#74](https://github.com/egohygiene/egolint/issues/74) owns
reviewed offline diagram validators. Checkpoint 6 must reconcile all #5 criteria
and leave unavailable capabilities open. Merged checkpoint PRs alone do not
close #99, #5 or #27. Release, fleet rollout, Relay #115 collection/build and
Observatory #25 partial-domain publication acceptance remain separate gates.
