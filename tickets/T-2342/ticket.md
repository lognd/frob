---
id: T-2342
title: post-land sweep filer emits absolute-path scope; frob ticket new crashes fleet-wide
  on one corrupt entry
state: queued
kind: bug
origin: human
created: '2026-08-17'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/app/verify_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Two related defects found while working T-2331 (a "post-land sweep
regression" auto-filed ticket):

1. The deferred post-land sweep's ticket-filer (the mechanism behind
   T-1684, whatever writes `scope:` for these auto-filed
   "post-land sweep regression from T-XXXX" tickets) sometimes emits
   ABSOLUTE filesystem paths into `scope:` instead of repo-relative ones,
   e.g. T-2308 was filed with scope
   ['/home/logan/projects/frob/scripts/fleet_status.py',
   '/home/logan/projects/frob/tests/test_ticket_land.py'] instead of
   ['scripts/fleet_status.py', 'tests/test_ticket_land.py']. Confirmed at
   least 3 instances: T-1753, T-1756 (both state=done, harmless now),
   T-2308 (state=queued, live). Find and fix wherever this filer
   constructs scope globs from finding file paths -- it is almost
   certainly using an absolute Path object directly instead of relativizing
   against repo root first.

2. `src/frob/app/ticket_runner/_new.py::_expand_scope_globs_to_paths`
   (reached via `_scope_overlap_warnings`, called on every single `frob
   ticket new` for every OTHER non-terminal ticket's scope) has NO
   defensive handling for a non-relative/absolute glob pattern -- it calls
   `Path.glob()` directly, which raises
   `NotImplementedError: Non-relative patterns are unsupported` for any
   pattern starting with `/`. Because this function walks EVERY
   non-terminal ticket's scope on every `frob ticket new` call, a single
   corrupted ticket (item 1 above) took down `frob ticket new` for the
   ENTIRE fleet -- every agent, not just whoever holds the corrupted
   ticket. This is a severity mismatch: a single bad ledger entry should
   not be able to brick a core CLI verb repo-wide. Add defensive handling
   (skip the malformed pattern with a WARNING, the way `_scope_closure_
   warnings`/`_scope_overlap_warnings`'s own docstring already promises
   "best-effort... yields () silently" for other failure modes) rather
   than letting the exception propagate uncaught.

Reproduction (before this ticket's fix landed): any `frob ticket new`
call crashed with the traceback rooted at
_new.py:1002 _emit_scope_overlap_warnings ->
_new.py:983 _scope_overlap_warnings ->
_new.py:942 _expand_scope_globs_to_paths ->
pathlib.py:949 glob() -> NotImplementedError.

T-2308's own corruption was repaired directly (via
`frob ticket scope T-2308 --remove <abs> --add <rel>`) as part of
unblocking T-2331's own work -- see T-2331's Done report. This ticket is
for the two ROOT causes: the filer that produces absolute paths, and the
missing defensive guard that let one corrupt ticket become a fleet-wide
outage.
