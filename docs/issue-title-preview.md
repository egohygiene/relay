# Canonical issue-title preview

Refs [Relay #133](https://github.com/egohygiene/relay/issues/133).

This local, read-only tool shows current titles, explicitly reviewed candidates,
and classification or provider-label blockers for one repository. The implementation
and bounded Aether pilot are complete for maintainer review in
[PR #136](https://github.com/egohygiene/relay/pull/136). The PR remains draft;
merging, issue mutation, label rollout, and enforcement are separate actions.

## Ownership and source selection

`scripts/preview_issue_titles.py` exposes `prepare`, `collect`, and `preview`.
Only `egohygiene/aether` is allowlisted. Relay reuses its existing runtime preparation
and safe-I/O helpers. Egolint owns formatting and validation; Relay contains no
second emoji/type mapping or title parser.

The [lock](../catalog/issue-title-preview.v1.lock.json) records the complete tree
and source-file digests:

| Input | Selected revision / state |
| --- | --- |
| Egolint source | `20edc7d98ab7750388e4783ffaf1bab0d9278d60` |
| Egolint tree | `caeb2d3800d0d65de1822c59e74a9c671f0eab95` |
| Contract source | `egohygiene/.github@19d2be9bf0191710508cefbb9f0b1abb3a40d9be` |
| Contract | `egohygiene.issue-title/v1`, version `1.0.0` |
| Authority / adoption | Candidate / observe |

Merge status does not promote authority or install a release. Changing the lock
or allowlist requires a reviewed source-selection change.

## Prepare the local runtime

Use Python 3.12+, Git, and a compatible Rust/Cargo toolchain. Install the existing
Python dependencies in a virtual environment, acquire the exact Egolint revision,
and populate Cargo's dependency cache. Acquisition may use the network:

```bash
python3 -m pip install --requirement actions/repository-intelligence/contracts/roadmap-collector-requirements.txt

git clone --no-checkout "https://github.com/egohygiene/egolint.git" \
  "/absolute/path/to/egolint"
git -C "/absolute/path/to/egolint" checkout --detach \
  "20edc7d98ab7750388e4783ffaf1bab0d9278d60"
(
  cd "/absolute/path/to/egolint"
  cargo fetch --locked
)

python3 scripts/preview_issue_titles.py prepare \
  --egolint "/absolute/path/to/egolint" \
  --output "/absolute/path/to/new-title-runtime"
```

Preparation reads exact Git objects, verifies the lock, and builds with
`cargo build --locked --offline --bin egolint`. The runtime receipt binds the
lock and executable digests. The source checkout must contain the pinned tree.
`--cargo` may select an absolute Cargo executable; `CARGO_HOME`, `RUSTUP_HOME`,
and `CARGO_BUILD_JOBS` select trusted build inputs. This source-pinned preparation
does not establish hermetic or cross-platform binary reproducibility.

Use paths without symlink components or `..` traversal. Preparation rejects an
existing destination; preview requires a new output directory.

## Collect or replay

For a new public observation:

```bash
python3 scripts/preview_issue_titles.py collect \
  --repository "egohygiene/aether" \
  --output "/absolute/path/to/new-aether-snapshot.json"
```

Collection uses credential-free GitHub GETs without redirect following. No issue
write permission is required. It records repository identity, open issue IDs,
titles, full labels, update/observation times, label inventory, page counts/digests,
and coverage errors. PRs are excluded. Each endpoint is bounded to 20 pages of
100 records; a short terminal page establishes complete traversal. Partial reads,
page limits, and unavailable access remain explicit. Sequential reads are not
atomic. An inconsistent issue/label inventory is rejected as `INVENTORY_CHANGED`;
collect again rather than assuming completeness.

Replay the retained capture offline:

```bash
python3 scripts/preview_issue_titles.py preview \
  --repository "egohygiene/aether" \
  --snapshot "docs/evidence/issue-title-preview/aether-snapshot-2026-10-06.json" \
  --runtime "/absolute/path/to/new-title-runtime" \
  --output-dir "/absolute/path/to/new-unreviewed-preview"
```

Omitting `--reviews` evaluates current conformance without proposing titles.
Outputs are deterministic `plan.json` and `preview.md`. The JSON separates current
and proposed snapshots, native validation summaries, reviews, required-label
availability, coverage, and source/runtime provenance.

## Explicit review inputs

The [review schema](../schemas/issue-title-reviews.v1.schema.json) and
[three pilot reviews](evidence/issue-title-preview/aether-reviews-2026-10-07.json)
define the input: repository identity, `snapshot_sha256`, and entries with `id`,
`number`, `type`, and `subject`. Read issue scope before choosing a type. Copy the
intended subject explicitly, preserving wording, case, and identifiers. Do not
infer type from emoji, automatically strip prefixes, or treat titles as native
parent/child links. Agent review prepares candidates, not owner approval to apply.

`snapshot_sha256` hashes the parsed snapshot serialized as UTF-8 JSON with sorted
keys, two-space indentation, literal Unicode, no non-finite numbers, and a final
newline. It is not necessarily the raw-file digest. A changed snapshot or mismatched
issue ID is rejected as `STALE_REVIEW`; never transplant a review by number alone.

```bash
python3 scripts/preview_issue_titles.py preview \
  --repository "egohygiene/aether" \
  --snapshot "docs/evidence/issue-title-preview/aether-snapshot-2026-10-06.json" \
  --reviews "docs/evidence/issue-title-preview/aether-reviews-2026-10-07.json" \
  --runtime "/absolute/path/to/new-title-runtime" \
  --output-dir "/absolute/path/to/new-reviewed-preview"
```

Egolint formats the explicit type/subject and validates that title with its intended
primary label. Separately, it validates the proposed title with **all observed labels
unchanged**. Thus `format_validation` may be conformant while provider classification
remains missing or conflicted. No labels are silently added, removed, or rewritten.

## Interpret results

| Row status | Meaning |
| --- | --- |
| `unchanged` | Current title/classification conforms, or a reviewed conformant title already matches. |
| `proposed` | Reviewed title differs, existing labels conform, and required provider label exists. Still no approval or write. |
| `needs-review` | Current title is nonconformant and an explicit type/subject review is missing. |
| `needs-classification` | Primary type is missing, unknown, or conflicting; inspect native validation. |
| `blocked` | Reviewed title exists but label availability or preserved classification blocks application. |
| `unavailable` | Issue evidence, runtime/source provenance, or reviewed formatter input cannot be validated. |

Exit 0 means execution coverage completed, even with blocked or unclassified rows.
Exit 2 retains partial/unavailable evidence. Exit 3 rejects input/setup, for example
`STALE_REVIEW`, `INPUT`, `PATH`, or `REPOSITORY`. Missing/stale runtime evidence yields
unavailable rows. Inspect coverage, diagnostics, native messages, and row reasons
together. No exit code grants mutation authority.

## Aether pilot and acceptance evidence

The [snapshot](evidence/issue-title-preview/aether-snapshot-2026-10-06.json) contains
28 open issues, one excluded PR, and 41 labels, observed 2026-10-06 at
17:25:23–17:25:42 UTC. Both endpoints reached a terminal page. This is dated
public-provider evidence, not a fresh claim about today's backlog.

The [human preview](evidence/issue-title-preview/aether-pilot-2026-10-07/preview.md)
and [machine plan](evidence/issue-title-preview/aether-pilot-2026-10-07/plan.json)
were generated and reviewed on 2026-10-07 UTC. Without reviews all 28 issues need
classification. Three reviewed subjects yield **25 needing classification and three
blocked candidates**. The captured inventory has no canonical `type:*` labels.
Each candidate formats conformantly, but its preserved empty labels still need
classification. No candidate is ready to apply.

- #63 retains `spec(distribution):` verbatim, without interpreting its legacy prefix.
- #92 removes only the explicitly reviewed compass decoration.
- #94 retains `[Release checkpoint 1]` exactly while replacing that decoration.

All three use `architecture` after review of their contract/system-boundary scope.
Their identity, title, labels, and update time matched the capture when reread for
review. The other 25 issues were not individually classified. The
[pilot receipt](evidence/issue-title-preview/aether-pilot-validation-2026-10-07.json)
records review rationale, body digests, commands, output digests, and limitations.

| Issue #133 criterion | Retained evidence |
| --- | --- |
| Bounded draft and exact pins | PR #136 and the immutable source lock. |
| Synthetic boundary cases | [24 passing tests, zero skips](evidence/issue-title-preview/local-validation-2026-10-07.json), including 11 native cases; three valid schemas. |
| Native reviewed formatting | Synthetic legacy/checkpoint cases plus three provider-backed candidates; no independent mapping/parser. |
| Repeatability and preserved inputs | Focused tests and byte-identical pilot JSON/Markdown in distinct directories; unchanged input digests and separate current/proposed state. |
| Read-only execution | Credential-free GET collection, offline preview, no mutation command, and zero title/label/state/relationship writes or workflow dispatches. |
| Bounded Aether report | Complete recorded traversal, all 28 issues accounted for, explicit label gaps and non-atomic/freshness limits. |
| Apply/recovery handoff | Next checkpoint below; no application authority implied. |

The earlier pagination failure was a fixture matching `page=1` inside `per_page=100`.
Exact query parsing and page/identity assertions fixed it; the recovered implementation
passed the focused suite. To repeat:

```bash
RELAY_ISSUE_TITLE_RUNTIME="/absolute/path/to/new-title-runtime" \
  python3 -m unittest discover --start-directory tests \
  --pattern "test_issue_title_preview.py" --verbose
```

Without that variable, native tests skip and do not supply equivalent evidence.
The pilot reused the verified runtime and unchanged implementation. Broad tests,
linting, hosted Actions, audits, publication, and platform portability remain deferred.

## Next checkpoint

Maintainer review of PR #136 is next. Preview-only acceptance evidence is assembled;
#133 remains open pending review and normal merge/closure. Label provisioning and
classification follow the governed rollout in [Pace #10](https://github.com/egohygiene/pace/issues/10).

Before any title write, a separate Relay apply/recovery checkpoint must bind an
explicitly approved plan to fresh current-state comparison, stop on conflicts,
restrict writes to approved identities/fields, and retain per-operation receipts.
It must cover interrupted execution/retry, guarded rollback that preserves newer
edits, and verified no-op repeat. Missing classification or provider labels remain
blocked until separately authorized resolution. Preview stays read-only.

Event enforcement belongs to [organization #24](https://github.com/egohygiene/.github/issues/24),
and the fleet sweep to [organization #23](https://github.com/egohygiene/.github/issues/23).
Neither is installed by this pilot. Parallel ADR PR #135 and its continuity remain
independent.
