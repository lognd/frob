---
id: T-3039
title: mutate scores timeout as run-abort not killed-mutant after T-3015
state: done
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
- src/frob/mutate/__init__.py
evidence_scope:
- tests/test_mutate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_mutate.py::test_run_mutants_scores_a_timeout_as_killed_and_continues
- tests/test_mutate.py::test_run_mutations_kill_switch_refuses_without_spawning
designated_repro_test: tests/test_mutate.py::test_run_mutants_scores_a_timeout_as_killed_and_continues
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while auditing T-3015's callers: `frob.mutate.__init__`'s mutant-test
spawn wraps `guarded_subprocess_run(...)` in `except subprocess.TimeoutExpired:`
and treats a timeout as "this mutant was KILLED" (`killed += 1; continue`) --
a hung test process is legitimate mutation-kill evidence. The `if guarded.is_err:`
branch immediately below is a DIFFERENT, more severe outcome: it aborts the
entire mutation run (`return Err(MutateError.ExecDisabled)`).

Now that T-3015 makes `guarded_subprocess_run` return
`Err(ProcessGuardError.Timeout)` instead of raising, this `except
subprocess.TimeoutExpired:` branch is dead code -- a real timeout now falls
into `if guarded.is_err:` and ABORTS THE WHOLE MUTATION RUN instead of
scoring one mutant as killed and continuing. This is a real functional
regression once T-3015 lands, not just a stale comment.

FIX: inside the existing `if guarded.is_err:` branch, check
`guarded.danger_err is ProcessGuardError.Timeout` first (score as killed,
continue) before falling through to the `ExecDisabled`-abort path.

ACCEPTANCE
- A regression test: `guarded_subprocess_run` monkeypatched to return
  `Err(ProcessGuardError.Timeout)` for one mutant -> that mutant is scored
  killed and the run continues to the next mutant (not aborted).
- Existing ExecDisabled-abort test still passes unchanged.