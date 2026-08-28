---
id: T-3240
title: Remove stale WIRE001 follow_up=T-2931 waiver on _remove_scratch_file now that
  atexit.register is recognized
state: dropped
kind: docs
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_unlanded.py
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
T-2931 landed the atexit.register dynamic-dispatch exemption for WIRE001 -- the frob:waive WIRE001 follow_up="T-2931" directive above _remove_scratch_file in this file is now redundant (the gate no longer fires on this symbol without it). Remove the waiver comment; verify WIRE001 stays silent.

## Drop reason
- 2026-08-28: done directly inside T-2931 -- removed the redundant frob:waive WIRE001 follow_up=T-2931 waiver in the same change that landed the atexit.register exemption, no separate follow-up needed
