---
id: T-2013
title: 'ARCH001: extract fix_sys111_capability_ratchet_sync''s load/compute/write
  body under threshold'
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
T-2001's own new Tier-A handler landed at 114 lines, over the ARCH001
threshold -- filed and fixed in the same pass as discovery. Split the
load-lock/compute-bumps/write half into _apply_capability_ratchet_bumps.

frob:no-behavior-change reason="pure ARCH001 structural split of fix_sys111_capability_ratchet_sync into itself plus a new _apply_capability_ratchet_bumps helper -- the same load/compute/write logic, just split across two function bodies; zero lines of executable logic changed, verified by the same 3 sys111 tests passing identically before and after the split"

## Done report

Pure structural split of fix_sys111_capability_ratchet_sync (114 lines, ARCH001) into itself plus a new _apply_capability_ratchet_bumps helper -- zero behavior change (frob:no-behavior-change), verified by the same 3 sys111 tests passing identically before and after.

### Changed
```
 rapid-debt.jsonl                        |  5 +++++
 src/frob/gates/_fix_engine_sync.py      | 28 ++++++++++++++++++++-------
 tickets/T-2013/ticket.md      | 34 +++++++++++++++++++++++++++++++++
 tickets/T-2014/done-report.md | 23 ++++++++++++++++++++++
 tickets/T-2014/ticket.md      | 29 ++++++++++++++++++++++++++++
 tickets/T-2015/done-report.md | 19 ++++++++++++++++++
 tickets/T-2015/ticket.md      | 30 +++++++++++++++++++++++++++++
 7 files changed, 161 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestFixEngineTierA::test_sys111_bumps_growth_this_lands_diff_caused` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_sys111_leaves_a_pre_existing_breach_untouched` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_sys111_no_design_dir_is_a_no_op` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/gates/_fix_engine_sync.py, COV003@tickets/T-0907, F401@/home/logan/projects/frob/.claude/worktrees/t2001-follow/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t2001-follow/tests/unit/test_tickets_evidence_only_scope.py
