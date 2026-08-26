---
id: T-2952
title: 'Windows still cannot import frob: bare unconditional ''import fcntl'' in _new_renumber.py/_socketd.py/_coverage_wait.py'
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_new_renumber.py
- src/frob/serve/_socketd.py
- src/frob/testing/_coverage_wait.py
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
MEASURED via a real windows-latest CI run (re-triggered after T-2936
landed, run 32937296490, job 98080981096), verifying whether frob now
imports on Windows: it still does NOT. T-2936 fixed the SIGKILL
default-arg crash; a DIFFERENT, unguarded import crashes immediately
afterward, in the same import chain:

  File "src/frob/tickets/_new_renumber.py", line 31, in <module>
    import fcntl
  ModuleNotFoundError: No module named 'fcntl'

This is a BARE, unconditional `import fcntl` at module level -- not
even the guarded `try: import fcntl / except ImportError: fcntl = None`
idiom every other fcntl call site in this repo uses. There is no
platform check at all; the module cannot be imported on any non-POSIX
interpreter, period.

Repo-wide sweep (measured during T-2917/T-2936, re-confirmed here):
three files carry a BARE unconditional `import fcntl` with no guard:

  src/frob/tickets/_new_renumber.py:31
  src/frob/serve/_socketd.py:53
  src/frob/testing/_coverage_wait.py:45

`_new_renumber.py` is the one currently reachable from `frob --help`'s
own import chain (via `frob.tickets.__init__` -> `_draft_finalize` ->
`_new_renumber`), so it is the one blocking THIS measurement, but all
three are the same defect: guard with the standard
`try: import fcntl / except ImportError: fcntl = None` idiom already
used by ~10 other files in this repo, and give the guarded call sites a
loud refusal or real behavior on platforms without it (not a NEW silent
warn-and-continue -- match whatever this repo's now-established T-2918
posture is for each).

Acceptance: a REAL windows-latest CI run (this repo's own T-2917 matrix)
gets past `uv run frob natives build`'s import step. Re-verify with a
real CI run, not a local assertion -- this exact class of claim
(“the import is fixed”) was measured wrong once already in this same
series (T-2936's own fix was real but incomplete; watching the next
crash instead of asserting success is what caught it).
