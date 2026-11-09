# Captured Work evidence collector

Refs [Relay #146](https://github.com/egohygiene/relay/issues/146).
This is a local, read-only implementation checkpoint. Every output is a
**publication-denied review envelope**. It does not collect over the network,
execute consumer code, deploy a site, infer completion, or award achievements.

## Supported owner mapping

The collector uses the same reviewed graph/coverage intersection as the ADR
collector, through its own `work-collector.v1.lock.json`:

| Owner | Immutable source | Supported responsibility |
| --- | --- | --- |
| Hygiene | `639a003d5ddc4d242c2cf190eeb59a9fc522d199` | Proposed graph `egohygiene.repository-intelligence/v1` alpha.2, alpha.1 relationship vocabulary, nine-domain coverage and reference validation |
| EgoLint | `d917ea524962639494e5bb4b3196192238ba57d9` | Native `intelligence validate-coverage`, with the compatible Hygiene source set |
| Observatory | `f411b83398dd07aa3d5e6e2c89d1e8dfff746085` | Alpha.2 repository snapshot normalization, Work open-record lists, Search and related graph views |

File hashes and source trees remain in the lock. Runtime acquisition reuses
`collect_repository_roadmap.py`; graph normalization reuses the ADR collector's
Hygiene → native EgoLint coverage → Observatory adapter. No source-level ADR or
roadmap validation is run against provider inventory. Native coverage validation
does not establish semantic acceptance of provider work or historical outcomes.

This is a provider transport seam, not a new canonical Work schema. The closed
`work-provider-capture.v1.schema.json` admits only already-selected public
metadata and explicit same-repository links. Bodies, comments, raw API objects,
actors, emails, labels, private targets, cursors, signed URLs and logs are absent.
An authorized capture producer must verify public visibility before preparing
the file. A caller's `public` declaration is not independent provider proof.

| Captured metadata | Existing Hygiene graph mapping |
| --- | --- |
| `issues.records[*]`, `kind: issue` | `issue`, native number as key and required `attributes.number`; `github_issue` provenance |
| `pull_requests.records[*]`, `kind: pull_request` | `pull_request`, native number and `attributes.number/draft`; `github_pull_request` provenance |
| Provider state | Authoritative provider observation: issue `open/closed`, PR `open/closed/merged` |
| Provider ID, issue state reason, explicit timestamps | Allowlisted entity attributes; they do not change semantic roadmap state |
| Explicit `blocks/depends-on/implements/informs` link | Existing relationship vocabulary, original direction and assertion; owning Hygiene validator checks endpoint-kind compatibility |
| Domain scope, pagination and terminal outcome | Existing `issues/pull_requests` collection coverage; other seven domains stay `uncollected` |

URLs are constructed from the declared repository and positive number. Input
cannot supply a navigation URL. Titles remain bounded untrusted text; the static
renderer owns escaping. Known credential, email and runner-path patterns fail
closed without echoing text. A number may occur only once across both inventories,
because GitHub shares issue/PR numbering. Duplicate provider IDs, wrong types,
contradictory lifecycle dates and scope/state mismatches are rejected.

## Coverage and time

Each inventory has its own `captured_at`, `scope`, `outcome`, `pagination` and
records. `scope: all`, `outcome: complete`, at least one received page, exhausted
pagination, and no truncation are all necessary for `observed/observed_empty`.
`open`, `closed` or `references` scope always remains partial. A `merged` PR
belongs to the closed scope. A referenced subset can never establish an empty
backlog or historical completeness.

Rate limits, permission loss, provider failure or a page bound after usable
pages yield `partial` with the original observation time, even when the received
pages were empty. With no usable page, access denial/provider unavailability
becomes `unavailable`; collection error becomes `failed`. `not_requested` admits
no pages, records or timestamp. Pagination is capped at 64 pages, each inventory
at 2,000 records, and the capture file at 1 MiB; larger inputs must retain an
explicit partial scope rather than claim an exhausted inventory.

Freshness is measured against the explicit projection `--observed-at`; the
collector never reads the wall clock. A stale complete capture remains stale.
No inventory claims `history`, and no synthetic lifecycle event is emitted.
The collector retains provider closure reasons, including `not_planned`, without
interpreting closure as accepted work. PR merge does not complete an issue,
roadmap step, milestone, campaign or human disposition.

Links require represented public endpoints. An unresolved link is withheld with
a fixed diagnostic rather than creating a placeholder. Inferred and authoritative
links remain distinct. No raw link body or inferred private gap is exported.

## Local use

Install the existing exact collector Python requirements and prepare trusted
runtime bytes separately from the consumer checkout:

```bash
python actions/repository-intelligence/scripts/collect_repository_work.py prepare \
  --hygiene /path/to/hygiene --egolint /path/to/egolint \
  --observatory /path/to/observatory --output /path/to/work-runtime

python actions/repository-intelligence/scripts/collect_repository_work.py collect \
  --runtime /path/to/work-runtime --repository-root /path/to/consumer \
  --repository egohygiene/relay --visibility public \
  --source-commit FULL_CONSUMER_SHA --observed-at 2026-11-09T00:00:00Z \
  --provider-evidence /path/to/capture.json \
  --output /path/to/review/work-collection.review.json
```

Use the versioned provider schema to construct a capture. An unrequested domain
has `scope: all`, `outcome: not_requested`, `captured_at: null`, zero received
pages, `exhausted: false`, `truncated: false`, and an empty record array. A usable
empty inventory needs an actual received, exhausted page at an explicit capture
time; an empty local array alone is insufficient.

`source_commit` in the capture must equal the explicit represented commit and
exist as a Git commit in the consumer repository. This binds the build context;
present-state provider observations do not become historical observations at
that Git revision. Keep the generated envelope outside consumer source and
public output. Exit 0 means both inventories are complete and fresh with valid
normalization; 2 retains partial, stale, failed, unavailable or unrequested
evidence for review; 3 retains a bounded denial when possible.

The envelope includes capture/schema/runtime hashes, exact pins, capture bounds,
per-domain coverage, fixed diagnostics, the canonical graph candidate and its
normalized snapshot candidate. Equal source/capture/runtime inputs serialize
deterministically without checkout names or execution timestamps. The candidate
can be inspected through the existing renderers after deliberate extraction;
the production builder does not automatically admit or publish this envelope.

## Remaining acceptance

No tests, CI, live capture, consumer rendering, deterministic replay, or deployed
canary were run for this implementation pass; the user deferred those checks.
The next pass must cover adversarial capture inputs, pagination/rate-limit and
partial-empty cases, native runtime replay, different checkout names, and a named
consumer's Work evidence. Current Observatory Now priorities remain sourced only
from canonical roadmap queues and explicit blockers: this collector deliberately
does not invent a next action from an open issue list. Production composition
and CLI/action/workflow parity remain Relay #151 and the owning build integration.
Consumers retain publication and rollout authority.
