# Relay schema ownership

The action and workflow catalog schemas are native to Relay and therefore use
the stable Relay namespace:

```text
https://egohygiene.github.io/relay/contracts/action-catalog/v1/schema.json
https://egohygiene.github.io/relay/contracts/workflow-catalog/v1/schema.json
https://egohygiene.github.io/relay/contracts/release-profiles/v1/schema.json
https://egohygiene.github.io/relay/contracts/cargo-crate-release/v1/schema.json
https://egohygiene.github.io/relay/contracts/python-package-release/v1/schema.json
https://egohygiene.github.io/relay/contracts/release-plan-evidence/v1/schema.json
https://egohygiene.github.io/relay/contracts/release-publication-outcome/v1/schema.json
https://egohygiene.github.io/relay/contracts/repository-continuity-preflight-profile/v1/schema.json
https://egohygiene.github.io/relay/contracts/repository-continuity-preflight-request/v1/schema.json
https://egohygiene.github.io/relay/contracts/repository-continuity-preflight-result/v1/schema.json
https://egohygiene.github.io/relay/contracts/artifact-budget-report/v1/schema.json
https://egohygiene.github.io/relay/contracts/repository-journal-runtime-profile/v1/schema.json
https://egohygiene.github.io/relay/contracts/repository-journal-runtime-preflight-result/v1/schema.json
https://egohygiene.github.io/relay/contracts/repository-journal-evidence/v1/schema.json
https://egohygiene.github.io/relay/contracts/repository-journal-candidate/v1/schema.json
https://egohygiene.github.io/relay/contracts/repository-journal-result/v1/schema.json
https://egohygiene.github.io/relay/contracts/repository-journal-aether-profile/v1/schema.json
```

`action-catalog.json` inventories public composite actions and reusable entry
points. `workflow-catalog.json` inventories every current workflow, including
internal validation and release automation, with owner, purpose, permissions,
timeouts, concurrency, caller parameters, and failure semantics.

`release-profiles.json` defines Relay's immutable artifact profiles.
`cargo-crate-release/v1` defines the component, manifest authority, crate, and
external-registry record required by the `cargo-crate` profile.
`python-package-release/v1` defines the component, authority, distribution,
and external-registry record required by the `python-package` profile.
`release-plan-evidence/v1` records deterministic semantic-release preparation
success or bounded failure without copying Aether's declaration schema.
`release-publication-outcome/v1` retains the preparation and immutable
publication job results even when the write handoff fails.
The continuity-preflight profile pins Aether, Hygiene, EgoLint, and Holon
inputs; its request and result schemas keep local and future CI evidence
byte-compatible without copying or publishing consumer handoff prose.
The artifact-budget report normalizes bounded filesystem and Size Limit JSON
measurements, baseline deltas, thresholds, coverage, and enforcement state.
The repository-journal runtime profile locks the Copilot CLI package and
authentication choices; its preflight result records only credential presence,
policy and permission assertions, version evidence, and safe failure reasons.
The repository-journal Aether profile binds the upstream draft contract,
renderer, schema, template, and distribution metadata to one immutable commit
and verifies every vendored byte before execution.

The schemas packaged inside the Intelligence actions intentionally retain the
public identities established while the implementation was incubated in
Empathy:

| Contract | Preserved `$id` namespace |
| -------- | ------------------------- |
| Repository analytics | `https://egohygiene.github.io/contracts/...` |
| Repository tree | `https://egohygiene.github.io/contracts/...` |
| Normalized producer report | `https://egohygiene.dev/schemas/...` |
| Dashboard aggregate | `https://egohygiene.dev/schemas/...` |

Moving implementation ownership does not rename serialized data. Unifying
these namespaces later requires explicit v2 schemas, compatibility guidance,
and permanent redirects; v1 must not drift silently.
