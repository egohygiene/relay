# CI run lifecycle and durable reports

Relay issue [#6](https://github.com/egohygiene/relay/issues/6) defines one
versioned answer to two related questions: when may a newer workflow run cancel
an older run, and how does useful evidence survive a failing check?

The machine-readable authority is
[`catalog/ci-run-lifecycle.json`](../catalog/ci-run-lifecycle.json). It maps
every executable Relay workflow to exactly one class without changing the
workflow catalog v1 schema.

## Workflow classes

| Class | Cancel stale work | Use when |
| --- | --- | --- |
| `supersedable-check` | Yes | Read-only or workspace-only analysis can be recomputed for the same repository and ref. |
| `evidence-preserving-check` | No | Read-only accepted bytes or review evidence must finish even if a newer run starts. |
| `serialized-write` | No | A run may mutate repository or deployment state, so runs serialize by their mutation target. |
| `immutable-publication` | No | A release is keyed by immutable identity and may resume only matching evidence. |

Concurrency groups are repository-scoped by GitHub and include the smallest
stable work identity that represents contention: a ref or pull-request/run ID
for checks, a mutation target for writers, or an immutable version for
releases. A workflow must not select
`cancel-in-progress: true` merely to reduce queue time when cancellation could
strand provider writes or accepted artifact state.

## Report contract

Producers own their native report semantics and write to one compact stable
directory: `.reports/<producer>/`. They do not create timestamped history trees.
GitHub run identity and attempt belong in the artifact name instead:

```text
relay-report-<producer>-<run-id>-<run-attempt>
```

Thirty days is the default retention. Consumers may select 1–90 days when the
evidence sensitivity, investigation window, or storage cost justifies it. The
default bundle is bounded to 100 files and 100 MiB. A consumer that needs more
must review and declare larger bounds explicitly.

[`preserve-ci-report`](../actions/preserve-ci-report/) adds a versioned manifest
and checksums, then uploads the complete directory through an immutable
`actions/upload-artifact` pin. The producer step captures its raw outcome, the
preservation step runs with `always()`, and a later step reasserts failure.
Missing native output from a failed, skipped, or cancelled check becomes
`unavailable`; it never appears as a passing report.

Cancellation is not an artifact guarantee. GitHub may stop a superseded runner
before cleanup executes. The contract guarantees that a run which reaches its
preservation step keeps honest bounded evidence; the replacement run remains
the authoritative current result.

## Consumer proof

### Empathy golden consumer

At immutable Empathy revision
[`98778e8442d3be3ea7a3d1f62b71f33969346ecc`](https://github.com/egohygiene/empathy/commit/98778e8442d3be3ea7a3d1f62b71f33969346ecc),
`.github/workflows/osv-scan.yml` demonstrates the contract that Relay
standardizes:

- its repository/ref group cancels superseded scans;
- scanner outcomes are captured before the policy gate;
- `.reports/osv/` is the stable producer directory;
- artifact upload runs with `always()` and 30-day retention;
- the severity gate fails only after report validation and preservation; and
- trusted default-branch publication consumes the exact uploaded artifact.

Empathy run
[`35354888576`](https://github.com/egohygiene/empathy/actions/runs/35354888576)
materialized those reports for revision `b44f798bb49259f9f48416b4ffebde1103e135c0`.
Its report upload completed successfully before the severity-threshold step
failed, and the separately conditioned publication job still completed.
The Actions bot then published the bounded stable snapshot in immutable commit
[`c9800ed19293e7c1b1d4a70c3bea006c1f2b64f5`](https://github.com/egohygiene/empathy/commit/c9800ed19293e7c1b1d4a70c3bea006c1f2b64f5),
which records the same run ID in `.reports/osv/summary.json`.

This is reviewed adoption evidence, not a mutable dependency. Relay neither
copies nor executes Empathy implementation.

### Disposable consumer

Relay's validation workflow contains a deliberately failing disposable check.
It writes a synthetic report, records the failed step outcome, invokes
`preserve-ci-report` with `always()` and one-day retention, then verifies the
artifact outputs before allowing the test job to pass. That smoke path proves
that failure evidence remains uploadable without weakening the final status of
real consumer checks.

## Recovery and rollback

- A failed report upload means the workflow has no durable success result.
- Re-run the same revision for transient artifact-service failures; the unique
  attempt suffix prevents ambiguous replacement.
- Revert a consumer to its previous pinned Relay revision to roll back this
  action. Existing artifacts retain their original expiry.
- Repository snapshot commits remain a separate trusted operation owned by
  `publish-report-snapshot`; report preservation grants no write permission.
