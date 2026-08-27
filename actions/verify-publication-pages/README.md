# Verify Publication Pages

`verify-publication-pages` compares an HTTPS deployment with the exact static
tree already reviewed in the workflow. It validates the local Beacon catalog
and complete checksum inventory again, then retrieves the remote catalog,
inventory, every checksummed file, and every declared route under a bounded
application-level deadline.

Redirects may move only between the declared canonical and fallback HTTPS
hosts. Attempts, delay, per-request timeout, and total elapsed time are capped.
The action never logs response bodies or headers and emits sorted JSON evidence
containing the source revision, exact Relay workflow identity, deterministic
site-tree digest, verified targets, routes, and result.

An empty `fallback-base-url` accepts nullable fallback metadata in the catalog
but does not authorize redirects or remote verification through that host. Set
the input to the exact catalog value before using `verify-fallback: true`; Relay
then pins the fallback as a second allowed endpoint.

The verifier resolves every hostname and rejects non-global DNS answers before
each HTTPS request, validates every redirect hop, and never automatically
follows a redirect. Python's platform DNS resolver has no per-call timeout, so
the reusable workflow's fixed 20-minute job timeout is the final outer
bound around DNS and the application-level request/retry deadline.

The `configuration-only` input performs all local contract, public-host,
fallback, workflow-identity, and retry-bound checks without network access. The
reusable workflow uses this gate before granting bytes to GitHub Pages.
Successful deployment, successful predeploy, and sanitized failure evidence use
the versioned
[`publication-pages-evidence.schema.json`](schemas/publication-pages-evidence.schema.json).

This action is normally called by Relay's `publication-pages.yml` reusable
workflow after `actions/deploy-pages`. Products should not use it to build,
render, mutate, or publish source content.
