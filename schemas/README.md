# Relay schema ownership

The action and workflow catalog schemas are native to Relay and therefore use
the stable Relay namespace:

```text
https://egohygiene.github.io/relay/contracts/action-catalog/v1/schema.json
https://egohygiene.github.io/relay/contracts/workflow-catalog/v1/schema.json
```

`action-catalog.json` inventories public composite actions and reusable entry
points. `workflow-catalog.json` inventories every current workflow, including
internal validation and release automation, with owner, purpose, permissions,
timeouts, concurrency, caller parameters, and failure semantics.

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
