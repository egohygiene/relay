# Changelog

All notable changes to Relay are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and Relay uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- A hardened Repository Intelligence artifact workflow contract covering
  trusted and fork pull requests, default-branch and manual rebuilds,
  cache-free read-only execution, workflow-path/ref-scoped cancellation,
  revision-scoped site artifacts, and fixed 30-day sanitized success or
  actionable-failure evidence.
- A proposed, advisory-first repository-architecture validation profile with
  immutable Hygiene, EgoLint, and Holon inputs; closed local/CI request and
  result contracts; bounded privacy-safe fixtures; and explicit planned or
  unavailable diagram coverage.
- A versioned CI run lifecycle contract and reusable report-preservation action
  with explicit cancellation classes, stable `.reports/<producer>` paths,
  bounded checksummed manifests, failure-safe upload, and retention policy.
- A reusable evidence-bound repository journal with deterministic and
  reviewed-manual no-billing modes, a separately permissioned future Copilot
  adapter, pinned Aether rendering, explicit incomplete states, and Relay
  scheduled/manual dogfood.
- A reusable artifact-budget action and workflow with Size Limit JSON and
  filesystem adapters, absolute and baseline-relative thresholds, explicit
  advisory or blocking enforcement, and deterministic machine-readable reports.
- An advisory-first stale pull-request action and reusable workflow with
  explicit exemptions, checksum-bound plans, mandatory visible warnings,
  optional delayed closure, bounded summaries, and reopen recovery.
- A documented quarantine and graduation lifecycle for legacy GitHub Actions,
  with inert provenance evidence and executable guards against accidental
  activation or catalog inclusion.
- A bounded `release-name` input that keeps product-facing archive, tag, and
  GitHub Release names separate from Relay's artifact-class validation profile.

### Changed

- Repository Intelligence now distinguishes its overview from `/now/`, exposes
  every supporting route as a public action output, carries applicable URL
  context across views, and pins the Hygiene repository-route registry.
- Relay dogfood releases now use `relay` as their explicit product-facing name.

### Fixed

- Repository Intelligence isolates checkout-context inline Python from
  caller-controlled module shadowing before parsing timestamps or provenance.
- CI report preservation rejects symbolic-link path components before creating
  directories and can preserve pre-created evidence only from real directories
  beneath the runner's temporary root.
- Repository Intelligence snapshots may omit optional Health and Work queries
  without failing the whole site, and Compare can render structural evidence
  before the optional Search projection is adopted.
- Repository Intelligence now labels missing route projections as unknown,
  exposes every projected record state to filtering, keeps carried filters from
  blanking the overview, and announces restored entity context accessibly.
- Deterministic repository journals now select a breadth-first bounded summary
  and report candidate truncation as partial instead of failing when live
  provider evidence exceeds the configured item or byte ceiling.

## [1.5.0] - 2026-09-12

### Added

- Reusable read-only semantic-release planning and prepared-candidate verification.
- Durable success and failure evidence for release preparation and publication handoffs.
- Aether release-declaration, changelog, Taskfile, and version-authority dogfooding.
- Python-package and Cargo-crate release evidence profiles.
- Canonical organization label synchronization with reviewable, checksum-bound
  plans and explicit deletion authority.
- Shared and repository-overridable path labels, size labels, first-contributor
  welcomes, and fork maintainer-edit checks through a read-only planner and
  independently recomputed trusted apply handoff.
- Reusable read-only repository continuity pull-request preflight with pinned
  EgoLint acquisition, bounded annotations and artifacts, and Relay dogfood.

### Changed

- Relay publication now requires an explicit manual default-branch dispatch and
  delegates immutable release creation through the profile-bound release surface.
- Profile-bound publication accepts exact SemVer `v0.x.y` candidates while
  continuing to reject numeric identifiers with leading zeroes.

### Fixed

- The release-bundle action resolves its bundled profile catalog at composite
  runtime when callers omit the optional path override.

## [1.4.0] - 2026-08-31

### Added

- Versioned immutable release profiles for binaries, containers, GitHub Actions,
  npm specifications, PDF/A publications, and static sites.

[Unreleased]: https://github.com/egohygiene/relay/compare/v1.5.0...HEAD
[1.5.0]: https://github.com/egohygiene/relay/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/egohygiene/relay/releases/tag/v1.4.0
