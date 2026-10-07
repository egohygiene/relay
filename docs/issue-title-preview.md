# Issue-title preview — draft checkpoint

Refs [Relay #133](https://github.com/egohygiene/relay/issues/133).

This unfinished checkpoint preserves the local implementation for review and
resumption. It is not ready to merge. No provider mutation or apply command exists.

## Current implementation

`scripts/preview_issue_titles.py` exposes `prepare`, `collect`, and `preview`.
The allowlisted pilot is `egohygiene/aether`. Collection uses public GitHub GETs,
excludes pull requests, and records issue identity, titles, labels, timestamps,
page coverage, and bounded errors. Preview uses captured files offline.

Relay reuses the existing collection runtime preparation and safe-I/O helpers.
The source pin is Egolint `20edc7d98ab7750388e4783ffaf1bab0d9278d60`;
the organization contract remains candidate `egohygiene.issue-title/v1` at
`19d2be9bf0191710508cefbb9f0b1abb3a40d9be`. The lock records the full source
tree and artifact digests. Merge status does not promote authority or adoption.

The actual Egolint CLI validates current snapshots and formats only explicitly
reviewed type/subject inputs. Reviews bind to a snapshot digest and issue IDs.
Proposals retain all current labels. Formatted-title conformance, provider-label
availability, and current issue classification remain separate findings.

## Evidence retained

- [Public Aether snapshot](evidence/issue-title-preview/aether-snapshot-2026-10-06.json):
  collected 2026-10-06 17:25:23–17:25:42 UTC; 28 open issues, one excluded PR,
  41 labels; each endpoint returned a terminal page below 100 records.
- This is a completed page traversal, not an atomic provider snapshot or a
  completed pilot preview. No reviewed live proposals or pilot plan are retained yet.
- [Focused local validation](evidence/issue-title-preview/local-validation-2026-10-07.json):
  all 24 tests passed with no skips, including 11 real Egolint integration tests.
  All three JSON schemas passed schema validation. The pagination fixture failure
  was caused by substring matching `page=1` inside `per_page=100`; exact query parsing
  fixes the fixture. Production adapter behavior is unchanged.
- Workspace maintenance removed the unpushed checkout. Source and tests were restored
  from the recorded patches; schemas and lock were regenerated with the surviving
  generator and pinned runtime sources. The public snapshot survived unchanged.
  Restored source has now passed the focused suite. Broad repository tests and
  linting remain deferred; these results do not establish live pilot acceptance.

## Resume commands

Use Python 3.12+, Git, and the Egolint-pinned Rust toolchain. Install the existing
Python runtime dependencies in your virtual environment:

```bash
python3 -m pip install --requirement actions/repository-intelligence/contracts/roadmap-collector-requirements.txt
```

Acquire the exact Egolint source and run `cargo fetch --locked` in that checkout
before offline preparation. Supply absolute paths without parent traversal:

```bash
python3 scripts/preview_issue_titles.py prepare \
  --egolint "/absolute/path/to/egolint" \
  --output "/absolute/path/to/new-title-runtime"

python3 scripts/preview_issue_titles.py preview \
  --repository "egohygiene/aether" \
  --snapshot "docs/evidence/issue-title-preview/aether-snapshot-2026-10-06.json" \
  --runtime "/absolute/path/to/new-title-runtime" \
  --output-dir "/absolute/path/to/new-preview-directory"

RELAY_ISSUE_TITLE_RUNTIME="/absolute/path/to/new-title-runtime" \
  python3 -m unittest discover --start-directory tests \
  --pattern "test_issue_title_preview.py" --verbose
```

Omitting `--reviews` reports current conformance without proposing titles.
Output directories must be new. Preview returns 0 for complete execution coverage,
2 for partial/unavailable evidence, and 3 for rejected inputs or execution setup.
Exit 0 does not mean every issue conforms or is approved to change.

## Remaining before acceptance

1. Generate and inspect the Aether preview; add reviewed per-issue inputs only where
   classification and wording have actually been reviewed.
2. Finish the usage guide and reconcile the remaining issue133 acceptance evidence.

The pagination fix and focused verification are complete. Tests cover current/proposed
separation, preserved identifiers and labels, missing/unknown/conflicting classification,
incomplete collection, stale/missing runtime evidence, unchanged inputs, and repeatable
CLI output across distinct output locations. This is bounded local evidence, not a
broader audit or proof of portability across platforms/toolchains.

Actions, broad linting, and broader audits are deferred. The later apply/recovery
checkpoint still needs an approved plan, current-state comparison, conflict
handling, receipts, rollback, and no-op repeat. Label rollout belongs to Pace #10;
fleet reconciliation belongs to organization #23. This draft does not close #133.
