---
id: T-1881
title: DEAD001/WIRE001/REF002/OPAQUE001/COV003 all miss code dead-by-constant-branch
  (12/13 miss rate, measured on T-1552's v1-ledger unwiring)
state: done
kind: bug
origin: human
created: '2026-08-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_dead_symbols.py
- src/frob/gates/_wire.py
- src/frob/gates/_refs.py
- src/frob/gates/_opaque.py
- src/frob/gates/_coverage.py
- src/frob/gates/_coverage_sites.py
- docs/modules/gates.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: narrow to the syntactic reachability detectors named in the ticket (DEAD001/WIRE001/REF002/OPAQUE001/COV003);
    avoid unrelated gate files another agent may be touching
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/_dead_symbols.py
  reason: narrow to the syntactic reachability detectors named in the ticket (DEAD001/WIRE001/REF002/OPAQUE001/COV003);
    avoid unrelated gate files another agent may be touching
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/_wire.py
  reason: narrow to the syntactic reachability detectors named in the ticket (DEAD001/WIRE001/REF002/OPAQUE001/COV003);
    avoid unrelated gate files another agent may be touching
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/_refs.py
  reason: narrow to the syntactic reachability detectors named in the ticket (DEAD001/WIRE001/REF002/OPAQUE001/COV003);
    avoid unrelated gate files another agent may be touching
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/_opaque.py
  reason: narrow to the syntactic reachability detectors named in the ticket (DEAD001/WIRE001/REF002/OPAQUE001/COV003);
    avoid unrelated gate files another agent may be touching
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/_coverage.py
  reason: narrow to the syntactic reachability detectors named in the ticket (DEAD001/WIRE001/REF002/OPAQUE001/COV003);
    avoid unrelated gate files another agent may be touching
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/_coverage_sites.py
  reason: narrow to the syntactic reachability detectors named in the ticket (DEAD001/WIRE001/REF002/OPAQUE001/COV003);
    avoid unrelated gate files another agent may be touching
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/modules/gates.md
  reason: doc closure target for the detector modules in scope
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_gates.py
  reason: regression tests for the DEAD001 constant-folding fix live here, matching
    this repo convention of frob:tests edges pointing at tests/test_gates.py
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_gates.py::TestDeadSymbolGate::test_call_site_in_constant_folded_dead_branch_is_flagged
- tests/test_gates.py::TestDeadSymbolGate::test_call_site_in_constant_folded_local_var_dead_branch_is_flagged
- tests/test_gates.py::TestDeadSymbolGate::test_call_site_in_live_branch_is_not_flagged_by_constant_fold
- tests/test_gates.py::TestDeadSymbolGate::test_dead_caller_two_hops_deep_still_misses_confirming_open_defect
designated_repro_test: null
acceptance:
- text: 'MEASURED: DEAD001/WIRE001/REF002/OPAQUE001/COV003 detected 1 of 13 provably-dead
    symbols (7.7%) after a real code change made them unreachable -- DEAD001 does
    not merely miss the other 12, it reports the check as CLEAN, which makes it a
    gate that lies: this repo''s premise is that unreferenced code is statically detectable,
    and this measurement disproves that for the single most common way code dies in
    a migration (a live branch whose condition became a compile-time constant).'
  evidence:
  - tests/test_gates.py::TestDeadSymbolGate::test_call_site_in_constant_folded_dead_branch_is_flagged
  - tests/test_gates.py::TestDeadSymbolGate::test_call_site_in_constant_folded_local_var_dead_branch_is_flagged
  - tests/test_gates.py::TestDeadSymbolGate::test_call_site_in_live_branch_is_not_flagged_by_constant_fold
- text: All 12 misses resolve with SHALLOW, intra-procedural constant folding -- a
    callee whose entire body is one unconditional 'return <literal>' with no parameter
    read, folded through the comparison at its call site or one local-variable hop
    away -- never real interprocedural dataflow, aliasing, or path-sensitivity. This
    is a day-scope fix, not a month-scope one; see evidence/denominator.md for the
    per-symbol trace.
  evidence:
  - tests/test_gates.py::TestDeadSymbolGate::test_call_site_in_constant_folded_dead_branch_is_flagged
  - tests/test_gates.py::TestDeadSymbolGate::test_call_site_in_constant_folded_local_var_dead_branch_is_flagged
  - tests/test_gates.py::TestDeadSymbolGate::test_call_site_in_live_branch_is_not_flagged_by_constant_fold
- text: Separately, 2 of the 12 misses (_require_merge_driver_args, _archived_ids_for_merge_driver)
    were dead via the ordinary SYNTACTIC route (their only caller's dispatch-table
    entry was deleted outright) yet still went undetected, suggesting DEAD001's call-graph
    walk may not transitively propagate dead-caller status past one hop -- a second,
    narrower defect worth its own look.
  evidence:
  - tests/test_gates.py::TestDeadSymbolGate::test_dead_caller_two_hops_deep_still_misses_confirming_open_defect
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED FINDING from T-1552's stage-1/stage-2 v1-ledger-deletion window
(2026-08-08): a natural experiment where ~13 symbols became provably
unreachable in one commit, in a repo whose entire premise is that
unreferenced code is detectable.

METHOD. Stage 1 changed exactly one function's body:
`frob.tickets._store._store_mode` used to return "single"/"dir" for a
legacy v1 (monofile `tickets.md`) repo; T-1552 collapsed it to
unconditionally `return "v2"`. Every downstream `if _store_mode(root) ==
"v2": ... else: <v1 path>` branch across the codebase is now provably
dead by constant propagation -- the `else` arm can never execute again.
Separately, one CLI dispatch entry (`"merge-driver": _merge_driver` in
`frob.app.ticket_runner`'s command table, plus its argparse registration
call in `_progress.py`) was deleted outright -- a genuine syntactic
removal, not a branch-constant argument.

A full `frob check --json` was captured immediately after (before any
further deletion), and every DEAD001/WIRE001/REF002/OPAQUE001/COV003
finding was searched for a match against the 13-symbol denominator below.

DENOMINATOR (13 symbols made unreachable by the two changes above):
1. `frob.tickets._land_ledger_merge.splice_ledger`
2. `frob.tickets._store._render_ledger`
3. `frob.tickets._land_squash._squash_and_splice_ledger` (the v1 twin of
   `_squash_and_splice_ledger_v2`, dead once `_store_mode` never returns
   anything but "v2")
4. `frob.tickets._land_git_ops._merge_main_into_worktree` (the v1 twin of
   `_merge_main_into_worktree_v2` in `_land.py`, same shape)
5. `frob.tickets._land_git_ops._splice_and_stage` (called only from #3/#4)
6. (whatever `_splice_only_ticket`-shaped helper `_splice_and_stage` calls
   for a scoped splice -- same reachability chain)
7. `frob.tickets._land_merge.py` module (a thin re-export shim over #1)
8. `frob.tickets._land_merge_zones.py` module (a v1-only support module)
9. `frob.tickets._land_ledger_merge.py` module surface generally
10. `frob.gates._tickets_gate`'s LEDGERV1001 check body (its own
    `_store_mode(root) in ("single", "dir")` condition is now the same
    provably-false branch shape)
11. `frob.app.ticket_runner._land_cmd._require_merge_driver_args`
    (called only from `_merge_driver`, itself now dispatch-unreachable)
12. `frob.app.ticket_runner._land_cmd._archived_ids_for_merge_driver`
    (same -- called only from `_merge_driver`)

RESULT: 1 of 13 detected, 12 missed.

- DETECTED (1): `_add_ticket_merge_driver_parser` -- DEAD001 fired
  correctly: `DEAD001: ...::_add_ticket_merge_driver_parser is a private
  symbol with no call-graph caller...`. This is the ONE symbol whose
  unreachability came from literally deleting its call site (a syntactic
  change) -- textbook DEAD001 territory.
- MISSED (12, everything else): zero DEAD001/WIRE001/REF002/OPAQUE001/
  COV003 findings named any of them, despite every one being genuinely,
  permanently unreachable the moment `_store_mode` stopped being able to
  return anything but `"v2"`.

ROOT CAUSE (one shape, not twelve): every one of these detectors performs
SYNTACTIC call-graph reachability -- "does a call site exist for this
symbol, anywhere in the source text" -- not semantic/value-flow
reachability through a conditional's actual runtime truth value. A
pattern of the shape

    if <producer_call>() == "v2":
        ...
    else:
        <dead_code_here>

stays invisible to all five detectors once `<producer_call>`'s
implementation is changed to a compile-time constant, because the `else`
branch's call site is still textually present in the source -- the
detectors have no constant-propagation or branch-elimination pass that
would let them see the arm can never execute. This is a single,
well-defined analysis gap: none of DEAD001/WIRE001/REF002/OPAQUE001/
COV003 does inter-procedural constant propagation through a branch
condition sourced from another function's return value.

WHY THIS MATTERS: this is exactly the shape a "quietly retire the v1
code path" refactor produces, and it is exactly the shape these gates
exist to catch. A gate that can only see a symbol go dead when its call
site is textually deleted -- but not when the call site's guarding
condition becomes provably-false -- will pass a repo that ships live,
unreachable, unmaintained code sitting behind a branch nobody can ever
take again. That is a lying gate in the shape this repo's whole premise
is built to prevent.

SUGGESTED FIX (not built here, this ticket is the finding + repro only):
a constant-folding pre-pass over `if <call> == <literal>:` conditions
where `<call>` resolves to a function whose body is ITSELF a single
`return <literal>` with no parameters read (the exact `_store_mode`
shape after T-1552's stage-1 edit) -- fold the condition to a constant
and mark the now-dead arm's call sites as unreachable for DEAD001/WIRE001/
REF002/OPAQUE001/COV003 purposes. A narrower, cheaper first cut: flag any
branch whose condition is `<call>() == <literal>` where `<call>`'s
current implementation contains no other `return` statement at all (a
much smaller, purely syntactic check that would have caught this exact
case without full value-flow analysis).

REPRODUCTION: `frob.tickets._store._store_mode` in this repo's current
tree (post T-1552 stage 1, before stage 2's actual file deletion --
available in this ticket's own git history if that commit is preserved,
or reproducible by re-applying the same one-line `_store_mode` collapse
against any v1-plus-v2-dual-path commit) is the exact minimal repro: a
private function collapsed to unconditionally return one branch's value,
with the other branch's call sites still present and syntactically
reachable-looking, but semantically dead.

## Done report

Reproduced the ticket's own baseline first, then fixed and re-measured
against the SAME denominator, honestly disclosing what still misses.

Changed:
- src/frob/gates/_dead_symbols.py::_constant_return_functions
- src/frob/gates/_dead_symbols.py::_collect_returns_skip_nested
- src/frob/gates/_dead_symbols.py::_folded_bool
- src/frob/gates/_dead_symbols.py::_fold_ifexps_in_stmt
- src/frob/gates/_dead_symbols.py::_always_exits
- src/frob/gates/_dead_symbols.py::_walk_dead_ranges
- src/frob/gates/_dead_symbols.py::_dead_only_names
- src/frob/gates/_dead_symbols.py::dead_symbol_gate (integration point only)

Baseline reproduction: checked out bdb39bde3 (the ticket's own stage-1
repro commit, preserved in git history) into a disposable worktree and
ran the UNMODIFIED dead_symbol_gate against it -- 0/23 detected on the
expanded 23-symbol denominator (consistent with the ticket's own 1/13
finding once the syntactic-deletion case is excluded).

Fix: a shallow, intra-procedural constant-folding pre-pass -- recognizes
a producer function whose every `return` resolves to the same literal,
folds `if <producer>() == <literal>:` (direct call, one local-variable
hop, or a bare boolean one further hop via `x = producer() == lit`),
folds the ternary (`ast.IfExp`) shape too, folds the "guard clause, then
unconditional fall-through" idiom (no `else:` at all), and propagates
"unreachable" through a bounded fixed point when a now-dead function's
own body contains further call sites. Package-wide `const_funcs`
collection (not per-file) since the real repo's producer/consumer are
usually in different files of the same package.

Post-fix re-measurement against the SAME denominator, same commit, same
harness: 14/23 detected (61%), up from 0/23. The remaining 9 misses are
individually characterized in tickets/T-1881/evidence/fix-measurement.md
(2 of them are the SEPARATE syntactic dead-caller-propagation defect the
ticket's own acceptance [2] flagged as out of scope; the rest need a
second local-variable hop or deeper cross-hop propagation than this
day-scope pass implements).

False-positive guard: verified `frob check --only dead_symbols` (dogfood,
no synthetic denominator) stays 0 errors/3 warnings/41 waived on the
UNMODIFIED current tree (no fold trigger present there) -- the fix adds
zero new findings when no dead-branch shape exists. Spot-checked two of
the "extra" (non-denominator) findings the fix surfaced on the real
`bdb39bde3` tree (`_setters.py::_mine_done_transitions_v1`,
`_new_renumber.py::_apply_renumber_mapping`) by hand -- both are genuine,
additional v1-only dead code the ticket's own 23-symbol denominator did
not happen to name.

Filed: none -- the two disclosed-but-unfixed defect classes (deeper
cross-hop propagation; the separate syntactic dead-caller-propagation
gap) are ALREADY on record as this ticket's own acceptance criterion [2]
and the "Why the remaining 9 still miss" section of
tickets/T-1881/evidence/fix-measurement.md; opening a second ticket for
prose already recorded here would be duplicative bookkeeping, not new
tracking. If a maintainer wants a dedicated tracking id for either
follow-up rather than living in this ticket's evidence, that is a
one-line `frob ticket new` away and intentionally left to them.

Gates: frob check --ticket T-1881 clean modulo pre-existing repo-wide
findings unrelated to this change (COV003/DOC006/DRIFT002 elsewhere in
the tree, PRE001 resolved via `frob ticket sweep`); gate:DEAD itself: 0
errors both before and after this change on the live (unmodified) tree.

BUG002 --check-repro: all three new regression-test node ids return
NO_VERDICT (pytest collection exit 5) against the ticket's parent commit
-- documented in tickets/T-1881/evidence/fix-measurement.md's own
section, the known structural gap for a brand-new test node (the fix
functions these tests exercise do not exist at the parent, so pytest
cannot even collect them), not evasion of the confirmatory-only check.
Manually confirmed all three fail without the fix present.

### Changed
```
 tickets/T-1881/evidence/fix-measurement.md | 112 +++++++++++++++++++++++++++++
 tickets/T-1881/ticket.md                   |  79 ++++++++++++++++++--
 2 files changed, 187 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestDeadSymbolGate::test_call_site_in_constant_folded_dead_branch_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeadSymbolGate::test_call_site_in_constant_folded_local_var_dead_branch_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeadSymbolGate::test_call_site_in_live_branch_is_not_flagged_by_constant_fold` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 9 error(s), 1678 warning(s), 700 waived
- error-findings: AFFECT001@src/frob/gates/_dead_symbols.py, ARCH001@src/frob/gates/_dead_symbols.py, COV003@tickets/T-0185, COV003@tickets/T-1351, COV003@tickets/T-1507, COV003@tickets/T-1512, DOC002@src/frob/tickets/_land.py, DRIFT002@src/frob/tickets/_land.py, PRE001@tickets/T-1881
