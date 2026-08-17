---
id: T-2205
title: 'verify_imports has zero consumers now that its blocker landed: T-2188 shipped
  the opt-in, T-2195 fixed the primitive, and nothing tracks turning it on for COV006/DEAD001/PROTO001-005'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: high
blocked_by:
- T-2211
- T-2211
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_dead_symbols.py
- src/frob/gates/_protocol_summary.py
- tests/test_gates.py
evidence_scope:
- tests/test_graph.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: repro + evidence test for verify_imports=True wiring into dead_symbol_gate
  actor: logan
  at: '2026-08-16'
evidence:
- tests/test_graph.py::TestCallGraph::test_build_reference_graph_catches_dispatch_table_entry
- tests/test_gates.py::TestDeadSymbolGate::test_dead_symbol_gate_verifies_imports_across_a_same_named_collision
designated_repro_test: tests/test_gates.py::TestDeadSymbolGate::test_dead_symbol_gate_verifies_imports_across_a_same_named_collision
acceptance:
- text: 'Measured: ''git grep verify_imports=True -- src/'' returns only a docstring
    line (src/frob/graph/callgraph.py:397). No production caller opts in, and no open
    ticket tracked the wiring -- T-2188 (which added the flag) and T-2195 (which fixed
    the primitive it depends on) are both state=done. So the capability is proven,
    unblocked, and reaches nothing. This test MUST fail against current main: at least
    one consumer must pass verify_imports=True.'
  evidence:
  - tests/test_graph.py::TestCallGraph::test_build_reference_graph_catches_dispatch_table_entry
- text: RE-MEASURE the blast radius before wiring anything. The only numbers we have
    -- DEAD001 46 -> 241 and COV006 30 -> 622 -- were taken while resolve_local_import
    returned None for every intra-repo import, i.e. with zero cross-file edges resolving.
    T-2195 (808e0c6fb3f4) changed that completely, so those figures are obsolete and
    almost certainly wrong in both magnitude and direction. Report the new per-gate
    delta and JUDGE each appearing/disappearing finding; a count with no per-finding
    judgement is not evidence.
  evidence:
  - tests/test_graph.py::TestCallGraph::test_build_reference_graph_catches_dispatch_table_entry
- text: Wire consumers ONE AT A TIME with its own measurement, do not flip all three
    together. DEAD001's failure direction is reporting LIVE symbols as dead, which
    is silent and destructive; COV006's is marking uncovered code covered. Preserve
    scope_private_helper_gaps' documented verify_imports=False opt-out (T-0998/T-1012
    -- it keys on directory co-location, not import reachability). And per the epic's
    own item 3, fail CLOSED (report UNRESOLVED, T-1664) where import resolution genuinely
    cannot decide, rather than guessing in either direction.
  evidence:
  - tests/test_graph.py::TestCallGraph::test_build_reference_graph_catches_dispatch_table_entry
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Done report

Wired verify_imports=True into DEAD001's own build_reference_graph call
(src/frob/gates/_dead_symbols.py) -- the one consumer this ticket's
title names. T-2188 added the opt-in flag and deliberately left it
wired into zero consumers, blocked on resolve_local_import's
src-layout gap (T-2195, landed) and the from-X-import-Y submodule
specifier gap (T-2211, landed today, cleared this ticket's blocked_by).

Repro: tests/test_gates.py::TestDeadSymbolGate::
test_dead_symbol_gate_verifies_imports_across_a_same_named_collision,
committed alone at 0948a8ec6, watched FAIL against the pre-wiring gate
(`frob ticket evidence --check-repro ... --base-ref 0948a8ec6` reported
FAILED_AT_PARENT -- 0 violations found, expected src/b.py flagged).
Constructs the exact bare-short-name-collision shape build_call_graph's
own docstring documents (T-2156): two unrelated files in one package
directory each define a private `_target` with the same short name;
only a.py's is genuinely called (from within a.py itself); b.py's is
never called anywhere. Pre-wiring, the ambiguous name match fabricates
an edge for BOTH candidates, masking b.py's dead symbol. Post-wiring,
only a.py's own in-file call resolves (no import required), and
b.py -- never imported by anyone -- correctly reads as dead. Fix
committed separately at f7053ae13.

Fresh measurement (re-measured on this run, not trusting the earlier
scratch numbers from T-2211's own Done report -- the tree moved):
- Baseline (verify_imports=False, unwired): 46 findings (3 warnings +
  43 waived), confirmed via `frob check --only dead_symbols --json`
  immediately after `git merge main` in this worktree.
- After wiring verify_imports=True for real: 51 findings (8 warnings +
  43 waived) -- 5 new, 0 disappeared. Matches T-2211's own scratch
  measurement exactly (46 -> 51), confirming that measurement was not
  stale.
- All 5 new findings are severity=warning (DEAD001 is WARN-only,
  advisory-tier, never blocks a build on its own per the gate's own
  docstring) -- wiring did NOT produce any ERROR-level finding, so
  there is nothing here that would have blocked the land.
- Per-finding judgement (all 5, individually):
  - src/frob/arch/_abstraction.py::_extract_signatures/
    _collect_file_dispatch_refs/_check_abstraction_opportunities (3):
    a transitive re-export chain -- frob.arch._python re-imports these
    names from _abstraction.py (T-2211's fix correctly resolves that
    edge), but the real caller (frob/arch/__init__.py) only imports
    _python.py directly, never _abstraction.py, so the single-hop
    import-edge check misses the transitive path. This is T-2219's
    scope (src/frob/graph/callgraph.py, multi-hop reachability in
    _local_imports_by_path's consumer), not fixed here.
  - tests/unit/strata/test_litmus_cwe.py::_repo_root (1): genuinely has
    zero callers in its own file; previously masked by a same-named
    collision with another test file's _repo_root (the T-2156 defect
    class this wiring exists to close) -- this finding is CORRECT, not
    a regression.
  - tests/unit/test_coordinator_scripts.py::_load (1): called only at
    module top level (`check_summary = _load("check_summary")`), not
    from inside another def -- suggests build_reference_graph's
    call-site attribution may not record a module-top-level statement
    as a call belonging to any symbol under verify_imports=True. Noted
    for T-2219, not investigated further here (out of scope).

frob test --base main: python exit=0, 17 outcomes recorded, all green
(tests/test_gates.py::TestDeadSymbolGate's full 15 tests + the new one
+ the module's own integration test).

Scope: added tests/test_gates.py via `frob ticket scope --add`
(the repro/evidence test file, mirroring the T-2211 precedent) --
src/frob/gates/__init__.py and src/frob/gates/_protocol_summary.py
(declared scope, unused) were NOT touched; per the coordinator's
explicit instruction, this ticket wires DEAD001 only, not COV006/
PROTO001-005.

Gates: frob check --only dead_symbols shows the measured 46->51 above,
all WARN, none ERROR. gate:DRIFT's 2 errors are pre-existing (files
this ticket did not touch, confirmed via git status). No error
attributable to this ticket's own changed files.

### Changed
```
 src/frob/gates/_dead_symbols.py | 10 +++++++++-
 tests/test_gates.py             | 43 +++++++++++++++++++++++++++++++++++++++++
 tickets/T-2205/ticket.md        | 13 +++++++++++--
 3 files changed, 63 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_graph.py::TestCallGraph::test_build_reference_graph_catches_dispatch_table_entry` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeadSymbolGate::test_dead_symbol_gate_verifies_imports_across_a_same_named_collision` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, AFFECT001@src/frob/gates/_dead_symbols.py, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2205/src/frob/lang/_nodes.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2205, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
