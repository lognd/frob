---
id: T-1869
title: Close is_stamp_stale's WIRE001 waiver now that TEST006 is a real caller
state: dropped
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1830 gave frob.gates._coverage.is_stamp_stale a real, callgraph-traceable caller (frob.gates.__init__._test006_stale now calls it directly) -- the WIRE001 waiver on is_stamp_stale (T-1366, follow_up=T-1830) is now stale and should be removed since the finding can no longer fire. Filed as a successor because T-1830's own declared scope was src/frob/gates/__init__.py only, not _coverage.py.

## Drop reason
- 2026-08-08: absorbed into T-1830's own change -- fixed directly (removed the now-stale WIRE001 waiver on is_stamp_stale) rather than as a separate follow-up, since land needed the citing row re-pointed before T-1830 could close
