---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: "2026-09-12T14:37:58Z"
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Preserve the minimum verified state needed to release Relay's product-facing release-name contract safely.
  includes:
    - The active issue, represented Git state, contract validation, v1.6.0 release gate, and OptiFlow consumer dependency.
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
    - .github/workflows/semantic-release.yml
    - .github/workflows/release-artifact.yml
work:
  objective: Separate consumer product release names from Relay artifact-class validation profiles.
  success_conditions:
    - Accept an optional bounded product-facing release name while retaining the profile as validation authority.
    - Preserve profile-derived naming when the new input is omitted.
    - Use the resolved name consistently for archives, tags, releases, notes, and resume checks.
    - Publish the additive contract as v1.6.0 before OptiFlow adopts release-name optiflow.
  active_issue:
    provider: github
    id: egohygiene/relay#71
    url: https://github.com/egohygiene/relay/issues/71
  next:
    kind: pull-request
    id: egohygiene/relay#72
    description: Review and merge the validated Relay issue 71 candidate.
    readiness: ready-for-review
    references:
      - https://github.com/egohygiene/relay/issues/71
      - https://github.com/egohygiene/relay/pull/72
    depends_on: []
state:
  base:
    revision: 1eada5142f7fc7da7862f335589e3b8f5884ffaf
    ref: refs/heads/main
    verified_at: "2026-09-12T14:25:37Z"
  candidate:
    branch: fix/71-release-name
    revision: null
    pull_request: https://github.com/egohygiene/relay/pull/72
    handoff_state: ready-for-review
  live:
    status: verified
    observed_at: "2026-09-12T14:37:58Z"
    default_branch_revision: 1eada5142f7fc7da7862f335589e3b8f5884ffaf
    issue_state: open
    pull_request_state: open
    notes: Pull request 72 carries the validated contract tree; Relay v1.5.0 and OptiFlow v0.1.0 are published, OptiFlow's immutable first release retains the legacy binary-derived outer asset name, and Relay v1.6.0 remains untagged.
  parallel_changes: []
review:
  status: complete
  reviewed_at: "2026-09-12T14:37:58Z"
  reviewed_by: Codex
  evidence:
    - command: Repository instructions, architecture sources, issue and pull-request state, releases, and consumer evidence inspection
      outcome: passed
      observed_at: "2026-09-12T14:25:37Z"
      notes: Relay main and v1.5.0, issue 71, no competing release pull request, and OptiFlow's v0.1.0 naming evidence were verified before implementation.
    - command: Focused release-artifact, semantic-release, workflow-catalog, and release-profile tests; action catalog validation; continuity contract validation; YAML parse; compileall; git diff check
      outcome: passed
      observed_at: "2026-09-12T14:30:02Z"
      notes: Custom and fallback naming, unsafe-name rejection, shell syntax, catalog alignment, and immutable resume checks passed.
    - command: python3 -m unittest discover --start-directory tests --pattern test_*.py --verbose
      outcome: passed
      observed_at: "2026-09-12T14:30:45Z"
      notes: All 213 Relay tests passed.
    - command: verify_release_plan.py --mode plan for v1.6.0
      outcome: passed
      observed_at: "2026-09-12T14:31:58Z"
      notes: The exact candidate commit produced verified unpromoted release-plan evidence with the v1.6.0 tag available.
    - command: Compare local candidate tree with GitHub pull request 72 head tree
      outcome: passed
      observed_at: "2026-09-12T14:37:58Z"
      notes: Both resolved to tree 4d3d0de1d86e88ecc9d4940e67230b3e925ea0f7 before this checkpoint-only handoff update.
  environment_limitations:
    - The task runner is unavailable locally; documented underlying commands were invoked directly.
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
#71. It remains subordinate to user and repository instructions, live Git and
GitHub evidence, and the canonical sources listed above; it grants no authority.

## Resume protocol

1. Read `AGENTS.md`, inspect the checkout, and load the named canonical sources.
2. Verify issue, pull-request, branch, tag, release, and default-branch claims live.
3. Continue only the named dependency-ready work and keep publication explicit.

## Current objective and state

Issue #71 separates product-facing release identity from Relay's generic
artifact-class profile. The verified base is released Relay v1.5.0 at
`1eada5142f7fc7da7862f335589e3b8f5884ffaf`. Pull request #72 adds an optional
`release-name`, falls back to the profile for compatibility, and prepares
unpromoted v1.6.0.

## Material changes and evidence

- `release-artifact.yml` validates a lowercase kebab-case release name and uses
  it for the outer archive, tag subject, Release title, notes, and resume lookup.
- `semantic-release.yml` and Relay dogfood propagate explicit product identity;
  Relay's own next archive is named `relay-v1.6.0.tar.gz`.
- Existing callers that omit the input retain their previous profile-derived
  archive, title, notes, and resume behavior.
- ADR-009, catalog metadata, examples, version authority, and release docs agree.
- Focused checks, all 214 tests, catalog and continuity validation, YAML parsing,
  Python compilation, whitespace checks, and v1.6.0 plan verification passed.

## Blockers, risks, and deferred work

- Relay v1.6.0 must not be published until the candidate is reviewed, merged,
  and promoted through the repository's release gate on the exact new main.
- OptiFlow cannot pass `release-name: optiflow` while pinned to Relay v1.5.0;
  it must wait for the immutable v1.6.0 commit and then repin.
- OptiFlow v0.1.0 is immutable historical evidence. Correct product naming begins
  with its next version instead of deleting or replacing the published assets.

## Next dependency-ready work

Review and merge pull request #72. After merge, promote and publish Relay
v1.6.0, verify its `relay-v1.6.0.tar.gz` asset and v1 alias, then repin OptiFlow
and add `release-name: "optiflow"` before its next release.

## Parallel changes and reconciliation

No competing open release pull request was observed. Recheck remote heads and
pull requests before review, then reconcile semantically if another branch
changes the same public workflows or checkpoint.

## Privacy and compaction

This public checkpoint contains only public repository, Git, GitHub, contract,
and validation state. Keep it below 16,384 UTF-8 bytes and 240 lines, and replace
stale state instead of accumulating history.
