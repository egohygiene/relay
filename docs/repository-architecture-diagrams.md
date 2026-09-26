# Bounded architecture diagram evidence

This is checkpoint 3 of [Relay #99](https://github.com/egohygiene/relay/issues/99).
The existing [offline adapter](repository-architecture-validation.md) inventories
diagram source from its bounded temporary Git snapshot. Relay owns the discovery
contract and evidence metadata. The format projects retain their language and
file-format semantics.

The current immutable profile has no reviewed format-validator runtime. Every
format therefore reports `unavailable` semantic validation with a null validator.
An installed executable or a JSON-looking source file cannot establish validity.
[EgoLint #74](https://github.com/egohygiene/egolint/issues/74) tracks the reviewed
capability needed for a future profile upgrade. The existing profile remains
unchanged and advisory-only; its diagram-semantic capability remains `planned`.

## Select explicit roots

Use the existing request fields:

```json
{
  "adoption": {
    "repository-contracts": "not-applicable",
    "architecture-records": "not-applicable",
    "diagram-sources": "present"
  },
  "inputs": {
    "repository_contracts": [],
    "repository_intelligence_policy": null,
    "diagram_roots": ["ARCHITECTURE.md", "docs/diagrams"]
  }
}
```

This fragment belongs in a complete versioned adapter request. Each root may be
an existing snapshot file or a directory prefix. At most 16 normalized relative
roots are accepted. Missing, duplicate, overlapping, traversal and excluded Git
or report roots are rejected; input is never silently deduplicated. Only the
declared roots are searched for diagrams. An immutable source commit is preferred
for reproducible evidence; working-tree evidence remains explicitly mutable.

Run the existing adapter command. When both native surfaces are explicitly
`not-applicable`, discovery requires only Python's standard library and Git.
The CLI's `--runtime` argument remains present for request/command compatibility
but is not read in that case. Any requested or unknown native surface retains
the pinned EgoLint runtime requirement.

## Discovery contract v1

`relay.diagram-source-discovery/v1` defines a deliberately explicit lexical
inventory. It does not parse diagram grammar, render images, fetch includes,
resolve Markdown links, execute code or infer architectural correctness.

| Format | Standalone suffixes, case-insensitive | Markdown fence labels |
| --- | --- | --- |
| Mermaid | `.mmd`, `.mermaid` | `mermaid` |
| PlantUML | `.puml`, `.plantuml`, `.pu` | `plantuml`, `puml` |
| Excalidraw | `.excalidraw`, `.excalidraw.json` | None |

Markdown discovery applies to `.md` and `.markdown` files. It recognizes
backtick or tilde fence lines of at least three characters, indented by at
most three spaces. The first info-string word selects the language. Closing
fences use the same marker and at least the opening length. Nested examples
inside another fence are ignored. A fence without a closer extends to EOF.
LF, CRLF and CR byte ranges are preserved. This is a lexical convention, not a
complete Markdown parser: it does not interpret HTML blocks, container/list
nesting, MDX, indented code or link targets. Fence-looking lines inside such
constructs follow the same lexical rules. Completeness refers only to this
explicit discovery grammar, not every possible diagram convention.

A standalone record represents the whole source file, including a PlantUML
file containing multiple diagrams. A Markdown record represents one selected
fence; its inclusive source range includes the opening and closing fence (or
EOF), while its digest and byte count cover only the contained source bytes.
Malformed diagram syntax and invalid Excalidraw JSON are still discoverable
source; their semantic validation remains unavailable. Invalid Markdown UTF-8
rejects discovery rather than silently losing fence locations.

Generated PNG/SVG/PDF files and unrelated JSON are ignored. Excalidraw data
embedded in image metadata is outside this source-only contract. Directory
contents with unsupported suffixes contribute only to an ignored-file count.
An existing root containing no recognized source has a complete empty inventory;
this does not establish semantic validity or not-applicable adoption.

Format-owner reference interfaces, reviewed as documentation only:

- [Mermaid CLI](https://github.com/mermaid-js/mermaid-cli) documents standalone
  source and Markdown block processing.
- [PlantUML CLI](https://plantuml.com/command-line) documents source processing
  and syntax checking.
- [Excalidraw's source-format documentation](https://docs.excalidraw.com/docs/codebase/json-schema)
  describes scene JSON, including embedded image data.

These are reference interfaces, not approved dependency pins. A future adapter
must review immutable artifacts, offline behavior and source-access limits
before invoking one; it must retain the format owner's findings and locations.

## Evidence and failure states

The result's `artifacts.diagram_evidence` points to `diagram-evidence.json` in
the same content-addressed report directory as native evidence. It conforms to
[`architecture-diagram-evidence.v1.schema.json`](../schemas/architecture-diagram-evidence.v1.schema.json).
The standard-library validator also checks request identity, sorted unique
records, source/root containment, exact counts and state consistency.

The envelope retains the profile hash, canonical repository identity, represented
revision, complete snapshot digest, declared adoption, sorted roots, bounds and
per-format validator availability. Each record contains only a relative source
path, format, origin, optional line range, byte count, SHA-256 and unavailable
validation state. There are no diagram bodies, extracted labels, links, include
targets, image data, script text, parse-error prose, timestamps or local paths.
Private repository visibility remains attached to the envelope.

| Inventory state | Meaning | Semantic validation |
| --- | --- | --- |
| `complete` | All recognized sources in declared roots were inventoried within bounds, possibly zero | `unavailable` |
| `rejected` | The snapshot or discovery input was unsafe, missing or over a bound; no source records are retained | `unavailable` |
| `unknown` | Adoption was explicitly unknown and no roots were claimed | `unavailable` |
| `not-applicable` | Caller declared the surface irrelevant; no diagram artifact is emitted | `not-applicable` |

Legacy adoption remains `legacy` in the overall result even if inventory is
complete. Requested diagram coverage remains `unavailable`, so discovery alone
cannot make an overall result conformant. Advisory incomplete results exit 0
with warning; consumers must read semantic status. Required mode remains gated.

Native validation and diagram discovery retain evidence independently. A missing
EgoLint runtime cannot erase a completed diagram inventory. A rejected inventory
cannot erase native rule findings or turn failed contracts into a pass. A
snapshot failure retains a closed `snapshot-unavailable` diagram diagnostic.
No fallback changes a failure into successful validation.

## Bounds and trust

The adapter first enforces the request's whole-snapshot ceiling, at most 10,000
files and 100 MiB. Discovery uses that bounded file inventory rather than walking
the filesystem again. Root `.git/` and `.reports/` are excluded; symlinks, special
files, submodules and unsafe paths cannot enter the temporary snapshot.

Diagram discovery additionally caps each examined source or Markdown file at
1 MiB, the number of source records at 256, and its evidence envelope at 1 MiB.
The entire inventory is rejected on overflow; discovered prefixes are not
retained as complete evidence. Observed counts, zero retained count and explicit
truncation explain the failure. Reports use the adapter's bounded atomic writer.

The collector never executes diagram directives, caller scripts, packages or
validators discovered on `PATH`. This prevents includes, callbacks and embedded
assets from acquiring local-file, network or execution authority. The next
validator-capability review must prove those same boundaries for every backend.

## Validation and remaining gates

```bash
python3 -m unittest discover --start-directory tests \
  --pattern test_architecture_diagram_evidence.py --verbose
```

The discovery and safety fixtures use disposable repositories without a native
runtime. Set `RELAY_ARCHITECTURE_RUNTIME` to the prepared runtime to include
native composition/failure retention. Install the pinned schema dependencies
to include the separate JSON Schema agreement check; skipped checks are explicit.

Fixtures cover exact standalone/fenced byte identities, newline and fence
boundaries, empty/unknown/legacy states, rejected roots and bounds, symlink
denial, hostile private payloads, immutable versus working-tree behavior,
complete evidence equality across checkout names, and independent native errors.
Reusable CI and acceptance remain #99 checkpoints 4–6. Diagram validators remain
the explicit #74 capability gap; this inventory does not promote that gate.
