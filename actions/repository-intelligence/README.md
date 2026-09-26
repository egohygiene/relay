# Repository Intelligence

Generate a complete static repository-intelligence dashboard without deploying
it. The action is intentionally a **builder**, so a consumer can compose the
result with any existing GitHub Pages, documentation, or product-site artifact.

## Consumer contract

After a complete-history checkout, the production integration can be one step:

```yaml
- name: Generate repository intelligence
  # egohygiene/relay repository-intelligence v1.1.0
  uses: egohygiene/relay/actions/repository-intelligence@<full-commit-sha>
```

The defaults write the generated subtree to `dist/intelligence/`, keep private
work under `.cache/repository-intelligence/`, and derive repository visibility
and the default branch from workflow event metadata. Public repositories receive
a `public-safe` projection; private, internal, or unknown repositories receive
an `internal-only` artifact classification. Inputs cannot override GitHub's
repository identity or visibility. Production consumers must pin the full Relay
commit SHA and retain the release in a comment for readable dependency updates.
The moving `v1` alias is not an immutable production pin.

For example, after a release replaces the placeholder with the reviewed commit:

```yaml
- name: Generate repository intelligence
  # egohygiene/relay repository-intelligence v1.1.0
  uses: egohygiene/relay/actions/repository-intelligence@0123456789abcdef0123456789abcdef01234567
  with:
    output-directory: dist/intelligence
    default-branch: "${{ github.event.repository.default_branch }}"
```

The caller must check out complete history when `require-full-history` remains
enabled:

```yaml
- name: Checkout complete history
  uses: actions/checkout@<full-commit-sha>
  with:
    fetch-depth: 0
    persist-credentials: false
```

## Pages composition

The action never invokes `upload-pages-artifact` or `deploy-pages`. It writes
only the requested subtree, so the repository's existing build stays the sole
owner of its Pages artifact:

```yaml
- name: Build product site
  run: pnpm run build

- name: Add repository intelligence
  uses: egohygiene/relay/actions/repository-intelligence@<full-commit-sha>
  with:
    output-directory: dist/intelligence
    default-branch: "${{ github.event.repository.default_branch }}"

- name: Upload composed Pages artifact
  uses: actions/upload-pages-artifact@<full-commit-sha>
  with:
    path: dist
```

The deployed result is `/intelligence/` beneath that repository's configured
Pages domain—for example, `https://repository.example/intelligence/`.

The action clears and rebuilds only the configured output subtree. It rejects
an output path that does not end in `intelligence`, private work or reports
inside the output's site composition root, protected repository areas, path
traversal, and symlinked managed paths before writing. Root-site files such as
`dist/index.html` and `dist/CNAME` remain consumer-owned.

## Standalone artifact

Repositories without a site can generate a reviewable artifact without taking
on Pages deployment:

```yaml
jobs:
  intelligence:
    # egohygiene/relay repository-intelligence v1.1.0
    uses: egohygiene/relay/.github/workflows/repository-intelligence.yml@<full-commit-sha>
```

The reusable workflow checks out the caller, invokes the action from the exact
called Relay revision, and uploads only the generated dashboard subtree as an
ordinary GitHub Actions artifact. This is the default integration for private,
internal, unknown-visibility, and artifact-first repositories. Use the composite
action directly for site composition because a reusable-workflow job cannot
modify another job's workspace.

The reusable workflow additionally preserves a fixed, sanitized run report for
success or actionable failure and then reasserts any failed outcome. That
retention behavior belongs to workflow orchestration; invoking this composite
action directly does not upload either a site artifact or failure evidence.
See the
[event, trust, artifact, and recovery contract](../../docs/repository-intelligence-publication.md#reusable-workflow-trust-and-event-contract)
for trusted and fork pull requests, default-branch pushes, reusable calls, and
consumer-owned manual rebuilds.

## Standalone Pages subtree

A public repository without an existing site stack can still keep deployment
authority locally. This publishes only the `/intelligence/` subtree; root-site
content remains available for a later LaunchKit build.

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - name: Checkout complete history
        uses: actions/checkout@<full-commit-sha>
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Generate repository intelligence
        # egohygiene/relay repository-intelligence v1.1.0
        uses: egohygiene/relay/actions/repository-intelligence@<full-commit-sha>

      - name: Upload standalone Pages artifact
        uses: actions/upload-pages-artifact@<full-commit-sha>
        with:
          path: dist

  deploy:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: "${{ steps.deployment.outputs.page_url }}"
    steps:
      - name: Deploy consumer-owned Pages artifact
        id: deployment
        uses: actions/deploy-pages@<full-commit-sha>
```

Do not use this public deployment recipe for a private or internal repository
without a separate reviewed authorization.

## Portable repository identity

The source tree's root display label is the complete canonical `owner/name`,
passed explicitly from the action's resolved repository metadata. GitHub's
`GITHUB_REPOSITORY` wins; an explicit input may match case-insensitively but
cannot replace that identity or its spelling. Visibility retains its separate
event-authoritative validation. Outside GitHub, supply `repository` explicitly;
there is no `local/<checkout-basename>` fallback.

The standalone tree CLI accepts `--repository "owner/name"`, or uses
`GITHUB_REPOSITORY` when available. Missing, malformed, dot-segment, or conflicting
identities fail before output generation. For example, from a local consumer
checkout without GitHub metadata:

```bash
python3 "/path/to/relay/actions/repository-intelligence/scripts/generate_repository_intelligence.py" \
  --repo-root "." \
  --output-root ".cache/repository-intelligence" \
  --repository "example/consumer" \
  --ref "<full-consumer-sha>"
```

This corrects the root `name` value in the existing
`egohygiene.repository-tree/v1` contract; fields, relative paths, and schema
versions are unchanged. Callers that ran the standalone script without an
identity must now supply one. The corrected generator can legitimately change
tree, dashboard, summary, and manifest bytes relative to older generator pins.
It does not retroactively repair their output.

Portable reproduction fixes canonical identity (including spelling), represented
consumer commit, immutable Relay revision, evidence bytes, and all declared
inputs, including ref, source epoch/as-of, exclusions, history window, depth,
visibility, and default branch. Checkout basenames and parent directories are
not inputs. Complete history must be available in both checkouts. Identical
inputs must produce identical complete payload inventories, bytes, and manifest
digests; same-directory repetition is a separate, weaker check.

Run the cross-directory fixture with:

```bash
python3 -m unittest discover --start-directory "tests" \
  --pattern "test_repository_intelligence_portability.py" --verbose
```

It executes the composite action's checked-in Bash bodies in two complete,
detached checkouts under different parents, with optional evidence present and
absent. It checks canonical root identity, every public file, provenance, tree
exports, manifest hashes, and path exclusion. The existing same-workspace bundle
test and separate receipt tests remain required. This local harness substitutes
env expressions; it does not simulate GitHub scheduling or establish deployment
success. Follow the [publication evidence procedure](../../docs/repository-intelligence-publication.md#acceptance-evidence-by-stage)
for provider proof and consumer adoption.

## Inputs

| Input                       | Default                          | Purpose                                                                 |
| --------------------------- | -------------------------------- | ----------------------------------------------------------------------- |
| `output-directory`          | `dist/intelligence`              | Generated HTML, CSS, JavaScript, and aggregate JSON bundle               |
| `work-directory`            | `.cache/repository-intelligence` | Private collection workspace; do not publish wholesale                  |
| `reports-directory`         | `.reports`                       | Optional summaries; always excluded from tree and analytics              |
| `observatory-snapshot`      | empty                            | Optional commit-matched public-safe Repository Intelligence read model    |
| `observatory-comparison`    | empty                            | Optional comparison whose after boundary matches the snapshot and commit |
| `repository`                | workflow repository              | Required without `GITHUB_REPOSITORY`; cannot override GitHub identity    |
| `repository-visibility`     | event visibility, else `unknown` | Local-only fallback; cannot override GitHub visibility                  |
| `default-branch`            | event default, then `main`       | Optional branch override for repository vitality                        |
| `source-commit`             | commit resolved from `activity-ref` | Explicit represented commit                                          |
| `as-of`                     | represented commit timestamp     | Deterministic report-freshness instant                                  |
| `activity-ref`              | `HEAD`                           | Git revision inspected by collectors                                    |
| `activity-since`            | `1 year ago`                     | History window anchored to the represented commit                       |
| `activity-author`           | empty                            | Optional author filter for private diagnostics                          |
| `max-depth`                 | `10`                             | Maximum source-tree depth, from 1 through 20                             |
| `excluded-paths`            | curated defaults                 | Paths removed from the repository tree                                  |
| `analytics-excluded-paths`  | curated defaults                 | Generated/vendor/cache paths removed from public analytics              |
| `require-full-history`      | `true`                           | Reject shallow history rather than presenting incomplete statistics     |

## Outputs

| Output                  | Contents                                                               |
| ----------------------- | ---------------------------------------------------------------------- |
| `output-directory`      | Complete validated bundle                                               |
| `index`                 | Repository Intelligence overview `index.html`                           |
| `now`                   | Operational `/now/` entry                                               |
| `roadmap`               | Scrollable `/roadmap/` quest line                                       |
| `decisions`             | Authority-aware `/decisions/` ADR ledger                                |
| `journey`               | Release-bounded `/journey/` semantic Git history                        |
| `dependencies`          | Directed dependency-impact `/dependencies/` view                         |
| `health`                | Normalized check-evidence `/health/` view                                 |
| `releases`              | Shipped release-evidence `/releases/` view                                |
| `work`                  | Active-work orientation `/work/` view                                     |
| `search`                | Normalized entity `/search/` view                                         |
| `compare`               | Structural snapshot `/compare/` view                                     |
| `dashboard`             | Compatibility analytics `/dashboard/` entry                            |
| `summary`               | `egohygiene.repository-intelligence-dashboard/v3` aggregate            |
| `provenance`            | `egohygiene.relay.repository-intelligence-provenance/v1` metadata       |
| `build-manifest`        | Deterministic `egohygiene.relay.repository-intelligence-build-manifest/v1` handoff |
| `build-manifest-sha256` | Tagged SHA-256 digest of the exact build manifest                       |
| `bundle-digest`         | Tagged digest of the canonical payload file inventory                   |
| `analytics-summary`     | `egohygiene.repository-analytics/v1` public-safe analytics              |
| `repository-tree`       | `egohygiene.repository-tree/v1` commit-scoped source tree               |
| `diagnostics-directory` | Raw activity diagnostics that may contain identities and commit messages |

## Optional producer reports

The builder looks for the following contracts when available:

```text
.reports/
├── osv/summary.json
├── megalinter/summary.json
└── scorecard/summary.json
```

Each file must use `egohygiene.repository-report-summary/v1`. Missing producer
directories, missing files, malformed JSON, stale evidence, and commit-mismatched
reports remain visible as unavailable, invalid, or stale states. They never
become an implicit green result.

Use [`normalize-repository-report`](../normalize-repository-report/README.md) in
the authoritative scanner workflow to produce these summaries. Raw SARIF,
scanner JSON, workflow logs, tokens, and artifact URLs are not copied into the
public dashboard.

## Generated bundle and provenance

The generated output directory has one exact, validated shape:

```text
dist/intelligence/
├── index.html
├── now/index.html
├── roadmap/index.html
├── decisions/index.html
├── journey/index.html
├── dependencies/index.html
├── health/index.html
├── releases/index.html
├── work/index.html
├── search/index.html
├── compare/index.html
├── dashboard/index.html
├── summary.json
├── provenance.json
├── build-manifest.json
├── site.css
├── site.js
├── styles.css
└── explorer.js
```

The root is the Repository Intelligence overview and `/now/` is the focused
current-state view. `/roadmap/` renders the
commit-matched Observatory roadmap view as a static-first quest line. Declared
roots form chapters; stable step IDs form durable fragments; dependencies and
blockers link in both display directions; and each native evidence drawer keeps
ADRs, issues, pull requests, commits, checks, releases, deployments, and changed
files attached to canonical sources. Large evidence drawers virtualize only
after browser enhancement, so the static HTML and print projection remain
complete. Progress uses declared state and exit criteria, never commit volume.

`/decisions/` renders the normalized ADR projection without copying or rewriting
canonical records. Organization-scoped inheritance and repository-local
authority occupy separate ledger sections; lifecycle status, implementation
status, supersession, source assertion, freshness, and represented revision stay
visually distinct. Stable fragments, affected-quest links, URL-backed facets,
keyboard navigation, complete static evidence, print output, and an optional
browser-enhanced compare table keep long histories usable. Missing date, domain,
or affected-component facets remain explicitly “Not projected” until the pinned
Observatory contract supplies them.

`/journey/` renders the normalized lifecycle-event projection as a semantic
history rather than a raw commit list. Observatory's deterministic rule closes
each chapter at a `release.published` event and places later events in an open
chapter. Relay preserves that order, presents intent, work, code, proof, and
delivery as calm visual lanes, and reverses only explicit roadmap/ADR evidence
relationships for cross-view links. Orphaned work is labelled “Unclassified
context” without assigning intent. Every event remains in static HTML while
browser `content-visibility` keeps long histories responsive. Gaps of at least
72 hours receive a neutral interval marker that never claims the repository was
inactive during an unprojected period.

Journey filters cover projected state, kind, time, chapter, release boundary,
actor, assertion, freshness, quest, and decision context. The current
public-safe contract does not project raw Git parents, branch names, or changed
paths at event granularity; those filters remain explicitly unavailable. The
browser-only chapter comparison reports structural counts rather than causality
or productivity. Automatic replay is optional, stops when filters change, and
is disabled when the operating system requests reduced motion; the manual
scrubber remains available.

The supporting views stay intentionally focused:

| Bundle route | Primary question | Accepted evidence boundary |
| --- | --- | --- |
| `/dependencies/` | What depends on what? | Directed normalized relationships and impact paths |
| `/health/` | What does the current evidence say? | Core check, assertion, and freshness evidence; not full Hygiene conformance |
| `/releases/` | What has actually shipped? | Release publication, included entities, deployments, and boundary IDs |
| `/work/` | What work needs attention? | Open execution records and explicit roadmap readiness queues |
| `/search/` | Where is the normalized object? | Observatory-supplied entity index and `search_text`, without local ranking |
| `/compare/` | What structurally changed? | Separate before/after comparison artifact, never causal inference |

These paths are relative to the generated subtree. When a repository-profile
consumer mounts it at `/intelligence/`, their canonical public routes are
`/intelligence/<route>/` under the pinned Hygiene surface registry. Top-level
aliases are consumer-owned redirects only. The builder has no site-origin or
deployment authority and therefore does not manufacture canonical URLs or
duplicate alias content.

`provenance.json` records the generator name/version, the requested Relay source
ref, its resolved commit when GitHub exposes one, whether the requested ref was
itself immutable, the consumer source and visibility, every data-contract
version, and the generation instant. The instant defaults to the represented
consumer commit timestamp, or to an explicit `as-of` input, so identical
normalized inputs produce byte-identical bundles. A moving reusable-workflow
ref retains its resolved commit but is marked non-immutable; a direct moving or
local ref never fabricates a commit.

The projection metadata records the intended `/intelligence/` subtree and
`deployment_authority: consumer`; it is not evidence that Pages was deployed.
Its classification is `public-safe` only for a GitHub-public repository and
`internal-only` otherwise. Hygiene owns organization eligibility, route policy,
privacy requirements, and exceptions; Relay implements and validates this
module contract.

`build-manifest.json` is the deterministic deployment handoff. It binds the
represented consumer revision, exact Relay generator revision, input and schema
contract versions, source epoch, enabled routes, every payload file digest, and
one canonical bundle digest. The manifest inventories every generated byte
except itself; its own SHA-256 is exposed separately as an action output. Run,
environment, URL, deployment conclusion, aliases, final composed-site digest,
and rollback metadata are intentionally excluded from this bundle.

Consumers that deploy the composed site use the separate
[`repository-intelligence-deployment-provenance`](../repository-intelligence-deployment-provenance/)
action to capture pre-existing routes, verify composition before deployment,
and record a consumer-owned receipt afterward. That receipt remains outside
the public site and does not change the Relay bundle digest.

The final validation rejects unexpected files, invalid JSON relationships,
broken or traversing local links, unsafe or cross-repository URLs, a non-
`intelligence` subtree, noncanonical client assets, and private-data markers. It
runs automatically inside the action. For debugging, a Relay maintainer can
repeat it from an exact-SHA Relay checkout against an already generated consumer
checkout:

```bash
consumer_root="/path/to/consumer-checkout"
consumer_commit="$(git -C "${consumer_root}" rev-parse HEAD)"
relay_commit="$(git rev-parse HEAD)"

python3 actions/repository-intelligence/scripts/validate_repository_intelligence_bundle.py \
  --repository-root "${consumer_root}" \
  --output-root "${consumer_root}/dist/intelligence" \
  --repository "owner/repository" \
  --repository-visibility "public" \
  --source-commit "${consumer_commit}" \
  --generator-version "1.1.0" \
  --generator-source-ref "${relay_commit}" \
  --generator-source-commit "${relay_commit}" \
  --generator-immutable "true"
```

## Runtime and safety model

- Requires only Bash, Git, and Python 3 already available on GitHub-hosted runners.
- Makes no network requests and installs no dependencies.
- Reads no token or secret and performs no cache restore or save operation.
- Executes no repository-owned build, test, package-manager, or installation command.
- Writes no commits, tags, releases, deployments, or repository settings.
- Emits only deterministic build metadata; deployment-specific receipts are a separate consumer action.
- Never uploads artifacts itself when used as a composite action.
- Pins analytics and tree contracts to one resolved Git commit.
- Excludes generated reports, caches, builds, and vendored dependencies from
  change statistics by default.
- Omits contributor names, email addresses, and commit messages from public
  contracts.
- Keeps charts accessible through semantic table fallbacks.
- Keeps the source explorer usable without JavaScript via native `<details>`.

The raw `activity/` directory is diagnostic evidence, not a site artifact. Only
the configured `output-directory` may be composed into a public site, and only
when provenance classifies it `public-safe`. Do not commit generated HTML, CSS,
JavaScript, or JSON to a consumer repository by default; retain the subtree as
a build or Pages artifact instead.

## v1.1 migration notes

- The validated bundle adds `provenance.json` as its fifth exact file.
- `output-directory` must end in `intelligence`; its parent is the action's site
  composition boundary, so work and report evidence must remain outside it.
- The configured reports directory is excluded from both source anatomy and
  analytics even when it is not named `.reports`.
- Default tree and analytics exclusions now preserve an ordinary `site/`
  source directory while excluding generated `.site/` and report evidence.
- Public URLs are now limited to canonical HTTPS links for the represented
  consumer and source commit; credential, query, fragment, traversal, and
  nonstandard-port variants are rejected or omitted.
- Normalizer failures no longer echo local input paths, and its optional URL
  inputs apply the same credential-free HTTPS boundary.

## Deployment-provenance migration notes

- Production composition now requires an exact Relay revision so
  `build-manifest.json` can identify an immutable generator commit.
- The uploaded site includes the deterministic manifest; Actions artifact
  digests remain transport digests and are not substitutes for `bundle-digest`.
- Deployment receipts must stay outside `output-directory` and the final
  composed site. See the consumer integration and rollback action linked above.
