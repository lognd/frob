---
id: T-3509
title: Spawn-safe multiprocessing context selection where fork is unavailable
state: dropped
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
- src/frob/process/_reap.py
- src/frob/serve/_socketd.py
scope_breadth_ack: true
scope_breadth_ack_reason: T-3076 names the ValueError shape but not the exact get_context
  call site; scope covers the three forkserver-aware modules until the grep pins it
  down, per the ticket body's own instruction to narrow via scope --add
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Select a spawn-safe multiprocessing start method on platforms where
'fork' is unavailable (Windows has no fork context at all; only
'spawn' works).

MEASURED: 8 of T-3076's 278 windows-only failures are
ValueError: cannot find context for 'fork'.

DESIGN: any `multiprocessing.get_context("fork")` (or equivalent
hardcoded 'fork' start-method selection) must become a platform-aware
choice: 'fork' on POSIX (cheapest, current behavior, unchanged), 'spawn'
on Windows (the only method Windows' multiprocessing implementation
supports). This is a narrower fix than T-2963's daemon-transport epic
-- it is specifically about multiprocessing start-method selection, not
socket transport. Where 'fork'-specific behavior is load-bearing (e.g.
forkserver-helper process-scanning logic in
src/frob/process/_proc_scan.py, src/frob/process/_reap.py which both
already special-case multiprocessing.forkserver cmdlines), a Windows
run either uses the spawn-based equivalent or declares that specific
codepath a loud POSIX-only boundary if no spawn equivalent exists --
never a silent no-op.

FILES IN SCOPE (identify the exact hardcoded 'fork' get_context call
sites and their forkserver-aware neighbors; confirm via
`git grep -n "get_context(" -- src` since T-3076's own log doesn't name
the exact line, only the ValueError shape):
  src/frob/process/_proc_scan.py
  src/frob/process/_reap.py
  src/frob/serve/_socketd.py
  (plus any other module whose get_context("fork") call the grep
  above surfaces -- widen scope with `frob ticket scope --add` and a
  reason if the grep finds call sites outside this list)

MUST-FIRE
- On Windows, any multiprocessing context selection uses 'spawn' (or a
  documented, loud PlatformUnsupported refusal where 'fork'-specific
  semantics have no spawn equivalent) instead of raising ValueError.
- The 8 windows-only ValueError failures collapse.

MUST-STAY-QUIET
- POSIX behavior (fork context, existing forkserver-helper scanning/
  reaping logic) is unchanged -- this is Windows-additive only.

SCOPE GROUPING: scope-disjoint from the fcntl, os.sysconf, AF_UNIX and
charmap leaves -- dispatchable in parallel with all four. NOTE: shares
src/frob/serve/_socketd.py with the AF_UNIX leaf -- coordinate via
frob ticket contention / sequential land if both leaves touch the same
lines, but the changes themselves are logically independent (transport
guard vs. multiprocessing context) so parallel implementation is fine;
only the LAND needs to serialize if there's a literal line conflict.

## Failure log
- 2026-08-30 attempt 1: no hardcoded get_context("fork") exists in scope (src/frob/process/_proc_scan.py, _reap.py, src/frob/serve/_socketd.py) -- grep confirms zero context-selection calls there; gates/__init__.py (out of scope) already picks forkserver/spawn correctly. All literal get_context("fork") sites are in test files (tests/test_ticket_land.py, tests/unit/test_land_finish_guard.py, tests/unit/test_land_lock_liveness.py) outside T-3509 scope, and test_ticket_land.py plus src/frob/serve/_socketd.py are already claimed by T-3506's scope -- widening into those test files here would collide with the other agent's ticket. No safe in-scope fix exists; deferring to T-3506 or a follow-up ticket for the fork-hardcoded test harnesses.

## Drop reason
- 2026-08-30: No in-scope fix exists: no production get_context(fork) site in the scoped files; the only context selection (gates/__init__.py) is already forkserver/spawn-aware, and the literal test-file sites belong to T-3506's scope (series Z measurement, 2026-08-31).
