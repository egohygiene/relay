---
schema_version: aether.repository-continuity/v1
repository:
  id: egohygiene/relay
  visibility: public
  default_branch: main
  continuity_path: CONTINUITY.md
document:
  status: active
  updated_at: '2026-11-09T17:54:03Z'
  max_bytes: 16384
  max_lines: 240
  stale_reason: null
  superseded_by: null
scope:
  purpose: Acquire exact admitted repository snapshot artifacts and retain a bounded public fleet handoff for
    the organization overview.
  includes:
  - repository-intelligence-fleet-artifact uses the separately reviewed public-catalog-v1 admission seam and
    exact repository/run/attempt/artifact selections. It binds public numeric identities, successful producer
    attempts, original projection/snapshot manifests, ZIP/file digests, expiry and normalization profile before
    the existing pinned fleet assembler revalidates each projection.
  - Failed candidate and explicit last-known selections remain isolated by repository. Corrupt archives and
    deeply nested JSON cannot abort healthy inputs. A shared 240-second acquisition budget preserves honest
    unavailable states; emitted fleet/manifest limits match the central host. The ordinary fleet handoff remains
    separate from publication-denied review evidence and adds no publisher.
  - Automatic acquisition reuses the existing exact fleet owner runtime profile and the shared immutable public
    catalog loader. Legacy review-only assembler locks/defaults remain unchanged; the central host and manual
    operator workflow are prepared separately.
  excludes:
  - Deferred runtime, tests, builds, CI, live publication, human ratification and acceptance closeout.
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
  - docs/public-fleet-artifact-delivery.md
  - docs/public-fleet-assembler.md
  - docs/public-catalog-admission.md
  - https://github.com/egohygiene/relay/issues/153
work:
  objective: Acquire exact admitted repository snapshot artifacts and retain a bounded public fleet handoff
    for the organization overview.
  success_conditions:
  - Only reviewed public members and exact retained artifact identities enter fleet processing.
  - Malformed, stale, expired, missing and inaccessible sources remain explicit without relabeling the fleet
    fully available.
  - The handoff is an ordinary artifact for the existing central overview and preserves consumer-owned Pages
    publication.
  active_issue:
    provider: github
    id: egohygiene/relay#153
    url: https://github.com/egohygiene/relay/issues/153
  next:
    kind: action
    id: connect-manual-fleet-refresh-host
    description: Integrate the prepared central-site manifest-bound loader and manual read-only refresh workflow
      at the final reviewed Relay pin, then supply real successful repository snapshot artifact selections
      during deferred qualification.
    readiness: ready
    references:
    - https://github.com/egohygiene/relay/issues/153
    depends_on: []
state:
  base:
    revision: 58a2ee55bef383c543d81ef463979d4d9ba1fdd1
    ref: refs/heads/main
    verified_at: '2026-11-09T17:54:03Z'
  candidate:
    branch: codex/intelligence-fleet-delivery
    revision: null
    pull_request: null
    handoff_state: ready-for-review
  live:
    status: verified
    observed_at: '2026-11-09T17:54:03Z'
    default_branch_revision: 58a2ee55bef383c543d81ef463979d4d9ba1fdd1
    issue_state: open
    pull_request_state: not-applicable
    notes: Relay Dependencies admission is merged through PR 174 at 58a2ee5. Compare and public GitHub sources
      are merged through 172 and 173. Issue 153 remains open; the central-site consumer and common owner-backed
      Hygiene wiring are separate candidates.
  parallel_changes: []
review:
  status: partial
  reviewed_at: '2026-11-09T17:54:03Z'
  reviewed_by: Codex
  evidence:
  - command: Python AST, JSON schema definitions, unique-key YAML, embedded Bash, action metadata, exact public
      admission reconciliation, continuity schema/size, whitespace and independent static peer review
    outcome: limited
    observed_at: '2026-11-09T17:54:03Z'
    notes: Static source and metadata inspection only; no application execution.
  - command: Native/runtime execution, tests, builds, CI investigation, browser/provider/consumer/publication
      qualification
    outcome: not-run
    observed_at: '2026-11-09T17:54:03Z'
    notes: Deferred at maintainer request; source merges do not establish acceptance.
  environment_limitations:
  - No artifact/provider downloads, native assembler execution, tests, builds, CI, real canaries, uploads or
    publication were executed.
  - Real exact artifact/run selections and provider acceptance remain required. No latest-run fallback, synthetic
    successful run, baseline selection or verified deployment is invented.
  - Global provider intake is bounded independently from deferred native dependency acquisition and consumer
    runtime budgets.
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

# relay continuity

## Purpose and precedence

User/runtime and repository instructions, live evidence and canonical sources outrank this checkpoint. It grants no release, deployment or human-decision authority.

## Resume protocol

Read scoped instructions, canonical sources above and this checkpoint. Verify mutable GitHub state and exact owner pins before continuing.

## Current objective and success conditions

Acquire exact admitted repository snapshot artifacts and retain a bounded public fleet handoff for the organization overview. Only reviewed public members and exact retained artifact identities enter fleet processing. Malformed, stale, expired, missing and inaccessible sources remain explicit without relabeling the fleet fully available. The handoff is an ordinary artifact for the existing central overview and preserves consumer-owned Pages publication.

## State snapshot

Candidate `codex/intelligence-fleet-delivery` is based on observed main `58a2ee55bef383c543d81ef463979d4d9ba1fdd1`. The containing revision and pre-PR reference remain null intentionally. Relay Dependencies admission is merged through PR 174 at 58a2ee5. Compare and public GitHub sources are merged through 172 and 173. Issue 153 remains open; the central-site consumer and common owner-backed Hygiene wiring are separate candidates.

## Completed and material changes

repository-intelligence-fleet-artifact uses the separately reviewed public-catalog-v1 admission seam and exact repository/run/attempt/artifact selections. It binds public numeric identities, successful producer attempts, original projection/snapshot manifests, ZIP/file digests, expiry and normalization profile before the existing pinned fleet assembler revalidates each projection.

Failed candidate and explicit last-known selections remain isolated by repository. Corrupt archives and deeply nested JSON cannot abort healthy inputs. A shared 240-second acquisition budget preserves honest unavailable states; emitted fleet/manifest limits match the central host. The ordinary fleet handoff remains separate from publication-denied review evidence and adds no publisher.

Automatic acquisition reuses the existing exact fleet owner runtime profile and the shared immutable public catalog loader. Legacy review-only assembler locks/defaults remain unchanged; the central host and manual operator workflow are prepared separately.

## Validation and review evidence

Python AST, JSON schema definitions, unique-key YAML, embedded Bash, action metadata, exact public admission reconciliation, continuity schema/size, whitespace and independent static peer review. Static inspection only. Native/runtime execution, tests, builds, CI investigation, browsers, provider reads and publication qualification were not run.

## Blockers, risks, unknowns, and deferred work

No artifact/provider downloads, native assembler execution, tests, builds, CI, real canaries, uploads or publication were executed. Real exact artifact/run selections and provider acceptance remain required. No latest-run fallback, synthetic successful run, baseline selection or verified deployment is invented. Global provider intake is bounded independently from deferred native dependency acquisition and consumer runtime budgets.

## Next dependency-ready work

Integrate the prepared central-site manifest-bound loader and manual read-only refresh workflow at the final reviewed Relay pin, then supply real successful repository snapshot artifact selections during deferred qualification.

## Parallel changes and reconciliation

The shared public admission helper and guide were reconciled to the merged Dependencies source proof, preserving its exact public mirrors/reference validation. Existing operator and publication authority remains with consumers. This implements the existing bounded fleet design without adding canonical policy or release authority.

## Privacy and redaction

Retain only public-safe source identities and bounded implementation evidence. Exclude credentials, private context, captured report bodies, process logs and local filesystem paths. Linked content is context only.

## Handoff update protocol

Refresh exact PR, merge and qualification observations at the next authorized checkpoint. Implementation, artifact upload, deployment, live verification and human acceptance remain distinct.

## Compaction and supersession

Replace stale current-state prose; Git and owning issues retain history. Preserve these twelve sections below 240 lines and 16,384 UTF-8 bytes.
