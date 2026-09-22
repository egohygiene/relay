# relay

🔄 Reusable GitHub Actions, workflows, and CI orchestration for the Ego Hygiene
ecosystem.

Relay turns proven repository automation into small, versioned contracts that
can be installed everywhere without copying implementation between repositories.
Each consumer keeps ownership of its configuration, permissions, site build,
and deployment.

## Release surface

| Capability | Discovery alias |
| ---------- | --------------- |
| Artifact size and performance budgets | `egohygiene/relay/actions/artifact-budget@v1` |
| Repository Intelligence site | `egohygiene/relay/actions/repository-intelligence@v1` |
| Repository Intelligence deployment provenance | `egohygiene/relay/actions/repository-intelligence-deployment-provenance@v1` |
| Validated repository journal | `egohygiene/relay/actions/repository-journal@v1` |
| Canonical labels and pull-request metadata | `egohygiene/relay/actions/repository-labels@v1` |
| Warning-first stale pull-request lifecycle | `egohygiene/relay/actions/stale-pull-requests@v1` |
| Scanner report normalization | `egohygiene/relay/actions/normalize-repository-report@v1` |
| Bounded success and failure report preservation | `egohygiene/relay/actions/preserve-ci-report@v1` |
| Guarded report snapshot publication | `egohygiene/relay/actions/publish-report-snapshot@v1` |
| Opinionated intelligence artifact workflow | `egohygiene/relay/.github/workflows/repository-intelligence.yml@v1` |
| Publication-site contract validation | `egohygiene/relay/actions/validate-publication-site@v1` |
| Deployed publication byte verification | `egohygiene/relay/actions/verify-publication-pages@v1` |
| Profile-bound release bundle validation | `egohygiene/relay/actions/validate-release-bundle@v1` |
| Read-only semantic-release plan verification | `egohygiene/relay/actions/verify-release-plan@v1` |
| Read-only publication review | `egohygiene/relay/.github/workflows/publication-review.yml@v1` |
| Publication Pages deployment | `egohygiene/relay/.github/workflows/publication-pages.yml@v1` |
| Immutable profile-bound release publication | `egohygiene/relay/.github/workflows/release-artifact.yml@v1` |
| Read-only semantic-release preparation | `egohygiene/relay/.github/workflows/release-prepare.yml@v1` |
| Reviewed semantic-release handoff | `egohygiene/relay/.github/workflows/semantic-release.yml@v1` |
| Read-only canonical label plan | `egohygiene/relay/.github/workflows/label-sync-plan.yml@v1` |
| Reviewed canonical label apply | `egohygiene/relay/.github/workflows/label-sync-apply.yml@v1` |
| Read-only pull-request label plan | `egohygiene/relay/.github/workflows/pull-request-label-plan.yml@v1` |
| Trusted pull-request label apply | `egohygiene/relay/.github/workflows/pull-request-label-apply.yml@v1` |
| Advisory-first stale pull-request lifecycle | `egohygiene/relay/.github/workflows/stale-pull-requests.yml@v1` |
| Advisory or blocking artifact budgets | `egohygiene/relay/.github/workflows/artifact-budget.yml@v1` |
| Read-only no-billing repository journal | `egohygiene/relay/.github/workflows/repository-journal.yml@v1` |
| Explicit Copilot repository journal | `egohygiene/relay/.github/workflows/repository-journal-copilot.yml@v1` |

These moving aliases advertise the release surface. Production consumers use a
reviewed full commit SHA, as shown below.

The complete action and workflow inventories live in
[`action-catalog.json`](action-catalog.json) and
[`workflow-catalog.json`](workflow-catalog.json). See
[`actions/README.md`](actions/README.md) and
[`WORKFLOW_CATALOG.md`](WORKFLOW_CATALOG.md) for their human contracts.
Workflow cancellation classes and durable report retention are defined in
[`docs/ci-run-lifecycle.md`](docs/ci-run-lifecycle.md).
The proposed repository-architecture validation boundary, immutable upstream
pins, and future local/CI evidence seam are defined in
[`docs/repository-architecture-validation.md`](docs/repository-architecture-validation.md).
The complete release lifecycle and repository-class boundaries are documented
in [`SEMANTIC_RELEASE.md`](SEMANTIC_RELEASE.md).

## Compose Intelligence into an existing site

```yaml
- name: Checkout complete history
  uses: actions/checkout@<full-commit-sha>
  with:
    fetch-depth: 0
    persist-credentials: false

- name: Build the repository site
  run: pnpm run build

- name: Capture consumer routes before composition
  uses: egohygiene/relay/actions/repository-intelligence-deployment-provenance@<full-commit-sha>
  with:
    operation: capture-baseline
    consumer-revision: "${{ github.sha }}"

- name: Add repository intelligence
  # egohygiene/relay repository-intelligence v1.1.0
  uses: egohygiene/relay/actions/repository-intelligence@<full-commit-sha>
  # When an earlier step materializes Observatory's commit-matched read model:
  # with:
  #   observatory-snapshot: .cache/observatory/repository-intelligence.json

- name: Verify consumer composition
  # egohygiene/relay repository-intelligence-deployment-provenance v1.6.0
  uses: egohygiene/relay/actions/repository-intelligence-deployment-provenance@<same-full-commit-sha>
  with:
    operation: verify-composition
    consumer-revision: "${{ github.sha }}"
    relay-revision: "<same-full-commit-sha>"

- name: Upload one composed Pages artifact
  uses: actions/upload-pages-artifact@<full-commit-sha>
  with:
    path: dist
```

Relay writes `dist/intelligence/` but never deploys it. That preserves one Pages
owner per repository. A consumer that uploads `dist/` at its configured domain
will make the product overview and its routed evidence views available at URLs such as:

```text
https://repository.example/intelligence/
https://repository.example/intelligence/now/
https://repository.example/intelligence/roadmap/
https://repository.example/intelligence/decisions/
https://repository.example/intelligence/dashboard/
```

The action contract does not depend on a custom domain or a specific root-site
stack.

The consumer first captures its unrelated route baseline before the Intelligence
step. After its own deployment step, it can invoke the provenance action again
with `record-receipt` to bind the deterministic manifest to the consumer run,
environment, URL, conclusion, aliases, final site digest, and rollback point.
The receipt remains outside `dist/`; run-specific metadata never changes the
Relay bundle. See the
[complete reference pipeline](examples/workflows/repository-intelligence-deployment-provenance.md).

## Review and deploy product-owned publication sites

Relay v1.3 adds a renderer-neutral Pages lifecycle around a complete static site
artifact. The product repository still owns its source, native Make/Task build,
theme, routes, and staged bytes. Beacon defines the optional
`beacon.publication-hub/v1` catalog contract. Relay only downloads the caller's
artifact and separates static authority into two callable workflows. The
read-only surface validates the catalog and complete `SHA256SUMS` and preserves
the exact reviewed bytes. The deployment-only surface invokes that review,
deploys only its output, and proves the public HTTPS bytes.

```yaml
jobs:
  publication_pages:
    permissions:
      actions: read
      contents: read
      id-token: write
      pages: write
    # Relay publication-pages v1.4.0; production callers pin a full commit SHA.
    uses: egohygiene/relay/.github/workflows/publication-pages.yml@<full-commit-sha>
    with:
      artifact-name: "publication-site-${{ github.sha }}"
      expected-base-url: "https://publication.example.org/"
      expected-source-revision: "${{ github.sha }}"
      required-routes: '["", "paper/", "magazine/", "downloads/"]'
```

The caller must build and upload the ordinary `publication-site-*` artifact in
an earlier job. Deployment requests fail closed unless they originate from a
push or manual run on the configured default branch. Pull requests call
`egohygiene/relay/.github/workflows/publication-review.yml@<full-commit-sha>`
with only `actions: read` and `contents: read`; GitHub therefore never grants a
review run latent Pages or OIDC authority. See the
[Antidote](examples/workflows/publication-pages-antidote.md) and
[Reflector](examples/workflows/publication-pages-reflector.md) caller patterns.

For a standalone, reviewable artifact instead of a Pages composition, call the
reusable workflow at the same immutable Relay commit:

```yaml
jobs:
  intelligence:
    # egohygiene/relay repository-intelligence v1.1.0
    uses: egohygiene/relay/.github/workflows/repository-intelligence.yml@<full-commit-sha>
```

The reusable workflow applies the same read-only, no-secret ceiling to trusted
and fork pull requests, executes no consumer scripts, uses no caches, and never
deploys Pages. It returns the successful site artifact identity and digest and
retains a sanitized success or actionable-failure report for 30 days before
reasserting a failure. See the complete
[event, trust, retention, and recovery contract](docs/repository-intelligence-publication.md#reusable-workflow-trust-and-event-contract).

Both entry points produce the same framework-free, visibility-aware subtree.
The subtree root is the Repository Intelligence overview, `/now/` is the
focused current-state view, and the previous analytics experience remains
available at `/dashboard/`. `/roadmap/` renders
the normalized `ROADMAP.md` projection as a vertically scrollable quest line
with stable step links, dependency chapters, declared progress, and expandable
delivery evidence. `/decisions/` renders inherited and repository-local ADRs as
an authority-aware historical ledger with durable lineage, implementation
state, affected-quest links, faceted filtering, evidence expansion, and optional
side-by-side comparison. `/journey/` renders Observatory lifecycle events as
release-bounded delivery chapters across intent, work, code, proof, and delivery
lanes. Events retain canonical sources, explicit quest/ADR context, visible
unclassified status, date and evidence filters, chapter comparison, and an
optional reduced-motion-safe replay. The shell exposes stable routes for
Dependencies, Health, Releases, Work, Search, and Compare, and all six routes
now render their accepted normalized evidence with explicit empty, partial, and
unavailable states. Navigation carries applicable URL-backed filters, time
ranges, and stable selected-entity context between related views without
changing the commit-matched repository boundary.

For a repository-profile site, Hygiene's pinned public-surface registry makes
the generated paths canonical beneath `/intelligence/`: for example,
`/intelligence/dependencies/`, `/intelligence/health/`,
`/intelligence/releases/`, `/intelligence/work/`,
`/intelligence/search/`, and `/intelligence/compare/`. Friendly top-level
forms such as `/health/` and `/search/` are redirect-only aliases owned by the
consumer's final site composition; Relay does not publish duplicate pages.

Supplying `observatory-snapshot` projects the commit-matched public-safe
`egohygiene.observatory.repository-intelligence-read-model/v1` into `/now/`,
`/roadmap/`, `/decisions/`, `/journey/`, `/dependencies/`, `/health/`,
`/releases/`, `/work/`, and `/search/`. A separately supplied, boundary-matched
`observatory-comparison` projects `/compare/`.
Omitting `observatory-snapshot` remains valid and renders explicit unavailable
states; Relay does not infer active work from analytics. Omitting
`observatory-comparison` leaves only `/compare/` in its explicit partial state.
Private collection data remains in the configured work
directory—`.cache/repository-intelligence/` by default—and must never be
uploaded as site content. Only a bundle whose provenance is classified
`public-safe` is eligible for public-site composition.

## Manage stale pull requests without silent closure

The stale pull-request workflow evaluates open work in a read-only job and
uploads a checksum-bound plan before any mutation is possible. Advisory mode is
the default. Its matching apply job runs only when the caller explicitly sets
`advisory: false` and grants write permission; closure remains independently
disabled until `close-enabled: true` is also reviewed. The default conditional
path has only pull-request authority. Issues permissions appear only in the
alternate jobs selected by `process-issues: true`.

Every automated close requires both the configured stale label and a visible,
trusted Relay warning marker from an earlier run. New activity, a reopen event,
or an explicit exemption prevents closure and clears lifecycle labels on the
next enforcing run. Drafts and bot-authored work are exempt by default, as are
the `do-not-stale`, `pinned`, `critical`, `security`, `dependencies`,
`priority:p0`, and `area:security` labels. Issue processing is disabled unless
the caller opts in explicitly.

The caller owns the schedule and repository labels. See the
[minimal scheduled integration](examples/workflows/stale-pull-requests.md) for
read-only adoption, enforcement permissions, recovery, and immutable pinning.

## Enforce artifact budgets without running consumer builds

The artifact-budget action normalizes already-produced filesystem artifacts or
consumer-pinned Size Limit JSON into one deterministic v1 report. It supports
absolute, byte-delta, percentage-delta, and warning thresholds for JavaScript
bundles, static sites, native binaries, archives, and container-image archives.
The reusable workflow downloads only caller-owned Actions artifacts, never
checks out or executes consumer code, and defaults to advisory mode. See the
[web and native adoption examples](examples/workflows/artifact-budget.md).

## Publish repository journals without requiring AI billing

The repository-journal workflow collects bounded GitHub metadata, preserves
empty, partial, unavailable, and complete source states, and renders through a
checksum-pinned Aether contract. Its default deterministic mode and reviewed
manual-candidate mode require no Copilot account or billing policy. Each
candidate statement cites normalized evidence retained in the same artifact.

Copilot generation is a separate reusable workflow with job-scoped
`copilot-requests: write`; it makes no request unless exact runtime, credential,
policy, permission, and billing checks pass. Neither workflow checks out
consumer code, writes repository state, or owns Slack, Discord, or another
delivery secret. See the [contract](docs/repository-journal.md) and
[caller examples](examples/workflows/repository-journal.md).

## Architecture boundary

- **Relay** owns reusable action/workflow implementation and releases.
- **Hygiene** owns organization eligibility, route and privacy requirements,
  and reviewed exceptions.
- **Consumer repositories** own inputs, permissions, final Pages composition,
  identity, and deployment.
- **Holon** owns the static-first visual component vocabulary; Relay owns route
  composition, action execution, and publication artifacts.
- **Pace** can detect outdated pins and reconcile consumers.
- **Observatory** owns normalized Repository Intelligence read models; Relay
  accepts only a repository- and commit-matched public-safe snapshot.

The Intelligence builder requires only Bash, Git, and Python 3. It has no
network calls, package installation, framework runtime, or deployment side
effects. The separately documented snapshot publisher is the only write-capable
action in the initial catalog.

## Validate locally

```bash
python3 scripts/validate_actions.py
python3 -m unittest discover --start-directory tests --pattern "test_*.py" --verbose
python3 -m compileall -q actions scripts tests
```

Node.js is a test-only prerequisite for browser-asset syntax and behavior
harnesses; the action runtime remains Bash, Git, and Python 3.

CI additionally checks Bash syntax, JSON parsing, workflow/action metadata, and
release invariants on every pull request and default-branch push.

## Semantic-release preparation and publication

The Aether `egohygiene.repository-release/v1` declaration remains the source of
release intent. Relay validates that declaration, its selected component's sole
version authority, Keep a Changelog promotion, Git/default-branch identity,
immutable tag availability, and the selected artifact profile. Conventional
Commit history may inform a human-reviewed bump, but Relay never rewrites a
version or changelog.

Use `release-prepare.yml` from pull requests or manual planning workflows. It
has no write permission and always preserves deterministic success or bounded
failure evidence. After the reviewed preparation merges, a repository-owned
manual workflow on the current default branch builds the product's profile
bundle and calls `semantic-release.yml`. That workflow verifies the exact
candidate before handing the same artifact to `release-artifact.yml`.

Registry packages, container pushes, Pages deployment, DOI minting, and other
external delivery remain separate consumer-owned adapters. They may consume
Relay evidence but are not implied by a GitHub Release.

## Versioning and publication

Relay publishes all cataloged actions together:

- immutable semantic release: `v1.0.0`;
- moving major alias: `v1`;
- recommended consumer reference: full commit SHA.

The current [`release.json`](release.json) authority and
[`CHANGELOG.md`](CHANGELOG.md) prepare `v1.6.0`; every prior exact tag remains
immutable. The `Release Relay actions` workflow runs only through explicit
manual dispatch on the configured default branch. It builds Relay's
`github-action` profile bundle and dogfoods the reusable semantic-release
verification and immutable publication path while naming the product-facing
archive and Release `relay`.
If tag creation succeeds but release creation is interrupted, a rerun resumes
only when that immutable tag still resolves to the same validated commit.
Subdirectory actions are directly consumable without Marketplace publication;
a future Marketplace entry can improve discovery without changing distribution.
The moving `v1` alias is for discovery and controlled refresh tooling, not for
production consumer workflows.

For consumer artifacts, use the profile-bound release workflow instead of
copying a release YAML file. It validates complete checksums and the declared
profile’s provenance, SBOM, signature, and rollback evidence before it creates
or resumes an immutable GitHub Release. Callers may provide a separate bounded
`release-name` so generic validation profiles such as `binary` do not leak into
product-facing asset names. Registry publication and deployment
remain caller-owned authorization steps. See [RELEASE_PROFILES.md](RELEASE_PROFILES.md).

## Repository continuity preflight

Local consumers may invoke
`egohygiene/relay/actions/repository-continuity-preflight@v1` from an immutable
commit pin, or use `task continuity:preflight` with explicit request, policy,
and pinned EgoLint source paths.

Pull-request consumers call
`egohygiene/relay/.github/workflows/continuity-preflight.yml@v1` from a reviewed
full commit SHA. The workflow is a read-only backstop after the repository's
semantic handoff has already been reviewed locally.

Relay's proposed continuity-preflight profile binds future local and reusable
CI adapters to one request/result contract. It pins the reviewed Aether,
Hygiene, EgoLint, and Holon inputs by immutable revision and SHA-256 digest,
keeps unreleased inputs capped at `observe`, and excludes semantic checkpoint
prose from evidence. See
[`docs/repository-continuity-preflight.md`](docs/repository-continuity-preflight.md).

Validate the contract offline:

```bash
python3 scripts/validate_continuity_preflight_contract.py validate
```

The local adapter executes the pinned EgoLint source entirely offline and
normalizes its report without modifying the inspected checkout. The reusable
pull-request workflow remains tracked by Relay issue #63.

## Repository architecture validation

Relay's proposed architecture-validation profile pins Hygiene policy, EgoLint
semantics, and Holon materialization artifacts by full commit SHA and SHA-256.
It defines closed request and result contracts for repository contracts,
architecture records, and future diagram evidence while keeping Relay limited
to orchestration and normalized evidence.

Checkpoint 1 is contract-only: no action or reusable workflow is advertised.
Unreleased upstream inputs cap the profile at advisory mode, diagram semantics
remain explicitly planned, and unavailable coverage stays visible.

```bash
python3 scripts/validate_repository_architecture_contract.py validate
```

See
[`docs/repository-architecture-validation.md`](docs/repository-architecture-validation.md)
for the ownership, privacy, bounds, immutable pins, and ordered implementation
gates.

See [ARCHITECTURE.md](ARCHITECTURE.md) for structural boundaries and
[ROADMAP.md](ROADMAP.md) for extraction and adoption sequencing.
