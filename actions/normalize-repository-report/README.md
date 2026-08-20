# Normalize Repository Report

Convert canonical OSV, MegaLinter, or OpenSSF Scorecard output into the compact
`egohygiene.repository-report-summary/v1` contract consumed by repository
intelligence dashboards. Native scanner JSON, SARIF, workflow artifacts, and
GitHub Security integrations remain authoritative.

## Example

```yaml
- name: Normalize MegaLinter report
  if: always()
  uses: egohygiene/relay/actions/normalize-repository-report@<full-commit-sha>
  with:
    producer: megalinter
    input: .reports/megalinter/mega-linter-report.json
    output: .reports/megalinter/summary.json
    policy-input: egolint/.config/megalinter/tool-matrix.json
```

## Status model

The summary preserves three independent dimensions:

- `execution.state`: whether usable producer output was emitted;
- `findings.state`: whether policy sees clear, advisory, or blocking findings;
- `freshness.expires_at`: when consumers must treat the evidence as stale.

Unavailable input becomes `unknown`; malformed producer data becomes an
execution `failure`. Neither condition becomes green.

## Producer behavior

| Producer   | Canonical input                              | Policy behavior                                                                    |
| ---------- | -------------------------------------------- | ---------------------------------------------------------------------------------- |
| OSV        | Workflow-generated OSV JSON summary          | Findings at or above `severity_threshold` are blocking; lower findings advisory.   |
| MegaLinter | `mega-linter-report.json` plus tool matrix   | Each finding-bearing tool inherits `blocking` or `advisory` from the matrix.        |
| Scorecard  | OpenSSF SARIF and optional official API JSON | Checks below ten are advisory; no aggregate score is invented from SARIF.           |

An official Scorecard aggregate is accepted only when its repository and full
commit match the evaluated workflow commit. Stale, missing, or incompatible API
data leaves `aggregate_score` null while retaining SARIF-derived check signals.

## Inputs and output

`producer`, `input`, and `output` are required. MegaLinter also requires
`policy-input`. `scorecard-api-input`, `stale-after-days`, `generated-at`,
`detail-url`, `repository`, and `commit` are optional. All file inputs are
repository-relative and traversal-free. The action resolves every input and
output against `GITHUB_WORKSPACE`, rejects symbolic-link escapes, rejects
non-finite or out-of-range producer numbers, and serializes standards-compliant
JSON only.

The `summary` output contains the same repository-relative path passed through
`output`. The action makes no network requests, commits, or deployments.
