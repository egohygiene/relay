# Repository Intelligence

Generate a complete static repository-intelligence dashboard without deploying
it. The action is intentionally a **builder**, so a consumer can compose the
result with any existing GitHub Pages, documentation, or product-site artifact.

## Consumer contract

```yaml
- name: Generate repository intelligence
  uses: egohygiene/relay/actions/repository-intelligence@v1
  with:
    output-directory: dist/intelligence
    default-branch: "${{ github.event.repository.default_branch }}"
```

For production consumers, pin the full Relay commit SHA and retain the release
in a comment for readable dependency updates:

```yaml
- name: Generate repository intelligence
  # egohygiene/relay repository-intelligence v1.0.0
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
Pages domain—for example, `https://akashic.egohygiene.io/intelligence/`.

## Inputs

| Input                       | Default                          | Purpose                                                                 |
| --------------------------- | -------------------------------- | ----------------------------------------------------------------------- |
| `output-directory`          | `dist/intelligence`              | Public HTML, CSS, JavaScript, and aggregate JSON bundle                  |
| `work-directory`            | `.cache/repository-intelligence` | Private collection workspace; do not publish wholesale                  |
| `reports-directory`         | `.reports`                       | Optional normalized producer summaries                                 |
| `repository`                | workflow repository              | Repository name in `owner/name` form                                    |
| `default-branch`            | `main`                           | Branch displayed in repository vitality                                |
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
| `output-directory`      | Complete public bundle                                                  |
| `index`                 | Dashboard `index.html`                                                  |
| `summary`               | `egohygiene.repository-intelligence-dashboard/v3` aggregate            |
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
reports remain visible as unavailable, invalid, stale, or unknown states. They
never become an implicit green result.

Use [`normalize-repository-report`](../normalize-repository-report/README.md) in
the authoritative scanner workflow to produce these summaries. Raw SARIF,
scanner JSON, workflow logs, tokens, and artifact URLs are not copied into the
public dashboard.

## Runtime and safety model

- Requires only Bash, Git, and Python 3 already available on GitHub-hosted runners.
- Makes no network requests and installs no dependencies.
- Writes no commits, tags, releases, deployments, or repository settings.
- Pins analytics and tree contracts to one resolved Git commit.
- Excludes generated reports, caches, builds, and vendored dependencies from
  change statistics by default.
- Omits contributor names, email addresses, and commit messages from public
  contracts.
- Keeps charts accessible through semantic table fallbacks.
- Keeps the source explorer usable without JavaScript via native `<details>`.

The raw `activity/` directory is diagnostic evidence, not a public artifact.
Only publish the configured `output-directory` and the explicitly documented
public JSON outputs.
