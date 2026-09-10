# Continuity preflight adoption

After Relay publishes the workflow, replace the marker below with the reviewed
release commit and retain the adjacent version note during dependency updates.

```yaml
name: Repository continuity
on:
  pull_request:
permissions:
  contents: read
jobs:
  continuity:
    permissions:
      contents: read
    # egohygiene/relay continuity preflight v1
    uses: egohygiene/relay/.github/workflows/continuity-preflight.yml@<full-commit-sha>
    with:
      repository-id: "example/repository"
      visibility: "public"
      base-revision: "${{ github.event.pull_request.base.sha }}"
      head-revision: "working-tree"
      disposition: "updated"
      # Required only when disposition is "exception".
      exception-reference: ""
      transition: "pull-request"
      rollout-mode: "observe"
      evaluation-date: "${{ github.event.pull_request.updated_at }}"
      live-evidence-status: "verified"
      live-evidence-references: '["${{ github.event.pull_request.html_url }}"]'
      artifact-retention-days: 14
```
