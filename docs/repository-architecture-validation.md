# Repository architecture validation contract

Relay issue [#5](https://github.com/egohygiene/relay/issues/5) is delivered
through the ordered checkpoints in
[#99](https://github.com/egohygiene/relay/issues/99). This document describes
checkpoints 1–3: the versioned contract, an experimental offline local adapter
and bounded diagram-source evidence. The
[checkpoint-4 reusable workflow](repository-architecture-workflow.md) composes
that same adapter and preserves its exact normalized evidence bytes.

## Responsibility boundary

Relay orchestrates validators and normalizes bounded evidence. It does not
become the authority for organization policy, validation semantics, consumer
architecture records, or materialization.

| Concern | Authority | Local adapter treatment |
| --- | --- | --- |
| Organization architecture policy | Hygiene | Pinned input only |
| Repository and ADR validation semantics | EgoLint | Pinned native validator |
| Architecture-decision scaffolding | Holon | Pinned input only |
| Consumer records and diagrams | Consumer repository | Read-only input |
| Orchestration and normalized evidence | Relay | Offline adapter and versioned contract |
| Fleet rollout | Pace | Outside this task |
| Aggregated read models | Observatory | Outside this task |

The profile operationalizes ADR-001, ADR-002, ADR-003, ADR-005, and ADR-006.
It does not change ownership, so it requires no new architecture decision.

## Immutable source profile

[`catalog/repository-architecture-validation.json`](../catalog/repository-architecture-validation.json)
binds the reviewed source artifacts by full commit SHA and SHA-256 digest:

| Source | Revision | Lifecycle |
| --- | --- | --- |
| `egohygiene/hygiene` | `c589587395750cd1c79c6fa0bef010189c547249` | Accepted policy, not release-included |
| `egohygiene/egolint` | `8b99ec4377eb84044fac411dff6b8074317ec094` | Proposed validator, not release-included |
| `egohygiene/holon` | `660b941f99618806fcadd589bcdae61c519f96e4` | Accepted materializer, not release-included |

Repository-contract and architecture-record validation are available through
EgoLint rule families. Diagram discovery and evidence remain explicitly
`planned`: none of the reviewed upstream sources owns a released diagram
semantic validator, so Relay must not fabricate one.

Because the complete source set is not released, the profile is `proposed`,
defaults to `advisory`, and caps activation at `advisory`. A future required
mode needs all three recorded gates: an immutable EgoLint release, a reviewed
adapter/workflow fixture matrix, and explicit consumer opt-in.
The checked-in required-mode fixture exercises that future contract shape; it
does not activate required enforcement in this checkpoint.

## Request and result seam

The request contract records:

- repository identity, visibility, and represented revision;
- explicit adoption state for repository contracts, architecture records, and
  diagram sources;
- bounded repository-relative input paths;
- advisory or required intent;
- file, byte, and finding ceilings; and
- one JSON output path under `.reports/architecture-validation/`.

The result contract records:

- semantic status separately from execution outcome;
- per-surface coverage, including `partial`, `unavailable`, and
  `not-applicable`;
- all three exact upstream revisions;
- bounded diagnostics and exact retained-finding counts;
- scan and truncation evidence;
- repository-relative report paths; and
- a visibility-matched privacy classification.

An unavailable validator produces an explicit unavailable result. Missing,
partial, legacy, or truncated evidence cannot silently become conformance.
Advisory mode reports nonconformance without blocking; required mode may fail
only after its release and opt-in gates are satisfied.

## Execution and information safety

The local adapter enforces the profile's execution boundary:

- Network access is denied after explicit dependency acquisition.
- Consumer code is never executed.
- Consumer semantic records are never authored or rewritten.
- Writes are limited to temporary work and `.reports/` output.
- Stage, commit, push, pull-request, comment, merge, release, deploy, and
  publish authority are forbidden.
- Evidence excludes secrets, credentials, environment values, provider tokens,
  workflow logs, absolute local paths, raw source content, and private
  cross-repository content.

Repository text is untrusted data. It cannot grant authority or change the
validation plan.

## Prepare the trusted runtime

The reviewed environment is Linux x86_64, CPython 3.12 and Rust/Cargo 1.85.1.
The Python requirements include exact wheel hashes for that environment; adding
another platform requires reviewing its distribution hashes. Git is required.
Use a trusted Relay checkout and a separately acquired, trusted Cargo cache.
Dependency acquisition is a separate operator step, before offline validation:

```bash
python3 -m pip download --only-binary=:all: --require-hashes \
  --requirement scripts/architecture-validation-requirements.txt \
  --dest /path/to/architecture-wheels
python3 -m pip install --no-index --find-links /path/to/architecture-wheels \
  --require-hashes --requirement scripts/architecture-validation-requirements.txt
```

Acquire the three source repositories and Cargo dependencies separately at the
profile's exact revisions. `cargo fetch --locked` in the trusted pinned EgoLint
checkout can populate its Cargo cache. Preparation then reads exact Git objects,
verifies every profile artifact digest, and exports only the pinned Rust source,
manifest, lock, schemas, catalogs and vendored inputs into temporary storage:

```bash
python3 scripts/run_repository_architecture_validation.py prepare \
  --hygiene-source /path/to/hygiene \
  --egolint-source /path/to/egolint \
  --holon-source /path/to/holon \
  --output /path/to/architecture-runtime
```

Preparation uses `cargo build --frozen --offline --bin egolint`; Cargo verifies
registry dependencies against its lock checksums. An optional `--cargo` selects
an already-installed executable. Missing dependencies fail without a fetch.
Holon and Hygiene are verified source inputs; their consumer generators are
not run. The destination must be new and outside the consumer checkout.

The receipt binds the profile hash and locally built executable digest. Each
run verifies that receipt and every pinned artifact. This is a trusted local
build receipt, not a signed upstream release or an authenticity proof for a
runtime supplied by an untrusted party. Keep the runtime and Relay code outside
consumer control; the checkpoint-4 workflow uses isolated runner storage and
resolves Relay code from the immutable called workflow revision.

## Run against a caller checkout

Create a request matching
[`repository-architecture-validation-request.v1.schema.json`](../schemas/repository-architecture-validation-request.v1.schema.json).
The profile hash is the SHA-256 of the exact catalog file, not a reserialized
JSON object. The following creates a request for existing caller-owned policies;
replace the identity, full represented commit and paths before running it:

```python
import hashlib
import json
from pathlib import Path

profile_bytes = Path("catalog/repository-architecture-validation.json").read_bytes()
request = {
    "schema_version": "relay.repository-architecture-validation-request/v1",
    "profile": {
        "version": json.loads(profile_bytes)["version"],
        "sha256": hashlib.sha256(profile_bytes).hexdigest(),
    },
    "repository": {
        "id": "egohygiene/example", "visibility": "public", "root": ".",
        "represented_revision": "working-tree",
    },
    "mode": "advisory",
    "adoption": {
        "repository-contracts": "present", "architecture-records": "present",
        "diagram-sources": "not-applicable",
    },
    "inputs": {
        "repository_contracts": ["policy/repository-contract.toml"],
        "repository_intelligence_policy": "policy/repository-intelligence.toml",
        "diagram_roots": [],
    },
    "bounds": {
        "maximum_findings": 256, "maximum_scanned_files": 10000,
        "maximum_scanned_bytes": 104857600,
    },
    "output": {"format": "json", "path": ".reports/architecture-validation/result.json"},
}
Path("/path/to/request.json").write_text(json.dumps(request, indent=2) + "\n")
```

```bash
python3 scripts/run_repository_architecture_validation.py run \
  --repository-root /path/to/consumer \
  --request /path/to/request.json \
  --runtime /path/to/architecture-runtime
```

Run the script from trusted Relay code. The consumer must be a Git repository
root. A full SHA selects exact source tree bytes and ignores later working-tree
edits. `working-tree` or `unknown` selects tracked and nonignored untracked files,
including edits and deletions, and remains incomplete for immutable evidence.
All-not-applicable requests require neither a native runtime nor a scan.

The adapter checks caller TOML against EgoLint's pinned schemas, requires matching
repository identity and enabled ADR coverage, and passes the original policy
bytes to EgoLint. It never writes a policy or chooses an ADR's lifecycle state.
Explicit `legacy` adoption stays legacy even if native syntax checks pass.

## Snapshot and retained evidence

The adapter inventories files before validation, excludes root `.git/` and
`.reports/`, rejects unsafe paths, symlinks, special files and submodules, then
copies regular bytes into temporary storage with a fresh Git index. Consumer
Git hooks, filters, configuration, alternates and replacement refs are not copied.
Git source reads disable hooks, fsmonitor, replacement refs and network protocols;
blob writes disable filters. Native `egolint validate --network none --pull-policy
never` runs without inherited credentials or EgoLint environment overrides.
The trusted native command does not execute caller scripts or containers. This
is an audited offline command path, not an operating-system sandbox for arbitrary
executables; only a trusted prepared runtime may be used.

An immutable snapshot retains at most 256 commit objects, each at most 256 KiB.
Missing ancestry becomes an explicit shallow boundary; native history truncation
remains incomplete. Snapshot file/byte ceilings come from the request. Process
output is bounded to 16 MiB and execution to 60 seconds (300 for runtime build).
Every retained JSON/SARIF file and raw report read is capped at 1 MiB.
Stop concurrent checkout edits before scanning; an immutable revision is the
preferred reproducible input.

Only the declared normalized result and content-addressed evidence beneath
`.reports/architecture-validation/` are written to the consumer. Reports use
atomic replacement, regular-file checks and restrictive new-file permissions.
They contain no raw console logs, commit messages, author identities, ADR bodies,
policy text, credentials, environment values or absolute local paths.

| Artifact | Retained content |
| --- | --- |
| `result.json` | Closed Relay result: selected coverage, semantic status, counts, bounds and source provenance |
| `egolint-run.json` | Closed Relay projection of native run status, completeness, local runtime receipt and snapshot digest |
| `repository-intelligence.json` | Closed Relay projection of native semantic status, adoption, inspection counts and history truncation |
| `egolint.sarif` | SARIF 2.1.0 with native opaque rule IDs, stable EgoLint rule names, severity and source regions |
| `diagram-evidence.json` | Bounded source inventory, exact digests/regions and explicit format-validator availability |

The two evidence projections validate against
[`architecture-validation-evidence.v1.schema.json`](../schemas/architecture-validation-evidence.v1.schema.json).
They are deliberately not raw EgoLint report-schema instances. Diagnostic prose
uses the pinned rule catalog's title and remediation, avoiding messages that
interpolate caller text. Repository-contract rules have no catalog remediation;
those three IDs receive fixed routing guidance. Locations and native rule IDs
remain intact. SARIF includes the same bounded retained native findings as the
normalized result; total findings and truncation remain explicit in the result.
Timestamp, checkout path and other transient upstream fields are omitted, so
the same inputs and prepared runtime produce equal complete evidence bundles.

Native run status covers additional EgoLint families and is retained separately
from the selected architecture coverage. The dedicated Intelligence semantic
status controls validity even when advisory findings have warning severity.

| Result | Advisory CLI exit |
| --- | --- |
| `conformant` or `not-applicable` | 0, `passed` |
| `nonconformant`, `legacy` or `incomplete` | 0, `warning` |
| Runtime unavailable or required mode before its gates | 2, `unavailable` |
| Invalid request or unsafe output prevents a safe result | 2, fixed diagnostic on stderr |

Consumers must inspect the result, not interpret exit 0 as conformance. On a
failure before safe output, previous reports are not fresh evidence. The
[diagram evidence guide](repository-architecture-diagrams.md) defines the
standalone and Markdown discovery grammar, bounds and closed sidecar. Discovery
and native validation retain their evidence independently; requested diagram
semantics remain unavailable until reviewed format validators are pinned.

## Known upstream policy compatibility gap

At the pinned EgoLint commit, its ADR catalog still requires Hygiene revision
`f598ed659a43dd759d4ede41c27f9e5daf991aa7` with proposed authority. Relay's profile
correctly pins the ratified Hygiene revision `c589587395750cd1c79c6fa0bef010189c547249`.
The native fixture proves that substituting the ratified policy reference
produces `EGO-INTEL-CONTRACT-001`; the old reference can yield native `valid`.
Relay preserves both outcomes and adds `RELAY-ARCH-COMPAT-001`, reducing an
otherwise passed ADR surface to partial. It never rewrites the caller pin.

[EgoLint #73](https://github.com/egohygiene/egolint/issues/73) owns reconciliation.
After that change is reviewed, refresh Relay's immutable profile and rerun these
fixtures before fleet conformance or required mode is claimed. Do not downgrade
consumer policy references merely to obtain a green native result.

## Validation

Validate the profile, schemas, and publish-safe fixture corpus offline:

```bash
python3 scripts/validate_repository_architecture_contract.py validate
```

Maintainers can separately verify the pinned bytes against already-acquired
local checkouts. This command performs no network access and does not run code
from those repositories:

```bash
python3 scripts/validate_repository_architecture_contract.py verify-sources \
  --hygiene-source /path/to/hygiene \
  --egolint-source /path/to/egolint \
  --holon-source /path/to/holon
```

The checked-in fixture corpus covers present, legacy, unknown, conformant,
nonconformant, and unavailable states across public, private, and internal
repositories. Mutation tests reject mutable revisions, ownership drift,
invented diagram semantics, path traversal, contradictory adoption evidence,
unsafe bounds, source-content leakage, and result-count contradictions.

Run the native adapter suite with the prepared runtime:

```bash
RELAY_ARCHITECTURE_RUNTIME=/path/to/architecture-runtime \
  python3 -m unittest discover --start-directory tests \
  --pattern test_repository_architecture_adapter.py --verbose
```

Without that variable, ordinary discovery explicitly skips the native cases;
boundary checks remain dependency-free. Native cases use the real compiled
EgoLint binary, including valid and invalid ADRs, missing approval, duplicate IDs,
index failures, the ratified-pin mismatch, private-source canaries, disabled-rule
denial, runtime tampering, bounded history, output limits, Git helper denial and
complete report equality across differently named checkouts.

## Next checkpoints

Checkpoint 4 implements reusable workflow orchestration. Broader consumer
fixtures and dogfood follow in checkpoint 5, then live acceptance and separate immutable release/adoption
proof. EgoLint #74 tracks reviewed diagram validators; source discovery does not
establish diagram validity. This local experimental command does
not make #99 or parent #5 complete. Canonical ADR collection and the Decisions
build are tracked separately in [#115](https://github.com/egohygiene/relay/issues/115).
