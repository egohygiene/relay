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
| Scanner report normalization | `egohygiene/relay/actions/normalize-repository-report@v1` |
| Guarded report snapshot publication | `egohygiene/relay/actions/publish-report-snapshot@v1` |
| Opinionated intelligence artifact workflow | `egohygiene/relay/.github/workflows/repository-intelligence.yml@v1` |

These moving aliases advertise the release surface. Production consumers use a
reviewed full commit SHA, as shown below.

The complete action and workflow inventories live in
[`action-catalog.json`](action-catalog.json) and
[`workflow-catalog.json`](workflow-catalog.json). See
[`actions/README.md`](actions/README.md) and
[`WORKFLOW_CATALOG.md`](WORKFLOW_CATALOG.md) for their human contracts.

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
https://repository.example/intelligence/dashboard/
```

The action contract does not depend on a custom domain or a specific root-site
stack.

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
analytics experience remains available at `/dashboard/`. The shell reserves
stable routes for Roadmap, Decisions, Journey, Dependencies, Health, Releases,
Work, Search, and Compare so focused follow-up work can fill them without
changing navigation contracts.

Supplying `observatory-snapshot` projects the commit-matched public-safe
`egohygiene.observatory.repository-intelligence-read-model/v1` into `/now/`.
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

## Versioning and publication

Relay publishes all cataloged actions together:

- immutable semantic release: `v1.0.0`;
- moving major alias: `v1`;
- recommended consumer reference: full commit SHA.

The current [`release.json`](release.json) manifest requests `v1.2.0`; the
existing `v1.0.0` and `v1.1.0` tags remain immutable. The `Release Relay actions` workflow
also supports manual dispatch. In both cases it validates an unused exact
`vMAJOR.MINOR.PATCH`, verifies the current default-branch commit, creates the
immutable tag and GitHub Release, and then advances the matching major alias.
If tag creation succeeds but release creation is interrupted, a rerun resumes
only when that immutable tag still resolves to the same validated commit.
Subdirectory actions are directly consumable without Marketplace publication;
a future Marketplace entry can improve discovery without changing distribution.
The moving `v1` alias is for discovery and controlled refresh tooling, not for
production consumer workflows.

See [ARCHITECTURE.md](ARCHITECTURE.md) for structural boundaries and
[ROADMAP.md](ROADMAP.md) for extraction and adoption sequencing.
