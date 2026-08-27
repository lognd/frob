---
id: T-3036
title: bug_repro loses TIMEOUT-vs-NO_VERDICT distinction after T-3015
state: dropped
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
- src/frob/gates/_bug_repro.py
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
Found while auditing T-3015's callers: `frob.gates._bug_repro._spawn_designated_test`
wraps `guarded_subprocess_run(...)` in `except subprocess.TimeoutExpired:` and
returns `Err(_BugReproOutcome.TIMEOUT)` -- a distinct outcome from `NO_VERDICT`,
by explicit design (see its own docstring: "Catching the timeout HERE ... is
what makes TIMEOUT a real distinct outcome instead of another shade of
NO_VERDICT").

Now that T-3015 makes `guarded_subprocess_run` return
`Err(ProcessGuardError.Timeout)` instead of raising, this function's
`except subprocess.TimeoutExpired:` branch is dead code -- a real timeout
now falls into the `if guarded.is_err:` branch below, which only special-cases
`ProcessGuardError.ExecDisabled` and treats everything else (including the
new `Timeout` member) as generic `NO_VERDICT`. This silently collapses the
TIMEOUT outcome T-2480 built this split specifically to preserve.

FIX: replace the `except subprocess.TimeoutExpired:` block with a check on
`guarded.danger_err is ProcessGuardError.Timeout` inside the existing
`if guarded.is_err:` branch, returning `Err(_BugReproOutcome.TIMEOUT)` for
that case and `Err(_BugReproOutcome.NO_VERDICT)` otherwise (unchanged).

ACCEPTANCE
- A regression test: `guarded_subprocess_run` monkeypatched to return
  `Err(ProcessGuardError.Timeout)` -> `_spawn_designated_test` returns
  `Err(_BugReproOutcome.TIMEOUT)`, not `NO_VERDICT`.
- Existing ExecDisabled-refusal test still passes unchanged.

## Drop reason
- 2026-08-26: fixed in-place inside T-3015 (the same regression the widened scope caught via an existing test) (absorbed by T-3015)
