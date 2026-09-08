---
id: T-4321
title: SCOPE002 pre-existing closure debt on check/__init__.py's declared scope
state: queued
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/__init__.py
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
Found while working T-4309 (bugfix in as_text's tool-summary rendering). T-4309's own ticket scope is the entire src/frob/check/__init__.py file (declared at ticket creation, not something T-4309 chose). 'frob check --only gates-fast --ticket T-4309' reports 11 SCOPE002 findings totalling 130+ symbols across many unrelated files (docs/commands/check.md, docs/modules/gates.md, tests/unit/test_check.py, tests/unit/test_check_admission.py, src/frob/check/_native.py, src/frob/check/_python.py, src/frob/check/_ts.py, ...) whose frob:doc/frob:tests/private-helper edges point outside the declared scope -- pre-existing to any change T-4309 made (reproducible against untouched symbols like _admission_budget, run_check_ts). This makes any ticket scoped to the whole check/__init__.py file structurally unable to pass frob check --only gates-fast cleanly without a scope blowout across dozens of files. Separately, these SCOPE002 Violation objects are built with severity=Severity.WARN (per the gate's own docstring: 'a nudge, not a hard block'), but they render under frob check's ## Errors section and count toward total_errors/the FAIL verdict, not ## Warnings -- worth checking whether _diag_severity's WARN mapping is actually being hit for gate:SCOPE specifically. Recommend: either narrow check/__init__.py-scoped tickets going forward to smaller symbol-level scope, or fix the SCOPE002-to-error miscategorization, or both.