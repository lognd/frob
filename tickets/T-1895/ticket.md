---
id: T-1895
title: Extract shared .strata node-body brace-depth scanner (SYS-IFACE-ORDER/_sync_may
  duplicate)
state: queued
kind: bug
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fix_engine_sync.py
- src/frob/strata/_sync_may.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1872's fix_sys_interface_canonical_order needed its own _iface_node_body_span, a byte-identical brace-depth node-body scanner to _sync_may.py::_node_body_span (both independently mirror the deleted _sync_interface.py's own copy). DUP001 waived in T-1872 rather than fixed, since extracting a shared helper module both files import from is a real refactor outside that order-only ticket's declared scope. Extract the shared scanner into one home (e.g. frob.strata._strata_text or similar) and have both call sites use it.