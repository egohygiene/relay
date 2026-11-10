# Repository Intelligence production batch review

The next implementation batch is indexed in the
[Audits and Sanity review](repository-intelligence-audits-sanity-review.md).

Observed 2026-11-09: twelve implementation PRs are merged across eight repositories.
Each reviewed head and actual merge commit was verified against GitHub. These are
implementation observations; runtime, publication and acceptance remain separate.

## Review the slices

| Slice | Merged PR | Reviewed source | Merge |
| --- | --- | --- | --- |
| Native Compare composition | [egohygiene/relay#172](https://github.com/egohygiene/relay/pull/172) | [e83cb314](https://github.com/egohygiene/relay/commit/e83cb314d1e3f5f496b02b6f9fdf1116a4f08b09) | [d4e89c59](https://github.com/egohygiene/relay/commit/d4e89c594c2428ff48407b4a29734bd59eda7def) |
| Real GitHub source producer | [egohygiene/relay#173](https://github.com/egohygiene/relay/pull/173) | [55aba890](https://github.com/egohygiene/relay/commit/55aba89028999e3c2b36ed6b3d1f8bd09641c89c) | [0ccf44ca](https://github.com/egohygiene/relay/commit/0ccf44ca495c3874ecb5f264bb674e66ced9262e) |
| Bounded conformance owner model | [egohygiene/observatory#30](https://github.com/egohygiene/observatory/pull/30) | [05f5f3ad](https://github.com/egohygiene/observatory/commit/05f5f3ad75c7bcc13ece375d3c0ddde558f357ce) | [2eebdb63](https://github.com/egohygiene/observatory/commit/2eebdb63c3239cbb790be4146df5340c7ad59c17) |
| Public dependency source admission | [egohygiene/relay#174](https://github.com/egohygiene/relay/pull/174) | [4c045a34](https://github.com/egohygiene/relay/commit/4c045a34abe767027aedbe0a33629dfdc8e459e4) | [58a2ee55](https://github.com/egohygiene/relay/commit/58a2ee55bef383c543d81ef463979d4d9ba1fdd1) |
| Exact fleet artifact transport | [egohygiene/relay#175](https://github.com/egohygiene/relay/pull/175) | [2e559096](https://github.com/egohygiene/relay/commit/2e559096e690fe713fc7c718d7b9cbad625feb41) | [2e6430e8](https://github.com/egohygiene/relay/commit/2e6430e885283ea662206fe5f7929bb57002ebab) |
| Common source and Hygiene integration | [egohygiene/relay#176](https://github.com/egohygiene/relay/pull/176) | [981ddf43](https://github.com/egohygiene/relay/commit/981ddf4367c67fcd625e54321d95bab027f6c0f2) | [50027a10](https://github.com/egohygiene/relay/commit/50027a108169fa92de3e58f26c1f41c9aea2945a) |
| Identity sources and manual Compare | [egohygiene/identity#143](https://github.com/egohygiene/identity/pull/143) | [84fcf60b](https://github.com/egohygiene/identity/commit/84fcf60b7b31d20620d2c787b8c3d515a4ed0043) | [401b2f1d](https://github.com/egohygiene/identity/commit/401b2f1de298a171fbb5bf4ee6b510e0cf12c301) |
| Hygiene admitted source preparation | [egohygiene/hygiene#99](https://github.com/egohygiene/hygiene/pull/99) | [be90474d](https://github.com/egohygiene/hygiene/commit/be90474daad0e2c3a9eb3028b01f8a57690e1054) | [e7643012](https://github.com/egohygiene/hygiene/commit/e764301251d962f2b886e7805891c9d8f2bfde4c) |
| Empathy current source feeds | [egohygiene/empathy#124](https://github.com/egohygiene/empathy/pull/124) | [3bd0ce29](https://github.com/egohygiene/empathy/commit/3bd0ce298c9fe2cc845a00fe10ab32a45a6660de) | [18d22e11](https://github.com/egohygiene/empathy/commit/18d22e113e87c306b76d24873841249d41358c77) |
| Akashic feeds and strict source proof | [egohygiene/akashic#225](https://github.com/egohygiene/akashic/pull/225) | [7466b365](https://github.com/egohygiene/akashic/commit/7466b36551f78712a1e0943eedd2ad6455f957a0) | [dc21c6a2](https://github.com/egohygiene/akashic/commit/dc21c6a24506d748deb45f29ce54fc7e7bf69753) |
| OptiFlow current source feeds | [egohygiene/optiflow#163](https://github.com/egohygiene/optiflow/pull/163) | [08ecd10b](https://github.com/egohygiene/optiflow/commit/08ecd10b8362c151f8629e980eab15cf3cbc504a) | [4b4ff465](https://github.com/egohygiene/optiflow/commit/4b4ff465e7974fc08f1959cf72c58662e65a4466) |
| Central fleet refresh and intake | [egohygiene/egohygiene.io#127](https://github.com/egohygiene/egohygiene.io/pull/127) | [4405646a](https://github.com/egohygiene/egohygiene.io/commit/4405646a0143c6d0d51da034fd57515b47a01989) | [e02fc595](https://github.com/egohygiene/egohygiene.io/commit/e02fc595855dcc94256a96ac56bc0446feaf3e35) |

Current consumer builders, producers, profile seals and provenance helpers select
Relay `981ddf4367c67fcd625e54321d95bab027f6c0f2`. The owner-backed Hygiene
validator is independently pinned to Observatory
`a1884942e953bb371499b2822b52f6865ecdae9d`. Public catalog admission retains
Hygiene `49639c1845cdfd08fbd5a768261a8b3cf515f80f` and exact public artifact
SHA-256 `af9c7186ded0bb57b18741eaa5905314b96d6adb03736946c868e0fc4aa50b26`.
None is a moving release alias.

## Resulting data paths

- **Dependencies:** exact public identity admission plus authored consumption
  declarations enter normal native builds. The bounded receipt verifies
  selected edges and policies; runtime/package adoption remains uncollected.
- **Fleet:** explicit retained repository artifacts feed a read-only assembler
  and ordinary handoff. The central site binds exact manifest/fleet bytes,
  expiry and partial state; its manual refresh workflow adds no publisher.
- **Work/Now, Health and Releases:** current push/manual consumer paths produce
  bounded real GitHub captures, upload a same-run artifact, and replay its exact
  ID/digest and actual observation clock. Duplicate builds reuse the captures.
  Deployment evidence stays uncollected without its own real receipt.
- **Compare:** post-build composition preserves the native source receipt and
  all non-Compare bytes. Identity exposes off/seed/compare; off is the default,
  seed requires a real first capture and compare requires a complete exact
  prior selection. No baseline was invented.
- **Hygiene:** an optional exact owner conformance model enables the existing
  route through validated provenance and DOM bindings. It displays supplied
  assessments, revision and freshness while whole applicability remains
  unknown. Missing owner input keeps the explicit unsupported state.

Each repository retains its Pages publisher; the organization site is the fleet
overview linking into those repository-owned destinations. Historical/no-capture
and frozen recovery paths preserve their prior clocks and selections. No new
dependency coverage domain or extra published Hygiene asset is introduced.

The original Relay #158–#166 and website #118–#125 review drafts are closed as
superseded by merged Relay #167 and site #126. Their source was already
integrated, and original branches remain available. Unrelated website draft
ancestry was not imported or marked merged by the reconciliation.

## Review evidence and remaining acceptance

Static work included independent source review, Python AST, JSON schema
definitions/local references, exact owner byte comparisons, unique-key YAML,
embedded shell/Python and affected JavaScript syntax, immutable pin metadata and
continuity checks. Shared reusable input/catalog parity is 21 and 23 inputs.
Consumer source comparison preserved 22 existing jobs and 144 existing step
guards; newly added source permissions are read-only.

Tests, builds, native/application execution, actual provider/artifact transport,
CI, browsers, canaries, live publication and rollback qualification were deferred
at the maintainer's request. No workflow was manually dispatched. Existing
automatic workflow effects are not inspected or presented as proof.

Real successful retained snapshot pairs and fleet artifact selections still
need to be produced and qualified. The optional Hygiene view needs an actual
supplied owner model to display assessments. Hygiene #47 retains the ADR-0001
metadata/human approval hold; Akashic's roadmap prerequisite remains separate.
Source merges cannot supply approval, clear those holds, or complete the feature,
integration, release and adoption acceptance issues.

## Next owner work and the organization sanity sweep

Continue structured Audits through
[Aether #86](https://github.com/egohygiene/aether/issues/86) →
[Observatory #20](https://github.com/egohygiene/observatory/issues/20) →
[Relay #74](https://github.com/egohygiene/relay/issues/74).

Continue Sanity through
[Hygiene #59](https://github.com/egohygiene/hygiene/issues/59) and
[Aether #87](https://github.com/egohygiene/aether/issues/87) →
[Observatory #21](https://github.com/egohygiene/observatory/issues/21) →
[Relay #76](https://github.com/egohygiene/relay/issues/76).

After those owner contracts and pages exist, run the separate organization sanity
sweep over the reviewed public roster, retaining exact repository revisions,
audit profiles, structured findings, applicability gaps, source evidence and
explicit review dispositions. Aggregate coverage without treating absent audits
as passes or builds as architectural ratification. No sweep ran in this batch.

[Production paths and operator boundaries](repository-intelligence-production-paths.md)
hold the implementation details. [Organization parent #41](https://github.com/egohygiene/.github/issues/41)
and [Pace #13](https://github.com/egohygiene/pace/issues/13) retain program and
adoption acceptance.

