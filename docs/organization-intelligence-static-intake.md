# Organization Intelligence export intake

Relay's [review-only static intake](../actions/repository-intelligence-static-intake/README.md)
is the portable boundary between the website-owned Intelligence compositor and
a future consumer-owned Pages deployment. The first consumer workflow only
downloads exact producer bytes, verifies them, and retains an ordinary review
artifact. It has no Pages upload, deployment, OIDC or production activation.

The producer artifact is `export-manifest.json` plus `site/`. The manifest owns
the immutable website source revision, explicit intended origin/base path,
organization route allowlist, exact resource inventory, authenticated public
scope, and the three independent core/Audits/Sanity model availability claims.
Relay consumes the owner's exact schema and fixed route fixture; it does not
author a second normalized model or reinterpret missing evidence as success.

The intake receipt is execution evidence for byte and static-profile checks.
It does not prove the GitHub artifact's origin, model derivation, JavaScript
behavior, human ratification, accepted catalog roles, site declaration admission,
hosting acceptance or publication. The caller must retain exact transport
metadata and expected digests. The website's isolated export module boundary and
later execution/browser qualification remain separate acceptance work.

`/.github/` is an explicit intended review mount. Its representation in this
contract does not bypass the separate Hygiene surface-declaration compatibility
proposal or the consumer's proposed hosting-transition decision. Historical
repository publishers, recovery pins and canonical domain policy stay intact.

Refs egohygiene/.github#41.
