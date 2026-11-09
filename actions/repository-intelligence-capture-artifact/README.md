# Repository Intelligence Capture Artifact

Pack an existing caller-owned public JSON capture directory for exact same-run
Repository Intelligence intake. This read-only preparation action does not
capture provider data, upload artifacts, execute consumer code or deploy a site.

Inputs:

- `source-directory`: directory containing `source-plan.json` and referenced
  Work/Health JSON captures.
- `as-of`: explicit UTC evaluation boundary, preserving original capture times
  and source revisions.

Outputs: `artifact-name`, private `artifact-directory`, `manifest-sha256` and
unchanged `as-of`. Upload only that directory with the returned exact name, then
pass its immutable artifact ID/digest and evaluation boundary to
`repository-intelligence-captures.yml`. The preparation action needs no token
permission; the capture-enabled consumer workflow needs `contents: read` and
`actions: read`.

Initial scope is public default-branch push/manual dispatch. See the
[complete source/consumer handoff](../../docs/repository-capture-artifact-intake.md)
for source contracts, bounds, retained proof, exact pinning, failure behavior
and the explicitly unrun acceptance checks. ADR-0007/0010 govern this existing
collection/publication boundary; no new policy authority is introduced.
