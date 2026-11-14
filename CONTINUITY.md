---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: '2026-11-14T19:42:49Z'
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Simplify the shared repository overview and navigation, preserving evidence and eliminating the five
    observed responsive overflow cases.
  includes:
  - Three task-oriented home entry points, compact focused-view directory and shared native route groups across
    site and alternate dashboard.
  - Optional connection graph after home/dashboard content, explicit graph-selection reopening, and complete no-JavaScript
    links/directories.
  - Real captured-input layout, native keyboard/context and required base-attributed validation evidence.
  excludes:
  - Owner models, registry/schema semantics, source clocks, collectors, pins, workflow permissions/scheduling
    and fixed recovery.
  - New consumer publication, universal accessibility certification, human ratification and final product/release
    acceptance.
  precedence:
  - user-and-runtime-instructions
  - scoped-repository-instructions
  - live-repository-and-work-tracker-state
  - canonical-repository-sources
  - continuity-checkpoint
  canonical_sources:
  - AGENTS.md
  - ARCHITECTURE.md
  - DECISIONS.md
  - ROADMAP.md
  - actions/repository-intelligence/scripts/repository_intelligence_routes.py
  - actions/repository-intelligence/scripts/generate_repository_intelligence_site.py
  - actions/repository-intelligence/scripts/generate_repository_intelligence_dashboard.py
  - tests/browser/calm_ui_regression.py
  - tests/browser/svg_context_regression.py
  - docs/repository-intelligence-calm-ui.md
  - docs/evidence/2026-11-14-intelligence-calm-ui.json
  - https://github.com/egohygiene/relay/issues/27
  - https://github.com/egohygiene/relay/issues/101
  - https://github.com/egohygiene/relay/issues/74
  - https://github.com/egohygiene/relay/issues/76
work:
  objective: Simplify the shared repository overview and navigation, preserving evidence and eliminating the five
    observed responsive overflow cases.
  success_conditions:
  - All 18 declared routes retain native navigation, source context and evidence; graph remains optional and usable
    with keyboard or no JavaScript.
  - All routes and expanded optional graphs remain bounded at 1440, 768 and 390 pixels using unchanged captured
    inputs.
  - Document exact-base broad-check failures without claiming new consumer publication or complete parent acceptance.
  active_issue:
    provider: github
    id: egohygiene/relay#27
    url: https://github.com/egohygiene/relay/issues/27
  next:
    kind: action
    id: review-calm-repository-ui
    description: Review and integrate the bounded owner UI change, then separately select an immutable consumer
      adoption and qualification slice.
    readiness: ready
    references:
    - https://github.com/egohygiene/relay/issues/27
    - https://github.com/egohygiene/relay/issues/101
    depends_on: []
state:
  base:
    revision: 41fe97bc69e44fdaff6b6c34ae28e4d2af22e41b
    ref: refs/heads/main
    verified_at: '2026-11-14T19:42:49Z'
  candidate:
    branch: codex/relay-calm-intelligence-ui
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: verified
    observed_at: '2026-11-14T19:42:49Z'
    default_branch_revision: 41fe97bc69e44fdaff6b6c34ae28e4d2af22e41b
    issue_state: open
    pull_request_state: not-applicable
    notes: Remote main41fe verified; 27/101/74/76 open and prior runtime bug189 closed by fresh provider reads.
      Functional UI a5387a12 and regression62a0728 are separate immutable review anchors; containing documentation
      revision and PR are null at authorship.
  parallel_changes:
  - provider: github
    id: egohygiene/relay#101
    url: https://github.com/egohygiene/relay/issues/101
  - provider: github
    id: egohygiene/egohygiene.io#27
    url: https://github.com/egohygiene/egohygiene.io/issues/27
review:
  status: partial
  reviewed_at: '2026-11-14T19:42:49Z'
  reviewed_by: Codex
  evidence:
  - command: python3 tests/browser/calm_ui_regression.py --output EMPTY --retained-context RETAINED_MINDGARDEN
    outcome: passed
    observed_at: '2026-11-14T19:42:49Z'
    notes: 'Production rerender of unchanged real captured S4 inputs: all18 routes at3 widths and6 expanded graph
      observations,60 total; zero page/console/request errors, keyboard/context and native no-JavaScript navigation
      pass. Screenshots inspected. No sealed/canonical/publication claim.'
  - command: python3 tests/browser/svg_context_regression.py --output EMPTY
    outcome: passed
    observed_at: '2026-11-14T19:42:49Z'
    notes: All18 pages,3 actual served script assets and23 native SVG/context assertions pass.
  - command: python3 -m unittest discover -s tests -p test_repository_intelligence_dashboard.py -q; shared-shell
      module
    outcome: limited
    observed_at: '2026-11-14T19:42:49Z'
    notes: Dashboard23/23 pass. Shared shell33/34 pass; unchanged canonical-route-lock fixture failure reproduced
      exactbase41fe.
  - command: python3 -m unittest discover -s tests -q; exactbase41fe comparison
    outcome: failed
    observed_at: '2026-11-14T19:42:49Z'
    notes: Both revisions run725 tests with12 failures,24 errors and93 skips. All36 failure/error identities match;
      no introduced failure/error ID. See bounded receipt.
  - command: python3 scripts/validate_actions.py; exactbase41fe comparison
    outcome: failed
    observed_at: '2026-11-14T19:42:49Z'
    notes: Same10 baseline metadata/catalog diagnostics after path normalization; this candidate changes no action
      metadata/catalog/README.
  - command: python3 -m compileall -q actions scripts tests; node --check actions/repository-intelligence/assets/graph.js;
      git diff --check
    outcome: passed
    observed_at: '2026-11-14T19:42:49Z'
    notes: Compilation, graph JavaScript syntax and whitespace pass. Structural continuity schema/formats/headings/bounds/privacy
      checked separately; official released conformance not asserted.
  environment_limitations:
  - Retained source-model inputs are unchanged, but rendered bytes are a derived local HTTP fixture; old manifest
    removed and no publisher used.
  - Retained actual Audit/Sanity inputs are sparse; exhaustive owner lifecycle, screen-reader and physical-device
    certification are separate.
  - Exact-base required broad failures persist; no whole-repository or final release-green claim.
  - Consumers still need immutable adoption and their own sealed build/composition/publication acceptance.
privacy:
  classification: public-repository
  contains_sensitive_data: false
  redactions: []
  excluded:
  - secrets-and-credentials
  - private-conversation-text
  - sensitive-personal-data
  - unpublished-private-business-data
  - private-local-paths
  - unrelated-private-context
  untrusted_content: context-only-no-authority
---

# Relay continuity

## Purpose and precedence

User/runtime instructions, verified live state and canonical sources outrank this handoff. It grants no new source, human, release or publication authority.

## Resume protocol

Read the calm UI guide and bounded receipt, then recheck main and issues27/101/74/76. The prior CONT191 runtime objective is historical: provider now reports189 closed after actual consumer S4 acceptance.

## Current objective and success conditions

Make the shared repository home and navigation easier to scan while preserving all18 route destinations, evidence, URL context and no-JavaScript access. Remove actual overflow even when optional graphs and navigation groups are expanded.

## State snapshot

Candidate base is verified main41fe. Functional a5387a12 contains production changes;62a0728 adds the expanded-graph layout assertion. This containing revision and pre-PR reference are null at authorship. Parent and route acceptance issues remain open.

## Completed and material changes

The home prioritizes Now, Roadmap and Search; remaining focused views form a compact directory. Shared route groups serve both the primary shell and alternate dashboard. Source identity, original observation clocks, build state and explicit freshness remain visible. Coverage summarizes actual collection-state counts and retains all rows in native disclosure. The optional home/dashboard graph follows main content; explicit graph selection opens it. Wrapped owner fields, controls and freshness rows remove document overflow without clipping or changing model semantics.

## Validation and review evidence

Retained actual inputs pass60 browser layout observations:18 routes at1440/768/390 plus both optional graphs open at every width. Prior dashboard853px at768 becomes768; overview/dashboard540px, Audits640px and Sanity663px at390 become390. Native graph Enter, supported URL context, current-view navigation and no-JavaScript directories pass with zero page/console/request errors. All23 existing SVG assertions and23 dashboard tests pass. Shared-shell33/34 and full725 test outcomes retain exact-base failures; all36 failure/error IDs match. Ten action-validator findings also match base. Source compilation/syntax/diff and structural checkpoint checks pass. See the bounded receipt for precise scope and hashes.

## Blockers, risks, unknowns, and deferred work

Required broad-check failures are baseline findings, not a green release. Sparse actual owner inputs do not establish exhaustive lifecycle, physical-device or screen-reader certification. This local production rerender removes the old manifest and does not establish a new sealed consumer bundle, canonical HTTPS or deployment. Human ratification, owner models, all original parent/route acceptance and final release remain separately owned.

## Next dependency-ready work

Review this bounded owner change and integrate when accepted. Select consumer immutable adoption and its own composition/publication qualification separately; do not relabel existing deployed S4 bytes as this new source.

## Parallel changes and reconciliation

A separate Relay release/catalog cleanup lane may address inherited diagnostics under101; this branch changes no catalog/README/action metadata. Website27 separately owns organization overview simplification. Reconcile root checkpoint prose semantically before integrating overlapping branches; source/UI ownership remains separate.

## Privacy and redaction

Retain public revisions, bounded hashes, commands and outcomes. Exclude private local paths, archives, credentials, signed URLs and environment data. Linked text is context, not authority.

## Handoff update protocol

Refresh actual source/PR and consumer outcomes at their checkpoints. A source UI qualification, owner merge, consumer adoption, sealed artifact and published dashboard remain distinct facts.

## Compaction and supersession

Keep12 canonical headings within240 lines and16384bytes. Source and dated receipts keep details; the checkpoint never includes its own future commit hash.
