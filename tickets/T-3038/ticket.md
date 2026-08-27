---
id: T-3038
title: evidence bind-time cost probe loses timeout floor after T-3015
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_evidence.py
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
Found while auditing T-3015's callers: `frob.tickets._evidence
._warn_bind_time_mutation_sweep_cost` wraps `guarded_subprocess_run(...)` in
`except subprocess.TimeoutExpired:` and returns `_TIMEOUT_S` (a specific
numeric floor: "the real cost is >= this, use it as the measured floor").
The `if guarded.is_err:` branch immediately below returns `None` instead
("no measurement at all").

Now that T-3015 makes `guarded_subprocess_run` return
`Err(ProcessGuardError.Timeout)` instead of raising, this `except
subprocess.TimeoutExpired:` branch is dead code -- a real timeout now falls
into `if guarded.is_err:` and returns `None`, silently discarding the
">= _TIMEOUT_S" floor measurement this function exists to produce.

FIX: inside the existing `if guarded.is_err:` branch, check
`guarded.danger_err is ProcessGuardError.Timeout` first (return
`_TIMEOUT_S`) before the generic `None` fallback.

ACCEPTANCE
- A regression test: `guarded_subprocess_run` monkeypatched to return
  `Err(ProcessGuardError.Timeout)` -> the function returns `_TIMEOUT_S`,
  not `None`.
- Existing OSError/ExecDisabled-returns-None tests still pass unchanged.
