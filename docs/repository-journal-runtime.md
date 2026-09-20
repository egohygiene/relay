# Repository journal runtime and account connection

Relay issue #15 executes an Aether-governed repository journal through bounded
deterministic, reviewed-manual, unavailable, and optional agent adapters. This
document owns the optional Copilot runtime and authentication preflight from
issue #95 step 1. The complete evidence, rendering, and workflow contract is in
[`repository-journal.md`](repository-journal.md).

## Current decision

The current Relay schedule uses deterministic no-billing mode. No Copilot
account connection is required for that workflow.

When the separate Copilot workflow is enabled later, the preferred CI identity
is the short-lived GitHub Actions `GITHUB_TOKEN`. Its agent job declares:

```yaml
permissions:
  contents: read
  copilot-requests: write
```

GitHub requires the organization policy named **Allow use of Copilot CLI billed
to the organization** for this mode. No stored personal token is required. The
request is billed to the organization rather than an individual Copilot seat.

The non-automatic fallback is a user-owned fine-grained personal access token
with the **Copilot Requests** account permission and repository access limited
to the intended repositories. Relay maps the Actions secret
`REPOSITORY_JOURNAL_COPILOT_TOKEN` to `COPILOT_GITHUB_TOKEN` only inside the
agent step. Classic personal access tokens are unsupported and prohibited.
Fallback usage is billed to the token owner's Copilot entitlement.

Relay never silently switches authentication modes. A maintainer must select
the fallback explicitly and acknowledge its billing and rotation ownership.

## Locked runtime

The initial runtime is `@github/copilot@1.0.85` on Node.js 24. Its npm package,
platform binaries, transitive dependencies, and integrity values are locked in
[`vendor/copilot-cli/package-lock.json`](../vendor/copilot-cli/package-lock.json).
The profile records the manifest and lockfile SHA-256 digests. Runtime drift is
a validation failure.

The future workflow may invoke the agent at most once per run, may make no
automatic retry, and has a five-minute outer timeout. Scheduled execution is
limited by contract to at most once per day. GitHub organization billing and
usage remain the authoritative cost-observation surface.

## Safe connection procedure

The account and organization connection is intentionally not performed by
repository code.

### Preferred organization-billed mode

1. An organization owner opens the organization's GitHub Copilot policy
   settings.
2. Confirm **Allow use of Copilot CLI billed to the organization** is enabled.
3. Confirm the future workflow job grants `copilot-requests: write` and no
   broader permission than its evidence collector requires.
4. Run the offline preflight with the policy, permission, and billing facts
   explicitly acknowledged.
5. Perform a separately authorized live canary through
   `repository-journal-copilot.yml`.

No credential should be pasted into an issue, pull request, chat, command-line
argument, or workflow log.

### Fine-grained PAT fallback

1. Create a fine-grained token owned by the personal account, not the
   organization.
2. Grant the **Copilot Requests** account permission.
3. Limit repository access to the repositories that require journal runs.
4. Store it as the Actions secret `REPOSITORY_JOURNAL_COPILOT_TOKEN`.
5. Select `fine-grained-pat` explicitly in the future caller configuration.
6. Record the token owner and rotation responsibility outside public artifacts.

The fallback is never inferred from a missing organization policy and is never
selected automatically.

## Offline preflight

Validate the checked-in profile and npm lock without network access:

```bash
python3 scripts/validate_repository_journal_runtime.py validate
```

After installing the locked runtime, the preferred-mode environment can be
checked without making a Copilot request:

```bash
python3 scripts/validate_repository_journal_runtime.py preflight \
  --auth-mode "github-token" \
  --organization-policy-state "enabled" \
  --permission-state "granted" \
  --billing-acknowledged \
  --copilot-command "vendor/copilot-cli/node_modules/.bin/copilot" \
  --output "repository-journal-runtime-preflight.json"
```

The command inspects only credential presence and type. It never writes token
values, prefixes, lengths, hashes, or fragments to the result. It does not
contact GitHub or claim that a policy is enabled unless the caller explicitly
supplies that verified state.

## Failure behavior

Unknown or disabled organization policy, missing workflow permission, missing
or unsupported credentials, credential-precedence conflicts, version drift,
unacknowledged billing, authentication rejection, and rate limiting are
`unavailable` outcomes. They cannot produce a successful journal.

The preflight is not a security sandbox. The implemented adapter separately
provides no available tools, disables built-in MCP servers and custom
instructions, runs in an isolated temporary directory, and passes only bounded
normalized evidence. It never checks out repository source. Leaving billing or
policy unacknowledged prevents invocation but does not affect the deterministic
or manual no-billing workflows.

## Primary references

- [About using Copilot CLI in GitHub Actions](https://docs.github.com/en/copilot/concepts/agents/copilot-cli/copilot-cli-in-github-actions)
- [Using Copilot CLI with `GITHUB_TOKEN`](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli-in-actions)
- [Authenticating GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/authenticate-copilot-cli)
- [Copilot CLI programmatic reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-programmatic-reference)
