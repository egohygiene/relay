# Publish Report Snapshot

Commit and push a curated, stable subset of `.reports/` from a trusted
default-branch workflow. This action is intentionally narrow and consequential:
it is the only Repository Intelligence component that writes to the consumer
repository.

```yaml
- name: Publish normalized OSV snapshot
  if: >-
    always() &&
    github.event_name != 'pull_request' &&
    github.ref_name == github.event.repository.default_branch
  uses: egohygiene/relay/actions/publish-report-snapshot@<full-commit-sha>
  with:
    paths: |
      .reports/osv/summary.json
    commit-message: "chore(reports): 📊 refresh OSV snapshot [skip ci]"
    default-branch: "${{ github.event.repository.default_branch }}"
```

## Caller requirements

- Grant `contents: write` only to the publication job.
- Check out the default branch with credentials available to `git push`.
- Never invoke the action from pull-request or untrusted fork jobs.
- Pass one existing literal path under `.reports/` per line.
- Keep canonical native reports and public normalized summaries separate.

The action independently permits only `push`, `schedule`, and
`workflow_dispatch` events; requires a branch ref matching `default-branch`;
rejects symbolic links; accepts only literal traversal-free `.reports/` paths;
and bans timestamped `history` directories. It audits the staged diff before
committing, retries bounded push races, and returns `changed` plus `commit-sha`.

The caller remains responsible for workflow concurrency. A recommended group is
`report-snapshot-${{ github.repository }}-${{ github.ref_name }}` with
`cancel-in-progress: false`, so trusted report writers serialize rather than
cancel one another.
