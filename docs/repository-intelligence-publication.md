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

## Deterministic build and consumer deployment handoff

Every current Repository Intelligence bundle contains
`build-manifest.json` using
`egohygiene.relay.repository-intelligence-build-manifest/v1`. It records the
represented consumer revision, exact Relay generator revision, input and schema
contract versions, source epoch, enabled routes, a sorted per-file inventory,
and the deterministic `sha256-canonical-file-inventory-v1` bundle digest. The
manifest excludes itself from that inventory and exposes its own SHA-256 as a
separate action or reusable-workflow output.

The manifest never records a run ID, environment, deployment URL, deployment
conclusion, alias, final composed-site digest, or rollback point. Those values
belong to the separate consumer-owned
`repository-intelligence-deployment-provenance` action. Its ordered integration
is:

1. Build the consumer site and capture its unrelated route baseline.
2. Add Repository Intelligence and consumer-owned redirect aliases.
3. Verify manifest identity, freshness, digest, required routes, aliases, and
   byte-for-byte preservation before uploading or deploying.
4. Let the consumer workflow compose, upload, and deploy the one final site.
5. Record a separate receipt with the exact manifest digest, bundle digest,
   workflow run/attempt, environment/URL, conclusion, final site digest and
   route inventory, aliases, and prior deployed rollback point.
6. Preserve the receipt outside the deployed site and use `verify-receipt`
   during audit or rollback rehearsal.

The verifier rejects revision drift, digest mismatch, incompatible contracts,
missing required routes, stale source evidence, clobbered consumer routes, and
incomplete receipts. Diagnostics use closed labels and canonical public route
paths; they do not serialize tokens, secrets, private payloads, or runner
filesystem roots. The complete reference pipeline and recovery procedure are
documented in
[`actions/repository-intelligence-deployment-provenance/README.md`](../actions/repository-intelligence-deployment-provenance/README.md).

The executable Relay fixture proves this boundary without claiming a live
production deployment. Real consumer runs and remote-route proof remain
consumer-side evidence and later #33 adoption checkpoints.

## Portable reproduction and historical recovery

Public identity comes from the action's validated `owner/name`, never the
checkout basename or runner path. The tree uses that complete identity as its
root label. Local invocations must declare it when `GITHUB_REPOSITORY` is absent;
an explicit input cannot override GitHub identity or visibility. The
[action README](../actions/repository-intelligence/README.md#portable-repository-identity)
documents the standalone CLI and corrected root-label compatibility boundary.

For reproduction, hold the consumer SHA, immutable Relay SHA, canonical identity
and spelling, evidence bytes, source epoch/as-of, and every declared input fixed.
Build in complete checkouts with different basenames **and** parents. Compare the
entire relative file inventory and bytes, including summary, dashboard,
provenance, build manifest, bundle digest, and manifest SHA-256. Confirm the tree
root equals the declared identity and no checkout/runner path appears. Keep the
same-workspace repeat test as an additional invariant. Run IDs, attempts, receipt
times, deployment URLs, and environment observations remain outside that bundle;
distinct receipts can refer to one deterministic manifest. Transport ZIP hashes,
manifest hashes, payload digests, and composed-site digests are different evidence.

A corrected generator produces a new reviewed output boundary. Historical
rollback reconstruction must keep its original consumer/generator pins, payload
and digest, operation ordering, and recorded environment constraints, including
any old checkout-name requirement. Do not rewrite old receipts or claim the fix
retroactively repaired them. Consumer adoption and an accepted new rollback point
are separate reviewed work.

**Akashic disposition (Relay #109):** Akashic maintainers own a follow-up to add
an `AGENTS.md` pointer to their publication guide's provider scheduling and
stage-evidence requirements. Track that follow-up under
[#109](https://github.com/egohygiene/relay/issues/109) until a consumer-owned PR is
reviewed. The issue records that both Akashic's then-current v1.6 generator pin
`9a6315978766c336566b9fa7139b800fa8789ba5` and historical v1.3 rollback generator
`55587de4ff322931d401e964f5af0716633dd675` have the basename limitation. Keep that
qualification until a corrected generator is reviewed and adopted. This Relay
change neither edits a consumer pin nor changes historical rollback records.

## Acceptance evidence by stage

Record the exact candidate head SHA/tree separately from GitHub's synthetic PR
merge SHA. Bind each observed run/attempt, represented consumer revision,
generator revision, artifact name/ID/digest, and inspected job/step conclusion to
the stage it actually proves. A green overall run with required jobs skipped is
not publication success. Report skipped, failed, cancelled, unavailable, and
not-run stages explicitly.

| Stage | Required evidence |
| --- | --- |
| Build | Cross-directory fixture, complete bundle and manifest equality; canonical root and path exclusion; applicable local suite and validators. |
| Ordinary artifact upload | Exact run/attempt and retained artifact identity, successful upload conclusion, downloaded payload/manifest verification when inspected. |
| Pages upload | Exact consumer composition, preservation checks, Pages artifact identity and upload conclusion. |
| Deployment | Consumer-owned deployment job/step conclusion, environment and URL; neither build nor upload implies this stage. |
| Receipt finalization | Separate receipt bound to the deterministic manifest, composition, and actual deployment result; successful retention and verification. |
| Live verification | Observed public routes and bytes/digests at the deployed revision, with observation time. |

The existing Relay validation workflow runs the portability fixture through test
discovery. Retain its exact-head provider run link/attempt and digest evidence
before marking that acceptance criterion complete. Local runs cannot substitute
for provider execution; a PR handoff may explicitly leave this evidence pending
without polling hosted CI.

When changing deployment/recovery job dependencies or skip/failure/cancellation
gates, additionally execute a read-only no-op fixture on GitHub. Exercise an
intentionally skipped ancestor followed by a successful build and guarded
downstream jobs, plus PR denial and unsuccessful/cancelled prerequisite denial.
Inspect individual job/step conclusions. The fixture must have no inherited
secrets, write permissions, protected environment, Pages artifact upload, or
deployment. Local expression tests supplement this scheduler proof. Generator
identity changes alone do not alter scheduling gates or need a new deployment
workflow.

For acceptance that continues after merge, use reference-only `Refs #N` wording
in commit messages and PR bodies. Avoid automatic issue-closing keywords beside
issue references even in negated sentences. Close an issue explicitly only after
its recorded acceptance stages pass. #109 portability and #106 publication
reconciliation retain their separate criteria and owner boundaries.

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
from 1 through 90 days; its default is 30. The workflow returns `artifact-name`,
the transport-level `artifact-digest`, `build-manifest-sha256`, and
`bundle-digest`. The latter two identify the deterministic payload handoff;
none is deployment evidence by itself.

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
deployment requires the separate consumer receipt described above.

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
- Deployment-specific metadata remains outside the deterministic Relay bundle.
- Private work directories and producer reports are not published wholesale.
- A partial or unavailable source remains partial or unavailable in the static output.
