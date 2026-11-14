# Provider reference compatibility

The Health collector admits canonical same-consumer `/actions/runs/N/job/J` and
`/runs/N` check URLs with positive decimal identifiers. The bundle validator now
recognizes those existing shapes, while preserving exact repository identity,
canonical HTTPS origin, query/fragment/credential and traversal boundaries.
Check deep links remain consumer-only even if another repository is admitted.

Search also renders canonical bare repository roots for declared dependencies.
Those roots now validate only when the exact repository is already in that
HTML document's existing source membership. This changes route recognition,
not repository membership, catalog scope or public admission.

The [retained qualification](evidence/2026-11-14-provider-reference-compatibility.json)
binds verifier `396e2a82f581a18d6d5618353e1ab561ae91269b`, the unchanged Health
producer `946175a7e56dcfe6e0d43f6264a04f6bd54487d8`, consumer source
`7639304babcba9d4baf21ccea163f31f9045a0c6`, and captured boundary
`2026-11-14T01:55:36Z`. All 30 retained bundle files now validate without any
byte change. The original twelve rejected references (eight unique URLs) are
accepted within their original document source sets; unsafe and unadmitted
forms still deny. All eight new reference tests pass; an independent peer ran
18 focused reference/bundle tests and replayed all 2,358 references.

The producer, captures, manifest, owner profiles and Health evidence are not
regenerated or retimed. Fresh final immutable consumer adoption and hosted
artifact/deployment/live acceptance remain separate.

Refs egohygiene/empathy#105 and egohygiene/empathy#98.
