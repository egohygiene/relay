# Preserve CI Report

Preserve bounded success or failure evidence from a CI check as one immutable
GitHub Actions artifact. By default, the producer writes beneath
`.reports/<producer>/`; a trusted reusable workflow may instead provide one
isolated source beneath `RUNNER_TEMP`. Relay adds a checksummed manifest,
assigns a unique run-and-attempt artifact name, and uploads the complete
directory.

Call this action with `always()` after a producer step whose raw failure is
temporarily captured. Reassert the producer failure only after the evidence is
uploaded:

```yaml
- name: Run the check
  id: check
  continue-on-error: true
  run: |
    set -euo pipefail
    mkdir -p ".reports/example"
    example-check --json > ".reports/example/result.json"

- name: Preserve success or failure evidence
  if: "${{ always() }}"
  # egohygiene/relay preserve-ci-report v1
  uses: egohygiene/relay/actions/preserve-ci-report@<full-commit-sha>
  with:
    producer: "example"
    outcome: "${{ steps.check.outcome }}"
    retention-days: 30

- name: Enforce the check outcome
  if: "${{ steps.check.outcome == 'failure' }}"
  run: exit 1
```

The check must write to the exact stable directory
`.reports/<producer>/`. A successful check must leave at least one regular
file. Failed, cancelled, or skipped checks may have no native output; Relay
still produces an `unavailable` manifest instead of presenting missing evidence
as success.

Trusted reusable workflows may instead pass `source-directory` for an isolated
evidence directory beneath `RUNNER_TEMP`. The path must be absolute, normalized,
already exist, contain no symbolic-link component, and resolve strictly inside
the runner temporary directory. Relay never creates an isolated source path;
the trusted producer must create and populate it before preservation. Manifest
paths and checksums remain relative to that source, while the action uploads the
exact isolated directory.

The action rejects symbolic links in the report-directory path before creating
missing directories. It also rejects symbolic links or non-regular entries in
the report itself, unsafe producer IDs, non-full represented revisions, more
than 100 files by default, more than 100 MiB by default, and retention outside
1–90 days. It never checks out code, executes producer output, changes
repository state, or grants permissions.

Use `publish-report-snapshot` separately when a trusted default-branch job also
needs to commit a curated `.reports` projection. This action owns only the
per-run artifact and its provenance.
