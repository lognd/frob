---
id: T-1547
title: 'Tier-A auto-fix: E501 introduced by merge, targeted ruff-format'
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine.py
- tests/test_gates_fix_engine.py
- docs/modules/gates_e501_autofix.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates_fix_engine.py
  reason: E501 Tier-A handler needs its own test in the fix-engine-dedicated test
    module
  actor: logan
  at: '2026-08-05'
- op: add
  glob: docs/modules/gates_e501_autofix.md
  reason: new dedicated doc page for the E501 Tier-A handler (docs/modules/gates.md
    itself is under an in-progress T-1205 lease -- see Done report)
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/test_gates.py
  reason: T-1547 enrolled E501 in TIER_A_HANDLERS; the handler-set assertion in tests/test_gates.py
    must list it (plus SYS100/SYS104/COV002 enrolled by sibling tickets in this series)
    -- blocked until T-1205's tests/** lease cleared on the merged ledger
  actor: logan
  at: '2026-08-05'
evidence:
- tests/test_gates_fix_engine.py::TestFixE501MergeIntroduced::test_e501_merge_introduced_targeted_format_applies
- tests/test_gates_fix_engine.py::TestFixE501MergeIntroduced::test_e501_no_merge_shape_is_a_no_op
designated_repro_test: null
threat: null
component: null
---
Follow-up from T-1531: an E501 finding introduced specifically by a land-time merge should get a targeted ruff-format pass over just the offending lines/files, distinct from fix_fmt001_directive_wrap (which is scoped to frob:-directive comment lines only). Needs a handler reusing the same touched-path plumbing _fmt_pre_land_step already has, re-verifying E501 is gone before counting it as a fix.