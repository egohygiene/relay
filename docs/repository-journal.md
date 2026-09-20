# Repository journal

Relay's repository journal turns bounded GitHub provider evidence into the
versioned Aether `aether.repository-journal/v1` report. The normal workflow is
useful without a Copilot subscription, organization billing policy, or stored
agent credential.

## Execution modes

| Mode | Generator | Billing | Successful output condition |
| --- | --- | --- | --- |
| `deterministic` | Relay maps normalized provider records directly | None | Evidence validates; incomplete sources remain `partial` or `unavailable` |
| `manual` | A reviewer supplies a structured candidate | None | Every item has a valid shape and cites evidence from the exact run |
| `unavailable` | No candidate is generated | None | An honest empty-state journal and unavailable result are retained |
| `copilot` | Pinned GitHub Copilot CLI, one no-tool invocation | Selected GitHub billing principal | The explicit runtime and account preflight is ready and output validates |

`repository-journal.yml` exposes only the three no-billing modes and never
receives `copilot-requests: write`. `repository-journal-copilot.yml` is the
separate, explicit future opt-in. Relay's own schedule currently calls the
deterministic workflow.

Manual validation proves identity, interval, shape, bounds, safe normalized
text, and evidence-reference integrity. It does not pretend that software can
prove the semantic accuracy of arbitrary reviewer prose. The candidate,
normalized evidence, final report, and checksums are retained together so a
human can inspect that judgment.

## Evidence boundary

Relay reads merged pull requests, open pull requests, open issues, releases,
workflow runs, and open Dependabot alerts through the GitHub API. Each source
has its own explicit `complete`, `empty`, `truncated`, or `unavailable` state.
Provider pages, records, response bytes, text bytes, reporting-window length,
candidate items, prompt bytes, and runtime are bounded before use.

Repository text is untrusted data. Control characters and line breaks are
removed, common credential forms are redacted, URLs are limited to the selected
GitHub repository, duplicate record identities fail closed, and incomplete or
unstable scans never become complete evidence. Neither reusable workflow checks
out or executes consumer code.

The final bundle contains:

- normalized `repository-journal-evidence.json`;
- the exact candidate when one was accepted;
- the pinned Aether input, Markdown journal, and machine-readable journal;
- `repository-journal-result.json` with repository revision, reporting window,
  generation timestamp, runner adapter/version, Aether version/digest, source
  states, checksums, and optional prior-success metadata;
- a bounded Step Summary with explicit status and unavailable reasons.

## No-billing adoption

Use `deterministic` for a scheduled baseline. It produces useful factual lines
without an agent. If a source cannot be read—for example, Dependabot alerts are
not available—the result is `partial` and names that source. If all sources are
unavailable, the result is `unavailable`; it is still a valid diagnostic
artifact, not a successful complete report.

For a reviewer-authored first pass, a caller-owned producer uploads files named
`repository-journal-evidence.json` and
`repository-journal-candidate.json` as ordinary artifacts in earlier jobs of
the same run, then calls the reusable workflow in `manual` mode. Candidate
repository, full revision, and interval must exactly match the evidence. Every
candidate item must cite at least one existing normalized record ID. A stale,
invented, oversized, or malformed candidate is rejected before Aether runs.

See [the complete caller patterns](../examples/workflows/repository-journal.md).

## Copilot opt-in later

The Copilot workflow installs the checksum-locked `@github/copilot@1.0.85`
graph on Node.js 24 and uses the same candidate validator as manual mode. It
invokes the CLI only when all of these are true:

- the exact CLI version is observed;
- one approved credential mode is present without a precedence conflict;
- organization policy and `copilot-requests: write` are explicitly verified
  for `GITHUB_TOKEN`, or the fine-grained PAT mode is explicitly selected;
- the selected billing principal is acknowledged;
- the preflight profile version and SHA-256 match the checked-in profile.

The invocation receives only normalized evidence in an isolated temporary
directory. Built-in MCP servers, custom instructions, remote mode, temporary
directory access, and available tools are disabled. The adapter permits one
invocation, no automatic retry, zero autopilot continuations, and one AI-credit
ceiling. Candidate output is size-bounded and parsed as one JSON object before
the same evidence-reference validation and offline Aether render.

With policy or billing disabled, the preflight returns `unavailable` and the
CLI is not invoked. Relay never silently falls back between organization and
personal billing. Connection and credential-rotation details live in
[the runtime guide](repository-journal-runtime.md).

## Recovery and reruns

The journal has no repository mutation to roll back. A fresh run is the retry
unit. Runs on the same repository/ref cancel stale in-progress work; accepted
artifacts are unique by run and attempt. Validation failure writes a bounded
failed result and summary before the workflow reports failure. Provider
unavailability reports an unavailable or partial result without inventing
missing facts.

An optional prior successful result may be supplied by a caller-owned producer.
Relay verifies its repository identity, full revision, successful state, and
timestamp before displaying last-success metadata. It does not search old runs
or choose historical artifacts implicitly.

Disable the Relay dogfood schedule by disabling or removing
`repository-journal-dogfood.yml`. Existing artifacts expire under their stated
retention and no provider-side state remains. Optional Slack, Discord, email,
or other delivery belongs in a separate downstream caller job that consumes a
validated artifact and owns its own secret and permission boundary.
