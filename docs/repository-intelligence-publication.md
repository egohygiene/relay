# Repository Intelligence publication contract

Repository Intelligence has one generation contract and two consumer integration shapes. Both preserve the same authority boundary: Relay builds and validates the `/intelligence/` subtree, while the consumer repository remains the only owner of its site composition and deployment.

Relay pins Hygiene's `egohygiene.public-site-surface-registry/v1` repository
profile for the subtree layout. The overview is `/intelligence/`; focused views
such as Now, Dependencies, Health, Releases, Work, Search, and Compare are
canonical at `/intelligence/<view>/`. Friendly top-level forms are redirect-only
aliases. The consumer owns those redirects, the public origin, canonical-link
metadata, and live-route verification; the generated artifact does not publish
duplicate alias pages or claim deployment evidence.

## Choose the integration shape

### Existing site or Pages build: use the composite action

Use `egohygiene/relay/actions/repository-intelligence@<full-commit-sha>` inside the consumer's existing build job when the generated subtree must be composed with product documentation, a Mindgarden, LaunchKit output, or another caller-owned static site.

The action writes only the configured `.../intelligence` subtree. The consumer then uploads or publishes its complete site artifact. This is the pattern currently used by the live Empathy and Akashic Pages integrations.

### Standalone review artifact: use the reusable workflow

Use `egohygiene/relay/.github/workflows/repository-intelligence.yml@<full-commit-sha>` when a repository needs a deterministic, reviewable Repository Intelligence artifact without sharing a workspace with another site build.

The reusable workflow:

- checks out complete caller history with persisted credentials disabled;
- invokes the Repository Intelligence action from the exact called Relay revision;
- validates generator provenance;
- uploads only the generated public/intended Intelligence subtree;
- retains `contents: read` as its permission ceiling;
- never invokes GitHub Pages deployment.

A reusable-workflow job cannot modify another job's workspace. Repositories that need to merge Intelligence into an existing site should therefore continue to use the composite action in the caller-owned build job rather than adding a second deployment authority.

## Reusable workflow trust and event contract

The consumer owns the event trigger and calls
`egohygiene/relay/.github/workflows/repository-intelligence.yml` at a reviewed
full commit SHA. The called workflow has a fixed `contents: read` ceiling. It
does not accept or inherit secrets, restore or save caches, execute
repository-owned build, test, or installation commands, write repository
state, upload a Pages artifact, or deploy Pages. `pull_request_target` is not a
supported trigger.

Relay's own validation workflow uses GitHub's repository-local `$/` resolution
so an unmerged candidate can exercise the exact candidate implementation. That
exception is accepted only when GitHub reports the called workflow revision as
the same full revision represented by the run; it does not relax the full-SHA
requirement for external consumers.

A same-repository pull request and a fork pull request have the same
candidate-code ceiling: Relay checks out the candidate revision without
persisted credentials and inspects its Git data and allowlisted inputs through
the exact called Relay implementation. A branch being trusted does not grant
its candidate code secrets, write permission, or deployment authority.

| Consumer event class | Represented consumer revision | Expected behavior |
| --- | --- | --- |
| Same-repository pull request | The caller's `github.sha` candidate revision | Produce an ordinary review artifact under the read-only, no-secret ceiling. |
| Fork pull request | The caller's `github.sha` candidate revision | Apply the identical ceiling; contributor-controlled scripts are not executed and no privileged event context is used. |
| Default-branch push | The pushed `github.sha` | Produce a reviewable site artifact only. A separate consumer-owned job may later compose or deploy it. |
| Reusable call | The calling workflow's `github.sha` and `github.ref` | Resolve Relay actions through `$/` from the exact called Relay revision and preserve the caller's event context. |
| Manual rebuild | The selected ref's `github.sha` in a consumer-owned `workflow_dispatch` wrapper | Rebuild and retain a new run-bound artifact without publishing it. Direct dispatch of Relay's workflow represents Relay itself, not another consumer. |

The reusable workflow uses
`relay-intelligence-v1-${{ github.repository }}-${{ github.workflow_ref }}-${{ github.ref }}`
and cancels superseded work only for the same logical contract, repository,
exact caller workflow path/ref identity, and target ref. GitHub scopes
concurrency groups to the repository and compares them case-insensitively, so
two caller workflow files cannot cross-cancel merely because they share a
display name. A different repository, caller workflow reference, target ref,
or contract version cannot cancel that work. A consumer wrapper uses its own
`consumer-repository-intelligence-*` prefix so caller and called workflow
groups cannot cancel one another. Repository Intelligence
intentionally has no cache surface; there is therefore no trusted cache for
untrusted candidate data to poison.

The complete minimal caller covering pull-request review, default-branch
refresh, and manual rebuild is checked in at
[`examples/workflows/repository-intelligence.yml`](../examples/workflows/repository-intelligence.yml).
It grants only `contents: read` and deliberately omits `secrets: inherit`.

## Success artifacts and durable run evidence

After successful generation and provenance validation, the reusable workflow
uploads only the validated Intelligence subtree. Its unique artifact identity
is:

```text
repository-intelligence-site-v1-<repository-id>-<full-represented-sha>-<run-id>-<attempt>
```

The `artifact-retention-days` input controls this site artifact and is validated
from 1 through 90 days; its default is 30. The workflow returns both
`artifact-name` and `artifact-digest`, so a caller can identify the exact
ordinary Actions artifact without treating it as deployment evidence.

Every run that reaches evidence preservation also writes the fixed,
machine-readable `repository-intelligence-run-report.json`. The report records
only allowlisted state: the failed or completed stage, stable rule/error code,
represented revision, relevant workflow/action contract versions, and an
immutable remediation link. It never copies raw exception text, arbitrary
caller input, tokens, secrets, local paths, or repository payloads.

The generic Relay report envelope preserves that file for the
`repository-intelligence-v1` producer as:

```text
relay-report-repository-intelligence-v1-<run-id>-<attempt>
```

Report retention is fixed at 30 days and cannot be weakened by a caller. The
workflow exposes `report-artifact-name`, `report-artifact-digest`, and
`report-manifest-sha256` for exact evidence lookup. On an actionable checkout,
generation, provenance, or success-artifact failure, Relay attempts to upload
the sanitized report and then reasserts the original failure; it never reports
partial site bytes as success.

Cancellation is not an artifact guarantee: GitHub may stop a superseded runner
before its evidence step. An artifact-service outage can likewise prevent the
report itself from being uploaded. Re-run the same revision for transient
infrastructure failures. A successful report proves only the run and artifact
boundary described above; binding that artifact to an actual consumer
deployment is owned by Relay issue
[#105](https://github.com/egohygiene/relay/issues/105).

### Failure codes and recovery

The report uses a closed stage/rule mapping. Codes never contain exception text
or caller input.

| Code | Stage | Rule | Recovery |
| --- | --- | --- | --- |
| `RIW-001` | Runner hardening | `repository-intelligence.workflow.runner-hardening` | Re-run after checking the runner and egress service status. |
| `RIW-002` | Trust and input validation | `repository-intelligence.workflow.trust-and-input-validation` | Use a supported event and canonical bounded inputs, then re-run the represented revision. |
| `RIW-003` | Checkout | `repository-intelligence.workflow.checkout` | Confirm the represented revision exists and can be fetched with read-only repository access. |
| `RIW-004` | Generation | `repository-intelligence.workflow.generation` | Run the composite action locally against the same revision and repair the rejected repository/evidence contract. |
| `RIW-005` | Provenance verification | `repository-intelligence.workflow.provenance-verification` | Re-pin the reusable workflow to a reviewed full Relay commit and rebuild. |
| `RIW-006` | Site artifact upload | `repository-intelligence.workflow.site-artifact-upload` | Retry the same revision after checking Actions artifact availability and retention policy. |

`RIW-000` records a completed run. A missing report means the runner was
cancelled before preservation, the evidence finalizer failed closed, or the
artifact service could not retain it; inspect the fixed workflow-step names and
retry the exact represented revision.

## Optional Observatory evidence

The reusable workflow accepts two separate file-path inputs whose semantics remain owned upstream:

- `observatory-snapshot` — the public-safe Repository Intelligence read model for the represented repository commit;
- `observatory-comparison` — an optional structural comparison whose `after` boundary matches that snapshot and represented commit.

Comparison evidence is additive. Omitting both inputs is valid and produces explicit unavailable/partial normalized views instead of manufacturing repository truth. Supplying a comparison without its matching snapshot, or supplying malformed/mismatched evidence, fails closed through the Repository Intelligence action.

Example caller:

```yaml
jobs:
  intelligence:
    permissions:
      contents: read
    uses: egohygiene/relay/.github/workflows/repository-intelligence.yml@<full-commit-sha>
    with:
      observatory-snapshot: ".cache/observatory/repository.json"
      observatory-comparison: ".cache/observatory/comparison.json"
      artifact-retention-days: 30
```

The referenced files must already be present in the checked-out caller revision available to the reusable job. If evidence is produced dynamically in another job, use the composite action in that evidence-producing/site-composition job unless a future reviewed artifact-transfer contract is added.

## Current canary evidence

As of September 16, 2026, live organization code search shows:

- `egohygiene/empathy` pins `actions/repository-intelligence` in its repository-intelligence and Mindgarden Pages workflows and exposes a public `/intelligence/` route;
- `egohygiene/akashic` pins `actions/repository-intelligence` in its Pages workflow and verifies the generated Intelligence subtree before deployment;
- Relay's validation workflow dogfoods the reusable artifact workflow with no producer reports or Observatory snapshot, proving the partial-adoption path remains explicit rather than silently green.

These integrations prove the builder and consumer-owned composition boundary. They do **not** by themselves satisfy the final `relay#33` migration goal of proving representative consumers against one current hardened Relay workflow revision. That adoption remains a separate bounded canary checkpoint.

## Invariants

- Production consumers pin a full Relay commit SHA.
- The reusable workflow is artifact-only and read-only with respect to repository contents.
- Trusted and fork pull requests receive the same no-secret, no-write, no-deployment ceiling.
- The reusable workflow executes no consumer scripts and has no cache surface.
- Successful site artifacts use caller-selected 1–90 day retention; sanitized run evidence is retained for a fixed 30 days.
- Relay never infers Observatory semantics or substitutes missing evidence.
- The builder never becomes a second Pages deployment owner.
- Generated output is deterministic for the same normalized inputs and represented commit.
- Private work directories and producer reports are not published wholesale.
- A partial or unavailable source remains partial or unavailable in the static output.
