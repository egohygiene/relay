# Flow #137 checkpoint 8 — Relay literal path guard

This candidate is a narrow backport on the consumer's exact Relay pin
`981ddf4367c67fcd625e54321d95bab027f6c0f2` (source tree
`1aa2f888d3433e2627b1ab5df6905c1064014c85`). It changes only the two
mis-scoped Bash path comparisons, adds focused regression coverage, and records
this handoff. Existing input/output contracts, defaults, locks, historical
recovery bytes, metadata and publication/scheduling gates are preserved.

The old guard closed its first `[[ ... ]]` before the two `||` comparisons.
Bash then tried to execute `/selected/path/` as a command. Canonical defaults
emitted six attempted-command diagnostics, and dot/parent path segments could
reach later action behavior. Each comparison now has its own Bash conditional,
so invalid segments return the existing fixed refusal before collection/writes.

## Executed observations

- Before the patch, the new focused suite ran seven methods and recorded forty
  failing subtests/assertions against this exact frozen baseline. The default
  path case reproduced the attempted-command stderr rather than a clean result.
- After the patch, `python3 -B -m unittest discover --start-directory tests
  --pattern test_repository_intelligence_path_guards.py --verbose` passed all
  seven methods. Subcases cover literal/hidden paths, segment-prefix siblings,
  dot/parent/noncanonical paths, shell metacharacters/controls, the four optional
  path selectors present at this pin, existing private/public overlap refusal,
  and protected output/work areas. Every invocation asserts no filesystem write.
- The harness executes the checked-in action's metadata prefix ending before
  source Git resolution. It neither executes Git nor collects, renders, uploads
  or deploys. It is not a GitHub scheduler or general filesystem sandbox proof.
- The complete metadata step passed `bash --noprofile --norc -n` via stdin, with
  no execution of the rest of that step.
- `python3 scripts/validate_continuity_preflight_contract.py validate` passed.
- `python3 -B scripts/validate_actions.py` still exits 1 with six catalog/README
  defects. An isolated checkout of the exact frozen base produced the identical
  diagnostics. The current-main comparison has ten pre-existing catalog/SPDX/
  README defects; neither baseline is advertised as green or repaired here.

## Integration and remaining gates

Relay main was observed at `12d3a0823c8c8f885dea4acf482160fd726325e2`, tree
`d47ac10463735cb000defd17a0907dd1058a06f6`; no open Relay PR was returned.
A separate current-main worktree also passed the seven-method guard suite with
its additional optional inputs. Those newer owner changes are intentionally
absent from this consumer backport. The parent sprint owns draft PR creation
and a separately reviewable Optiflow pin update to the exact backport commit.

No full Relay suite, owner runtime, hosted CI, acquisition, Pages upload,
deployment, release, merge or consumer acceptance ran. The pinned historical
continuity record is retained, with a dated pointer to this backport handoff;
its older next-action/qualification claims are history rather than authority
for this guard-only candidate. No new ADR or shared contract revision is needed.
The full suite acceptance ledger remains Flow #88, unchanged and last.
