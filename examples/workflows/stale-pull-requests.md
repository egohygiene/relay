# Scheduled stale pull-request lifecycle

The consumer owns the schedule, token permissions, labels, exemptions, and the
decision to enable mutations. Enforcement is accepted only from the configured
default branch. Start with the read-only advisory caller below.
Replace `<full-relay-commit-sha>` with a reviewed 40-character Relay commit;
the moving `v1` alias is discovery metadata, not a production pin.

```yaml
---
name: Stale pull-request advisory

on:
  schedule:
    - cron: "17 4 * * *"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  lifecycle:
    permissions:
      contents: read
      pull-requests: read
    uses: egohygiene/relay/.github/workflows/stale-pull-requests.yml@<full-relay-commit-sha>
    with:
      advisory: true
      inactivity-days: 30
      warning-days: 7
      stale-label: "stale"
      exempt-labels: "do-not-stale,pinned,critical,security,dependencies,priority:p0,area:security"
```

The `stale` label must already exist. A consumer may also configure an optional
`closed-label`, which must likewise exist. Advisory runs upload the exact
checksum-bound plan and write a summary without changing labels, comments, or
state. Issues are not scanned because `process-issues` defaults to `false`.

After reviewing advisory evidence, an enforcing caller changes only the job's
authority and the mode:

```yaml
jobs:
  lifecycle:
    permissions:
      actions: read
      contents: read
      pull-requests: write
    uses: egohygiene/relay/.github/workflows/stale-pull-requests.yml@<full-relay-commit-sha>
    with:
      advisory: false
      close-enabled: false
      inactivity-days: 30
      warning-days: 7
      stale-label: "stale"
      exempt-labels: "do-not-stale,pinned,critical,security,dependencies,priority:p0,area:security"
```

With `close-enabled: false`, enforcement can post visible warnings, apply the
stale label, and clear lifecycle labels after new activity, but it cannot close
anything. Enable closure only after at least one reviewed warning-only period.
A close-eligible item must still carry the stale label and a trusted Relay
warning marker from an earlier run, and the complete warning window must have
elapsed without later activity.

These PR-only callers intentionally omit the Issues permission. If
`process-issues: true` is set, add `issues: read` to advisory jobs and
`issues: write` to enforcing jobs.

Drafts and bot-authored items are exempt by default. `exempt-users` matches
authors, assignees, and requested reviewers. `exempt-review-teams` matches only
currently requested team slugs; it does not resolve organization membership or
grant organization-read authority. The default exempt labels protect pinned,
critical, security, dependency, and explicit `do-not-stale` work. Matching is
exact, including the organization labels `priority:p0` and `area:security`.

Closure never deletes a branch. A maintainer can reopen an item; that provider
event counts as activity, and the next enforcing run clears Relay's stale and
closure labels before starting a new inactivity window.
