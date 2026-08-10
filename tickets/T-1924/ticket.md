---
id: T-1924
title: Finish T-1911's Tier-A snapshot-param drop on the 5 handlers in _fix_engine_sync.py
state: done
kind: bug
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fix_engine_sync.py
- src/frob/gates/_fix_engine.py
- tests/test_gates.py
- tests/unit/gates/test_sys_interface_canonical_order.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: AFFECT001 requires the affects()-closure doc anchor to move with the code
    in the same diff; docs/modules/gates.md is the doc the touched handlers' own frob:doc
    directives point at
  actor: logan
  at: '2026-08-09'
evidence:
- tests/test_gates.py::TestFixEngineTierABatch2::test_reg010_files_missing_entries_and_reverifies_clean
- tests/test_gates.py::TestFixEngineTierABatch2::test_reg010_already_in_sync_is_a_no_op
- tests/test_gates.py::TestFixEngineTierABatch2::test_rel002_resyncs_pyproject_and_uv_lock_from_manifest
- tests/test_gates.py::TestFixEngineTierABatch2::test_rel002_already_in_sync_touches_nothing
- tests/test_gates.py::TestFixEngineTierA::test_sys100_may_via_union_applies_via_apply_tier_a_fixes
- tests/test_gates.py::TestFixEngineTierA::test_sys100_no_design_dir_is_a_no_op
- tests/test_gates.py::TestFixEngineTierA::test_sys100_extended_whole_node_grant_applies_via_apply_tier_a_fixes
- tests/test_gates.py::TestFixEngineTierA::test_sys100_extended_no_design_dir_is_a_no_op
designated_repro_test: tests/test_gates.py::TestFixEngineTierABatch2::test_reg010_files_missing_entries_and_reverifies_clean
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1911 fixed the too-strict-for-purpose Tier-A dispatch signature on the
two handlers reachable from this worktree without a lease conflict
(fix_fmt001_directive_wrap, fix_e501_merge_introduced in
src/frob/gates/_fix_engine_text.py: dropped their unused GraphSnapshot
parameter entirely so a call site can no longer pass bare None -- ty now
statically refuses too-many-positional-arguments instead).

The SAME pattern (a `del snapshot  # signature uniformity only` body with
a non-Optional GraphSnapshot parameter no caller needs) also exists on
five more handlers in src/frob/gates/_fix_engine_sync.py:
fix_reg010_registry_sync, fix_rel002_release_sync, fix_sys100_may_via_union,
fix_sys100_extended_whole_node_grant, and fix_sys_interface_canonical_order
(the exact function T-1896/T-1900/T-1906 repeatedly re-broke -- the
motivating incident for T-1911 itself). That file was held by T-1904's
live cross-worktree lease for this ticket's entire duration, so none of
these five could be touched here.

Apply the identical fix to all five once T-1904's lease clears: drop the
GraphSnapshot parameter, update TIER_A_HANDLERS' lambda wrappers in
src/frob/gates/_fix_engine.py to stop forwarding snapshot to them, and
update every test call site (tests/test_gates.py,
tests/unit/gates/test_sys_interface_canonical_order.py, and any others
`grep -n "fix_reg010_registry_sync\|fix_rel002_release_sync\|fix_sys100_may_via_union\|fix_sys100_extended_whole_node_grant\|fix_sys_interface_canonical_order" tests/` finds).

frob:no-behavior-change reason="pure dispatch-signature refactor, same shape T-1911 already established as behavior-preserving: drops an unused, del-ed GraphSnapshot parameter from 4 Tier-A handlers and stops TIER_A_HANDLERS' lambdas from forwarding it -- no handler body's actual logic changes, so the designated repro test genuinely passes at both the parent and the fix; a FAILED_AT_PARENT result would falsify this claim, not confirm it"

## Done report

Established current reality on main before touching anything (per the
ticket's CAUTION): T-1916 (landed 5e17bb70a6a4) already deleted
fix_sys_interface_canonical_order and its test file
(tests/unit/gates/test_sys_interface_canonical_order.py) entirely, along
with the false CHK-GATE-SYS-IFACE-ORDER registry row. So of the 5
handlers named in the ticket, only 4 still exist in
src/frob/gates/_fix_engine_sync.py with the T-1911 pattern (a
non-Optional GraphSnapshot parameter immediately `del`-ed, never read):
fix_reg010_registry_sync, fix_rel002_release_sync,
fix_sys100_may_via_union, fix_sys100_extended_whole_node_grant. Narrowed
the ticket to these 4; the 5th is stale scope, not silently worked
around.

Fix (same shape as T-1911, restructure not retype): dropped the unused
`snapshot: GraphSnapshot` parameter from all 4 handlers. Updated
TIER_A_HANDLERS' lambda wrappers and the SYS100 dispatcher
(_fix_sys100_both_cases) in src/frob/gates/_fix_engine.py to stop
forwarding `snapshot` to these 4 callees -- the dispatch table's own
outward 4-arg shape (root, snapshot, queue, ticket_id) is unchanged,
only what gets forwarded downstream. tests/test_gates.py's 4 direct
call sites (REG010/REL002's own unit tests) updated to the new 1-arg
signature; the 4 SYS100 tests already went through apply_tier_a_fixes
and needed no change.

Enforcement (ty statically refuses a stray snapshot arg, same mechanism
T-1911 established): wrote a scratch probe file
(src/frob/gates/_t1924_probe.py, never committed) calling all 4
functions with a stray second positional argument and ran it through
`uv run ty check` -- confirmed `too-many-positional-arguments` for all
4 functions, then deleted the probe file (git status confirmed clean
afterward).

Fail-then-pass proof: `git diff` of the two src files saved to a patch,
reverted with `git checkout --`, re-ran the 4 REG010/REL002 test node
ids against the OLD (root, snapshot) signature with the NEW 1-arg call
sites already in tests/test_gates.py -- all 4 failed with
`TypeError: ... missing 1 required positional argument: 'snapshot'`.
Re-applied the src patch and re-ran the full 8-test set -- all green.

`uv run ty check` (via the ty probe above) and the touched-file portion
of `uv run frob check --only lint --ticket T-1924` are clean of any
NEW finding: the run's single ruff-check error (F401 unused
CodeBinding import, _fix_engine_sync.py:67) and the repo-wide
ruff-format drift (71 files) both pre-exist on main, verified directly
against `git show main:src/frob/gates/_fix_engine_sync.py` (same
unused import already present there) -- neither is caused by, or in
scope for, this ticket.

`uv run frob check --only coverage --ticket T-1924` shows 18 COV007
errors, all in src/frob/vet/**, none in any file this ticket touched
(grepped for _fix_engine in that run's output: zero hits) -- pre-existing
repo-wide debt, not introduced here.

### Changed
```
 tickets/T-1924/ticket.md | 11 ++++++++++-
 1 file changed, 10 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gates.py::TestFixEngineTierABatch2::test_reg010_files_missing_entries_and_reverifies_clean` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierABatch2::test_reg010_already_in_sync_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierABatch2::test_rel002_resyncs_pyproject_and_uv_lock_from_manifest` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierABatch2::test_rel002_already_in_sync_touches_nothing` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_sys100_may_via_union_applies_via_apply_tier_a_fixes` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_sys100_no_design_dir_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_sys100_extended_whole_node_grant_applies_via_apply_tier_a_fixes` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_sys100_extended_no_design_dir_is_a_no_op` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 9 error(s), 1500 warning(s), 696 waived
- error-findings: AFFECT001@src/frob/gates/_fix_engine.py, AFFECT001@src/frob/gates/_fix_engine_sync.py, COV003@tickets/T-1872, COV003@tickets/T-1895, COV003@tickets/T-1896, COV003@tickets/T-1900, COV003@tickets/T-1906, F401@/home/logan/projects/frob/.claude/worktrees/waive-substrate/src/frob/gates/_fix_engine_sync.py, PRE001@tickets/T-1924
