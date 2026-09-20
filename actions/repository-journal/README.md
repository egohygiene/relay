# Repository Journal

This composite action collects bounded, read-only GitHub evidence and renders a
deterministic repository journal through Relay's checksum-pinned Aether
contract. It never checks out or executes consumer code and never mutates the
repository.

The default `deterministic` adapter requires no AI account or billing. It maps
normalized provider records directly into factual journal entries. `manual`
accepts a reviewed candidate JSON and verifies its repository, revision,
interval, bounds, safe shape, and evidence references before rendering. Those
checks establish provenance; they do not claim to prove that free-form prose is
a perfect semantic description of the cited record.

`unavailable` intentionally publishes an honest empty-state journal. `copilot`
uses the same candidate boundary, but only after the pinned CLI, credential,
organization policy, workflow permission, and billing acknowledgement all pass
the secret-free preflight. There is no automatic fallback between billing
principals. A failed or unavailable Copilot preflight produces an unavailable
journal without making an agent request.

## Minimal no-billing use

```yaml
- name: Create deterministic repository journal
  # Unreleased example; replace with the reviewed release metadata and full SHA.
  uses: egohygiene/relay/actions/repository-journal@<full-commit-sha>
  with:
    mode: deterministic
    repository: "${{ github.repository }}"
    revision: "${{ github.sha }}"
    interval-start: "2026-09-01T00:00:00Z"
    interval-end: "2026-09-08T00:00:00Z"
    generated-at: "2026-09-08T00:00:00Z"
    github-token: "${{ github.token }}"
```

Use the reusable workflow for normal adoption. It owns artifact download,
bounded retention, Step Summary publication, and the read-only permission
ceiling. The separately cataloged Copilot workflow is the explicit future
opt-in surface.
