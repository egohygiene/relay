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
