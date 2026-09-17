# Stale Pull Request Lifecycle

Plan and apply a conservative stale-item lifecycle without checking out or
executing consumer code. The action reads GitHub provider metadata through
`gh api`, writes a deterministic SHA-256-bound JSON plan, and requires that
exact reviewed checksum before any apply operation.

The default posture is advisory: pull requests are warned after 30 inactive
days, closure is disabled, drafts and bot authors are exempt, and ordinary
issues are not scanned. A repository must already contain the configured
`stale-label` and optional `closed-label`; Relay never creates or guesses
labels.

## Lifecycle

`plan` evaluates open pull requests from oldest activity to newest and records
only bounded identifiers, state fingerprints, reason codes, timestamps,
counts, and hashes of configured comment text. Titles, provider payloads,
emails, tokens, and comment bodies are not written to the artifact. The
`maximum-items` input caps lifecycle changes proposed in one run. Retained
active items and exemptions that need no label reset do not consume that limit;
`truncated: true` in the artifact and step summary means a later run is needed
for additional actionable items. A hard provider scan limit of 1,000 items,
labels, or comments fails closed. Relay requires two bounded open-item scans to
return the same unique identity set before it evaluates any lifecycle change;
duplicate identities, pagination drift, and incomplete issue-search results
fail closed.

`apply` is allowed only on the target repository's current default-branch ref.
It verifies the embedded plan checksum, the separately supplied expected
checksum, all configuration hashes, configured label existence, and every
planned item's live fingerprint before the first write. It rechecks each item
again immediately before that item's first mutation. A changed label, author,
assignee, requested reviewer or team, draft state, timestamp, comment marker,
or pull-request head SHA invalidates the apply.

The transitions are:

- An inactive item receives the stale label first and a visible warning comment
  last. The exact final marker binds the warning window, closure posture, and
  stale-label policy.
- A manually added stale label without a trusted Relay marker receives a fresh
  repair warning. It can never close from the label alone.
- Closure requires an open, non-exempt item with both the configured stale
  label and an exact final marker authored by `github-actions[bot]`. The marker
  must be the latest issue comment, provider `updated_at` must still equal its
  creation time, the pull-request head must be unchanged, and the larger of the
  promised and current warning windows must have elapsed.
- Enabling closure after a warning-only run changes the bound policy and emits
  a new visible closure warning; it never closes immediately from the earlier
  warning.
- Later activity, a new exemption, or a reopened item resets managed lifecycle
  labels and starts over. An optional closed label makes reopen recovery
  explicit; without one, activity after the warning still resets the stale
  label.

GitHub timestamps have second precision. Relay also compares the latest issue
comment ID and PR head SHA so same-second comments and force-pushes reset safely.
Some provider events, such as a review recorded in the same second without a
new issue comment, cannot be ordered more finely through this bounded contract.
Closure therefore remains opt-in and defaults off; any timestamp later than the
warning resets rather than using a tolerance.

GitHub does not offer a conditional close tied to the final metadata read, so a
provider event racing the last revalidation and close request is irreducible.
Keep closure opt-in, audit the bounded result, and use reopen recovery if that
race is ever observed.

GitHub's `github-actions[bot]` identity is shared by workflows in the target
repository. The marker therefore proves repository Actions authority, not the
identity of one workflow file. Every workflow granted `issues: write` or
`pull-requests: write` belongs to this trust boundary and should be reviewed as
carefully as the lifecycle caller.

## Exemptions

Label, login, and team comparisons are exact and case-insensitive; globbing and
organization-membership inference are unsupported.

The default exempt labels are `do-not-stale`, `pinned`, `critical`, `security`,
`dependencies`, `priority:p0`, and `area:security`. `exempt-users` matches the
current author, assignees, and individually requested reviewers.
`exempt-review-teams` matches only team slugs currently requested on the pull
request. It does not query or infer organization or team membership. Draft and
bot-author exemptions are independently configurable.

Ordinary issues remain excluded unless `process-issues: true`. Enabling them
also requires the caller to grant the corresponding Issues permission; the
same lifecycle and exemptions then apply.

## Caller authority

Composite actions cannot grant permissions. A pull-request-only planner needs
`pull-requests: read`; its apply job needs `pull-requests: write`. When ordinary
issues are enabled, add `issues: read` to plan and `issues: write` to apply.
Repository metadata remains read-only. Keep planning and applying in separate
jobs so the planner cannot inherit write authority.

The action uses `github.token` only as `GH_TOKEN` for `gh api`. It performs no
checkout. A representative direct call is:

```yaml
- id: plan
  uses: egohygiene/relay/actions/stale-pull-requests@<full-relay-commit-sha>
  with:
    operation: plan
    repository: ${{ github.repository }}
    close-enabled: false
    output: .relay/stale-plan.json
```

After reviewing and transferring that exact artifact into a separately
authorized default-branch job:

```yaml
- id: apply
  uses: egohygiene/relay/actions/stale-pull-requests@<full-relay-commit-sha>
  with:
    operation: apply
    repository: ${{ github.repository }}
    plan: .relay/stale-plan.json
    expected-plan-sha256: ${{ inputs.reviewed-plan-sha256 }}
    output: .relay/stale-apply.json
```

Every lifecycle configuration input, including custom messages and closure
enablement, must be identical in plan and apply. The plan stores comment hashes
rather than bodies and apply verifies the caller-supplied text against those
hashes. `evaluation-time` is plan-only deterministic replay input and must be
empty during apply; apply independently rejects a future time embedded in the
reviewed plan, so replay cannot accelerate inactivity or warning windows.

## Failure and recovery

Provider writes are not transactional across items. A failing mutation writes
no successful result JSON, but an earlier item may already have changed. Label
before comment keeps a partial warning safe: a stale label without the trusted
marker can only trigger a repair warning, never closure. Each fresh plan
reconciles open items idempotently.

Closure itself is the first close mutation. Only after GitHub confirms the
close does Relay add an optional closed label and the closure comment with
reopen guidance and a distinct closed marker. If either post-close metadata
write fails, the item is already closed and therefore outside the next open
scan; a maintainer must review it and may reopen it to run normal recovery.
Likewise, a later result-write failure can leave already completed provider
mutations. Treat any failed apply as partial provider-side evidence and create a
fresh plan before retrying.

The step summary reports bounded sanitized item IDs, kinds, transition/reason
codes, counts, the plan hash, and truncation. It never includes titles, comment
bodies, logins, raw API payloads, or token material.

## Why this is not `actions/stale`

The upstream stale action is useful reference evidence, including the
Lucide-maintained configuration examined for issue #14, but it is not a Relay
runtime dependency. That policy's message and timing differ, closure is
disabled, author/team exemption and bounded summary requirements are not
covered, and its raw outputs do not satisfy this checksum-bound plan/apply
contract.
