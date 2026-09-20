# Repository-journal callers

Production callers pin the reviewed full Relay commit SHA. The moving `v1`
alias is a discovery target, not an immutable production dependency.

## Scheduled deterministic journal

This default requires no Copilot policy, subscription, or agent token. The
caller owns the schedule and grants only provider-read permissions.

```yaml
name: Repository Journal

on:
  schedule:
    - cron: "17 6 * * 1"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  interval:
    permissions: {}
    runs-on: ubuntu-24.04
    outputs:
      start: "${{ steps.interval.outputs.start }}"
      end: "${{ steps.interval.outputs.end }}"
    steps:
      - id: interval
        shell: bash
        run: |
          python3 - <<'PYTHON'
          from datetime import datetime, timedelta, timezone
          import os
          end = datetime.now(timezone.utc).replace(microsecond=0)
          start = end - timedelta(days=7)
          with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
              stream.write(f"start={start.isoformat().replace('+00:00', 'Z')}\n")
              stream.write(f"end={end.isoformat().replace('+00:00', 'Z')}\n")
          PYTHON

  journal:
    needs: interval
    permissions:
      actions: read
      contents: read
      issues: read
      pull-requests: read
      security-events: read
    # Unreleased example; replace with the reviewed release metadata and full SHA.
    uses: egohygiene/relay/.github/workflows/repository-journal.yml@<full-commit-sha>
    with:
      mode: deterministic
      repository-id: "${{ github.repository }}"
      repository-revision: "${{ github.sha }}"
      interval-start: "${{ needs.interval.outputs.start }}"
      interval-end: "${{ needs.interval.outputs.end }}"
      generated-at: "${{ needs.interval.outputs.end }}"
```

## Reviewed manual candidate

A caller-owned producer first uploads exact evidence and candidate files under
separate artifact names. The manual workflow call then uses:

```yaml
  journal:
    needs: produce-reviewed-journal-inputs
    permissions:
      actions: read
      contents: read
      issues: read
      pull-requests: read
      security-events: read
    # Unreleased example; replace with the reviewed release metadata and full SHA.
    uses: egohygiene/relay/.github/workflows/repository-journal.yml@<full-commit-sha>
    with:
      mode: manual
      repository-id: "${{ github.repository }}"
      repository-revision: "${{ github.sha }}"
      interval-start: "${{ needs.produce-reviewed-journal-inputs.outputs.start }}"
      interval-end: "${{ needs.produce-reviewed-journal-inputs.outputs.end }}"
      generated-at: "${{ needs.produce-reviewed-journal-inputs.outputs.generated-at }}"
      evidence-artifact-name: repository-journal-reviewed-evidence
      candidate-artifact-name: repository-journal-reviewed-candidate
```

The evidence artifact must contain `repository-journal-evidence.json`; the
candidate artifact must contain `repository-journal-candidate.json`. The
checked-in test fixtures show the closed v1 shapes. A producer may be a trusted
default-branch job or a human-reviewed change. It must not process untrusted
pull-request code with a privileged token.

## Future Copilot opt-in

Do not add this job until organization policy, permission, credential, and
billing ownership are verified. It is intentionally a separate authority
surface:

```yaml
  journal-with-copilot:
    permissions:
      actions: read
      contents: read
      copilot-requests: write
      issues: read
      pull-requests: read
      security-events: read
    # Unreleased example; replace with the reviewed release metadata and full SHA.
    uses: egohygiene/relay/.github/workflows/repository-journal-copilot.yml@<full-commit-sha>
    with:
      repository-id: "${{ github.repository }}"
      repository-revision: "${{ github.sha }}"
      interval-start: "${{ needs.interval.outputs.start }}"
      interval-end: "${{ needs.interval.outputs.end }}"
      generated-at: "${{ needs.interval.outputs.end }}"
      auth-mode: github-token
      organization-policy-state: enabled
      permission-state: granted
      billing-acknowledged: true
```

The fine-grained PAT fallback is explicit and uses the reusable workflow secret
`copilot-token`. It is never selected because the preferred mode is unavailable.
