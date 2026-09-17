# Legacy workflow quarantine and graduation

Legacy workflow intake is an evidence-review process, not an activation path.
Relay may preserve a historical workflow so its behavior can be studied, but a
candidate is not supported automation until it has been normalized, tested,
cataloged, reviewed, and released through Relay's current contracts.

This policy operationalizes ADR-001, ADR-002, ADR-003, ADR-005, and ADR-006.
It does not expand Relay's authority or turn a legacy repository into a source
of executable policy.

## Lifecycle

```text
inventory + provenance
        -> quarantined candidate
        -> security and permission review
        -> contract normalization
        -> isolated validation
        -> reviewed Relay implementation
        -> immutable Relay release
        -> consumer-owned adoption
```

A candidate can instead end in one of three archival dispositions:

- **rejected** — unsafe, obsolete, out of scope, or not worth normalizing;
- **superseded** — a supported Relay capability already owns the behavior; or
- **graduated** — retained only as provenance after a separately implemented
  Relay workflow has passed the full release path.

These dispositions describe evidence. They never make the captured bytes
executable.

## Executable boundary

GitHub discovers workflows under `.github/workflows/`. Quarantined and archived
evidence must therefore stay outside that directory and use a non-runnable
suffix:

```text
tests/fixtures/legacy-workflows/
  quarantine/<candidate-id>/
    candidate.json
    workflow.yml.disabled
  archive/<disposition>/<candidate-id>/
    candidate.json
    workflow.yml.disabled
```

The following rules are invariant:

- never place a candidate, rejected, superseded, or graduated copy under
  `.github/workflows/`;
- never use `.yml` or `.yaml` as the final suffix for quarantined evidence;
- do not rely on `workflow_dispatch`, `workflow_call`, a false job condition,
  or branch filters as quarantine: those files remain executable workflows;
- keep evidence as ordinary files, not symlinks or generated links into the
  executable boundary;
- keep every retained evidence record out of `workflow-catalog.json` and
  `action-catalog.json`; the catalogs describe only current Relay packages;
- do not reference quarantined files from an active workflow, action, or
  consumer example; and
- do not copy secrets, credentials, private configuration, or private workflow
  bodies into the public Relay repository.

## Intake record

Every candidate directory contains exactly one manifest and one disabled
workflow artifact. `candidate.json` is internal review evidence, not a public
Relay schema or release contract. It records at least:

- a stable candidate identifier and current lifecycle state;
- the disabled artifact path and SHA-256;
- source repository, original path, exact observed revision, and immutable
  source URL when publication is allowed;
- capture mode, transformations, and redactions;
- observed triggers, permissions, token/secret interfaces, dependencies,
  mutations, deployment behavior, repository assumptions, and reusable
  suitability;
- review findings, disposition, blockers, and any replacement evidence; and
- review date and reviewer role.

Preserve public source bytes verbatim when practical. If normalization is
needed merely to store a safe fixture, enumerate every transformation and
retain the original hash in authorized evidence.

For restricted or private sources, keep exact repository/path/revision evidence
only in an authorized system. The public manifest may contain an opaque source
reference, review conclusions, and an explicit redaction reason. Its artifact
must be the fixed metadata-only redaction stub enforced by the guard tests, not
sanitized workflow-shaped bytes. The public record must not expose the workflow
body, repository identity, secret names that are themselves sensitive, internal
endpoints, immutable source identifiers, or private paths.

## Review gates

A candidate remains dormant until all applicable gates are answered with
evidence.

| Gate | Required review |
| --- | --- |
| Triggers and trust | Enumerate every event, actor, ref, fork path, reusable caller, schedule, and recursion risk. Reject `pull_request_target` and any route that combines untrusted code with privileged credentials. |
| Permissions | Reduce default and job permissions to the least privilege. Reject `write-all`; separate read/plan work from mutation, deployment, and publication. |
| Secrets and tokens | Record names/contracts and trust sources without values. Identify implicit `GITHUB_TOKEN`, persisted checkout credentials, OIDC, app tokens, environments, and protected-secret exposure. |
| Dependencies | Pin remote actions to full commit SHAs and containers/downloads to immutable digests or verified checksums. Review licenses and network acquisition. |
| Mutation and deployment | Identify every workspace, repository, release, registry, deployment, issue, PR, and external side effect. Define authorization, idempotency, concurrency, rollback, retry, and partial-failure behavior. |
| Reusable contract | Replace event- or repository-specific assumptions with typed inputs, outputs, permission ceilings, timeouts, concurrency, and explicit failure semantics. |
| Repository assumptions | Find hard-coded branches, paths, package managers, runners, tools, environments, artifact names, and provider settings. Keep consumer policy consumer-owned. |
| Evidence and privacy | Bound logs and artifacts, preserve provenance, distinguish unknown/partial states, and exclude secrets and inappropriate private data. |
| Testability | Prove behavior in an isolated temporary repository or fixture without relying on production credentials, branches, deployments, or mutable external state. |

The review assesses ideas, not just syntax. A full-SHA action pin does not make
an automatically triggered write workflow safe, and an unchanged copy is not a
reusable Relay contract.

## Normalization and isolated validation

Graduation work creates a new Relay implementation; it does not rename or move
the captured file into place. The implementation must:

1. assign a Relay owner and a single bounded purpose;
2. define typed caller inputs, outputs, permission ceilings, runtime bounds,
   concurrency, and honest failure/recovery semantics;
3. split review/plan from apply/publish when authority differs;
4. remove or explicitly parameterize source-repository assumptions;
5. use immutable dependencies and verified acquisition;
6. avoid persisted credentials except where a reviewed mutation boundary
   strictly requires them;
7. validate in an isolated fixture, including untrusted, no-op, failure,
   partial-state, retry, and idempotent cases; and
8. document local reproduction and emergency disable/rollback behavior.

Tests for the quarantine itself must prove that captured artifacts stay
disabled, provenance remains complete, catalogs exclude candidates, and active
automation never imports or invokes the evidence tree.

## Graduation

A normalization pull request is reviewable only when one change atomically
provides:

- a normalized implementation under the proper Relay action or workflow path;
- isolated positive and negative tests;
- explicit workflow/action YAML contracts;
- a `workflow-catalog.json` entry for every executable workflow and an
  `action-catalog.json` entry for every public action or reusable workflow;
- human documentation, adoption guidance, and changelog evidence; and
- passing canonical validation and dependency review.

Catalog status such as `experimental` describes a real executable Relay
contract; it is not a quarantine state. Candidates remain uncataloged until
the normalized implementation is ready to enter the supported surface.

After that pull request merges, publish and verify an immutable Relay release.
A dedicated follow-up then **moves** the evidence record to the `graduated`
archive and records the implementation commit, release, and replacement
relationship; copying is prohibited because one candidate ID has exactly one
lifecycle location. The original captured artifact remains disabled.

Consumer adoption follows graduation. Consumers pin the reviewed full commit
SHA and retain their own mutation, deployment, merge, and release authority.
Adoption evidence may be a separate rollout gate; it is not fabricated inside
the implementation pull request or required before the immutable Relay
capability can be recorded as graduated.

## Rejection and supersession

Rejected and superseded records remain non-executable and uncataloged. Record
the reason, reviewer, date, and—when applicable—the supported replacement and
its immutable release evidence. Never delete history merely to make the intake
queue look clean; remove public evidence only when retention would violate a
license, privacy boundary, or explicit repository policy.

## Representative fixture

The fixture under
`tests/fixtures/legacy-workflows/archive/superseded/relay-automatic-release-v1/`
preserves a public historical Relay release workflow from an immutable
revision. Although its third-party actions were pinned, it coupled an automatic
path trigger and repository-wide write token to validation, persisted checkout
credentials, tag mutation, GitHub Release creation, and a force-updated major
alias in one job. Relay's current split release workflows supersede that design.
The disabled artifact, replacement evidence, and guard tests demonstrate both
intake review and terminal archival without reactivating the old workflow.
