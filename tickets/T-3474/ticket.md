---
id: T-3474
title: may-raise resolver treats a list-comprehension leading expression as preceding
  its own trailing if-clause
state: queued
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/_mayraise.py
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
follow-up split off T-2568 (isdigit-guard discharge). src/frob/process/_proc_scan.py::reap_orphaned_forkservers has [int(entry.name) for entry in entries if entry.name.isdigit() and ...] -- the output expr int(entry.name) is TEXTUALLY before the if-clause's isdigit() guard even though it executes AFTER it at runtime per item. T-2568's guard-discharge only accepts a guard branch at or before the call's own line, so it never matches this shape. Needs comprehension-awareness (tag which NormalizedBranch is a comprehension if-clause and which calls are inside the same comprehension's output expr) that the current NormalizedFunction model does not carry. EXHAUST002 finding: src/frob/process/_proc_scan.py:318 (reap_orphaned_forkservers).