# Artifact Size Budget

Normalize bounded artifact-size evidence into the versioned
`egohygiene.relay.artifact-budget-report/v1` contract. The action supports raw
filesystem artifacts across ecosystems and the documented JSON output emitted
by a consumer-pinned [Size Limit](https://github.com/ai/size-limit) installation.

The action measures and evaluates already-produced artifacts. It does not build
consumer code, download package-manager dependencies, inspect container
registries, or claim that byte size proves runtime performance.

## Boundary

| Adapter | Intended inputs | Measurement |
| --- | --- | --- |
| `filesystem` | A file, native binary, package/archive, OCI image archive, complete static-site directory, or other materialized directory | Raw regular-file bytes and bounded file count |
| `size-limit-json` | A non-empty JSON array from project-pinned `size-limit --json` | Each named check's deterministic `size`, its `sizeLimit`, pass state, and optional loading/running observations |

Size Limit remains the JavaScript-specific producer. It currently publishes a
modular CLI with file, bundler, and time plugins and a `--json` reporter. Relay
does not install it because the correct plugins, lockfile, package manager,
build, compression mode, and configuration belong to the consumer. Relay
normalizes its stable JSON boundary and preserves upstream failure state.

The generic filesystem adapter proves the same report contract for non-JavaScript
artifacts without pretending Size Limit is language-neutral. A native binary,
release archive, static site, or exported container-image archive can therefore
use the same budgets and result states. Registry-native image measurement is a
future adapter because registry authentication and manifest semantics are not
equivalent to local file bytes.

## Inputs

Required inputs:

- `adapter`: `filesystem` or `size-limit-json`;
- `artifact-kind`: `file`, `directory`, `static-site`, `native-binary`,
  `archive`, `container-image-archive`, `javascript-bundle`, or `other`;
- `subject`: a stable bounded report identifier;
- `current-path`: current materialized artifact or Size Limit JSON;
- `current-revision`: the exact 40-character Git SHA represented by it.

Optional comparison inputs:

- `baseline-path` and matching `baseline-revision`;
- `maximum-bytes`;
- `maximum-increase-bytes`;
- `maximum-increase-percent`;
- `warning-threshold-percent`, which defaults to `90`.

Resource ceilings default to 10,000 filesystem entries, 100 Size Limit checks,
and 1 GiB for each filesystem artifact or Size Limit JSON document. Callers may
lower or deliberately raise those bounds through `maximum-files`,
`maximum-items`, and `scan-maximum-bytes`. Size Limit JSON also has a fixed 8
MiB parser safety ceiling because its bounded scalar contract does not require
larger input.

All paths are relative to `GITHUB_WORKSPACE`. Symlinks, escaping paths, special
files, output paths nested inside a measured directory, duplicate Size Limit
names, incomplete revisions, malformed numeric inputs, and over-limit scans
fail as contract errors before a successful report is emitted.

## States and enforcement

- `pass`: every available measurement remains below its applicable budgets;
- `warn`: no budget failed, but at least one value reached the configured
  warning band;
- `fail`: a Relay budget or Size Limit's own pass state failed;
- `missing-baseline`: a requested comparison is absent or a delta budget cannot
  be evaluated;
- `unsupported`: deterministic byte evidence is unavailable, including a
  runtime-only Size Limit check or an undefined percentage over a zero-byte
  baseline.

`advisory` mode writes and summarizes all five states without failing the job.
`blocking` mode exits unsuccessfully for `fail`, `missing-baseline`, or
`unsupported`; warnings remain visible but non-blocking. Invalid or unsafe
input always fails in either mode.

## Direct action example

```yaml
- name: Evaluate native archive budget
  # Relay artifact-budget v1; production callers pin a reviewed full commit SHA.
  uses: egohygiene/relay/actions/artifact-budget@<full-relay-commit-sha>
  with:
    adapter: "filesystem"
    artifact-kind: "archive"
    subject: "linux-amd64"
    current-path: "dist/tool-linux-amd64.tar.gz"
    current-revision: "${{ github.sha }}"
    mode: "blocking"
    maximum-bytes: "52428800"
    output: ".relay/linux-amd64-budget.json"
```

The caller may instead supply `baseline-path`, `baseline-revision`, and delta
budgets after materializing a trusted baseline artifact in a separate directory.

## Size Limit producer example

Install Size Limit and the appropriate plugins in the consumer's development
dependencies and lockfile. The producer job owns its build and records JSON:

```bash
mkdir -p ".relay"
pnpm exec size-limit --json > ".relay/size-limit.json"
```

Size Limit may return nonzero when a configured budget fails. A CI producer
should preserve its JSON as an ordinary artifact even in that case; Relay will
retain `passed: false` and enforce it according to `mode`. Fatal Size Limit
errors produce an `{ "error": ... }` object, which Relay rejects rather than
misreporting as an artifact result.

## Determinism and privacy

The report contains configured identifiers, workspace-relative source paths,
immutable revisions, numeric budgets, bounded measurements, states, and reason
codes. It contains no file bodies, directory listings, package manifests,
tokens, provider payloads, or absolute workspace paths. JSON keys and Size
Limit checks are sorted before hashing. No wall-clock timestamp is included,
so identical evidence produces byte-identical output.

The schema is published beside the action at
[`schemas/artifact-budget-report.schema.json`](schemas/artifact-budget-report.schema.json).
The reusable workflow documents the artifact handoff and preserves the report
as an ordinary GitHub Actions artifact without executing consumer code.
Caller producers that stage evidence beneath a dot-directory must enable
`include-hidden-files` when uploading it; the complete uploaded artifact is the
measurement boundary.

## Tool selection and maintenance

Relay reviewed the official Size Limit repository on 2026-09-17. The project
was active and not archived; its `main` source at
`b1d4c43c6a92ea8b610898d342c9086c66d43ac3` documented modular file, bundler,
and time plugins, while `packages/size-limit/create-reporter.js` defined the
normalized `--json` fields used here. Relay depends on that output contract,
not a third-party wrapper action. Consumer lockfiles remain the authority for
the exact Size Limit and plugin versions they execute.
