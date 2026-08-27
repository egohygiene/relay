# Reusable workflow adoption examples

These examples are complete caller-owned workflows, not templates that hide
authority. They demonstrate the minimum permissions and immutable dependency
pin expected in a production repository.

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

The `<full-relay-v1.3-commit-sha>` marker must be replaced with the reviewed
v1.3.0 release commit after publication. Keep the product's prior workflow as a
rollback reference until its canonical and optional fallback endpoints pass the
remote byte proof. Refs #38.
