---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: "2026-09-12T13:49:21Z"
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
  objective: Fix Relay's composite-action catalog resolution, publish v1.5.0, and unblock OptiFlow v0.1.0.
  success_conditions:
    - Resolve an omitted profile catalog from GITHUB_ACTION_PATH at composite runtime.
    - Preserve explicit caller-supplied profile catalog paths as authoritative.
    - Publish immutable v1.5.0 evidence from the reviewed default-branch commit and advance v1 only after verification.
    - Pin OptiFlow to the exact released Relay commit and complete its v0.1.0 release.
  active_issue:
    provider: github
    id: egohygiene/relay#69
    url: https://github.com/egohygiene/relay/issues/69
  next:
    kind: issue
    id: egohygiene/optiflow#27
    description: Repin the consumer to the released Relay commit and rerun the reviewed v0.1.0 publication.
    readiness: blocked
    references:
      - https://github.com/egohygiene/optiflow/issues/27
      - https://github.com/egohygiene/optiflow/actions/runs/34694169732
    depends_on:
      - egohygiene/relay#69
state:
  base:
    revision: 9982088b932750e1480c8e8c717e62580557606a
    ref: refs/heads/main
    verified_at: "2026-09-12T13:49:21Z"
  candidate:
    branch: fix/relay-self-release
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: verified
    observed_at: "2026-09-12T13:49:21Z"
    default_branch_revision: 9982088b932750e1480c8e8c717e62580557606a
    issue_state: open
    pull_request_state: not-applicable
    notes: GitHub confirmed PR 68 merged and issue 67 closed at the represented main revision; issue 69 is open, no competing pull request exists, release run 34697344773 failed before publication, and v1.5.0 remains untagged.
  parallel_changes: []
review:
  status: partial
  reviewed_at: "2026-09-12T13:49:21Z"
  reviewed_by: Codex
  evidence:
    - command: Repository, release history, and live GitHub baseline inspection
      outcome: passed
      observed_at: "2026-09-12T12:45:49Z"
      notes: Relay main, all repository instructions and canonical architecture sources, merged PR 68, failed release run 34697344773, and new issue 69 were inspected before implementation.
    - command: focused release-profile, artifact-workflow, and semantic-release tests; python3 scripts/validate_actions.py; continuity contract validation
      outcome: passed
      observed_at: "2026-09-12T13:49:00Z"
      notes: All 33 focused release tests passed, nine actions and sixteen workflows matched the catalogs, and the continuity profile remained valid.
    - command: full unittest discovery; workflow and action YAML parse; compileall; git diff --check
      outcome: passed
      observed_at: "2026-09-12T13:49:21Z"
      notes: All 212 Relay tests passed; every workflow and action manifest parsed; Python compilation and whitespace validation passed.
  environment_limitations:
    - The task runner is unavailable locally; the documented wrapper could not be invoked.
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
#69. It remains subordinate to user and repository instructions, live Git and
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

Fix the runtime path resolution exposed by Relay's first v1.5.0 dispatch. This
slice succeeds when omitted paths resolve from `GITHUB_ACTION_PATH`, explicit
caller overrides remain authoritative, local and CI checks pass, and immutable
publication precedes OptiFlow's full-SHA repin and v0.1.0 rerun.

## State snapshot

The verified base is Relay `main` at
`9982088b932750e1480c8e8c717e62580557606a`. The candidate branch is
`fix/relay-self-release`; issue #69 is open, no candidate pull request exists,
and these mutable claims must be rechecked before handoff.

## Completed and material changes

- PR #68 merged the v0 authorization regression proof and complete v1.5.0 notes.
- Release run 34697344773 passed default-branch authorization, Relay validation,
  deterministic bundle creation, and read-only release-plan verification.
- The run then failed before tag creation because an input default expanded
  `github.action_path` to empty, yielding `/../../release-profiles.json`.
- The candidate makes the metadata default context-independent, resolves an
  omitted path from runtime `GITHUB_ACTION_PATH`, and preserves explicit paths.

## Validation and review evidence

- Baseline repository, release history, and live GitHub inspection passed before
  implementation.
- All 33 focused release tests, all 212 Relay tests, action/workflow catalog and
  continuity validation, workflow/action YAML parsing, Python compilation, and
  whitespace checks passed locally.
- The `task` executable remains absent locally; exact underlying validators were
  invoked directly where possible.

## Blockers, risks, unknowns, and deferred work

- Release blocker: v1.5.0 cannot be published until issue #69's candidate is
  reviewed, merged, and independently verified on the exact resulting main commit.
- Consumer blocker: OptiFlow must not pin mutable Relay main or the moving v1
  alias; it waits for the immutable released Relay commit.
- Risk: resolving the catalog anywhere except the checked-out action revision
  could validate against mutable or consumer-owned policy; runtime action path
  keeps the catalog bound to the exact Relay revision.
- Deferred: OptiFlow v0.1.0 publication and Relay issue closure follow the Relay
  release and immutable consumer repin.

## Next dependency-ready work

Open and review the Relay #69 candidate. After merge, dispatch v1.5.0 from the
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
