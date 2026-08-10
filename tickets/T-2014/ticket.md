---
id: T-2014
title: 'ARCH001: split fix_sys111_capability_ratchet_sync (_fix_engine_sync.py) under
  the 60-line threshold'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fix_engine_sync.py
evidence_scope:
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestFixEngineTierA::test_sys111_bumps_growth_this_lands_diff_caused
- tests/test_gates.py::TestFixEngineTierA::test_sys111_leaves_a_pre_existing_breach_untouched
- tests/test_gates.py::TestFixEngineTierA::test_sys111_no_design_dir_is_a_no_op
designated_repro_test: tests/test_gates.py::TestFixEngineTierA::test_sys111_bumps_growth_this_lands_diff_caused
threat: null
component: null
anchor: false
anchor_reason: null
---
## Done report

Pure structural split of fix_sys111_capability_ratchet_sync (114 lines, ARCH001) into itself plus a new _apply_capability_ratchet_bumps helper (load-lock/compute-bumps/write half) -- zero behavior change (frob:no-behavior-change in ticket body), verified by the same 3 sys111 tests passing identically before and after.

### Changed
```
 rapid-debt.jsonl                        |  1 +
 src/frob/gates/_fix_engine_sync.py      | 28 +++++++++++++++++++++-------
 tickets/T-2014/ticket.md      | 29 +++++++++++++++++++++++++++++
 tickets/T-2015/done-report.md | 19 +++++++++++++++++++
 tickets/T-2015/ticket.md      | 30 ++++++++++++++++++++++++++++++
 5 files changed, 100 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestFixEngineTierA::test_sys111_bumps_growth_this_lands_diff_caused` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_sys111_leaves_a_pre_existing_breach_untouched` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_sys111_no_design_dir_is_a_no_op` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/gates/_fix_engine_sync.py, F401@/home/logan/projects/frob/.claude/worktrees/t2001-follow/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t2001-follow/tests/unit/test_tickets_evidence_only_scope.py
