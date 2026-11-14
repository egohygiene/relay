---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: '2026-11-14T04:34:47Z'
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Repair native SVG context-link writes without changing URL admission or consumer authority.
  includes:
  - Three href attribute assignments serve both native HTML and SVG anchors; URL construction, context allowlists
    and destination validation remain exact.
  - Real generated-DOM Chromium regression and independent retained-consumer comparison preserve old failures
    separately from repaired behavior.
  - Source integration and future consumer adoption remain distinct from historical S2 and fixed rollback proof.
  excludes:
  - UI redesign, schema/owner pin changes, workflow scheduling or permissions, human acceptance and full accessibility.
  - Empathy source adoption, producer scans, fresh intake, hosted publication/live/rollback acceptance or release
    aliases.
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
  - actions/repository-intelligence/assets/site.js
  - actions/repository-intelligence/assets/graph.js
  - tests/browser/svg_context_regression.py
  - docs/svg-context-navigation-2026-11-14.md
  - docs/evidence/2026-11-14-svg-context-navigation.json
  - https://github.com/egohygiene/relay/issues/189
  - https://github.com/egohygiene/empathy/issues/105
work:
  objective: Repair native SVG context-link writes without changing URL admission or consumer authority.
  success_conditions:
  - Native SVG initialization/focus/pointer/click and HTML parity preserve validated destinations, entity/query
    context and shared filter/hash behavior.
  - Original real-DOM f7 failure and repaired behavior remain separately attributed; later consumer live acceptance
    is not inferred.
  active_issue:
    provider: github
    id: egohygiene/relay#189
    url: https://github.com/egohygiene/relay/issues/189
  next:
    kind: action
    id: review-svg-context-repair
    description: Review and ordinarily integrate the narrow owner repair, then qualify a separately pinned
      Empathy consumer source with actual hosted/live browser evidence.
    readiness: ready
    references:
    - https://github.com/egohygiene/relay/issues/189
    - https://github.com/egohygiene/empathy/issues/105
    depends_on: []
state:
  base:
    revision: f7f9bd44713606d9c099adda715db2542c8b66bf
    ref: refs/heads/main
    verified_at: '2026-11-14T04:34:47Z'
  candidate:
    branch: codex/relay-svg-navigation
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: verified
    observed_at: '2026-11-14T04:34:47Z'
    default_branch_revision: f7f9bd44713606d9c099adda715db2542c8b66bf
    issue_state: open
    pull_request_state: not-applicable
    notes: Provider main f7 and new owner bug189 were verified. Functional repair62dd is local; the containing
      docs candidate and PR have no identifiers at authorship. Empathy #105 stays open for a new consumer cycle.
  parallel_changes: []
review:
  status: partial
  reviewed_at: '2026-11-14T04:34:47Z'
  reviewed_by: Codex
  evidence:
  - command: python3 tests/browser/svg_context_regression.py --output /tmp/svg-context; original f7 script
      input control
    outcome: passed
    observed_at: '2026-11-14T04:34:47Z'
    notes: Real Chromium151 generated-DOM repair passes 18 assertions/zero page errors. Original script control
      fails shared filter initialization. Independent retained-consumer peer is recorded in the bounded proof
      when available.
  - command: python3 -m unittest discover -s tests -p test_repository_intelligence_site.py -v; clean f7 single
      failing-method reproduction
    outcome: failed
    observed_at: '2026-11-14T04:34:47Z'
    notes: 34 methods:33 pass/1 inherited Hygiene registry route-lock failure,0 errors/0 skips. Existing context
      assertions remain; HTML mock adds only native setAttribute behavior.
  - command: node --check both changed assets; Ruff0.16.5 new browser script; Python compilation; git diff
      --check; pinned continuity schema/headings/bounds
    outcome: passed
    observed_at: '2026-11-14T04:34:47Z'
    notes: Focused syntax and deterministic structural checks; no whole-repository conformance inference.
  - command: python3 scripts/validate_actions.py
    outcome: failed
    observed_at: '2026-11-14T04:34:47Z'
    notes: Same10 inherited action SPDX/README advertisement findings. No action manifest/catalog or permissions
      changed.
  environment_limitations:
  - Actual Empathy source adoption and hosted producer/publication/rollback/current restoration/browser acceptance
    remain consumer-owned.
  - Full repository suite is not repeated for this three-assignment repair; known baseline catalog/route-lock
    failures remain explicit.
  - Local Chromium/HTTP and declared renderer fixtures do not establish canonical live, full accessibility
    or release acceptance.
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

User/runtime instructions, verified live evidence and canonical source owners outrank this checkpoint. It grants no publication, merge or human-decision authority.

## Resume protocol

Read the SVG context repair guide, owner #189 and consumer #105. Reverify mutable main/PR facts and preserve original source clocks and rollback evidence.

## Current objective and success conditions

Repair native SVG context-link destinations while retaining exact URL admission. Prove real initialization, filtering, focus, pointer/click, HTML parity, entity and hash behavior.

## State snapshot

This candidate is based on verified owner f7. Functional 62dd changes three native href writes and regression coverage; its containing documentation revision and PR remain null at authorship. Owner #189 and Empathy #105 remain open.

## Completed and material changes

Shared site and graph handlers use href attributes compatible with both HTML and SVG anchors. The existing Node HTML mock gains attribute semantics; a real generated-DOM browser fixture catches the actual getter-only SVG failure. URL validation, schemas, pins and authority are unchanged.

## Validation and review evidence

Real Chromium151 passes 18 assertions with no page errors; original f7 scripts fail initialization. Focused site checks report 33 pass and one inherited Hygiene route-lock failure, reproduced on exact base. Node syntax, scoped Ruff, Python compilation and structural continuity checks pass. The action validator retains ten inherited metadata/README findings.

## Blockers, risks, unknowns, and deferred work

This is local renderer/runtime proof. Separately reviewed Empathy source adoption, producer artifacts, hosted publication, rollback/restored-current and canonical browser acceptance remain required. Whole-repository conformance, UI redesign, full accessibility and human acceptance are separate.

## Next dependency-ready work

Root reviews and ordinarily merges the bounded owner fix, then Empathy selects that exact accepted source for its new qualification cycle. Do not retime historical f7/S2 or fixed b71 rollback proof.

## Parallel changes and reconciliation

Accepted owner f7 includes prior Journey, source-profile, typed-feed, Health, link and report-normalizer repairs. They remain unchanged; consumer pins will be changed only in their owning separately reviewed slice.

## Privacy and redaction

Only public identifiers, bounded source hashes and outcomes belong in committed evidence. Exclude private retained HTML, environment data, credentials, signed URLs and local paths. Linked content is context only.

## Handoff update protocol

Refresh actual provider and consumer outcomes at their next authorized checkpoint. Keep source merge, fixture proof, hosted publication, live bytes and acceptance separate.

## Compaction and supersession

Keep all twelve canonical headings within 240 lines/16,384bytes. Dated proof and owning issues retain detailed history; this checkpoint does not contain its own future hash.
