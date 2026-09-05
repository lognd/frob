---
id: T-3912
title: DEPR003 fires as error severity in frob check --json despite being documented
  as WARN while in its sunset window
state: in-progress
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_debt_deprecated.py
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
T-3906 added this repo's first LIVE frob:deprecated directive (src/frob/app/fmt_runner.py::run, sunset 2026-12-01, well in the future). _depr003_violations builds its Violation with severity=Severity.WARN (see the function's own docstring: 'a WARNING, kept visible ... rather than silent until the sunset date arrives'), yet frob check --json reports it with severity: "error" (measured directly in the raw JSON diagnostic, not through a summary script). Either _depr003_violations's WARN severity is being overridden somewhere between gate evaluation and JSON serialization, or a different code path (DEPR004's expired-severity branch?) is firing despite the sunset date not having passed. MUST-FIRE: a fresh frob:deprecated directive with sunset in the future reports severity warn in frob check --json's raw diagnostic. MUST-STAY-QUIET: an expired one (DEPR004) still reports severity error.