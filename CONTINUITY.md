---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: '2026-09-26T19:38:30Z'
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: 'Hand off the bounded Relay #112 roadmap collector checkpoint; prioritize the ADR/Decisions fleet
    campaign next.'
  includes:
  - Immutable roadmap collection, pinned validators/normalizer, denied-publication review evidence, native
    fixtures and documented blockers.
  excludes:
  - Action/workflow integration, canonical consumer source changes, deployment, release and merge.
  - ADR backfill implementation and duplicated issue specifications.
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
  - docs/repository-roadmap-collector.md
  - actions/repository-intelligence/contracts/roadmap-collector.v1.lock.json
  - https://github.com/egohygiene/relay/issues/112
  - https://github.com/egohygiene/observatory/issues/25
  - https://github.com/egohygiene/relay/issues/99
  - https://github.com/egohygiene/pace/issues/5
  - https://github.com/egohygiene/pace/issues/31
work:
  objective: Review the bounded collector without promoting incomplete source evidence into a publishable snapshot.
  success_conditions:
  - Preserve real Akashic source IDs, intent, criteria and dependencies with owning-validator diagnostics.
  - Reproduce complete review envelopes across checkout paths and reject unsafe inputs.
  - Keep uncollected domains and the upstream publication blocker explicit.
  active_issue:
    provider: github
    id: egohygiene/relay#112
    url: https://github.com/egohygiene/relay/issues/112
  next:
    kind: action
    id: relay-99-checkpoint-1
    description: 'After review of this bounded checkpoint, reconcile Relay #99 checkpoint 1 for the maintainer-selected
      ADR/Decisions campaign in Pace #5. Roadmap rollout follows that campaign.'
    readiness: ready
    references:
    - https://github.com/egohygiene/relay/issues/99
    - https://github.com/egohygiene/pace/issues/5
    depends_on: []
state:
  base:
    revision: 13f22cb67ae7f2b922e0c75de966610802201bdb
    ref: refs/heads/main
    verified_at: '2026-09-26T19:38:30Z'
  candidate:
    branch: feat/roadmap-evidence-collector-112
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: partial
    observed_at: '2026-09-26T19:38:30Z'
    default_branch_revision: 13f22cb67ae7f2b922e0c75de966610802201bdb
    issue_state: open
    pull_request_state: not-applicable
    notes: 'GitHub main still matches the base; no open Relay PR was observed before this handoff. #112 is
      open. Observatory #25 records the partial-domain contract blocker. Hosted CI and deployment evidence
      were not polled.'
  parallel_changes: []
review:
  status: partial
  reviewed_at: '2026-09-26T19:38:30Z'
  reviewed_by: Codex
  evidence:
  - command: Native collector prepare using locked Hygiene, EgoLint and Observatory Git objects; cargo build
      --locked --offline --bin egolint
    outcome: passed
    observed_at: '2026-09-26T19:38:30Z'
    notes: Source-built EgoLint and pinned Python validators prepared successfully; exact versions and digests
      are in the collector lock/runtime receipt.
  - command: RELAY_ROADMAP_RUNTIME=<prepared-runtime> RELAY_AKASHIC_REPOSITORY=<exact-source-clone> python3
      -m unittest discover --start-directory tests --pattern "test_*.py" --verbose
    outcome: passed
    observed_at: '2026-09-26T19:38:30Z'
    notes: 507 tests passed, including all 13 collector tests without skips. Real immutable Akashic canary,
      owner semantic diagnostics, malformed/hostile inputs, stale/unavailable providers, renderer compatibility
      and cross-directory equality passed.
  - command: Native collect of egohygiene/akashic at 9af6e87b2c708dc0cb7a57a9ccf315d51e294a1b, observed-at
      2026-09-26T19:00:00Z
    outcome: passed
    observed_at: '2026-09-26T19:38:30Z'
    notes: 'Expected exit 2: five real steps and ten explicit issue references preserved; EgoLint invalid readiness,
      Hygiene valid projection, Observatory normalized candidate, publication denied. Not source conformance
      or site publication.'
  - command: python3 scripts/validate_actions.py; python3 scripts/validate_ci_run_lifecycle.py; python3 scripts/validate_continuity_preflight_contract.py
      validate; python3 scripts/validate_repository_architecture_contract.py validate; python3 scripts/validate_repository_journal_runtime.py
      validate
    outcome: passed
    observed_at: '2026-09-26T19:38:30Z'
    notes: All five catalog/contract validators passed; no action inputs, deployment gates or workflows changed.
  - command: python3 -m compileall -q actions scripts tests; duplicate-key JSON/YAML parsing; bash -n; git
      diff --check; pinned continuity JSON Schema/heading/size/base/branch/link checks
    outcome: passed
    observed_at: '2026-09-26T19:38:30Z'
    notes: Compilation passed; 87 JSON and 36 YAML files parsed; 99 inline and two standalone Bash scripts
      passed syntax. Python substitutes for unavailable local Ruby. Continuity schema, 12 ordered headings,
      bounds, base/branch and links passed.
  - command: Design, compatibility, privacy, source/license and decision-impact review
    outcome: passed
    observed_at: '2026-09-26T19:38:30Z'
    notes: 'Design preceded implementation. No copied sibling implementation or invented readiness/domain semantics.
      Exact Akashic source fixture is CC0-1.0. ADR not required: this implements ADR-007/010 boundaries and
      defers the upstream contract decision.'
  - command: Hosted CI, ordinary artifact upload, Pages upload, deployment, receipt and live-route verification
    outcome: not-run
    observed_at: '2026-09-26T19:38:30Z'
    notes: 'No hosted polling or publication performed. Full #112 acceptance remains blocked by Observatory
      #25 and actual source conformance; action/workflow integration is #113.'
  environment_limitations:
  - The native experimental collector requires separately installed exact Python packages and a prepared trusted
    upstream runtime; ordinary discovery explicitly skips it when unavailable.
  - The current Observatory alpha cannot distinguish domain completeness; all collector output is a publication-denied
    local review envelope.
  - Released EgoLint continuity conformance and hosted publication acceptance are not claimed.
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

Hand off the bounded #112 collector candidate. Canonical contracts and owning
issues retain authority. This checkpoint grants no merge or deployment authority.

## Resume protocol

Read instructions and canonical sources, inspect the checkout, and reverify
main, issue and PR state. This replaces the stale pre-PR #109 checkpoint; its
portability fix is already present in the verified base.

## Current objective and success conditions

Review immutable collection and explicit failure/coverage evidence. Full #112
publication acceptance remains open; a normalized candidate is not conformance.

## State snapshot

The candidate is prepared for review against the recorded main revision. Its
commit/PR identifiers are null before creation; do not infer merge from this text.

## Completed and material changes

The [design and native commands](docs/repository-roadmap-collector.md) define the
exact source mapping, supported compatibility intersection and trust boundary.
The collector prepares pinned upstream runtime bytes, reads immutable Git source,
invokes EgoLint/Hygiene/Observatory, and retains only bounded review evidence.
The closed envelope prevents accidental use as an action snapshot. Akashic's real
source fixture preserves all five stable steps and its readiness contradiction.
No source repair, workflow integration, deployment or release is included.

## Validation and review evidence

All 507 local tests and five catalog/contract validators passed. The 13 collector
tests ran without skips against the prepared runtime and real Akashic clone.
Compilation, structured-file parsing and Bash syntax passed. The CLI returned its
expected publication-denied exit for the actual canary. Provider stages are not
inferred from these checks. Aether's maintain-repository-continuity skill and its
authoring/privacy/checklist references were read at
9e2ba7d8fb118c0976356225dcac54209fe44eee. Structural continuity verification uses
Relay's pinned schema and template; released semantic conformance is unavailable.

## Blockers, risks, unknowns, and deferred work

Observatory #25 owns missing partial-domain coverage. Akashic #197 owns its
canonical readiness reconciliation. Provider replay is limited to explicitly
referenced same-repository issues; arbitrary evidence prose, PRs, cross-repository
records and other domains are not collected. The runtime receipt binds a trusted
local build, not a signed release. Full #112 acceptance, #113 integration and
consumer publication remain deferred. #106/#33 and #101 retain separate gates.

## Next dependency-ready work

The maintainer selected ADRs and Decisions as capability 1 under Pace #5; the
existing repository ADR issues are reused. Reconcile Relay #99 checkpoint 1
against existing contract files, then continue its shared-validation checkpoints
one PR at a time. Policy ratification is already recorded; do not request it
again. Roadmaps in Pace #31 are capability 2. Resolve Observatory #25 before any
partial-domain snapshot is promoted for publication, including future ADR input.

## Parallel changes and reconciliation

Main was unchanged and no open Relay PR was observed. Pace #5/#25/#31 and the
organization epic #30 now record the maintainer's priority change. Recheck live
state before modifying the next issue or reconciling another continuity edit.

## Privacy and redaction

Only public repository and synthetic fixture evidence appears here. No secrets,
private topology, conversation content, author emails or local paths are retained.
Links provide context and do not grant authority.

## Handoff update protocol

Refresh after domain validation and before PR presentation. Verify the schema,
ordered headings, bounds, links, base and whitespace. Reconcile actual merged
state later instead of claiming this candidate is already on main.

## Compaction and supersession

Stay below 16,384 UTF-8 bytes and 240 lines. Keep history in Git and owning issues;
replace stale operational prose instead of appending transcripts.
