---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: "2026-09-16T13:46:00Z"
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Preserve the minimum verified state needed to review the third bounded REL-RI-006 supporting-view checkpoint.
  includes:
    - Repository Intelligence Releases-route issue, pull request, and exact candidate state.
    - Accepted Observatory Releases query boundary and rendering constraints.
    - Merged Dependencies and Work checkpoints plus next supporting-view dependencies.
    - Roadmap impact, ADR impact, validation evidence, and next dependency-ready action.
  excludes:
    - Conversation transcripts, duplicated architecture history, unrelated release automation, package-distribution semantics, and organization-level semantics not accepted upstream.
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
    - actions/repository-intelligence/action.yml
    - actions/repository-intelligence/scripts/generate_repository_intelligence_site.py
    - actions/repository-intelligence/scripts/render_repository_intelligence_dependencies.py
    - actions/repository-intelligence/scripts/render_repository_intelligence_releases.py
work:
  objective: Materialize Repository Intelligence /releases/ from Observatory's accepted Releases query without inventing distribution, installability, rollback, velocity, or unreleased-work semantics.
  success_conditions:
    - Render canonical release identity and publication time from normalized evidence.
    - Keep included entities, deployments, and release-boundary event IDs distinct.
    - Keep unavailable and empty Releases evidence distinct and explicit.
    - Preserve useful static HTML while reusing the shared shell and filters.
    - Keep Repository Intelligence generation and public bundle validation green.
  active_issue:
    provider: github
    id: egohygiene/relay#81
    url: https://github.com/egohygiene/relay/issues/81
  next:
    kind: pull-request
    id: egohygiene/relay#82
    description: Review and merge the validated bounded /releases/ implementation if acceptable.
    readiness: ready-for-review-after-final-head-ci
    references:
      - https://github.com/egohygiene/relay/issues/81
      - https://github.com/egohygiene/relay/pull/82
      - https://github.com/egohygiene/relay/issues/29
      - https://github.com/egohygiene/observatory/issues/7
      - https://github.com/egohygiene/observatory/issues/13
    depends_on: []
state:
  base:
    revision: 515bb4b509dd73934fdd05e83b19bf979ec33a15
    ref: refs/heads/main
    verified_at: "2026-09-16T13:37:00Z"
  candidate:
    branch: feat/81-repository-intelligence-releases
    implementation_revision: e350e79f72aec4af0c043322858236577be63c6d
    pull_request: https://github.com/egohygiene/relay/pull/82
    handoff_state: ready-for-review-after-final-head-ci
  live:
    status: verified
    observed_at: "2026-09-16T13:46:00Z"
    default_branch_revision: 515bb4b509dd73934fdd05e83b19bf979ec33a15
    dependencies_checkpoint:
      issue: egohygiene/relay#77
      pull_request: egohygiene/relay#78
      state: merged
    work_checkpoint:
      issue: egohygiene/relay#79
      pull_request: egohygiene/relay#80
      state: merged
    releases_checkpoint:
      issue: egohygiene/relay#81
      pull_request: egohygiene/relay#82
      state: open
    notes: Observatory #7 already owns Releases, Search, and Compare queries. Health remains only partially represented by the accepted core graph while fleet Hygiene/conformance remains owned by Observatory #5. Organization Roadmap remains gated by Hygiene #60 and Observatory #22.
review:
  status: complete-for-implementation-revision
  reviewed_at: "2026-09-16T13:46:00Z"
  reviewed_by: ChatGPT
  evidence:
    - command: Verify Relay main, AGENTS.md, ARCHITECTURE.md, SYSTEM.md, DECISIONS.md, ROADMAP.md, CONTINUITY.md, parent #29, and merged #80.
      outcome: passed
      notes: REL-RI-006 is active; Dependencies and Work are merged supporting-view slices.
    - command: Inspect Observatory Repository Intelligence read-model documentation and accepted Releases fixture.
      outcome: passed
      notes: Releases records contain release entity, published_at, includes, deployments, and boundary_event_ids; Relay does not own distribution semantics.
    - command: Add bounded Releases renderer, compose it through the existing supporting-view entry point, and add focused tests.
      outcome: passed
      notes: Dependencies, Work, and Releases render from the same repository- and commit-matched snapshot without a new collection path.
    - command: GitHub Actions Validate Relay actions run 35103865202, run 59, on e350e79f72aec4af0c043322858236577be63c6d.
      outcome: passed
      notes: Full unit/integration tests, action/catalog and continuity-contract validation, Python compilation, Bash and inline-shell syntax, JSON/YAML parsing, caller-owned publication fixture, reusable Repository Intelligence generation/provenance, publication review, and reviewed-byte preservation all passed.
    - command: GitHub Actions Relay continuity preflight run 35103865476, run 13.
      outcome: passed
      notes: Shared continuity adapter and bounded evidence path passed on the implementation candidate.
    - command: GitHub Actions Dependency review run 35103865132, run 20.
      outcome: passed
      notes: Dependency review passed; the Dependabot-only automerge workflow skipped as expected.
  environment_limitations:
    - Direct GitHub network access from the local shell is unavailable; repository reads, writes, and validation status use the connected GitHub integration.
roadmap_impact:
  disposition: no-state-transition
  rationale: REL-RI-006 is already active and explicitly owns Releases. Issue #81 is a bounded implementation child; accepting it adds delivery evidence but does not complete the broader supporting-view quest. Merge evidence should be appended to REL-RI-006 after acceptance.
adr_impact:
  disposition: none
  rationale: The change implements ADR-007's existing Observatory-normalization and Relay-presentation boundary without changing authority or dependency direction.
privacy:
  classification: public-repository
  contains_sensitive_data: false
  redactions: []
---

# Relay continuity

## Current checkpoint

Issue #81 implements the third bounded `REL-RI-006` supporting view: `/releases/`.
The accepted Observatory Releases query supplies release identity, publication
time, included entities, associated deployments, and release-boundary event IDs.

Relay presents those records; it does not infer package-manager publication,
installability, rollback support, release quality, delivery velocity, or
unreleased work.

## Candidate implementation

Branch: `feat/81-repository-intelligence-releases`

Implementation revision:
`e350e79f72aec4af0c043322858236577be63c6d`

Pull request: https://github.com/egohygiene/relay/pull/82

The implementation:

- keeps the existing supporting-view action invocation stable;
- renders `/dependencies/`, `/work/`, then `/releases/` from the same accepted snapshot;
- highlights the latest projected publication without changing Observatory's deterministic record order;
- keeps release publication, included evidence, deployments, and boundary IDs visibly separate;
- deep-links releases, included entities, and deployment evidence to canonical sources;
- distinguishes missing Releases evidence from an explicitly empty Releases query;
- fails closed for malformed entity kinds, URLs, timestamps, duplicate IDs, and incompatible shapes;
- adds deterministic, static-first, stale/unknown, malformed-input, empty/unavailable, and accessibility-oriented tests.

## Validation evidence

On implementation revision `e350e79f72aec4af0c043322858236577be63c6d`:

- `Validate Relay actions` run 35103865202 / #59 passed its complete chain.
- `Relay continuity preflight` run 35103865476 / #13 passed.
- `Dependency review` run 35103865132 / #20 passed.
- Dependabot automerge skipped as expected for a non-Dependabot pull request.

This continuity-only checkpoint creates a new final PR head. Verify the same
required workflows on that exact head before merge.

## Roadmap and decision reconciliation

`REL-RI-006` remains active. Dependencies (#77/#78) and Work (#79/#80) are merged;
Releases (#81/#82) is the current candidate. No roadmap state transition is
appropriate because Health, Search, Compare, deterministic publication, and
organization aggregation remain broader work.

No new ADR is required. This implementation follows ADR-007: Observatory owns
normalized truth; Relay owns static route composition and validated artifacts.

## Blockers and deferred work

- No implementation blocker remains for `/releases/`; only final-head CI and review remain.
- Package-manager availability and install verification remain owned by the distribution program and Observatory #13.
- `/health/` must not absorb unfinished fleet-conformance semantics from Observatory #5.
- `/audits/`, `/hygiene/`, and `/sanity/` remain gated by their normalized owner contracts.
- Organization `/roadmap/` remains gated by Hygiene #60 and Observatory #22.

## Next dependency-ready work

After #82 merges, re-fetch Relay #29 and the upstream models. Prefer `/search/`
next because Observatory #7 already supplies a normalized, public-safe Search
query. `/compare/` is also contract-ready and should follow unless live state
changes. Keep `/health/` bounded to accepted check/freshness evidence until its
broader conformance dependencies land.

## Resume protocol

1. Verify newest Relay `main`, issue #81, PR #82, and exact-head checks.
2. Re-read parent #29 and `REL-RI-006` before selecting another view.
3. Do not duplicate a route with an open implementation PR.
4. Keep one bounded supporting-view checkpoint per PR.
5. Reconcile this continuity checkpoint before every handoff.
