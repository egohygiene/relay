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
| Repository Intelligence site | `egohygiene/relay/actions/repository-intelligence@v1` |
| Canonical labels and pull-request metadata | `egohygiene/relay/actions/repository-labels@v1` |
| Scanner report normalization | `egohygiene/relay/actions/normalize-repository-report@v1` |
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

These moving aliases advertise the release surface. Production consumers use a
reviewed full commit SHA, as shown below.

The complete action and workflow inventories live in
[`action-catalog.json`](action-catalog.json) and
[`workflow-catalog.json`](workflow-catalog.json). See
[`actions/README.md`](actions/README.md) and
[`WORKFLOW_CATALOG.md`](WORKFLOW_CATALOG.md) for their human contracts.
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

- name: Add repository intelligence
  # egohygiene/relay repository-intelligence v1.1.0
  uses: egohygiene/relay/actions/repository-intelligence@<full-commit-sha>
  # When an earlier step materializes Observatory's commit-matched read model:
  # with:
  #   observatory-snapshot: .cache/observatory/repository-intelligence.json

- name: Upload one composed Pages artifact
  uses: actions/upload-pages-artifact@<full-commit-sha>
  with:
    path: dist
```

Relay writes `dist/intelligence/` but never deploys it. That preserves one Pages
owner per repository. A consumer that uploads `dist/` at its configured domain
will make the operational entry and its routed views available at URLs such as:

```text
https://repository.example/intelligence/
https://repository.example/intelligence/now/
https://repository.example/intelligence/roadmap/
https://repository.example/intelligence/decisions/
https://repository.example/intelligence/dashboard/
```

The action contract does not depend on a custom domain or a specific root-site
stack.

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

Both entry points produce the same framework-free, visibility-aware subtree.
The root and `/now/` are equivalent operational entry points; the previous
analytics experience remains available at `/dashboard/`. `/roadmap/` renders
the normalized `ROADMAP.md` projection as a vertically scrollable quest line
with stable step links, dependency chapters, declared progress, and expandable
delivery evidence. `/decisions/` renders inherited and repository-local ADRs as
an authority-aware historical ledger with durable lineage, implementation
state, affected-quest links, faceted filtering, evidence expansion, and optional
side-by-side comparison. `/journey/` renders Observatory lifecycle events as
release-bounded delivery chapters across intent, work, code, proof, and delivery
lanes. Events retain canonical sources, explicit quest/ADR context, visible
unclassified status, date and evidence filters, chapter comparison, and an
optional reduced-motion-safe replay. The shell reserves stable routes for
Dependencies, Health, Releases, Work, Search, and Compare so focused follow-up
work can fill them without changing navigation contracts.

Supplying `observatory-snapshot` projects the commit-matched public-safe
`egohygiene.observatory.repository-intelligence-read-model/v1` into `/now/`,
`/roadmap/`, `/decisions/`, and `/journey/`.
Omitting it remains valid and renders an explicit unavailable state; Relay does
not infer active work from analytics. Private collection data remains in the
configured work directory—`.cache/repository-intelligence/` by default—and
must never be uploaded as site content. Only a bundle whose provenance is
classified `public-safe` is eligible for public-site composition.

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

See [ARCHITECTURE.md](ARCHITECTURE.md) for structural boundaries and
[ROADMAP.md](ROADMAP.md) for extraction and adoption sequencing.
