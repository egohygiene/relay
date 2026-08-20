# Relay schema ownership

`action-catalog.schema.json` is native to Relay and therefore uses the stable
Relay namespace:

```text
https://egohygiene.github.io/relay/contracts/action-catalog/v1/schema.json
```

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
