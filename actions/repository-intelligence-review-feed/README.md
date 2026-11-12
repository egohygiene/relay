# Repository Intelligence typed review feed

This experimental source implementation turns explicitly selected public
Aether typed sidecars into the existing Observatory repository and singleton
fleet Audits/Sanity models. It runs only pinned owner validators and pure
normalization queries. It does not execute an auditor or AI model, reinterpret
Markdown, fetch providers, create issues, verify human authority, or publish.

## Consumer API

Pin `egohygiene/relay/actions/repository-intelligence-review-feed` to an exact
reviewed Relay commit. All six action inputs are required:

| Input | Binding |
| --- | --- |
| `source-root` | Existing consumer Git worktree, absolute or local path |
| `plan` | Literal repository-relative plan path, read from immutable Git |
| `repository` | Explicit canonical public identity in the pinned catalog |
| `represented-commit` | Full source SHA selecting actual plan/report blobs |
| `as-of` | One actual UTC evaluation boundary shared with source capture and builder |
| `output-directory` | New repository-relative `.cache/` directory outside builder work/output |

Outputs `repository-audits`, `repository-sanity`, `fleet-audits`, and
`fleet-sanity` are repository-relative model paths. Forward the first two
unchanged into the existing builder's `observatory-audits` and
`observatory-sanity` inputs with the identical source SHA and `as-of`. Keep the
feed directory separate from builder work directories that may be cleaned.

`artifact-directory`, `receipt-path`, and `receipt-sha256` describe ordinary
review evidence. The caller owns a separate ordinary artifact upload and its
exact name, ID, run/attempt, source head and archive digest. These provider
identities are never inferred or put into public model bytes. The feed requires
no token or extra API permission; the caller's ordinary upload is independent.
Do not upload its receipt/source binding into Pages or imply deployment success.

## Explicit plan

The closed plan has `schema`, `contract_version`, `visibility`, `repository`,
`audits`, and `sanity`. Domain arrays contain sorted unique `{path,sha256}`
selectors. Each SHA-256 names the exact UTF-8 JSON sidecar bytes at the source
commit. Paths may include `.config`; exact `.`, `..`, `.git`, traversal,
backslash, escape, absolute and special-file paths are rejected.

Empty arrays are the initial honest adoption state; no report or finding is
fabricated. A selected path absent from that immutable tree remains unavailable
and is recorded as missing. A missing plan also yields empty unavailable
models. An existing malformed/ambiguous, non-public, wrong-hash, wrong-version,
mixed protected-scope or otherwise incompatible selected input fails closed.
The feed does no report discovery and never scrapes a Markdown report.

The plan is bounded to 64 KiB and 64 selectors per domain. Each report is at
most 2 MiB, total selected report bytes at most 16 MiB. Owner model bounds apply
in addition. Output is at most four 4 MiB model files plus a bounded receipt.

## Source clocks and historical context

The Git-only profile reads plan and sidecars from exact `represented-commit`
objects; symlinks, submodules, filters and working-tree replacements cannot
supply candidate code. Commit and source proofs are read with hooks, ambient
Git configuration, network and lazy fetching disabled. The evaluation boundary
must be at or after that source commit's committer clock and no later than the
actual invocation clock. It is never replaced with the invocation clock.
Use the caller's same actual captured UTC boundary for feed and builder.

An audit/review tracked in the current tree commonly represents a **prior**
revision: recording its own current source SHA would create a self-reference.
The owner query preserves that original revision, completion/generated clocks,
freshness and `different` historical context. A new receipt does not make it a
current audit, renew its observation, turn silence into resolution or promote
historical human claims. Empty evidence is unavailable, never healthy or clean.
Uncommitted current-review captures require a separately reviewed trusted
capture profile; they are not admitted by this first Git-only implementation.

## Owner and trust boundary

The new independent runtime lock pins Observatory
`7b857de2424f90de519fbc2e24332a7c0a89991b`, Aether
`74490907bf3979ac45594d97fb1bb5fa7071346d`, the exact Hygiene public catalog
`49639c1845cdfd08fbd5a768261a8b3cf515f80f` (`af9c7186…`), and the already
packaged proposed governance contract at `d11580e9…`. Existing locks/defaults
and source profiles are unchanged. Public catalog admission occurs before
source identities, counts or content hashes become retained evidence.

Only selected hash-bound owner modules/data are copied into a private temporary
runtime **outside** the consumer. A minimal namespace loads the two owner query
modules without executing Observatory's broader package initializer. No source
repository, plan field or sidecar can choose a runtime file/import. No Rust,
package installation, provider adapter, auditor/AI invocation or shell command
from candidate inputs is used. Linux Git/Python and the closed pure-owner
stdlib closure are the only runtime dependencies.

Sanity uses the owner's empty trusted-human-evidence context. Human claims may
be displayed as unverified, but JSON actor names, URLs, `verified` fields,
continued implementation and source ingestion never ratify architecture. No
policy, applicability, exception, migration or human lifecycle state is created.

## Retained artifacts and denial

Successful output contains exactly:

```text
repository-audits.json
repository-sanity.json
fleet-audits.json
fleet-sanity.json
review-feed-receipt.json
```

The two fleet models are generated by actual owner `build_fleet_*` APIs with
one explicit target. They retain the same clock and exact repository model.
True aggregation of independently captured frames is later owner-bridge work;
never retime/relabel different captures or hash missing raw data to simulate a
common fleet. A homepage may select one compatible retained fleet per module.

The receipt binds source clock/SHA, the actual plan bytes, selected/missing
report references, exact model file hashes/sizes, owner digests and pinned
implementation. It copies no report prose or raw sidecar body. No receipt is
proof that an auditor actually executed, a source claim is true, a human was
authenticated, or an artifact was uploaded. Canonical reports stay repository
owned; model projection is not a competing editable report.

On failure, no normalized model output paths are returned. When public source
context and a new safe output directory are already admitted, the action emits
only `review-feed-denial.json` with a closed diagnostic and returns failure.
Invalid public/source bindings or an existing destination can yield no artifact
output at all. Never reuse files from a prior failed/existing destination.

## Offline downstream receipt admission

`scripts/review_feed_contract.py` is a standalone stdlib binding helper.
`validate_receipt(value, *, admission, expected_implementation, repository,
represented_commit=None, as_of=None)` accepts raw bytes or a parsed object.
Supply **independently authenticated** single-row public admission and expected
hashes of the pinned producer, contract, owner lock and two schemas. Copying
those expectations from the candidate receipt proves nothing.

`validate_model_bytes(receipt, key, raw_bytes)` checks raw file/source framing
after receipt validation. It does not validate owner model meaning or replay
original assessments. Downstream existing Observatory model/public-scope
validators remain required. Retain each original frame unchanged; transport
provenance belongs in private caller receipts, not public website assets.

This checkpoint has source/AST/schema/static peer review only. No feed, owner
helper, auditor, model, provider, native scenario, application, tests, build,
browser or CI execution/qualification was performed.

Refs egohygiene/relay#74, egohygiene/relay#76 and egohygiene/reflector#258.
