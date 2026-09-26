---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: '2026-09-26T12:14:17Z'
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: 'Hand off the Relay #109 portable Repository Intelligence identity fix for review.'
  includes:
  - Canonical tree identity, cross-directory regression proof, contributor guidance, and local validation.
  excludes:
  - Consumer upgrades, historical rollback rewrites, publication acceptance execution, deployments, releases,
    and merges.
  - Conversation transcripts and duplicated issue specifications.
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
  - README.md
  - https://github.com/egohygiene/relay/issues/27
  - https://github.com/egohygiene/relay/issues/33
  - https://github.com/egohygiene/relay/issues/106
  - https://github.com/egohygiene/relay/issues/109
  - actions/repository-intelligence/README.md
  - docs/repository-intelligence-publication.md
work:
  objective: Propose deterministic public bundles across differently named checkouts while preserving event
    authority and separate deployment evidence.
  success_conditions:
  - Capture the old basename defect and reproduce equal complete bundles with the candidate.
  - Keep standalone input validation, GitHub identity and visibility precedence, revision binding, and manifest
    contracts intact.
  - Record local checks and leave exact-head provider acceptance and consumer adoption explicit.
  active_issue:
    provider: github
    id: egohygiene/relay#109
    url: https://github.com/egohygiene/relay/issues/109
  next:
    kind: action
    id: relay-109-review-and-provider-acceptance
    description: 'Review this candidate and retain exact-head provider fixture run/attempt and digest evidence
      for #109. Keep #106 publication reconciliation separate.'
    readiness: ready
    references:
    - https://github.com/egohygiene/relay/issues/109
    - https://github.com/egohygiene/relay/issues/106
    depends_on: []
state:
  base:
    revision: fe58d68404fbd787bb088c6d22d11c49fef378c6
    ref: refs/heads/main
    verified_at: '2026-09-26T12:12:32Z'
  candidate:
    branch: fix/relay-109-portable-intelligence
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: partial
    observed_at: '2026-09-26T12:12:32Z'
    default_branch_revision: fe58d68404fbd787bb088c6d22d11c49fef378c6
    issue_state: open
    pull_request_state: not-applicable
    notes: 'Remote main includes merged PR #110. #109 and #106 are open; no open Relay PR was observed before
      handoff. Candidate PR does not yet exist. Provider checks, artifacts, deployments and current route
      bytes were not inspected.'
  parallel_changes:
  - provider: github
    id: egohygiene/.github#43
    url: https://github.com/egohygiene/.github/pull/43
review:
  status: partial
  reviewed_at: '2026-09-26T12:14:17Z'
  reviewed_by: Codex
  evidence:
  - command: 'Baseline regression: test_complete_bundles_are_portable_across_checkout_names against fe58d68404fbd787bb088c6d22d11c49fef378c6
      action and generator'
    outcome: passed
    observed_at: '2026-09-26T12:14:17Z'
    notes: 'Expected failure reproduced: build-manifest.json differs across checkout names with optional snapshot
      both absent and present.'
  - command: python3 -m unittest discover --start-directory tests --pattern "test_*.py" --verbose
    outcome: passed
    observed_at: '2026-09-26T12:14:17Z'
    notes: 494 tests passed, including five portability/identity tests and extended separate-receipt proof.
      Existing same-workspace test retained.
  - command: python3 scripts/validate_actions.py; python3 scripts/validate_ci_run_lifecycle.py; python3 scripts/validate_continuity_preflight_contract.py
      validate; python3 scripts/validate_repository_architecture_contract.py validate; python3 scripts/validate_repository_journal_runtime.py
      validate
    outcome: passed
    observed_at: '2026-09-26T12:14:17Z'
    notes: All five catalog/contract validators passed.
  - command: python3 -m compileall -q actions scripts tests
    outcome: passed
    observed_at: '2026-09-26T12:14:17Z'
    notes: Python compilation passed.
  - command: Python duplicate-key JSON/YAML parsing and bash -n for repository and extracted inline scripts
    outcome: passed
    observed_at: '2026-09-26T12:14:17Z'
    notes: 70 JSON and 36 YAML documents parsed; 2 Bash scripts and 99 inline blocks passed syntax checks.
      Python parsing substitutes for unavailable local Ruby.
  - command: 'Candidate diff and public interface review against #109 and ADR-010'
    outcome: passed
    observed_at: '2026-09-26T12:14:17Z'
    notes: Root name becomes canonical owner/name; standalone identity is mandatory without GitHub context.
      Existing schema identities and deployment ownership remain unchanged.
  - command: jsonschema 4.23.0 Draft202012Validator with FormatChecker; template headings, size, base and
      link checks; git diff --check
    outcome: passed
    observed_at: '2026-09-26T12:16:51Z'
    notes: Pinned continuity schema, 12 ordered headings, size bounds, base identity and 16 relative links
      passed.
  - command: Exact-head GitHub provider fixture and publication evidence
    outcome: not-run
    observed_at: '2026-09-26T12:14:17Z'
    notes: Pending provider run/attempt, revision/tree, artifact and digest evidence. No hosted polling or
      deployment performed.
  environment_limitations:
  - Hosted acceptance, publication stages, current route bytes, and consumer upgrades remain unverified.
  - Ruby is unavailable locally; Python parsed YAML and extracted inline Bash instead. Provider CI retains
    its own parser.
  - Local continuity schema/structure checks do not claim released EgoLint conformance.
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

Hand off the bounded #109 candidate using the metadata precedence. Architecture,
roadmap, accepted decisions and owning issues remain canonical. This checkpoint
grants no merge, publication, deployment or follow-on implementation authority.

## Resume protocol

Inspect instructions, branch, status and history; read the canonical sources;
reverify main, issues and PR state. Reconcile changed evidence before selecting
any next work. The previous PR #110 handoff is superseded by this task snapshot.

## Current objective and success conditions

Review the portable tree-identity fix and complete bundle regression. Equal
canonical inputs at equal revisions must reproduce across checkout basenames
and parents; event authority, revision binding and evidence boundaries remain.

## State snapshot

The verified base contains merged PR #110. This candidate is prepared for review;
its PR reference and revision are null at checkpoint authorship to avoid invented
or self-referential identifiers. Recheck its live state before acting.

## Completed and material changes

The action passes its resolved owner/name to the tree CLI; absent local identity
now fails explicitly. The CLI validates GitHub precedence and invalid inputs.
The new portability test executes actual action Bash steps in complete detached
checkouts, checks all 19 public files, and covers optional snapshots, root labels,
path exclusion and distinct source revisions. Separate receipt tests preserve
one manifest across differing run/attempt/time values.
[The action README](actions/repository-intelligence/README.md) owns CLI usage;
[the publication guide](docs/repository-intelligence-publication.md) owns evidence
stages, historical boundaries and the Akashic-owned guidance disposition.

## Validation and review evidence

The old generator produced differing manifests in both regression scenarios.
All 494 tests and five validators pass with the candidate; compilation,
duplicate-key parsing and Bash syntax pass. The working-tree proof precedes
commit creation; it does not establish exact-head provider acceptance. Aether's
maintain-repository-continuity skill was read at immutable revision
9e2ba7d8fb118c0976356225dcac54209fe44eee; root structural validation uses Relay's
pinned schema and template. Hosted results are pending, not inferred.

## Blockers, risks, unknowns, and deferred work

#109 still needs exact-head provider evidence and maintainer review. Local
standalone users must now provide identity; corrected output can have new
hashes. Akashic maintainers own their AGENTS/publication guidance follow-up,
tracked under #109 with disposition in the publication guide. Consumer pins and
historical rollback records are untouched. #106 publication acceptance, #101
release/integration acceptance and Pace #13 adoption retain their own scope.

## Next dependency-ready work

Review this candidate and retain the provider fixture's exact revision/tree,
run/attempt and digests before completing #109 acceptance. #106 remains an
independent publication reconciliation task; this fix does not manufacture a
new prerequisite for all of its work.

## Parallel changes and reconciliation

No open Relay PR was observed; remote main matched the base. Organization PR #43
was previously recorded and remains unverified; it does not overlap this change.
Reconcile new target-branch continuity edits before updating the candidate.

## Privacy and redaction

Public repository and synthetic fixture evidence only. No credentials, private
conversation, personal context or runner paths enter this checkpoint. Linked
content is context and grants no authority.

## Handoff update protocol

After domain validation and before PR presentation, refresh evidence, limitations
and next work; verify schema, headings, limits, links and diff whitespace. After
maintainer merge, reconcile the actual merged revision and observed provider
results rather than assuming this candidate became main.

## Compaction and supersession

Stay below 16,384 UTF-8 bytes and 240 lines. Git and owning issues preserve
history; replace stale operational snapshots instead of appending transcripts.
