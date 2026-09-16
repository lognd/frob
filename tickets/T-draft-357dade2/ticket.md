---
id: T-draft-357dade2
title: 'Post-land residue from the v0.532.0 lands (T-4413/T-4414/T-4415): 8 uncovered-symbol,
  affect and dup findings'
state: queued
kind: bug
origin: agent
created: '2026-09-16'
priority: medium
parent: T-4410
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_models.py
- src/frob/gates/__init__.py
- src/frob/app/check_runner.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/check/__init__.py
- src/frob/check/_python.py
- tests/unit/test_ci_self_gate_unscoped.py
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN frob check --only gates on dev WHEN run THEN AFFECT001/COV001/COV002/DUP001/DRIFT002
    report zero errors for the eight files this ticket owns
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Quarantine raised by the post-land sweep on batch (d6cfcaf99, a5be90df4, aa3cb6304) 2026-09-16: AFFECT001 src/frob/gates/_models.py; COV001 src/frob/gates/__init__.py; COV002 on src/frob/app/check_runner.py, src/frob/app/ticket_runner/_rapid_sweep.py, src/frob/check/__init__.py, src/frob/check/_python.py, src/frob/gates/__init__.py; DUP001 tests/unit/test_ci_self_gate_unscoped.py; DRIFT002 docs/modules/tickets-landing.md. The landing tickets were closed by the land before the sweep read the tree, so the changed symbols have no open scope owner. Fix: bind frob:doc / frob:tests / frob:waive edges and re-ack the drifted doc anchor; no behaviour change.