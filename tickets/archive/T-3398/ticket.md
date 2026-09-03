---
id: T-3398
title: Waive tracked LARGE001/PERF004 debt in __main__.py and frob-suggest.py
state: done
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/__main__.py
- .claude/hooks/frob-suggest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_second_file_rewriting_same_module_import_fires
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 53072158bb03f5191be1e3337a0de561be465a79
---
gate:LARGE ER slice follow-up, previously deferred by a live T-3389 (Series EQ) lease which has since landed: LARGE001 in src/frob/__main__.py (tracked real-split follow-up T-3059) and PERF004 in .claude/hooks/frob-suggest.py (sort is not hoistable, files grows per iteration) both resolved via reasoned frob:waive.