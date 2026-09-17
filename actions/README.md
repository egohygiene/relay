# Relay actions

Relay is a monorepo of composable GitHub Actions. Every first-level directory
under `actions/` is a complete public action package with its own manifest,
documentation, implementation, contracts, and tests.

| Action                                                        | Capability                                                  | Side effects                  |
| ------------------------------------------------------------- | ----------------------------------------------------------- | ----------------------------- |
| [`artifact-budget`](artifact-budget/)                         | Normalize bounded filesystem or Size Limit evidence and evaluate absolute or baseline-relative budgets | Workspace report only |
| [`repository-continuity-preflight`](repository-continuity-preflight/) | Run pinned offline continuity validation and normalize evidence | Workspace evidence only |
| [`repository-intelligence`](repository-intelligence/)         | Build operational, roadmap, decision, and journey Repository Intelligence views | Workspace files only          |
| [`repository-labels`](repository-labels/)                     | Plan and apply canonical labels and pull-request metadata   | Optional repository metadata writes |
| [`stale-pull-requests`](stale-pull-requests/)                 | Plan and apply warning-first stale pull-request lifecycle transitions | Optional labels, comments, and closure |
| [`normalize-repository-report`](normalize-repository-report/) | Normalize OSV, MegaLinter, and Scorecard producer summaries | Workspace files only          |
| [`publish-report-snapshot`](publish-report-snapshot/)         | Guard and publish stable `.reports` snapshots               | Git commit and default-branch push |
| [`validate-publication-site`](validate-publication-site/)     | Validate product-owned publication hub bytes and checksums  | Workspace evidence only       |
| [`verify-publication-pages`](verify-publication-pages/)       | Prove deployed HTTPS publication bytes and routes           | Network reads and workspace evidence |
| [`validate-release-bundle`](validate-release-bundle/)         | Validate release profiles, checksums, and immutable evidence | Workspace evidence only              |
| [`verify-release-plan`](verify-release-plan/)                 | Verify semantic-release intent and prepared profile evidence | Git reads and workspace evidence      |

## Consumption

Subdirectory actions are directly consumable from a public GitHub repository;
they do not require separate packages or Marketplace listings. Their package
paths are:

```text
egohygiene/relay/actions/repository-intelligence
egohygiene/relay/actions/repository-labels
egohygiene/relay/actions/stale-pull-requests
egohygiene/relay/actions/normalize-repository-report
egohygiene/relay/actions/publish-report-snapshot
egohygiene/relay/actions/validate-publication-site
egohygiene/relay/actions/verify-publication-pages
egohygiene/relay/actions/validate-release-bundle
egohygiene/relay/actions/verify-release-plan
```

GitHub Marketplace is a discovery surface, not the distribution mechanism for
these packages. Consumers resolve the Relay repository ref and the action path.

For production workflows, pin the complete immutable Relay commit SHA and keep
the semantic release in a comment:

```yaml
- name: Build repository intelligence
  # egohygiene/relay repository-intelligence v1.1.0
  uses: egohygiene/relay/actions/repository-intelligence@0123456789abcdef0123456789abcdef01234567
```

## Release policy

Relay versions the repository as one tested unit. A release publishes every
action and reusable workflow at the same exact commit.

- `v1.2.3` is immutable.
- `v1` is a moving convenience alias updated only after validation.
- Full commit SHA is the recommended consumer pin.
- `action-catalog.json` is the machine-readable inventory for documentation,
  release validation, Holon installation, and future Pace reconciliation.

Moving aliases support discovery and controlled fleet refreshes. Production
consumer workflows use reviewed full-SHA pins so an implementation update
cannot enter a repository silently.

The reviewed root `release.json`, Aether declaration, and `CHANGELOG.md` are
verified by the read-only semantic-release gate. Explicit manual dispatch then
builds a profile bundle and invokes the reusable immutable publication handoff.
It refuses non-default branches and any existing immutable tag that targets a
different commit; matching partial releases can be resumed safely.
