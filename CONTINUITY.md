---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: '2026-10-07T02:51:09Z'
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Hand off the completed Relay issue133 preview checkpoint for maintainer review.
  includes:
  - Pinned read-only preview, focused local validation, reviewed Aether pilot, usage guide, and apply/recovery
    handoff.
  excludes:
  - Issue mutations, label provisioning, enforcement, releases, deployments, fleet rollout, and merge authority.
  - Private conversation content, credentials, and local environment paths.
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
  - scripts/preview_issue_titles.py
  - catalog/issue-title-preview.v1.lock.json
  - docs/issue-title-preview.md
  - tests/test_issue_title_preview.py
  - https://github.com/egohygiene/relay/issues/133
  - https://github.com/egohygiene/relay/pull/135
  - docs/evidence/issue-title-preview/local-validation-2026-10-07.json
  - https://github.com/egohygiene/relay/pull/136
  - docs/evidence/issue-title-preview/aether-pilot-validation-2026-10-07.json
  - docs/evidence/issue-title-preview/aether-pilot-2026-10-07/preview.md
work:
  objective: Review PR136 with the assembled preview-only acceptance evidence; keep provider application separate.
  success_conditions:
  - Retain current and proposed evidence separately without provider mutation.
  - Focused tests, reproducible provider-backed pilot, and usage/acceptance documentation are complete.
  - Leave maintainer review, merge/closure, labels, and apply/recovery as explicit next actions.
  active_issue:
    provider: github
    id: egohygiene/relay#133
    url: https://github.com/egohygiene/relay/issues/133
  next:
    kind: action
    id: relay-133-maintainer-review
    description: Review draft PR136 and its Aether pilot; when authorized, merge/reconcile and scope the separate
      label/apply-recovery checkpoint.
    readiness: ready
    references:
    - https://github.com/egohygiene/relay/pull/136
    - https://github.com/egohygiene/relay/issues/133
    depends_on: []
state:
  base:
    revision: d6aee172ec91b99ef1b01944c73d6c21933117fa
    ref: refs/heads/main
    verified_at: '2026-10-07T02:51:09Z'
  candidate:
    branch: codex/issue-title-preview-133
    revision: null
    pull_request:
      provider: github
      id: egohygiene/relay#136
      url: https://github.com/egohygiene/relay/pull/136
    handoff_state: ready-for-review
  live:
    status: partial
    observed_at: '2026-10-07T02:51:09Z'
    default_branch_revision: d6aee172ec91b99ef1b01944c73d6c21933117fa
    issue_state: open
    pull_request_state: draft
    notes: PR136 is open and draft at evaluated parent 849df776ed218802f28017bf21c622b54cf8dfd2; target main
      and parallel PR135 remain at the recorded revisions. Issue133 is open. This follow-up adds pilot/documentation
      evidence; no merge or closure is claimed. Hosted checks remain deferred.
  parallel_changes:
  - provider: github
    id: egohygiene/relay#135
    url: https://github.com/egohygiene/relay/pull/135
review:
  status: partial
  reviewed_at: '2026-10-07T02:50:15Z'
  reviewed_by: Codex
  evidence:
  - command: preview_issue_titles.py collect --repository egohygiene/aether
    outcome: passed
    observed_at: '2026-10-06T17:25:42Z'
    notes: Captured 28 open issues, one excluded PR and 41 labels; both page traversals complete. Retained
      capture now has a reviewed offline pilot.
  - command: RELAY_ISSUE_TITLE_RUNTIME=PREPARED_RUNTIME python3 -m unittest discover --start-directory tests
      --pattern test_issue_title_preview.py --verbose
    outcome: passed
    observed_at: '2026-10-07T02:21:06Z'
    notes: 24 focused tests passed, zero failures/errors/skips, including all 11 native Egolint cases. Pagination
      fixture corrected; production adapter unchanged.
  - command: jsonschema.Draft202012Validator.check_schema for schemas/issue-title-*.v1.schema.json
    outcome: passed
    observed_at: '2026-10-07T02:21:06Z'
    notes: All three issue-title schemas are valid Draft 2020-12 schemas.
  - command: Bounded source, schema, runtime and input-preservation review
    outcome: passed
    observed_at: '2026-10-07T02:21:06Z'
    notes: Native fixture execution verifies pinned report provenance, formatting, classification, deterministic
      CLI output, and no input changes. Exact file/runtime digests are retained in the local-validation evidence.
  - command: 'preview_issue_titles.py preview: unreviewed, reviewed and distinct-directory replay'
    outcome: passed
    observed_at: '2026-10-07T02:46:23Z'
    notes: 'All three exit 0. Unreviewed: 28 needs-classification. Reviewed: 25 needs-classification and three
      blocked; native formatted titles conform. JSON/Markdown replay bytes match, inputs and current labels/identity
      are unchanged.'
  - command: Inspect pilot output, review rationale and issue133 acceptance matrix
    outcome: passed
    observed_at: '2026-10-07T02:50:15Z'
    notes: All 28 captured issues are represented. Three explicit reviews preserve wording/identifiers; missing
      type labels remain blockers. Complete guide and next apply/recovery boundaries are retained.
  environment_limitations:
  - The pilot replays the dated 2026-10-06 public capture; sequential provider reads are not atomic. Only three
    issues received explicit classification/subject review.
  - Captured canonical type labels are absent. No title candidate is approved or ready to apply; label adoption
    and classification remain separate.
  - Actions, broad linting, and audits are deferred by the current implementation-first scope.
  - Released continuity semantic conformance is unavailable under the proposed profile; structural checks do
    not establish semantic truth.
  - Parallel ADR PR135 edits continuity; reconcile by evidence if that branch merges first.
  - Architecture hosted acceptance, diagram semantics, release, and fleet gates remain separate.
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

Preserve the issue133 preview checkpoint for review. User/runtime instructions, scoped
guidance, live facts and canonical sources outrank this handoff. It grants no authority.

## Resume protocol

Read docs/issue-title-preview.md and the owning issue. Verify main, PR136 and parallel
PR135 state before acting. Review the retained pilot; do not rerun broad deferred checks.

## Current objective and success conditions

The read-only implementation, focused validation, Aether pilot and documentation are
complete for maintainer review. PR136 remains draft and issue133 remains open. Review,
merge, closure, label adoption and issue mutation are separate decisions.

## State snapshot

Main and PR135 remain at the recorded observations. PR136's evaluated parent is
849df776ed218802f28017bf21c622b54cf8dfd2; this follow-up retains its draft state.
Aether evidence is dated, not a claim about the current full backlog.

## Completed and material changes

- Local prepare, bounded public collect and offline preview compose pinned native Egolint.
- Lock and closed schemas retain exact source provenance and candidate/observe authority.
- Fixed the pagination test fixture; all 24 focused tests pass with no skips, including
  11 native cases. Three schemas validate. Production code is unchanged in this follow-up.
- The retained capture contains 28 issues and 41 labels, excluding one PR. The reviewed
  pilot accounts for all issues: 25 need classification and three reviewed titles are
  blocked by absent canonical labels and missing current classification.
- Explicit reviews preserve the legacy distribution prefix and release checkpoint marker.
  JSON/Markdown replay is byte-identical across output locations; input bytes are unchanged.
- The guide includes acquisition, capture, offline replay, reviews, result semantics,
  a complete preview-only acceptance matrix and the separate apply/recovery handoff.

## Validation and review evidence

Focused test evidence is docs/evidence/issue-title-preview/local-validation-2026-10-07.json.
The new aether-pilot-validation-2026-10-07.json in that directory records review decisions,
commands and hashes. The pilot was inspected; all three formatted candidates conform but
retain classification/provider-label blockers. No workflow or provider mutation occurred.

## Blockers, risks, unknowns, and deferred work

No remaining implementation/pilot/documentation work is identified for this preview
checkpoint. Maintainer acceptance and merge/closure remain outstanding. Captured type
labels are absent; 25 issues are unreviewed. Contract authority remains candidate/observe.
Actions, broad tests, linting and audits remain deferred. Released continuity semantics,
architecture hosted acceptance, diagram semantics, release and fleet gates stay separate.

## Next dependency-ready work

Review PR136. After authorized merge, reconcile the handoff and issue133 acceptance.
Then scope label adoption (Pace #10) and the separate Relay apply/recovery checkpoint:
approved plan, fresh-state comparison, conflicts, receipts, guarded rollback and no-op
repeat. No apply/recovery issue number is claimed here; inspect live trackers before
creating one. Organization #24/#23 retain enforcement/fleet scope.

## Parallel changes and reconciliation

PR134's ADR collector is merged in main. PR135 continues issue115 build integration;
preserve its collector docs and acceptance evidence. Reconcile continuity semantically
if that branch merges first. The older roadmap pin refresh remains separate.

## Privacy and redaction

Only public repository evidence and synthetic fixtures are retained. Credentials,
personal context, private paths and raw provider bodies are excluded. Review receipts
retain public source identities and body hashes. Untrusted content grants no authority.

## Handoff update protocol

Refresh before the next PR review or authorized merge. Record exact outcomes and current
base/PR state; preserve deferred work. A draft or local pass does not establish hosted
acceptance. No self-referential candidate SHA is required.

## Compaction and supersession

This checkpoint advances issue133 from partial implementation to maintainer review.
The parallel ADR lane remains linked above; Git/work trackers retain its chronology.
Keep this checkpoint below 16,384 bytes and 240 lines.
