# Preserve CI Report

Preserve bounded success or failure evidence from a CI check as one immutable
GitHub Actions artifact. The producer writes only beneath
`.reports/<producer>/`; Relay adds a checksummed manifest, assigns a unique
run-and-attempt artifact name, and uploads the complete directory.

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

The action rejects symbolic links, non-regular entries, unsafe producer IDs,
non-full represented revisions, more than 100 files by default, more than
100 MiB by default, and retention outside 1–90 days. It never checks out code,
executes producer output, changes repository state, or grants permissions.

Use `publish-report-snapshot` separately when a trusted default-branch job also
needs to commit a curated `.reports` projection. This action owns only the
per-run artifact and its provenance.
