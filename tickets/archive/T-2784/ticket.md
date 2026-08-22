---
id: T-2784
title: 'Reformat batch 4/N: 13 files pending ruff-format (T-2359 child)'
state: dropped
kind: feature
origin: human
created: '2026-08-21'
priority: medium
parent: T-2359
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_profile_schema.py
- src/frob/gates/_rule_id_scan.py
- src/frob/gates/_testing_schema.py
- src/frob/gates/_wire.py
- src/frob/lang/__init__.py
- src/frob/lang/_extract.py
- src/frob/lang/_support.py
- src/frob/perf/_harness.py
- src/frob/release/_cli.py
- src/frob/strata/_capacity.py
- src/frob/strata/_design_load.py
- src/frob/strata/_effects.py
- src/frob/strata/_threat.py
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
Batch 4/N of T-2359: apply ruff-format-only reformat to 13 files.
Excludes src/frob/gates/_tickets_gate.py and src/frob/gates/_waive.py
(live T-2557 lease). No semantic changes; format-only diff.

## Drop reason
- 2026-08-21: refiling with narrower scope: T-2557 lease also covers _profile_schema.py, _rule_id_scan.py, _testing_schema.py per coordinator, not just _tickets_gate.py/_waive.py as the ticket file's declared scope currently shows
