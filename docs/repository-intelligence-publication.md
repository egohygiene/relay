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
- Relay never infers Observatory semantics or substitutes missing evidence.
- The builder never becomes a second Pages deployment owner.
- Generated output is deterministic for the same normalized inputs and represented commit.
- Private work directories and producer reports are not published wholesale.
- A partial or unavailable source remains partial or unavailable in the static output.
