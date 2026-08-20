# Relay actions

Relay is a monorepo of composable GitHub Actions. Every first-level directory
under `actions/` is a complete public action package with its own manifest,
documentation, implementation, contracts, and tests.

| Action                                                        | Capability                                                  | Side effects                  |
| ------------------------------------------------------------- | ----------------------------------------------------------- | ----------------------------- |
| [`repository-intelligence`](repository-intelligence/)         | Build a static repository dashboard                         | Workspace files only          |
| [`normalize-repository-report`](normalize-repository-report/) | Normalize OSV, MegaLinter, and Scorecard producer summaries | Workspace files only          |
| [`publish-report-snapshot`](publish-report-snapshot/)         | Guard and publish stable `.reports` snapshots               | Git commit and default-branch push |

## Consumption

Subdirectory actions are directly consumable from a public GitHub repository;
they do not require separate packages or Marketplace listings. Their package
paths are:

```text
egohygiene/relay/actions/repository-intelligence
egohygiene/relay/actions/normalize-repository-report
egohygiene/relay/actions/publish-report-snapshot
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

The reviewed root `release.json` manifest or a manual dispatch triggers the
release workflow. It validates the complete catalog and test suite, creates the
immutable SemVer tag and GitHub Release, and then advances the selected major
alias. It refuses non-default branches and any existing immutable tag that
targets a different commit; matching partial releases can be resumed safely.
