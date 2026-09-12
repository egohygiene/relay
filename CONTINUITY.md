---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: "2026-09-12T12:47:29Z"
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Preserve the minimum verified state needed to release Relay's v0-compatible publication contract safely.
  includes:
    - The active release issue, represented Git state, validation evidence, release gate, and OptiFlow consumer proof.
  excludes:
    - Conversation transcripts and duplicated architecture, roadmap, or changelog history.
  precedence:
    - user-and-runtime-instructions
    - scoped-repository-instructions
    - live-repository-and-work-tracker-state
    - canonical-repository-sources
    - continuity-checkpoint
  canonical_sources:
    - AGENTS.md
    - README.md
    - ARCHITECTURE.md
    - SYSTEM.md
    - DECISIONS.md
    - ROADMAP.md
    - CHANGELOG.md
    - release.json
    - .github/workflows/release.yml
    - .github/workflows/release-artifact.yml
work:
  objective: Publish Relay v1.5.0 with exact pre-one SemVer authorization and unblock OptiFlow v0.1.0.
  success_conditions:
    - Prove the reusable publication guard accepts v0.1.0 and rejects malformed or leading-zero versions.
    - Keep the v1.5.0 declaration, changelog, and shipped catalog aligned.
    - Publish immutable v1.5.0 evidence from the reviewed default-branch commit and advance v1 only after verification.
    - Pin OptiFlow to the exact released Relay commit and complete its v0.1.0 release.
  active_issue:
    provider: github
    id: egohygiene/relay#67
    url: https://github.com/egohygiene/relay/issues/67
  next:
    kind: issue
    id: egohygiene/optiflow#27
    description: Repin the consumer to the released Relay commit and rerun the reviewed v0.1.0 publication.
    readiness: blocked
    references:
      - https://github.com/egohygiene/optiflow/issues/27
      - https://github.com/egohygiene/optiflow/actions/runs/34694169732
    depends_on:
      - egohygiene/relay#67
state:
  base:
    revision: 30bc3cc34b5fea07163ecaf4eaf1a5e68fe03db5
    ref: refs/heads/main
    verified_at: "2026-09-12T12:47:29Z"
  candidate:
    branch: fix/relay-v0-release
    revision: a36e2cfee6c0b03a43a29d23426cf487e5e830c0
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: verified
    observed_at: "2026-09-12T12:47:29Z"
    default_branch_revision: 30bc3cc34b5fea07163ecaf4eaf1a5e68fe03db5
    issue_state: open
    pull_request_state: not-applicable
    notes: GitHub confirmed PR 66 merged at the represented main revision, Relay issue 67 is open, v1.5.0 is not tagged, and no competing pull request was found before implementation.
  parallel_changes: []
review:
  status: partial
  reviewed_at: "2026-09-12T12:47:29Z"
  reviewed_by: Codex
  evidence:
    - command: Repository, release history, and live GitHub baseline inspection
      outcome: passed
      observed_at: "2026-09-12T12:45:49Z"
      notes: Relay main, all repository instructions and canonical architecture sources, the v1.4.0-to-main release diff, merged PR 66, and new issue 67 were inspected before implementation.
    - command: python3 -m unittest tests.test_release_artifact_workflow tests.test_semantic_release_workflows -v; python3 scripts/validate_actions.py; compileall; git diff --check
      outcome: passed
      observed_at: "2026-09-12T12:46:25Z"
      notes: Eight focused release tests passed, nine actions and sixteen workflows matched the catalogs, Python compilation passed, and the diff had no whitespace errors.
    - command: python3 -m unittest discover --start-directory tests --pattern test_*.py --verbose; workflow YAML parse
      outcome: passed
      observed_at: "2026-09-12T12:46:50Z"
      notes: All 211 Relay tests passed and every GitHub workflow parsed successfully.
  environment_limitations:
    - The task runner is unavailable locally; the documented wrapper could not be invoked.
    - Full release verification requires the exact candidate to be the current remote default-branch head and is intentionally deferred until review and merge.
    - GitHub Actions evidence is pending the candidate pull request.
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

This checkpoint preserves the minimum public operational state for Relay issue
#67. It remains subordinate to user and repository instructions, live Git and
GitHub evidence, and the canonical sources listed above; it grants no authority.

## Resume protocol

1. Read `AGENTS.md`, inspect the branch, status, recent history, and repository
   shape.
2. Read the named canonical sources and active issue.
3. Read this checkpoint and independently verify mutable issue, pull-request,
   branch, tag, release, and merge claims.
4. Surface missing, stale, or contradictory evidence before continuing only the
   named dependency-ready work.

## Current objective and success conditions

Publish the already-prepared Relay v1.5.0 catalog so consumers can authorize
exact pre-one SemVer releases. This slice succeeds when the workflow-level test
binds directly to the shipped guard, the release notes cover every included
change, local and CI checks pass, and immutable publication precedes OptiFlow's
full-SHA repin and v0.1.0 rerun.

## State snapshot

The verified base is Relay `main` at
`30bc3cc34b5fea07163ecaf4eaf1a5e68fe03db5`. The candidate branch is
`fix/relay-v0-release`; issue #67 is open, no candidate pull request exists yet,
and these mutable claims must be rechecked before handoff.

## Completed and material changes

- OptiFlow run 34694169732 proved every consumer-owned build, smoke, SBOM,
  provenance, Sigstore, and bundle step before Relay v1.4.0 rejected v0.1.0.
- Relay main already contains the corrected exact-SemVer guard from the prepared
  v1.5.0 catalog.
- The candidate adds a workflow-level regression test for accepted pre-one and
  rejected leading-zero versions.
- The v1.5.0 changelog now covers the label and continuity features merged after
  its original preparation, plus the pre-one publication compatibility change.

## Validation and review evidence

- Baseline repository, release history, and live GitHub inspection passed before
  implementation.
- Eight focused release tests, all 211 Relay tests, action/workflow catalog
  validation, workflow YAML parsing, Python compilation, and whitespace checks
  passed locally.
- The `task` executable is absent locally. Its release-plan wrapper was inspected;
  full verify mode correctly remains gated on the reviewed candidate becoming
  the remote default-branch head.

## Blockers, risks, unknowns, and deferred work

- Release blocker: v1.5.0 cannot be published until this candidate is reviewed,
  merged, and independently verified on the exact resulting main commit.
- Consumer blocker: OptiFlow must not pin mutable Relay main or the moving v1
  alias; it waits for the immutable released Relay commit.
- Risk: publishing the earlier v1.5.0 preparation without reconciling later main
  changes would make the changelog incomplete; this candidate closes that gap.
- Deferred: OptiFlow v0.1.0 publication and Relay issue closure follow the Relay
  release and immutable consumer repin.

## Next dependency-ready work

Open and review the Relay #67 candidate. After merge, dispatch v1.5.0 from the
exact default-branch head, verify its tag, assets, evidence, and v1 alias, then
repin OptiFlow and rerun issue #27's v0.1.0 release.

## Parallel changes and reconciliation

No parallel release pull request was observed. Recheck remote heads, tags, and
open pull requests before final review and reconcile semantically if another
branch changes the same release contracts or checkpoint.

## Privacy and redaction

This public checkpoint contains only public repository, Git, GitHub, contract,
and validation state. Credentials, conversation text, sensitive personal data,
private paths, unpublished business data, and unrelated context are excluded.

## Handoff update protocol

After project validation and before presenting or updating a pull request,
reconcile this snapshot, replace stale state, record exact evidence, compact it,
and include it in the same bounded change. Never infer a merge, tag, or release
from local Git or an open candidate.

## Compaction and supersession

Keep this file below 16,384 UTF-8 bytes and 240 lines. Replace stale snapshot
prose instead of accumulating history; Git and the work tracker own chronology.
Mark stale or superseded state explicitly with its required reason or pointer.
