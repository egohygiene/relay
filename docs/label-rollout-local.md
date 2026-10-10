# Apply the Aether label pilot locally

Refs [Pace #10](https://github.com/egohygiene/pace/issues/10).

Apply the reviewed, create-only Aether label plan locally; no Actions run is
needed. The connector cannot create repository label definitions.

Use Bash, Python 3.10+, Git, and authenticated GitHub CLI (`gh`) with permission to
manage Aether labels. Check `gh auth status`; use `gh auth login` if needed.
Never paste tokens into files or chat. Apply requires `GH_TOKEN`; below it is
supplied only to that process from an existing variable or `gh` credential store.
Keep shell tracing disabled.

## Select the reviewed checkpoint

Use the exact merged Relay revision pinned by the reviewed Pace lock. Review
`operations` in `<PACE_REVIEWED_PREVIEW_ARTIFACT>` and select its **native plan
`plan_sha256`**, not a file hash or outer Pace report digest. This pilot creates
18 universal labels, retains existing labels, and leaves issue fields unchanged.

```bash
set -euo pipefail
set +x
RELAY_REVISION="<RELAY_REVISION_FROM_REVIEWED_PACE_LOCK>"
EXPECTED_PLAN_SHA256="<REVIEWED_NATIVE_PLAN_SHA256>"
RUN_DIRECTORY="${PWD}/aether-label-apply-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir "${RUN_DIRECTORY}"
cd "${RUN_DIRECTORY}"
git clone --no-checkout "https://github.com/egohygiene/relay.git" relay
git -C relay checkout --detach "${RELAY_REVISION}"
test "$(git -C relay rev-parse HEAD)" = "${RELAY_REVISION}"
ORGANIZATION_REVISION="$(python3 - <<'PYTHON'
import json
from pathlib import Path
lock = Path("relay/actions/repository-labels/contracts/organization-labels.lock.json")
print(json.loads(lock.read_text())["revision"])
PYTHON
)"
git clone --no-checkout "https://github.com/egohygiene/.github.git" organization
git -C organization checkout --detach "${ORGANIZATION_REVISION}"
test "$(git -C organization rev-parse HEAD)" = "${ORGANIZATION_REVISION}"
git clone --no-checkout "https://github.com/egohygiene/aether.git" aether
AETHER_REVISION="$(git -C aether rev-parse origin/main)"
git -C aether checkout --detach "${AETHER_REVISION}"
printf '%s\n' "${RELAY_REVISION}" "${ORGANIZATION_REVISION}" \
  "${AETHER_REVISION}" > source-revisions.txt
```

Do not edit these fresh detached checkouts or execute Aether code. An absent
`aether/.github/relay-labels.json` is supported and defaults to no retirement.
The planner verifies pinned policy byte digests and compatible versions.

## Capture, replan, and compare before writing

```bash
capture_labels() {
  local destination="$1"
  gh api --method GET --paginate --slurp \
    "repos/egohygiene/aether/labels?per_page=100" > "${destination}.pages.json"
  python3 - "${destination}.pages.json" "${destination}" <<'PYTHON'
import json
import sys
from pathlib import Path
pages = json.loads(Path(sys.argv[1]).read_text())
assert isinstance(pages, list) and all(isinstance(page, list) for page in pages)
Path(sys.argv[2]).write_text(
    json.dumps([label for page in pages for label in page],
               ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PYTHON
}
make_plan() {
  python3 relay/actions/repository-labels/scripts/repository_labels.py sync-plan \
    --repository "egohygiene/aether" \
    --lock "relay/actions/repository-labels/contracts/organization-labels.lock.json" \
    --catalog "organization/.github/labels/catalog.v1.json" \
    --assignments "organization/.github/labels/repositories.v1.json" \
    --config "aether/.github/relay-labels.json" \
    --observed-labels "$1" \
    --output "$2"
}
date -u +%Y-%m-%dT%H:%M:%SZ > before-observed-at.txt
capture_labels "before-labels.json"
make_plan "before-labels.json" "fresh-plan.json"
python3 - "${EXPECTED_PLAN_SHA256}" <<'PYTHON'
import json
import re
import sys
from pathlib import Path
plan = json.loads(Path("fresh-plan.json").read_text())
assert re.fullmatch(r"[0-9a-f]{64}", sys.argv[1]), "Replace the reviewed checksum"
assert plan["plan_sha256"] == sys.argv[1], "State changed: review a fresh plan"
assert plan["repository"] == "egohygiene/aether"
assert plan["operations"]["update"] == [], "This pilot is create-only"
assert plan["operations"]["delete"] == [], "Deletion is not authorized"
assert len(plan["operations"]["create"]) == 18, "Review the changed pilot scope"
print("Fresh plan matches the reviewed create-only pilot.")
PYTHON
```

Stop on any failed command or assertion. On checksum mismatch, inspect and
review the changed plan; do not merely substitute its checksum. Provider reads
and writes are sequential, not atomic. Apply promptly; after a pause, recapture
and compare using new evidence filenames.

## Apply once and verify a no-op plan

```bash
GH_TOKEN="${GH_TOKEN:-$(gh auth token)}" \
  python3 relay/actions/repository-labels/scripts/repository_labels.py sync-apply \
    --repository "egohygiene/aether" \
    --plan "fresh-plan.json" \
    --output "apply-evidence.json"
date -u +%Y-%m-%dT%H:%M:%SZ > after-observed-at.txt
capture_labels "after-labels.json"
make_plan "after-labels.json" "after-plan.json"
python3 - <<'PYTHON'
import json
from pathlib import Path
read = lambda name: json.loads(Path(name).read_text())
plan = read("after-plan.json")
assert all(not operations for operations in plan["operations"].values()), \
    "Canonical label drift remains; review before any further write"
assert plan["summary"]["unchanged"] == 18
before = {label["name"]: label for label in read("before-labels.json")}
after = {label["name"]: label for label in read("after-labels.json")}
for name, previous in before.items():
    assert name in after, f"An existing label disappeared: {name}"
    for field in ("id", "name", "color", "description"):
        assert previous.get(field) == after[name].get(field), \
            f"An existing label changed: {name} / {field}"
print("Verified: all 18 canonical labels match; existing labels are preserved.")
PYTHON
```

The zero-operation plan verifies no-op behavior without another apply. Retain
revisions, dated inventories, both plans, and the aggregate receipt with Pace;
the apply receipt alone does not prove final provider state.

Interrupted apply may have created labels without writing its aggregate receipt.
**Do not replay the old create plan.** Recapture into new files, replan, review,
and authorize only remaining operations; preserve earlier evidence. The engine
has no per-operation recovery receipts. Never automatically delete created
labels as rollback; retirement needs separate review.

## Follow-on: the three reviewed issue titles

After label verification, resume the separate title apply/recovery checkpoint
for Aether #63, #92, and #94; label creation does not classify issues:

1. Reread their identities, scope, titles, and full labels; reconfirm the reviewed
   `architecture` classification and preserved subjects.
2. Add only the existing `type:architecture` label without replacing other labels.
3. Collect a fresh title snapshot, bind explicit reviews to its digest, and run
   the [native title preview](issue-title-preview.md).
4. Implement the documented fresh-state guards, bounded title writes, receipts,
   interrupted retry, guarded rollback, and unchanged-title repeat verification.

The title tool remains preview-only; this guide does not implement its apply
path. Other issues, event enforcement, and fleet rollout remain separate.
