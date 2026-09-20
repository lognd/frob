---
id: T-4561
title: 'post-land sweep residue from T-4517: COV002 in src/frob/lang/_support.py and
  src/frob/testing/_collect_csharp.py (new public symbols lack frob:doc/frob:tests
  edges)'
state: queued
kind: bug
origin: agent
created: '2026-09-17'
priority: medium
parent: T-4513
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/_support.py
- src/frob/testing/_collect_csharp.py
- docs/modules/testing.md
- tests/unit/test_collect_csharp.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: v0.533.0
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
acceptance:
- text: GIVEN the T-4517 symbols in _support.py and _collect_csharp.py WHEN frob check
    runs THEN COV002 reports 0 findings for both files
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Raised by the post-land sweep of bcd55a738 (T-4517). Quarantine findings COV002:src/frob/lang/_support.py and COV002:src/frob/testing/_collect_csharp.py are filed onto this ticket. frob:waive BUG002 reason="sweep residue: the defect is a missing coverage edge, not runtime behaviour; no repro test can fail at parent"