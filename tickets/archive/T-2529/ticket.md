---
id: T-2529
title: fix F811 redefinition cluster in test_app_runners_json_guard_t2492.py
state: dropped
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_app_runners_json_guard_t2492.py
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
6 F811 errors on main right now: ruff flags tests.unit.test_app_runners_batch6._real_console_handlers (imported cross-module per DUP001, reusing T-2486's fixture rather than duplicating it) as "redefined" each time it appears as a pytest fixture parameter name in a different test method (lines 47/86/127/177/223/270).

Investigated: these are NOT six differing fixture definitions -- it is ONE cross-module import used as a parameter name in six different test functions, which is the correct, intended way pytest resolves a fixture by name. Ruff's F811 does not understand pytest fixture-injection semantics for a cross-module-imported fixture reused as a parameter name (it only suppresses F811 for same-file fixture defs shadowed via parameter, not for an imported name reused the same way). This is a lint false positive, not a functional bug: all six tests correctly receive the SAME real fixture, none run against a wrong one.

Fix: silence the false positive (per-usage # noqa: F811 on each parameter line, matching the existing # noqa: F401 already on the import line) -- do not change test behavior, since nothing is functionally wrong.

## Drop reason
- 2026-08-18: duplicate of already-filed T-2526 (post-land sweep regression from T-2503), which covers the identical F811 finding in this exact file plus 4 others
