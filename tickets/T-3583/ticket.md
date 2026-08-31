---
id: T-3583
title: DOC006 at docs/design/macos-portability.md:83 -- path pointer does not resolve
state: in-progress
kind: bug
origin: agent
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/design/macos-portability.md
- tests/test_docptr_gate.py
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
Run 33385515507. DOC006: file/path pointer in docs/design/macos-portability.md:83 does not resolve -- 'src/frob/tickets/_land_finish_guard.py' is not a tracked file (from T-3528's doc edit). Reword/backtick per the established idiom so it stops looking like a live tracked-file pointer, or fix the reference if the file moved/renamed.