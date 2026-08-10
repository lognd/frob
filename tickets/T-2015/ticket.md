---
id: T-2015
title: 'ARCH001: fix_sys111_capability_ratchet_sync (_fix_engine_sync.py) exceeds
  the 60-line function threshold'
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
T-2001's own new Tier-A handler landed at 114 lines, over the ARCH001 threshold -- filed and fixed in the same pass as discovery. Split the load-lock/compute-bumps/write half into _apply_capability_ratchet_bumps, zero behavior change.