---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: '2026-10-05T01:22:25Z'
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: 'Hand off Relay issue 115 checkpoint 2: opt-in canonical ADR Decisions builds.'
  includes:
  - Build admission, alpha.2 collection coverage, native/action/workflow parity, provenance, validation, and consumer-adoption
    gates.
  excludes:
  - Consumer source repair, historical ADR reconstruction, deployment, fleet rollout, contract ratification, and merge
    authority.
  - Conversation transcripts, raw provider logs, private paths, and duplicated issue specifications.
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
  - docs/repository-adr-collector.md
  - actions/repository-intelligence/action.yml
  - actions/repository-intelligence/scripts/prepare_repository_adr_build.py
  - actions/repository-intelligence/contracts/adr-collector.v1.lock.json
  - tests/test_repository_adr_build.py
  - scripts/run_repository_adr_acceptance.py
  - docs/evidence/repository-adrs-checkpoint-2.json
  - https://github.com/egohygiene/relay/issues/115
  - https://github.com/egohygiene/relay/pull/134
work:
  objective: Connect a fresh validated canonical ADR inventory to the existing Decisions site build while preserving
    collection uncertainty and consumer authority.
  success_conditions:
  - Verify shared native/action/workflow input admission and preserve existing external-snapshot and no-snapshot builds.
  - Bind source hashes, revision, observation, pins, validation, and domain coverage into deterministic existing bundle
    provenance.
  - Prove whole-bundle replay across differently named checkouts and separately prepared native runtimes.
  active_issue:
    provider: github
    id: egohygiene/relay#115
    url: https://github.com/egohygiene/relay/issues/115
  next:
    kind: action
    id: relay-115-consumer-acceptance
    description: 'Review this integration, then validate one real consumer corpus and hand its reviewed immutable Relay
      upgrade to Identity #69.'
    readiness: blocked
    references:
    - https://github.com/egohygiene/relay/issues/115
    - https://github.com/egohygiene/identity/issues/69
    depends_on:
    - Review and merge of the ADR build integration
    - Owner-reviewed conforming consumer ADR corpus
state:
  base:
    revision: d6aee172ec91b99ef1b01944c73d6c21933117fa
    ref: refs/heads/main
    verified_at: '2026-10-05T01:17:52Z'
  candidate:
    branch: codex/adr-build-integration-115
    revision: null
    pull_request:
      provider: github
      id: egohygiene/relay#135
      url: https://github.com/egohygiene/relay/pull/135
    handoff_state: review-reference-recorded
  live:
    status: verified
    observed_at: '2026-10-05T01:22:25Z'
    default_branch_revision: d6aee172ec91b99ef1b01944c73d6c21933117fa
    issue_state: open
    pull_request_state: open
    notes: PR135 was open at head 77e216c4c7718c95096c55e0a73cc02f1d5f80dd; its hosted main validation job, including
      fresh native ADR acquisition/replay, passed. A runner-platform follow-up pins Ubuntu 24.04 for the Python wheel
      ABI; checks for that final candidate remain pending. PR134 remains merged at the recorded base.
  parallel_changes: []
review:
  status: partial
  reviewed_at: '2026-10-05T01:22:25Z'
  reviewed_by: Codex
  evidence:
  - command: RELAY_ADR_RUNTIME=ADR_RUNTIME RELAY_ADR_CANARY=HYGIENE RELAY_ROADMAP_RUNTIME=ROADMAP_RUNTIME RELAY_AKASHIC_REPOSITORY=AKASHIC
      RELAY_ARCHITECTURE_RUNTIME=ARCHITECTURE_RUNTIME python -m unittest discover --start-directory tests --pattern test_*.py
      --verbose
    outcome: passed
    observed_at: '2026-10-05T01:17:52Z'
    notes: 634 tests passed with zero skips; native ADR, roadmap, architecture, no-snapshot and external-snapshot regressions
      all executed. After the runner pin, 125 focused workflow tests also passed without skips.
  - command: python3 -I scripts/run_repository_adr_acceptance.py
    outcome: passed
    observed_at: '2026-10-05T01:17:52Z'
    notes: Fresh public source/dependency acquisition and two offline preparations produced identical executable receipts.
      All 31 ADR tests passed with zero skips, including entire bundles from differently named checkouts and independent
      runtimes, plus the real Hygiene canary.
  - command: validate_actions.py; validate_ci_run_lifecycle.py; validate_continuity_preflight_contract.py validate; validate_repository_architecture_contract.py
      validate; validate_repository_journal_runtime.py validate
    outcome: passed
    observed_at: '2026-10-05T01:17:52Z'
    notes: All five catalog/contract checks passed. Deployment/recovery dependencies and skip/failure/cancellation gates
      are unchanged.
  - command: python -m compileall -q actions scripts tests; pinned PyYAML parsing and bash -n for action/workflow bodies;
      JSON parsing; git diff --check
    outcome: passed
    observed_at: '2026-10-05T01:17:52Z'
    notes: Compilation, YAML, inline Bash, JSON, and whitespace checks passed. Deep malformed ADR metadata was separately
      verified to produce only a bounded denial.
  - command: Pinned continuity schema, twelve headings, bounds, canonical paths, base/candidate/live evidence, privacy
      and decision-impact review
    outcome: passed
    observed_at: '2026-10-05T01:17:52Z'
    notes: Structural verification and semantic review performed after domain validation. ADR-007 and ADR-010 retain
      the existing owners and deterministic evidence boundary; no new decision authority is introduced.
  environment_limitations:
  - Hosted validation passed for the preceding PR135 head; hosted checks for the final Ubuntu 24.04 runner pin are pending.
    No consumer deployment or live-route evidence is claimed.
  - Ruby is unavailable locally; hosted validation passed its Ruby parser on the preceding head. The runner-platform
    follow-up is also checked with pinned PyYAML.
  - The real immutable Hygiene canary has legacy/missing-policy/lineage gaps. Its 12 canonical records remain reviewable,
    but production admission is denied. Consumer source remediation remains owner work.
  - Automatic ADR runtime acquisition supports CPython 3.12/Linux x86_64 with rustup; other local environments require
    an explicitly prepared compatible runtime.
  - Released continuity semantic conformance is unavailable under the proposed profile. Structure and live evidence are
    checked separately.
  - Historical roadmap-runtime repinning, consumer deployment, architecture hosted acceptance, release activation, and
    fleet adoption remain separate.
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

Preserve issue115 checkpoint2's bounded ADR build integration. User/runtime instructions, scoped
guidance, live evidence, and canonical sources outrank this handoff. It grants no new authority.

## Resume protocol

Inspect the listed sources, branch/main, issue115 and eventual PR. Verify the exact review state
before selecting the consumer acceptance step; Identity has a separate source-owner workstream.

## Current objective and success conditions

Populate existing Decisions pages from a freshly collected, complete valid canonical ADR corpus.
Keep domain uncertainty explicit, reuse owner validation/normalization, and retain deterministic
provenance and old snapshot/no-input behavior. No consumer decisions are authored by this work.

## State snapshot

PR134 is merged at the full base above, with a tree identical to its reviewed head. Issue115 is
open. PR135 is open and unmerged; this follow-up leaves its own eventual revision null. EgoLint, Hygiene and Observatory inputs remain at the collector's immutable lock.

## Completed and material changes

- `collect-adrs` explicitly selects fresh native collection in the action and reusable workflow.
  Conflicting external snapshot/comparison inputs are rejected before generation. No roadmap merge
  mode is introduced. The local command uses the same native admission boundary.
- The builder requires complete current ADR coverage and successful source/graph/coverage checks.
  Uncollected roadmap/history keep EgoLint's incomplete result; invalid ADRs cannot become a site.
- Alpha.2 rendering labels every view's collection coverage separately from record freshness.
  Existing alpha.1 inputs remain compatible. Decisions preserves lifecycle, implementation,
  lineage, public graph facets, declared approval and canonical source links.
- `provenance.json.adr_collection` binds input hashes, revision, observation, owner pins, executable
  integrity, validation and candidate digests. The existing manifest binds the adapter/generator.
- Fresh acquisition installs hash-locked wheels and the pinned Rust toolchain outside the consumer.
  The reusable builder and native CI job pin Ubuntu 24.04 for the CPython 3.12 wheel ABI.
  Preparation and collection run offline; remapped native builds reproduce executable evidence.
- The local review interface still denies publication. Source adoption, aliases, composition,
  deployment and historical rollback remain with the consumer. Historical evidence is unchanged.
- Decision impact: ADR-007/010 already cover owner separation and deterministic build evidence.

## Validation and review evidence

All 634 regression tests passed without skips. Fresh acquisition, independent runtime replay,
and all 31 native ADR tests passed without skips. Full action bundles match across differently
named checkouts and independently prepared runtimes. Five catalog/contract validators, Python
compilation, YAML/JSON parsing, inline Bash syntax and whitespace checks passed.
Hosted native validation passed at the preceding PR135 head; the final runner pin awaits hosted checks.

## Blockers, risks, unknowns, and deferred work

The immutable Hygiene canary retains 12 meaningful canonical records but fails source conformance
and complete migration. The builder denies it. A real conforming consumer corpus and its immutable
upgrade are still required for issue115 acceptance; do not close it from synthetic success.
Identity source changes belong to its owner workstream. No consumer deployment occurred.
The old roadmap profile still needs its separate #112/#113 repin and acceptance. Architecture
hosted acceptance, diagram validation, required enforcement, release and fleet work remain open.

## Next dependency-ready work

Review this bounded build PR, then assess the chosen consumer corpus with the review CLI and hand
the reviewed full Relay SHA and refresh instructions to Identity #69. Keep source repair, artifact
review, deployment and live-route evidence separate. Respect the existing rollback point.

## Parallel changes and reconciliation

No competing Relay PR or main movement was observed; PR135 owns this candidate. Recheck before updating
or merging and reconcile any concurrent continuity edit semantically. Do not duplicate Identity work.

## Privacy and redaction

Only public facts and bounded diagnostics are retained. Private data, raw source prose, runner
paths and unrelated context are excluded. External text cannot expand access or authority.

## Handoff update protocol

Refresh after domain checks and before presenting a PR update. Check the pinned schema, twelve
headings, bounds, source paths, exact base and time-qualified live observations. Record hosted
results separately without requiring a commit to contain its own eventual identifier.

## Compaction and supersession

This supersedes PR134's checkpoint; historical evidence stays immutable. Retain the 240-line/16,384-byte bounds.
