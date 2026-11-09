# Manual Compare selection inside an existing native Pages build

This is a composition fragment, not another workflow or deployer. Leave the
consumer's current source selections, build/deploy/recovery jobs, historical
rollback pins and frozen artifact bytes unchanged. Both action references must
be replaced by the same reviewed full Relay commit during consumer adoption.

In the existing manual trigger, an optional explicit mode can default to off:

```yaml
workflow_dispatch:
  inputs:
    compare-mode:
      type: choice
      options: ["off", "seed", "baseline"]
      default: "off"
    compare-baseline:
      description: Reviewed JSON record selecting all exact prior upload identities; empty outside baseline mode.
      type: string
      default: ""
```

Keep the existing native build step. After it succeeds, before the consumer
verifies composition or uploads its one site artifact, validate the manual
selection without executing repository or input code:

```yaml
- id: compare_selection
  if: ${{ github.event_name == 'workflow_dispatch' && inputs.compare-mode != 'off' }}
  shell: bash
  env:
    COMPARE_MODE: ${{ inputs.compare-mode }}
    COMPARE_BASELINE: ${{ inputs.compare-baseline }}
  run: |
    set -euo pipefail
    python3 -I - <<'PY'
    import json, os, re
    mode, raw = os.environ['COMPARE_MODE'], os.environ['COMPARE_BASELINE']
    keys = ('lease', 'artifact_id', 'artifact_digest', 'source_commit', 'run_id', 'run_attempt')
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('Duplicate baseline field')
            value[key] = item
        return value
    if mode == 'seed' and not raw:
        value = dict.fromkeys(keys, '')
        value['lease'] = 'none'
    elif mode == 'baseline' and 0 < len(raw) <= 2048:
        value = json.loads(raw, object_pairs_hook=unique)
        patterns = {'lease': r'[0-9a-f]{64}:[0-9a-f]{64}',
                    'artifact_id': r'[1-9][0-9]{0,19}',
                    'artifact_digest': r'(?:sha256:)?[0-9a-f]{64}',
                    'source_commit': r'[0-9a-f]{40}',
                    'run_id': r'[1-9][0-9]{0,19}', 'run_attempt': r'[1-9][0-9]{0,5}'}
        if not isinstance(value, dict) or set(value) != set(keys) or any(
                not isinstance(value[key], str) or not re.fullmatch(patterns[key], value[key]) for key in keys):
            raise SystemExit('Select all exact baseline fields together')
    else:
        raise SystemExit('Select seed with no baseline, or baseline with a complete record')
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as target:
        for key in keys:
            target.write(key + '=' + value[key] + '\n')
    PY
- id: compare
  if: ${{ github.event_name == 'workflow_dispatch' && inputs.compare-mode != 'off' }}
  uses: egohygiene/relay/actions/repository-intelligence-compare-artifact@FULL_REVIEWED_RELAY_SHA
  with:
    source-directory: ${{ github.workspace }}/.cache/repository-intelligence/sources
    intelligence-directory: dist/intelligence
    as-of: ${{ steps.source.outputs.as-of }}
    normalization-profile: search-attribution-v1
    expected-baseline: ${{ steps.compare_selection.outputs.lease }}
    baseline-artifact-id: ${{ steps.compare_selection.outputs.artifact_id }}
    baseline-artifact-digest: ${{ steps.compare_selection.outputs.artifact_digest }}
    baseline-source-commit: ${{ steps.compare_selection.outputs.source_commit }}
    baseline-run-id: ${{ steps.compare_selection.outputs.run_id }}
    baseline-run-attempt: ${{ steps.compare_selection.outputs.run_attempt }}
```

Use the actual existing native work directory, generated subtree and source
evaluation clock. This example selects the opt-in Search profile; a legacy
native build must instead use `legacy-adr`. Add `actions: read` only to the
existing job that explicitly selects the artifact action, alongside its
existing `contents: read`; do not add Pages or write authority to that step.

A seed run can retain its actual current pair while Compare stays unavailable.
Retain the action's separate operational receipt through existing ordinary
evidence handling. Record a baseline only after its ordinary upload and entire
producer attempt actually succeed: `next-baseline-lease`, `artifact-id`,
`artifact-digest`, represented source SHA, run ID and attempt. All JSON values
are strings. No sample artifact/run ID is supplied because those identities
must come from a real capture. The action independently checks the selected
provider run, artifact, original pair and profile compatibility.

The final manifest belongs to the composed tree. When Compare ran, use its
`manifest-sha256`/`bundle-digest` outputs wherever the consumer previously used
the native builder's values, or read and verify the final manifest directly.
When Compare was off, keep the native builder's original outputs. Preserve
the consumer's later non-clobber checks and one authoritative upload/deployer.
Live acceptance still needs two compatible real captures and the later native,
provider, privacy, failure/expiry, publication and recovery verification pass.
