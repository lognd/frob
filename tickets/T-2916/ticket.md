---
id: T-2916
title: 'frob is Linux-only in practice and degrades SILENTLY on Windows/macOS: locks
  no-op, orphan reaping disabled, CI cannot detect it'
state: dropped
kind: bug
origin: human
created: '2026-08-25'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: decision-record ticket being dropped as stale premise; no
  code fix
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Failure log
- 2026-08-28 attempt 1: stale premise: PLATFORM001 gate (T-2919/2934/2944/2951) already makes locks refuse loudly (msvcrt Windows backend + DerivedStateLockUnavailable) and orphan-reaping disable announces itself via _log.warning (T-2944, process/_reap.py:arm_parent_death_signal); gate:WALK is clean of PLATFORM001 findings on current main and runs inside CI's frob check (ci.yml self-gate), closing the silent-degrade detection gap this ticket describes. Remaining cross-platform work is already covered by in-flight T-3191 (multi-platform typecheck) and T-3192 (CI hang timeout).

## Drop reason
- 2026-08-28: 2026-08-28 stale premise confirmed by this session: PLATFORM001 gate (T-2919/2934/2944/2951) already makes locks refuse loudly on non-Linux (msvcrt Windows backend + DerivedStateLockUnavailable) and orphan-reaping disable announces itself via _log.warning (T-2944, process/_reap.py:arm_parent_death_signal). Verified: uv run ty check --python-platform linux,win32,darwin src all exit 0 on current main; gate:WALK runs inside CI's frob check (ci.yml self-gate) and is clean of PLATFORM001 findings, closing the silent-degrade detection gap this ticket describes. Remaining cross-platform work already covered by T-3191 (multi-platform typecheck) and T-3192 (CI hang timeout). This re-confirms the ticket's own attempt-1 failure-log finding; falsified premise -> drop, not fail.
