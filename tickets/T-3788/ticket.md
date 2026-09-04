---
id: T-3788
title: fix win32 EffectGraph symref path-separator mismatch
state: queued
kind: bug
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/perf/_effect_summaries.py tests/unit/perf/test_effect_summaries.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
win32 CI: 6 tests in tests/unit/perf/test_effect_summaries.py fail. Investigation TBD via winrun traceback. Likely same path-separator symref-mismatch pattern as T-3784/T-3786. Part of win32 CI drain.