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
