# Same-run Repository Intelligence capture handoff — Relay #151

The new `repository-intelligence-captures.yml` reusable entrypoint admits an
ordinary immutable public JSON capture artifact from the caller's current
repository, run, attempt and represented head. It then invokes the existing
fresh Work/Health collectors and repository site builder. The consumer still
owns its one Pages/site artifact, route composition, deployment and rollback.
The organization website remains a separate fleet overview.

The original `repository-intelligence.yml` remains byte-identical, including
its `contents: read` token contract. The capture-enabled entrypoint additionally
requires `actions: read` for exact artifact/run metadata and archive reads. It
adds no write permission, secret inheritance, Pages operation, provider mutation
or consumer-code execution. Intake runs inside the existing composite generation
stage; generation/provenance/upload/report sequencing is preserved.

## Caller-owned producer handoff

After selecting the source commit, the caller's producer steps write public
Work/Health transport captures and `source-plan.json` into one private directory.
Plan paths are relative to that directory. Preserve each original `source_commit`,
report `commit`, generation/capture time and provider record. Choose an explicit
UTC evaluation boundary after those observations; do not use a commit-time
clock for later captures. See the [capture-plan guide](repository-source-capture-builds.md).

The public preparation action packs only the plan and its referenced JSON
files. It performs no upload and runs no producer commands:

```yaml
# In the caller's existing capture-producing job, after its provider steps:
- id: bundle
  uses: egohygiene/relay/actions/repository-intelligence-capture-artifact@FULL_REVIEWED_RELAY_SHA
  with:
    source-directory: ${{ runner.temp }}/public-captures
    as-of: ${{ steps.producer.outputs.as-of }}
- id: upload
  # actions/upload-artifact v7.0.1
  uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a
  with:
    name: ${{ steps.bundle.outputs.artifact-name }}
    path: ${{ steps.bundle.outputs.artifact-directory }}
    if-no-files-found: error
    retention-days: 7
```

Replace `FULL_REVIEWED_RELAY_SHA` with the exact reviewed immutable Relay
revision. The example assumes actual caller-owned producer outputs; Relay does
not fabricate captures or their evaluation clock. Expose the upload's
`artifact-id`, `artifact-digest`, and the preparation action's `as-of` as caller
job outputs, then call the capture-enabled workflow:

```yaml
intelligence:
  needs: capture
  permissions:
    contents: read
    actions: read
  uses: egohygiene/relay/.github/workflows/repository-intelligence-captures.yml@FULL_REVIEWED_RELAY_SHA
  with:
    source-capture-artifact-id: ${{ needs.capture.outputs.artifact-id }}
    source-capture-artifact-digest: ${{ needs.capture.outputs.artifact-digest }}
    as-of: ${{ needs.capture.outputs.as-of }}
    collect-roadmap: true
    collect-adrs: true
```

Select canonical collection only where those sources actually exist at the
represented commit. The workflow's site artifact outputs retain the existing
consumer-owned composition/publication interface. Capture-only sources also
work; external snapshot/comparison inputs conflict with native capture intake.

## Exact admission boundary

The only accepted artifact name is derived from repository ID, full head SHA,
run ID and attempt:

`repository-intelligence-captures-v1-<repository-id>-<sha>-<run-id>-<attempt>`.

The caller supplies its exact immutable artifact ID and upload SHA-256. There is
no name search, latest-artifact fallback, cross-run lookup or cross-repository
download. Before archive retrieval, the helper verifies the current run attempt,
public repository identity, event and provider head, artifact name/digest/run
binding, expiry and creation after that attempt's start. It then verifies the
downloaded ZIP's SHA-256 independently. A missing or expired artifact stays
unavailable; it never falls back to another receipt.

The initial artifact seam supports default-branch push and manual dispatch.
Pull-request merge commits differ from provider workflow-run heads, so artifact
capture intake rejects PR events rather than rewriting a represented SHA.
Existing PR/no-capture builds and the local/composite untracked capture path
retain their existing behavior. A proven PR head/merge mapping is later #151
scope.

The bundle manifest binds repository/head/run/attempt/event/evaluation identity
and a sorted exact file/hash/size inventory. Admission allows only that manifest,
the closed plan and referenced JSON files: at most six payload files, 1 MiB per
capture, 64 KiB for plan/manifest, 6 MiB expanded and 8 MiB archived. ZIP members
cannot contain traversal, symlinks, executable files, case collisions, encrypted
or unsupported compression, unreferenced files, duplicate entries or excessive
expansion. Extraction never calls `ZipFile.extract`.

Every admitted Work/report/check-run source keeps its represented revision.
Original timestamps remain unchanged and cannot exceed the declared evaluation
boundary. Full schema/semantic validation still belongs to the existing fresh
collectors; transport admission does not imply complete inventory or healthy
checks. Partial, stale, failed and unavailable coverage stays explicit.

Only verified files enter a new private runner-temporary directory outside the
source checkout. The data-only plan cannot select executable runtimes. The
source builder rechecks its private receipt and every selected file before
collecting. No consumer-owned source, site file or retained comparison baseline
is overwritten. Signed archive URLs, credentials, headers, process logs and raw
exceptions never enter diagnostics. Authorization is sent only to GitHub's API;
the bounded storage redirect receives no token.

## Retained proof and failure

The private intake receipt binds exact artifact/archive, manifest and plan
digests to repository/head/run/attempt/evaluation identity. The ordinary run
report artifact retains that closed receipt beside its sanitized report, with
an explicit two-file/64-KiB bound. Raw capture files are not added to the site or
run-report artifact. Source-plan provenance independently binds original capture
and contract digests; run-specific receipt metadata stays outside deterministic
public site bytes.

Before ordinary site upload, the capture workflow verifies receipt bytes and
the source plan digest. Finalization requires inspectable admitted proof before
reporting success. Missing/tampered proof fails through the existing provenance
failure category. If proof disappears after an ordinary upload, the report
retains the true upload fact while the workflow still fails; no deployment is
performed. Failed generation can retain requested/unavailable intake evidence
without claiming admission. Cancellation and artifact-service loss retain the
existing limits on report delivery.

This is an implementation candidate. Static syntax, metadata and peer review
were performed; no packaging/admission execution, native build, tests, CI,
provider canary or consumer publication was run. Required follow-up is actual
same-run artifact/attempt/API proof, adversarial ZIP cases, captured-source
replay, no-capture compatibility and consumer-owned site preservation at the
reviewed immutable revision.
