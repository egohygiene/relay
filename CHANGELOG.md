# Changelog

All notable changes to Relay are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and Relay uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- An advisory-first stale pull-request action and reusable workflow with
  explicit exemptions, checksum-bound plans, mandatory visible warnings,
  optional delayed closure, bounded summaries, and reopen recovery.
- A documented quarantine and graduation lifecycle for legacy GitHub Actions,
  with inert provenance evidence and executable guards against accidental
  activation or catalog inclusion.
- A bounded `release-name` input that keeps product-facing archive, tag, and
  GitHub Release names separate from Relay's artifact-class validation profile.

### Changed

- Relay dogfood releases now use `relay` as their explicit product-facing name.

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
