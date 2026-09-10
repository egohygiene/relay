# Reusable workflow adoption examples

These examples are complete caller-owned workflows, not templates that hide
authority. They demonstrate the minimum permissions and immutable dependency
pin expected in a production repository.

[`continuity-preflight.md`](continuity-preflight.md) shows the read-only PR
backstop. The repository updates its semantic handoff before presenting the PR;
CI verifies explicit base/head evidence and never writes or repairs prose.

[`repository-intelligence.yml`](repository-intelligence.yml) uses the published
Relay v1.1.0 commit. A reviewed dependency update replaces both the full commit
SHA and its adjacent release comment. The moving `v1` alias is useful for
discovery but is not a production pin.

The reusable workflow owns checkout, generation, provenance verification, and
ordinary artifact upload. It does not deploy Pages, write repository content,
or receive caller secrets. A consumer that needs site composition should use
the composite action in its existing build job instead.

## Publication Pages lifecycle

The publication examples deliberately use two statically permissioned caller
jobs after one product-owned producer:

- a pull-request call to `publication-review.yml` grants only `actions: read`
  and `contents: read`;
- a mutually exclusive default-branch call to deployment-only
  `publication-pages.yml` additionally grants only `pages: write` and
  `id-token: write`.

Relay never checks out or builds the product. It downloads the ordinary static
artifact uploaded by the producer, validates it, and makes the exact reviewed
bytes the deployment boundary. Use the repository-specific migration guides:

- [Antidote publication Pages](publication-pages-antidote.md)
- [Reflector publication Pages](publication-pages-reflector.md)

## Profile-bound releases

For packages, specifications, container evidence, binaries, static sites, and
PDF/A documents, use the `release-artifact.yml` reusable workflow with the
profile declared in [Relay’s release-profile contract](../../RELEASE_PROFILES.md).
The caller builds and uploads the artifact first, grants `actions: read` and
`contents: write` only to the publication job, and pins Relay to a reviewed
full commit SHA. Relay validates the profile and exact `SHA256SUMS`, then
publishes a GitHub Release archive, archive checksum, and deterministic release
evidence. Registry publishing and deployment remain separate caller-owned
steps with separately authorized credentials.

The `<full-relay-v1.4-commit-sha>` marker must be replaced with the reviewed
v1.4.0 release commit after publication. Keep the product's prior workflow as a
rollback reference until its canonical and optional fallback endpoints pass the
remote byte proof. Refs #38.

Semantic-release consumers use separate read-only preparation and explicit
default-branch publication callers. See
[`semantic-release-preparation.md`](semantic-release-preparation.md) and the
complete lifecycle in [`../../SEMANTIC_RELEASE.md`](../../SEMANTIC_RELEASE.md).
