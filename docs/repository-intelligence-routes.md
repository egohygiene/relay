# Repository-hosted Intelligence routes

Refs [Relay #27](https://github.com/egohygiene/relay/issues/27),
[release acceptance #101](https://github.com/egohygiene/relay/issues/101), and
[Hygiene's route registry #25](https://github.com/egohygiene/hygiene/issues/25).

Repository Intelligence belongs on each consumer repository's own Pages/site
artifact. The central organization site supplies an overview and drill-down
links; it is not the sole host of repository evidence. This change reuses
Relay's existing shared static shell and the ten delivered focused renderers.
No website React implementation is copied into Relay.

## One repository-profile inventory

`repository_intelligence_routes.py` reads the exact Hygiene registry bytes
recorded by `repository-intelligence-siblings.v1.lock.json`. The new vendored
snapshot has the existing SHA-256
`95c9db34dc0b66bb090bd92f89ce16cb7f850a0bbf9a47bd3d64f7ac3d0ad7f3`
at Hygiene `63d313b1ddf8669808e897853b74928505494da0`; no owner policy or
historical lock is repinned. The original artifact's version/status are retained.
The helper selects only accepted repository bindings under `/intelligence/`.

The helper exports `CORE_ROUTES`, `RESERVED_ROUTES`, `ROUTES`,
`ROUTE_QUESTIONS`, `route(id)`, `canonical_routes()` and
`manifest(repository, source_commit)`. Metadata is independent of source
coverage: an implemented renderer does not establish that a domain was
collected, empty, current, applicable or published.

The existing Now, Roadmap, Decisions, Journey, Dependencies, Health, Releases,
Work, Search and Compare implementations remain the primary route set. The
existing dashboard remains a distinct compatibility/build-evidence surface.
The shared generator still permits the focused supporting renderer stages to
replace their own pages. A shell-only invocation now labels those temporary
pages unavailable, rather than falsely marking them not applicable.

## Registered routes with unsupported source models

The registry also supplies these repository bindings:

| Route | State in this build | Owning implementation |
| --- | --- | --- |
| `/intelligence/audits/` | Source projection unsupported | Relay #74; normalized audit model remains separate |
| `/intelligence/hygiene/` | Source projection unsupported | Relay #75; Health checks do not establish conformance |
| `/intelligence/sanity/` | Source projection unsupported | Relay #76; human architecture ratification is never inferred |
| `/intelligence/diagnostics/` | Source projection unsupported | Relay #57; unrestricted logs are not a safe investigation model |
| `/intelligence/distribution/` | Source projection unsupported | Relay #48; releases/build success do not prove installation |
| `/intelligence/identity/` | Source projection unsupported | Relay #27 integration boundary; canonical Identity authority remains separate |

Each route has a generated static page, the same repository/revision context,
one primary question, an explicit source boundary and its fixed owning issue.
It receives no unrelated coverage summary or misleading “snapshot loaded”
claim. Applicability, adoption, human acceptance and publication are not
invented. Additional navigation is progressively disclosed on the overview
and sidebar; direct page links remain usable without JavaScript.

The Identity adoption route is the `identity_intelligence` surface.
`/identity/` is the separate consumer-owned Identity product experience.
The repository Status binding is `/status/`, outside the Intelligence subtree;
this bundle does not fabricate `/intelligence/status/` or overwrite a consumer's
actual service-status surface. No organization-only shell is created.

## Canonical URLs, aliases and consumer composition

Shell pages emit relative canonical links and a relative `describedby` link to
`routes.json`. A project site such as a consumer-owned `/project/intelligence/`
therefore retains its deployment prefix. Relay does not infer a Pages hostname,
custom domain, origin or base path from repository identity or checkout paths.

`routes.json` is a deterministic, commit-bound presentation handoff with:

- the route schema/version, repository and represented commit;
- the pinned owner registry identity, revision, path and digest;
- canonical profile paths, bundle-relative files and one question per route;
- renderer/source-support state and fixed Relay owning-issue links;
- owner-declared aliases, explicitly marked consumer-owned redirects only;
- the separately owned `/status/` and product `/identity/` surfaces.

Aliases are metadata for review and consumer composition. Relay does not write
top-level redirect files or replace consumer routes. The consumer's one site
artifact/publisher must opt into nonconflicting aliases, preserve query and
selected-entity context as appropriate, and prove actual host behavior. The
manifest is not a deployment receipt or evidence that those aliases are live.

The shared browser enhancement obtains its permitted resume-route set from
the trusted shell metadata, with the bounded original route list as legacy
fallback. New pages reuse the existing URL-backed filter/entity transfer and
local-only resume boundary; browser state never becomes canonical evidence.

## Delivery and remaining acceptance

This slice begins at `afdcf1da38801b23d7635130ab270e36de26325d` on
`codex/intelligence-source-domains`. It adds route registration, honest unsupported
pages, shared navigation and a consumer handoff. It does not complete the
upstream Audits/Hygiene/Sanity/Diagnostics/Distribution/Identity models or
their route-specific owning issues.

The integration must include matching action outputs, deterministic bundle
inventory/build manifest, route-manifest validation and consumer composition
updates. Those checks remain owned by the shared integration change. No
existing rollback artifact or historical deployment receipt is modified.

The user deferred tests, CI, builds, browser checks and broad polish. Python
AST, registry JSON, JavaScript syntax and whitespace inspection are static
checks only. Per-repository publication, canaries, responsive/accessibility,
private-data non-disclosure, alias behavior, malformed-module isolation and
release closeout remain explicit later verification gates under #101.
