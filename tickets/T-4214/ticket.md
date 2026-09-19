---
id: T-4214
title: 'frob:waive premise-expiry: a waiver whose reason names a branch/tree condition
  must carry a checkable predicate and fail once it no longer holds'
state: done
kind: feature
origin: agent
created: '2026-09-07'
priority: critical
parent: T-4157
tier: ticket
sprint: v0.543.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
- src/frob/graph/dsl.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/graph/dsl.py
  reason: the until= predicate DSL is validated (date-only) at parse time in dsl.py's
    _attrs_verb_error_waive; the WAIVE012 evaluator in _waive.py cannot see a non-date
    until= value at all unless dsl.py's own grammar check is relaxed to accept the
    closed predicate vocabulary too
  actor: logan
  at: '2026-09-19'
- op: add
  glob: docs/modules/gates.md
  reason: WAIVE012's rule-catalog entry and the until= predicate DSL doc anchor live
    here, matching every sibling WAIVE00* rule's frob:doc target
  actor: logan
  at: '2026-09-19'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.543.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-13'
evidence:
- tests/test_waive_gate.py::TestWaive012PremiseExpiry::test_gate_stays_quiet_while_named_file_still_absent
- tests/test_waive_gate.py::TestWaive012PremiseExpiry::test_gate_fires_error_once_named_file_reappears
- tests/test_waive_gate.py::TestWaive012PremiseExpiry::test_ticket_closed_predicate_fires_once_ticket_is_done
- tests/test_waive_gate.py::TestWaive012PremiseExpiry::test_file_absent_predicate_fires_once_file_exists
- tests/test_waive_gate.py::TestWaive012PremiseExpiry::test_symbol_absent_predicate_fires_once_symbol_reappears
designated_repro_test: null
acceptance:
- text: the until= grammar accepts a closed tree-state predicate vocabulary (ticket-closed:T-####,
    file-absent:path, symbol-absent:path::Sym) alongside the existing YYYY-MM-DD date
    form
  evidence:
  - tests/test_waive_gate.py::TestWaive012PremiseExpiry::test_gate_fires_error_once_named_file_reappears
  - tests/test_waive_gate.py::TestWaive012PremiseExpiry::test_ticket_closed_predicate_fires_once_ticket_is_done
  - tests/test_waive_gate.py::TestWaive012PremiseExpiry::test_file_absent_predicate_fires_once_file_exists
  - tests/test_waive_gate.py::TestWaive012PremiseExpiry::test_symbol_absent_predicate_fires_once_symbol_reappears
- text: one evaluator (_until_premise_expired) judges each predicate against real
    tree state (ticket queue, filesystem, graph symbols) and returns whether the named
    condition still holds
  evidence:
  - tests/test_waive_gate.py::TestWaive012PremiseExpiry::test_ticket_closed_predicate_fires_once_ticket_is_done
  - tests/test_waive_gate.py::TestWaive012PremiseExpiry::test_file_absent_predicate_fires_once_file_exists
  - tests/test_waive_gate.py::TestWaive012PremiseExpiry::test_symbol_absent_predicate_fires_once_symbol_reappears
- text: a WAIVE012 gate error fires once a waiver's until= predicate no longer holds,
    and stays silent while it still does
  evidence:
  - tests/test_waive_gate.py::TestWaive012PremiseExpiry::test_gate_stays_quiet_while_named_file_still_absent
  - tests/test_waive_gate.py::TestWaive012PremiseExpiry::test_gate_fires_error_once_named_file_reappears
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THREE INDEPENDENT ARRIVALS OF ONE MECHANISM, consolidated into one leaf rather than three: (1) T-4157/H4-1 -- a frob:waive reasoning 'the file is absent on this branch' kept suppressing OPAQUE001 after a merge made that false, and nothing re-evaluated it. (2) T-4175/P8 -- a WIRE001 waiver reasoning 'not yet wired' was never re-examined once a sibling caller landed elsewhere. (3) T-4135/F-317/L-2 -- SYS101 waived wholesale for a browser node because 'the code is on a branch', which makes a stale grant and a not-yet-landed grant indistinguishable once the branch in question (T-0002) clears. All three are the same shape: a waiver's justification is contingent on tree state, and nothing re-checks the condition. Fix: a waiver whose reason names a branch condition must carry that condition as a checkable predicate (e.g. a file-existence check, a call-graph reachability check) and fail once the predicate no longer holds. Not every waiver needs a predicate -- only those contingent on tree state; working out which reasons are contingent should be answered by reading this repo's own waiver reasons (hundreds of them) rather than theorising. Fixture-testable: YES, using frob's own frob:waive DSL and its own tree-state-contingent waivers as the honest sample.