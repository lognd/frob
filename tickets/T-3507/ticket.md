---
id: T-3507
title: os.sysconf Windows fallback in process-scan CPU tick-rate helper
state: queued
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: T-3505
tier: ticket
sprint: null
runs_last: false
milestone: 1.0.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/process/_proc_scan.py
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
Add a Windows fallback for os.sysconf("SC_CLK_TCK") in the process-scan
CPU-tick-rate helper.

MEASURED: 12 of T-3076's 278 windows-only failures are
AttributeError: module 'os' has no attribute 'sysconf'.

DESIGN: src/frob/process/_proc_scan.py already documents the boundary
(T-3191 comments at lines ~377-409: os.sysconf is POSIX-only, typeshed
gates it off win32) but the actual call at line ~409
(`clk_tck = os.sysconf("SC_CLK_TCK")`) is not yet guarded for a live
Windows run -- it falls back to 100 only on an exception from sysconf
itself, per the existing docstring, but sysconf is not callable at all
on Windows (no attribute), which is a different failure shape (
AttributeError, not a sysconf-internal error) and needs its own guard,
not just a try/except around the call. Guard the call with a
platform check (or hasattr(os, "sysconf")) so Windows takes the
documented 100-tick fallback path directly instead of raising.

FILES IN SCOPE:
  src/frob/process/_proc_scan.py

MUST-FIRE
- On Windows, the CPU-tick-rate helper returns the documented 100
  fallback instead of raising AttributeError.
- The 12 windows-only failures rooted in this AttributeError collapse.

MUST-STAY-QUIET
- POSIX behavior (real os.sysconf("SC_CLK_TCK") read, and its own
  existing except-based 100 fallback on sysconf failure) is unchanged.
- No change to the /proc/uptime read path this helper also uses on
  Linux.

SCOPE GROUPING: scope-disjoint from the fcntl, AF_UNIX, fork-context
and charmap leaves -- dispatchable in parallel with all four.

## Failure log
- 2026-08-30 attempt 1: already resolved on main: _read_uptime_and_clk_tck already guards os.sysconf with sys.platform != win32, Windows takes the 100-tick fallback directly, AttributeError cannot occur. No code change needed.
