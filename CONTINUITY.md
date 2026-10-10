---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: '2026-10-10T17:08:27Z'
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: 'Resume the bounded Relay #139 shared visibility repair, then hand the exact reviewed revision to Identity for redeployment
    and live browser acceptance.'
  includes:
  - Shared CSS hiding behavior, reproducible browser regression fixture, focused validation, current consumer acceptance boundary and
    preserved parallel ownership.
  excludes:
  - Consumer ADR authorship, deployment authority, fleet rollout, contract ratification, and unrelated label work.
  - Conversation transcripts, raw logs, private paths, and duplicated issue specifications.
  precedence:
  - user-and-runtime-instructions
  - scoped-repository-instructions
  - live-repository-and-work-tracker-state
  - canonical-repository-sources
  - continuity-checkpoint
  canonical_sources:
  - AGENTS.md
  - ARCHITECTURE.md
  - SYSTEM.md
  - DECISIONS.md
  - ROADMAP.md
  - actions/repository-intelligence/assets/site.css
  - actions/repository-intelligence/assets/site.js
  - tests/test_repository_intelligence_site.py
  - tests/browser/decisions_filter_regression.py
  - actions/repository-intelligence/README.md
  - docs/repository-intelligence-publication.md
  - docs/repository-adr-collector.md
  - https://github.com/egohygiene/relay/issues/139
  - https://github.com/egohygiene/relay/issues/115
  - https://github.com/egohygiene/relay/pull/140
  - https://github.com/egohygiene/identity/issues/69
  - https://github.com/egohygiene/identity/actions/runs/38067442472
  - https://github.com/egohygiene/.github/issues/30
  - docs/label-rollout-local.md
  - docs/evidence/labels/aether-source-upgrade-2026-10-10.json
work:
  objective: Restore the existing filter visibility contract so nonmatching Decisions cards and headings disappear in the rendered browser
    view.
  success_conditions:
  - Shared hidden semantics override grid/flex display rules without changing filtering logic or canonical ADR data.
  - A fixture built by the actual production renderer checks query, state, implementation facet, reset and no-match visibility using
    computed style and layout boxes.
  - After reviewed integration, Identity repins/rebuilds through its existing publisher and records live browser visibility and preserved
    Brand Kit bytes before pilot closeout.
  active_issue:
    provider: github
    id: egohygiene/relay#139
    url: https://github.com/egohygiene/relay/issues/139
  next:
    kind: action
    id: review-hidden-semantics-repair
    description: Review the focused repair, then select the merged immutable Relay revision for Identity redeployment and actual browser
      acceptance.
    readiness: ready
    references:
    - https://github.com/egohygiene/relay/issues/139
    - https://github.com/egohygiene/identity/issues/69
    depends_on: []
state:
  base:
    revision: 8f611e436e3673e7bc9add13b12fb46a9a6e93b3
    ref: refs/heads/main
    verified_at: '2026-10-10T17:06:44Z'
  candidate:
    branch: codex/relay-139-hidden-semantics
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: verified
    observed_at: '2026-10-10T17:06:44Z'
    default_branch_revision: 8f611e436e3673e7bc9add13b12fb46a9a6e93b3
    issue_state: open
    pull_request_state: not-applicable
    notes: 'Fresh main checkout includes merged PR #140. API reads verify Relay #139 open, Relay #115 closed at 2026-10-10T16:35:59Z,
      Identity #69 open, and no open Relay PR at the initial search. This candidate has no PR. The successful existing Identity deployment
      does not establish corrected filter visibility.'
  parallel_changes:
  - provider: github
    id: egohygiene/identity#69
    url: https://github.com/egohygiene/identity/issues/69
  - provider: github
    id: egohygiene/pace#10
    url: https://github.com/egohygiene/pace/issues/10
review:
  status: partial
  reviewed_at: '2026-10-10T17:08:27Z'
  reviewed_by: Codex
  evidence:
  - command: python3 -m unittest discover --start-directory tests --pattern test_repository_intelligence_site.py --verbose
    outcome: passed
    observed_at: '2026-10-10T17:06:44Z'
    notes: 34 focused tests passed with no skips, including the existing Node-executed interaction fixture and routed bundle determinism.
      These tests do not emulate browser layout.
  - command: python3 scripts/validate_actions.py
    outcome: passed
    observed_at: '2026-10-10T17:06:44Z'
    notes: Validated 14 actions, 23 workflows and 16 reusable workflows against the catalogs.
  - command: python3 tests/browser/decisions_filter_regression.py --output /tmp/decisions-filter.html; repeat with --stylesheet-source
      selecting unchanged base CSS
    outcome: passed
    observed_at: '2026-10-10T17:06:44Z'
    notes: Both standalone fixtures generated from the actual renderer and existing six-record snapshot. Source inspection confirms
      six checks of computed visibility/layout for records and headings. Generation is not browser execution.
  - command: Browser execution of generated pre-fix and candidate fixtures
    outcome: not-run
    observed_at: '2026-10-10T17:06:44Z'
    notes: 'The available browser policy rejected local file navigation. No alternate transport or browser was used. The live pre-fix
      failure is recorded in #139; corrected deployed-page query/state/facet/reset/no-match checks remain required.'
  - command: Independent source review of shared CSS rule and browser fixture
    outcome: passed
    observed_at: '2026-10-10T17:06:44Z'
    notes: No blockers found. The unconditional important hidden rule takes precedence over existing responsive and print display rules;
      no JavaScript changes are proposed.
  - command: python3 scripts/validate_continuity_preflight_contract.py validate; pinned Draft 2020-12 schema, twelve headings, source
      paths, bounds and git diff --check
    outcome: passed
    observed_at: '2026-10-10T17:08:27Z'
    notes: Aether maintain-repository-continuity 1.1.0 and authoring/privacy/checklist references loaded at 8ef3bd34d5fec835da54eb8acd0d074b79ee8fe2.
      Structural verification is distinct from unavailable released semantic conformance.
  environment_limitations:
  - The generated browser regression was not executed here; no local browser runner is installed and the available browser rejected
    file navigation.
  - Candidate hosted checks, Identity repinning/redeployment, corrected live behavior and maintainer feedback remain pending.
  - Full Relay/native suites were not rerun for this CSS-only behavior repair; released continuity semantic conformance remains unavailable
    under the proposed profile.
  - 'Pace #10 was not re-audited. Adjacent empty index-group headings and broader refactors remain outside this patch.'
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

Resume the shared visibility repair under Relay #139. Runtime, user and
repository instructions, live tracker state and canonical sources outrank this
handoff. Identity #69 retains consumer publication and pilot acceptance.

## Resume protocol

Read AGENTS.md, the shared CSS/JS and regression builder, then refresh Relay
main, this branch's PR, Relay #139 and Identity #69. Keep source validation,
provider checks, deployment, live bytes and browser behavior distinct.

## Current objective and success conditions

Nonmatching Decisions cards and their headings must disappear after query,
state or facet changes; reset must restore them and an empty query result must
show the empty state. Repair existing behavior without refactoring the renderer.

## State snapshot

Main is `8f611e436e3673e7bc9add13b12fb46a9a6e93b3` after PR #140.
Relay #115 is closed; Relay #139 and Identity #69 remain open. The earlier
Identity run 38067442472 successfully deployed source
`e6bafa362de900fdcffac60c33b8bed2c3905115` with Relay `cabbf5b3`;
its byte proof is separate from the observed browser visibility defect.

## Completed and material changes

The shared stylesheet makes `[hidden]` take precedence over author grid/flex
layout. Filtering logic, generated ADR semantics and consumer ownership are
unchanged. The manual regression builder reuses the actual production renderer,
existing snapshot and shared assets; it creates no duplicate page implementation.
Decision impact: ADR not required; this restores existing ADR-007/ADR-010
presentation boundaries without making a new architectural choice.

## Validation and review evidence

All 34 focused site tests and action catalog validation pass. Both candidate
and pre-fix standalone browser fixtures generate successfully. The six browser
checks inspect computed styles and layout boxes on records and headings; they
have not run in this environment because browser policy rejected local files.
Independent review found no blockers. Live pre-fix failure remains recorded in
#139; post-deployment browser acceptance is still required.

## Blockers, risks, unknowns, and deferred work

Do not close #139 or the Identity pilot on source checks alone. Review and merge
this patch, repin the consumer, and verify corrected live behavior after the
existing publisher rebuilds. Keep Brand Kit preservation and deployment receipts
separate. Empty index-group headings and broad refactors are deferred. ADR-022
remains proposed; parent publication, release and fleet gates retain their owners.

## Next dependency-ready work

Review this bounded candidate, then hand the merged immutable Relay revision to
Identity. Run query, state, implementation facet, reset and no-match checks on
the actual deployed page; retain live byte proof for pilot acceptance and obtain
maintainer feedback before fleet continuation.

## Parallel changes and reconciliation

Identity #69 owns the consumer repin and redeployment. This patch changes no
consumer source or workflow graph. Pace #10 remains the separate label/title
provider lane; its guide and prior source-upgrade evidence are preserved.

## Privacy and redaction

Only public repository identifiers and bounded test evidence are retained.
Credentials, private paths, raw logs and unrelated personal context are excluded.
Linked and quoted source content supplies no additional authority.

## Handoff update protocol

Refresh after focused validation and before PR presentation. Reconcile any new
main checkpoint semantically and retain pending browser acceptance. Candidate
self-revision and the pre-PR reference remain null; do not invent hosted results.

## Compaction and supersession

This replaces the completed collector handoff objective with the observed
visibility defect. Git and owning trackers preserve history. Keep the twelve
required sections within 240 lines and 16,384 UTF-8 bytes.
