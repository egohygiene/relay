# Health unknown evidence binding

The pinned Observatory Health query counts freshness independently from assertion
uncertainty. Its `unknown_ids` list is the union of records with unknown freshness
or unknown assertion. A stale record with an unknown assertion can appear in
both `stale_ids` and `unknown_ids`.

The actual Empathy `7639304babcba9d4baf21ccea163f31f9045a0c6` snapshot at
`2026-11-14T01:55:36Z` has one unknown-freshness record and five unknown evidence
IDs. Four dependency repository declarations have current catalog freshness and
unknown runtime assertions. That is valid evidence; it must not be relabelled.

Relay now requires the full canonical graph on the production Health render
path. It independently checks freshness/assertion distributions, exact stale and
unknown ID memberships, and projected check identities and fields. Missing or
inconsistent graph/query data fails. Compact graphless helper calls provide only
structural view validation; production cannot fall back to those calls.

[Retained qualification](evidence/2026-11-14-health-unknown-evidence.json) binds
functional commit `946175a7e56dcfe6e0d43f6264a04f6bd54487d8`, original provider
captures and clocks, native source preparation, actual action build bodies,
seven production tamper denials and unchanged snapshot bytes. Health and the
other routes render, and the deterministic manifest succeeds. Final bundle
validation exposes a separate provider job-URL contract mismatch, retained as a
later hold. This is not complete bundle or hosted publication success.

All 25 Health tests pass. The full candidate and exact base retain identical
12 failures, 24 errors, 93 skips and ten action metadata findings. No collector,
owner runtime, catalog, schema or typed-review contract changes here.

Refs egohygiene/relay#150 and egohygiene/empathy#105.
