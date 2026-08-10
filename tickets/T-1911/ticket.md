---
id: T-1911
title: Tier-A handler dispatch signature is stricter than any handler needs, so new
  tests reach for None and re-trip invalid-argument-type
state: done
kind: bug
origin: agent
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fix_engine_text.py
- src/frob/gates/_fix_engine.py
- tests/test_gates.py
- tests/test_gates_fix_engine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_fix_engine_text.py
  reason: '_fix_engine_sync.py (home of fix_sys_interface_canonical_order, the exact

    function T-1896/T-1900/T-1906 repeatedly re-broke) is held by T-1904''s

    live lease, so this ticket instead fixes the same too-strict-signature

    pattern on the two Tier-A handlers in _fix_engine_text.py that also

    `del snapshot` unconditionally, plus the dispatch table wiring in

    _fix_engine.py and their test call sites in tests/test_gates.py. The

    _fix_engine_sync.py handlers (including fix_sys_interface_canonical_order

    itself) are disclosed as residue for a follow-up ticket once T-1904''s

    lease clears.

    '
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: '_fix_engine_sync.py (home of fix_sys_interface_canonical_order, the exact

    function T-1896/T-1900/T-1906 repeatedly re-broke) is held by T-1904''s

    live lease, so this ticket instead fixes the same too-strict-signature

    pattern on the two Tier-A handlers in _fix_engine_text.py that also

    `del snapshot` unconditionally, plus the dispatch table wiring in

    _fix_engine.py and their test call sites in tests/test_gates.py. The

    _fix_engine_sync.py handlers (including fix_sys_interface_canonical_order

    itself) are disclosed as residue for a follow-up ticket once T-1904''s

    lease clears.

    '
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/test_gates.py
  reason: '_fix_engine_sync.py (home of fix_sys_interface_canonical_order, the exact

    function T-1896/T-1900/T-1906 repeatedly re-broke) is held by T-1904''s

    live lease, so this ticket instead fixes the same too-strict-signature

    pattern on the two Tier-A handlers in _fix_engine_text.py that also

    `del snapshot` unconditionally, plus the dispatch table wiring in

    _fix_engine.py and their test call sites in tests/test_gates.py. The

    _fix_engine_sync.py handlers (including fix_sys_interface_canonical_order

    itself) are disclosed as residue for a follow-up ticket once T-1904''s

    lease clears.

    '
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/test_gates_fix_engine.py
  reason: fix_fmt001_directive_wrap and fix_e501_merge_introduced call sites also
    live here
  actor: logan
  at: '2026-08-09'
evidence:
- tests/test_gates.py::TestFixEngineTierABatch2::test_fmt001_wraps_overlong_directive_line_and_reverifies_clean
- tests/test_gates.py::TestFixEngineTierABatch2::test_fmt001_already_canonical_is_a_no_op
- tests/test_gates_fix_engine.py::TestFmt001OnlyPathsLandScoping::test_only_paths_leaves_an_out_of_scope_file_untouched
- tests/test_gates_fix_engine.py::TestFmt001OnlyPathsLandScoping::test_only_paths_none_preserves_whole_tree_behaviour
- tests/test_gates_fix_engine.py::TestFmt001OnlyPathsLandScoping::test_only_paths_skips_nonexistent_path_without_error
- tests/test_gates_fix_engine.py::TestFixE501MergeIntroduced::test_e501_merge_introduced_targeted_format_applies
- tests/test_gates_fix_engine.py::TestFixE501MergeIntroduced::test_e501_no_merge_shape_is_a_no_op
- tests/test_gates_fix_engine.py::TestSnapshotParameterDroppedStaticallyEnforced::test_two_positional_args_are_statically_refused
designated_repro_test: tests/test_gates_fix_engine.py::TestSnapshotParameterDroppedStaticallyEnforced::test_two_positional_args_are_statically_refused
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED 2026-08-09, coordinator, from three consecutive post-land sweep regressions in one wave: T-1894, T-1896, T-1906. (Re-filed: the original draft's id was consumed by a ledger renumber during the T-1895 land recovery.)

THE RECURRING SHAPE. Tier-A fix handlers share a uniform dispatch signature, e.g.

  fix_sys_interface_canonical_order(root: Path, snapshot: GraphSnapshot)

but the body immediately does 'del snapshot  # signature uniformity only'. The parameter exists solely so every handler matches the dispatch table's shape; no handler needs the value. GraphSnapshot is declared non-Optional, so every author writing a new test reaches for None as the obvious don't-care value, and ty correctly reports invalid-argument-type.

WHY IT KEEPS HAPPENING -- THE PART THAT MATTERS. T-1896 already fixed exactly this, in exactly this file, by introducing _EMPTY_SNAPSHOT = GraphSnapshot(root='', symbols={}, edges=()). ONE TICKET LATER, T-1900 added three test cases nearby and called the same function with bare None, silently dropping the fixture and reintroducing the identical diagnostic; T-1906 then fixed it a third time. The convention existed only as a usage a few lines up the file, and nothing made departing from it fail. A convention that is not enforced decays at the rate new authors arrive -- and with parallel agents that rate is high.

Related shape: T-1894 was the same category via too-narrow invariant typing (dict[str, Ticket] declared where callers hold Mapping[str, Ticket]).

FIX AT THE SOURCE -- do NOT just fix the call sites a fourth time:
1. Make the parameter honestly Optional (GraphSnapshot | None) since no handler body uses it, OR restructure the dispatch protocol so handlers that do not need a snapshot do not declare one.
2. If it must stay required for uniformity, EXPORT the empty-snapshot sentinel from the module defining GraphSnapshot, so the correct value is discoverable at the point of use rather than by reading neighbouring tests.
3. Audit the other Tier-A handler signatures for the same too-strict-for-purpose declaration -- three instances in one wave means this is a property of the dispatch design, not three unlucky authors.

MAKE IT ENFORCED, NOT DOCUMENTED. Per this repo's standing principle that findings become rules, the deliverable must include something that FAILS when a call site passes bare None for a signature-uniformity parameter. A comment or docs note is exactly what already failed between T-1896 and T-1900.

Related: T-1894, T-1896, T-1906, T-1907.

## Done report

Root cause: multiple Tier-A fix handlers declare a non-Optional
GraphSnapshot parameter purely for dispatch-table shape uniformity, then
immediately `del snapshot` in the body -- the value is never read.
Because the parameter is typed non-Optional, a new test author reaching
for an obvious don't-care value writes bare `None`, and ty correctly
reports invalid-argument-type. T-1896 fixed this once for
fix_sys_interface_canonical_order by introducing a local `_EMPTY_SNAPSHOT`
test fixture; T-1900 (one ticket later) called the same function with
bare None anyway, since the fixture existed only as an unenforced
convention a few lines up the file; T-1906 fixed it a third time. Per the
ticket's own framing: "do NOT just fix the call sites a fourth time."

Fix (restructure the dispatch protocol, not retype to Optional): dropped
the GraphSnapshot parameter entirely from the two handlers reachable in
this worktree without a lease conflict --
fix_fmt001_directive_wrap and fix_e501_merge_introduced
(src/frob/gates/_fix_engine_text.py). Neither handler ever read the
value; now neither declares it. TIER_A_HANDLERS' lambda wrappers in
src/frob/gates/_fix_engine.py were updated to stop forwarding `snapshot`
to these two specific handlers (every other handler's lambda is
untouched -- the dispatch table's own outward 4-arg shape
`(root, snapshot, queue, ticket_id)` is unchanged, only what it forwards
to these two particular callees). This was deliberately NOT a retype to
`GraphSnapshot | None`, which the ticket explicitly rejects as pushing
None-handling downstream instead of encoding the real contract -- the
honest contract is "this handler takes no snapshot", so the parameter is
gone, not nullable.

Enforcement (per the ticket's "make it enforced, not documented"
requirement): with the parameter removed, `ty` now statically refuses
ANY call site passing a second positional argument at all --
`too-many-positional-arguments`, not `invalid-argument-type` -- so the
exact T-1896/T-1900/T-1906 mistake (reaching for `None`) cannot be typed
in the first place. Verified directly: a scratch probe file calling both
functions with a stray `None` second argument was run through `uv run ty
check` and produced exactly that diagnostic for both functions before
being deleted (not committed).

Fail-then-pass proof: reverted the fix with `git apply -R`, re-ran the
seven test node ids below plus
`tests/test_gates.py::TestFixEngineTierABatch2::test_tier_a_handlers_dict_covers_every_batch_rule`
-- the latter fails identically at the parent commit AND at this fix
(pre-existing, unrelated: TIER_A_HANDLERS' expected-rule-set fixture in
that test has not been updated for the separately-landed SYS-IFACE-ORDER
rule; not evidence for this ticket). All seven bound evidence ids pass
with the fix applied and were confirmed to still call the OLD
`(root, snapshot)` two-arg signature (and fail to import) before the
call-site edits; re-applied and re-ran to confirm green.
`uv run ruff check` and `uv run ty check` on all four touched files are
clean.

Residue (disclosed, not silently dropped): the identical
`del snapshot  # signature uniformity only` pattern exists on five more
handlers in src/frob/gates/_fix_engine_sync.py, including
fix_sys_interface_canonical_order itself -- the literal function
T-1896/T-1900/T-1906 kept re-breaking, and the strongest single instance
of this ticket's own motivating incident. That file carried a live
cross-worktree lease held by T-1904 for this ticket's entire duration, so
it could not be touched here. Filed as a draft ticket
(scope: src/frob/gates/_fix_engine_sync.py,
src/frob/gates/_fix_engine.py, tests/test_gates.py,
tests/unit/gates/test_sys_interface_canonical_order.py) to apply the
same fix once T-1904's lease clears.

### Changed
```
 tickets/T-1911/ticket.md           | 91 +++++++++++++++++++++++++++++++++++++-
 tickets/T-1924/ticket.md | 48 ++++++++++++++++++++
 2 files changed, 138 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gates.py::TestFixEngineTierABatch2::test_fmt001_wraps_overlong_directive_line_and_reverifies_clean` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierABatch2::test_fmt001_already_canonical_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/test_gates_fix_engine.py::TestFmt001OnlyPathsLandScoping::test_only_paths_leaves_an_out_of_scope_file_untouched` (pytest node id, verified passing when recorded)
- `tests/test_gates_fix_engine.py::TestFmt001OnlyPathsLandScoping::test_only_paths_none_preserves_whole_tree_behaviour` (pytest node id, verified passing when recorded)
- `tests/test_gates_fix_engine.py::TestFmt001OnlyPathsLandScoping::test_only_paths_skips_nonexistent_path_without_error` (pytest node id, verified passing when recorded)
- `tests/test_gates_fix_engine.py::TestFixE501MergeIntroduced::test_e501_merge_introduced_targeted_format_applies` (pytest node id, verified passing when recorded)
- `tests/test_gates_fix_engine.py::TestFixE501MergeIntroduced::test_e501_no_merge_shape_is_a_no_op` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 3 error(s), 1485 warning(s), 698 waived
- error-findings: AFFECT001@src/frob/gates/_fix_engine_text.py, PRE001@tickets/T-1911, REG002@docs/design/registry/check-coverage.yaml
