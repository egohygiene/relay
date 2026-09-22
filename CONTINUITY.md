---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: "2026-09-22T18:12:07Z"
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: "Implement Relay checkpoint #105's deterministic Repository Intelligence build-to-consumer-deployment provenance handoff and publish the exact review evidence."
  includes:
    - "A deterministic in-bundle build manifest bound to consumer revision, Relay revision, contract versions, source epoch, routes, files, and payload digest."
    - "Separate consumer composition verification and deployment receipts with run, attempt, environment, URL, conclusion, aliases, final-site identity, and rollback point."
    - "Executable reference-consumer fixtures, negative cases, non-clobber proof, schemas, catalogs, documentation, and recovery guidance."
    - "Review-only pull-request publication; merge and deployment authority remain with the user and consumer."
  excludes:
    - "GitHub Pages deployment authority, provider writes, secrets, OIDC, or consumer artifact upload."
    - "Akashic or Empathy migration, fleet adoption, production deployment claims, or completion of parent #33."
    - "Relay #101 polish, #106 final reconciliation, Observatory attribution, or unrelated roadmap work."
    - "Weakening the read-only event and trust contract completed by #104."
  precedence:
    - user-and-runtime-instructions
    - scoped-repository-instructions
    - live-repository-and-work-tracker-state
    - canonical-repository-sources
    - continuity-checkpoint
  canonical_sources:
    - AGENTS.md
    - AI_CONSTITUTION.md
    - ARCHITECTURE.md
    - SYSTEM.md
    - DECISIONS.md
    - ROADMAP.md
    - README.md
    - .github/workflows/repository-intelligence.yml
    - actions/repository-intelligence/action.yml
    - actions/repository-intelligence/schemas/repository-intelligence-build-manifest.schema.json
    - actions/repository-intelligence-deployment-provenance/action.yml
    - actions/repository-intelligence-deployment-provenance/README.md
    - docs/repository-intelligence-publication.md
    - examples/workflows/repository-intelligence-deployment-provenance.md
    - action-catalog.json
work:
  objective: "Present one exact, fully validated #105 implementation PR while distinguishing fixture proof from consumer production deployment evidence."
  success_conditions:
    - "The Relay artifact contains one versioned deterministic build manifest with exact consumer and generator revisions, contract versions, source epoch, enabled routes, and canonical payload digest."
    - "Run-specific deployment facts remain in a separate consumer-owned receipt and cannot change the Relay bundle digest."
    - "Verification rejects revision drift, digest mismatch, incompatible contracts, missing routes, stale evidence, incomplete receipts, unsafe public metadata, and clobbered consumer files."
    - "The reference flow proves preserved consumer routes and aliases without giving Relay Pages, provider, token, or secret authority."
    - "Documentation covers consumer integration, evidence retention, audit, recovery, and rollback while labeling fixture evidence honestly."
  active_issue:
    provider: github
    id: egohygiene/relay#105
    url: https://github.com/egohygiene/relay/issues/105
  next:
    kind: issue
    id: egohygiene/relay#106
    description: "After #105 merges and exact provider evidence is recorded, perform the final #33 reconciliation without transferring consumer deployment authority."
    readiness: blocked-by-105-merge-and-closeout
    references:
      - https://github.com/egohygiene/relay/issues/106
      - https://github.com/egohygiene/relay/issues/33
    depends_on:
      - egohygiene/relay#105
state:
  base:
    revision: ecdf1d9bd8eda0d1aa2388a7caffe867968578a7
    tree: b10a4b1aa0b20b7f00f73f94f80c56a9d5fc8a22
    ref: refs/heads/main
    verified_at: "2026-09-22T18:12:07Z"
  candidate:
    branch: codex/relay-105-deployment-provenance
    revision: 5161555b243d5dc0e71110033f8616eb323b93fa
    tree: ee85f6b7bbbe34508554042a14b61665a5a12da4
    pull_request: https://github.com/egohygiene/relay/pull/108
    handoff_state: implementation-validated-continuity-update-pending
  live:
    status: verified
    observed_at: "2026-09-22T18:12:07Z"
    default_branch_revision: ecdf1d9bd8eda0d1aa2388a7caffe867968578a7
    issue_state: open
    parent_issue_state: open
    pull_request_state: draft
    notes: "Checkpoint #104 and PR #107 are complete at the exact base revision. PR #108 contains the locally validated #105 implementation tree. No merge, issue closure, production deployment, Akashic/Empathy migration, or completed #33 evidence is claimed."
  parallel_changes: []
review:
  status: passed-local-exact-head-provider-checks-pending
  reviewed_at: "2026-09-22T18:12:07Z"
  reviewed_by: ChatGPT
  evidence:
    - command: "Verify live main, #104, #105, #33, open pull requests, related branches, and supplied #104 provider evidence."
      outcome: passed
      observed_at: "2026-09-22T18:12:07Z"
      notes: "Main is ecdf1d9bd8eda0d1aa2388a7caffe867968578a7; #104 is completed, #105 and #33 are open, and no competing #105 branch or pull request preceded this work. The intentional RIW-002 run 35747527356 remains expected negative evidence."
    - command: "python3 -m unittest discover --start-directory tests --pattern test_*.py --verbose"
      outcome: passed
      observed_at: "2026-09-22T18:12:07Z"
      notes: "All 488 unit and integration tests passed, including passing receipt generation plus revision, digest, version, route, freshness, non-clobber, alias-target, incomplete-receipt, unsafe-URL, and pre-write path-boundary rejection fixtures."
    - command: "Run validate_actions.py, validate_ci_run_lifecycle.py, validate_continuity_preflight_contract.py, validate_repository_architecture_contract.py, and validate_repository_journal_runtime.py."
      outcome: passed
      observed_at: "2026-09-22T18:12:07Z"
      notes: "All catalog, lifecycle, continuity, architecture, and journal contract validators passed."
    - command: "Compile Python; parse JSON with duplicate-key rejection and YAML metadata; validate checked-in Bash, 96 inline Bash blocks, JavaScript syntax, and git diff whitespace."
      outcome: passed
      observed_at: "2026-09-22T18:12:07Z"
      notes: "All available deterministic syntax, metadata, and whitespace checks passed."
    - command: "Publish the implementation tree through the connected GitHub API and open draft PR #108."
      outcome: passed
      observed_at: "2026-09-22T18:12:07Z"
      notes: "Remote commit 5161555b243d5dc0e71110033f8616eb323b93fa and the locally validated checkpoint share exact tree ee85f6b7bbbe34508554042a14b61665a5a12da4."
  environment_limitations:
    - "The final continuity commit still requires exact-head GitHub Actions inspection before handoff."
    - "Relay fixtures prove the reference contract, not a real consumer production deployment; consumer run, URL, retained receipt, and remote-byte evidence remain consumer-owned."
    - "Exact merged revision and post-merge provider evidence are necessarily closeout work; #105 and parent #33 remain open."
    - "Ruby is unavailable locally; PyYAML parsed all metadata while canonical CI repeats YAML parsing with Ruby/Psych."
    - "The maintain-repository-continuity skill is unavailable in this session; this checkpoint was refreshed directly from the pinned local Aether template under AGENTS.md."
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

This checkpoint records #105's build-to-deployment provenance boundary. It does
not replace canonical architecture, roadmap, Git history, live issues, or PR
state. Resolve conflicts using the precedence above.

## Current state

- Base: merged `main` revision `ecdf1d9bd8eda0d1aa2388a7caffe867968578a7`.
- Candidate: draft PR #108 on `codex/relay-105-deployment-provenance`.
- Local verification: 488 tests, five contract validators, JSON/YAML parsing,
  Python/Bash/inline-Bash/JavaScript syntax, and whitespace checks passed.
- Live: #105 and parent #33 remain open. No production deployment or merge is
  claimed.

## Material changes

- Added a deterministic in-bundle manifest with exact identities, contract
  versions, source epoch, routes, file inventory, and payload digest.
- Added a no-network, no-token consumer action to capture existing files,
  verify composition, record a separate receipt, and re-verify it for audit.
- Bound receipts to the manifest, workflow run/attempt, deployment result,
  final site inventory, aliases, preserved consumer files, and rollback point.
- Added closed schemas and executable success/failure fixtures for drift,
  mismatch, incompatibility, missing routes, staleness, clobber, unsafe URLs,
  alias mismatch, and incomplete receipts.
- Updated catalogs, architecture decisions, roadmap evidence, changelog, and
  integration/recovery documentation without acquiring deployment authority.

## Remaining evidence and next work

The final continuity commit must be pushed and every exact-head PR check must be
inspected. Keep #105 open through review and merge; afterward record the exact
merged revision and provider evidence before closing it. A real consumer may
then retain its own production run and receipt evidence. Keep #33 open for #106
final reconciliation; do not migrate Akashic or Empathy under this checkpoint.

## Resume protocol

1. Re-verify main, #105, #33, draft PR #108, and the exact candidate head.
2. Inspect every required GitHub Actions result and retain exact run URLs.
3. Resolve substantive findings on this branch; do not merge for the user.
4. After user merge, record the exact merged revision and provider evidence
   before closing #105 or beginning #106.

## Privacy and compaction

This public checkpoint contains only public repository identifiers, revisions,
issue/PR URLs, contract names, and bounded validation outcomes. Keep it below
16,384 UTF-8 bytes and 240 lines; replace stale state instead of appending history.
