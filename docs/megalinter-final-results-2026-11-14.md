# Finalized MegaLinter report qualification

Refs [Empathy #98](https://github.com/egohygiene/empathy/issues/98),
[#105](https://github.com/egohygiene/empathy/issues/105) and
[organization #41](https://github.com/egohygiene/.github/issues/41).

## Actual source and failure

Actual manual [run 43543368762, attempt 1](https://github.com/egohygiene/empathy/actions/runs/43543368762)
represents Empathy `7639304babcba9d4baf21ccea163f31f9045a0c6`. Its scan job
failed and the snapshot writer was skipped. The dedicated normalized artifact
`14092703255` has archive SHA-256
`629515244e93a691796f64afb690cb885cfca3f3f1c4dbebf74ffd91bfa50a28`;
its summary payload is `c13105386260953b9a34e6cb96e8164797faaefa4b520670a3049f63bbde884c`.

The existing summary already preserves runner failure. Its incorrect tool
counts come from the detailed reporter's pre-run `active_linters`: all 50
entries still say success with zero diagnostics. The canonical final `linters`
collection has 101 entries, of which 50 are explicitly active: 21 success,
8 warning and 21 error. Native JSON Reporter at the exact MegaLinter source
selects that collection; its simple format also emits finalized active rows.

## Bounded correction

The normalizer prefers final `linters`, filters explicit active rows and checks
unique identities against any declared active inventory. Valid legacy
`active_linters`-only reports remain supported. Explicit invalid or empty final
collections never fall back. Missing/invalid selected status or counts,
duplicate JSON keys/tool identities and ambiguous policy bindings produce
failed execution with unknown findings. Unselected disabled policy entries
remain valid; contradictory active disabled selections fail admission.

Existing policy classifications, schema, original execution state, clocks,
source/provenance and links are preserved. The original native 124-tool matrix
contains 19 disabled rows; none is selected by this actual scan. No runtime,
bootstrap, scanner configuration, normalizer schema or snapshot publisher is
changed. Historical summaries remain immutable.

## Native reproduction and evidence

The frozen `1eada5142f7fc7da7862f335589e3b8f5884ffaf` normalizer reproduced the
actual old summary byte-for-byte from the full 42,296,168-byte raw report and
original canonical policy. Corrected functional source
`b8721978957c04d5c29c09d0821bd4e4729f40a1` processed those same bytes at the
original source and `2026-11-14T02:00:58Z` generation boundary:

| Field | Original | Corrected |
| --- | --- | --- |
| Execution | failure | failure |
| Active / passed tools | 50 / 50 | 50 / 21 |
| Finding-bearing tools | 0 | 29 |
| Blocking / advisory tools | 0 / 0 | 21 / 8 |
| Native diagnostic errors / warnings | 0 / 0 | 74,527 / 17 |

These diagnostic counts are native aggregates, not distinct repository issues
or vulnerabilities. Both outputs validate against the unchanged summary schema.
The corrected historical payload SHA-256 is
`04cba3dc81ebcd2227be2a487bc2c91a6e9e6c593d7cc8542985fd3b36ad7852`.
This replay is not a new scan, publication or current-source claim.

The [bounded receipt](evidence/2026-11-14-megalinter-final-results.json) records
original archive/payload identities, unchanged fields and exact outcomes. The
[fixture provenance](../tests/fixtures/repository-reports/megalinter-763-provenance.json)
identifies a 32,414-byte allowlisted projection of the original report and a
3,897-byte selected-policy projection. They retain original field values;
environment, paths, logs, file contents and free-form configuration are excluded.
The full raw report remains outside the repository.

All 22 focused methods pass, including actual final/prerun precedence, simple
and legacy formats, malformed/empty/duplicate cases and disabled-policy
compatibility. An independent peer reproduced the full raw/full-policy output
hash, original legacy bytes and 34 denial controls. Earlier broad candidate
708/base 704 tests had the same 12 failures, 24 errors and 93 skips; catalog
validation retained the same ten metadata/README findings. Those remain baseline
limits. The accepted concurrent Health change is normally merged and retained
byte-for-byte; its 25 focused tests and the 22 normalizer methods pass together.

Scoped Mypy 1.19.1, fatal Ruff checks, compilation, Markdown and new-document
links pass. Bandit retains two unchanged test-loader assertions; Secretlint
retains one unchanged fake-credential URL in a negative test. Both cases are
present in the base source; the changed implementation, fixture projections and
documents pass the secret scan. No suppression or unrelated fixture repair is
introduced.

ADR not required: this repairs the existing producer adapter under
ADR-0004/ADR-0007. Consumer immutable adoption, a fresh producer/normalization/
artifact handoff and reviewed live evidence remain with Empathy #98/#105.
No release or version alias is published by this repair.
