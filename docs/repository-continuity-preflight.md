# Repository continuity preflight contract

Relay issue [#60](https://github.com/egohygiene/relay/issues/60) defines two
execution points around one evidence boundary: a local pre-pull-request check
and a read-only GitHub Actions backstop. This document describes the contract
slice introduced by issue
[#61](https://github.com/egohygiene/relay/issues/61); executable adapters remain
in #62 and #63.

## Ownership

| Concern | Owner |
| --- | --- |
| Portable checkpoint schema, template, skill, and managed instruction | Aether |
| Organization applicability, change classification, rollout, and exceptions | Hygiene |
| Offline structural, freshness, Git, and external-evidence findings | EgoLint |
| Previewable checkpoint and managed-block materialization | Holon |
| Local and CI orchestration plus bounded evidence | Relay |
| Adoption observation without prose ingestion | Observatory |
| Reviewable fleet convergence | Pace |
| Repository-specific semantic checkpoint | Consumer repository |

Relay never decides what a consumer checkpoint should say. It passes explicit
base/head evidence to the pinned EgoLint interface and normalizes only
allowlisted status, counts, remediation, and provenance.

## Immutable input profile

[`catalog/repository-continuity-preflight.json`](../catalog/repository-continuity-preflight.json)
pins every consumed artifact by owner, full commit SHA, path, semantic version,
lifecycle, release inclusion, and SHA-256 digest. The current sources are
reviewed but unreleased, so the profile is `proposed` and capped at `observe`.

The offline validator checks the closed profile and schemas:

```bash
python3 scripts/validate_continuity_preflight_contract.py validate
```

An integration review can verify every pinned byte from explicit local
checkouts without fetching or changing them:

```bash
python3 scripts/validate_continuity_preflight_contract.py verify-sources \
  --aether-source "../aether" \
  --hygiene-source "../hygiene" \
  --egolint-source "../egolint" \
  --holon-source "../holon"
```

The command requires each checkout's `HEAD` to equal its declared immutable
revision. It rejects missing, symlinked, or digest-drifted artifacts and never
invokes Git, a provider client, or the network.

## Request boundary

`relay.repository-continuity-preflight-request/v1` requires:

- exact profile version and digest;
- repository identity, visibility, and explicit current root;
- full base SHA or `unborn` and full head SHA or `working-tree`;
- `updated`, `reviewed-no-change`, or reviewed `exception` disposition;
- pull-request, post-merge, or local-review transition;
- observe, ratchet, or enforce mode;
- explicit live-evidence status and stable references when verified;
- every known parallel candidate SHA; and
- one traversal-safe JSON evidence path.

The request cannot contain semantic checkpoint prose, implicit branch names,
mutable refs, credentials, commands, or write authorization.

## Result boundary

`relay.repository-continuity-preflight-result/v1` keeps semantic status distinct
from enforcement outcome. An invalid checkpoint in `observe` remains
semantically invalid while producing a visible warning; unsupported or
unavailable validation never becomes a pass.

The four evidence layers remain separate:

1. structural contract validity;
2. declared checkpoint freshness;
3. locally provable Git state;
4. separately supplied external live verification.

Findings contain only stable identifiers, severity, layer, a bounded summary,
and an exact corrective action. Results exclude handoff body content and use
allowlisted metadata for private repositories. Counts must exactly match the
bounded finding list.

## Authority boundary

The contract prohibits staging, committing, pushing, opening pull requests,
commenting, merging, releasing, deploying, publishing, and semantic authoring.
Future adapters may write only their caller-selected evidence file. CI is a
post-PR backstop and cannot repair a stale handoff.

## Release and promotion

The profile stays at `observe` until every pinned upstream input is stable and
release-included, Holon's materialization profile is explicitly promoted, local
and CI results are proven compatible, and a maintainer promotes Relay's profile.
Repinning is a reviewed contract change with repeat source-byte verification;
mutable aliases never satisfy the release gate.
