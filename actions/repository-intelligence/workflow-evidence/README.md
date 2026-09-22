# Repository Intelligence Workflow Evidence

`egohygiene/relay/actions/repository-intelligence/workflow-evidence` is the
trusted control-plane helper for Relay's reusable Repository Intelligence
workflow. It validates event, identity, input, retention, and artifact naming
before checkout, then creates a closed run report from provider step outcomes.

This helper is not a general diagnostic collector. It never imports caller
modules, executes caller scripts, records raw stderr, or copies environment
variables into the report. The final report contains only allowlisted identity,
contract, stage, rule, artifact, and remediation fields. It is created in an
unpredictable directory beneath `RUNNER_TEMP` and handed to
[`preserve-ci-report`](../../preserve-ci-report/README.md).

The public entry point is the reusable workflow documented in
[`docs/repository-intelligence-publication.md`](../../../docs/repository-intelligence-publication.md).
Direct consumers should not need to invoke this helper.

## Operations

- `prepare` rejects unsupported or privileged event origins and unsafe inputs,
  then emits the site artifact identity and normalized event/trust classes.
- `finalize` maps provider-owned step outcomes to a stable `RIW-*` code, writes
  `repository-intelligence-run-report.json`, downgrades contradictory success
  metadata to a trust/input failure, and exposes its isolated path for bounded
  preservation.

External reusable callers must resolve this workflow at the exact full commit
recorded by GitHub. Relay-local `$/` dogfood is the sole mutable-ref exception:
the provider-reported called revision must equal the represented Relay
revision. Direct dispatch is additionally restricted to Relay itself at that
same revision. Caller workflow references must have GitHub's
`owner/repository/.github/workflows/file.yml@ref` shape and belong to the
represented repository.

Both operations are permissionless composite-action logic. They do not use a
GitHub token, secrets, a cache, or deployment authority.
