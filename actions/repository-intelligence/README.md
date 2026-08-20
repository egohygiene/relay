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

## Inputs

| Input                       | Default                          | Purpose                                                                 |
| --------------------------- | -------------------------------- | ----------------------------------------------------------------------- |
| `output-directory`          | `dist/intelligence`              | Generated HTML, CSS, JavaScript, and aggregate JSON bundle               |
| `work-directory`            | `.cache/repository-intelligence` | Private collection workspace; do not publish wholesale                  |
| `reports-directory`         | `.reports`                       | Optional summaries; always excluded from tree and analytics              |
| `repository`                | workflow repository              | Local fallback; cannot override GitHub repository identity               |
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
| `index`                 | Dashboard `index.html`                                                  |
| `summary`               | `egohygiene.repository-intelligence-dashboard/v3` aggregate            |
| `provenance`            | `egohygiene.relay.repository-intelligence-provenance/v1` metadata       |
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
├── summary.json
├── provenance.json
├── styles.css
└── explorer.js
```

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
- Writes no commits, tags, releases, deployments, or repository settings.
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
