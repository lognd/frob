---
id: T-3015
title: guarded_subprocess_run raises subprocess.TimeoutExpired uncaught instead of
  returning Err
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/process/_guard.py
- src/frob/gates/_bug_repro.py
evidence_scope:
- tests/unit/test_process_guard.py
- tests/test_gates_mutation_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_bug_repro.py
  reason: 'T-3015''s guarded_subprocess_run fix (Err(Timeout) instead of raising)

    broke an EXISTING passing test:

    tests/test_gates_mutation_evidence.py::TestBugReproTimeout::test_slow_test_exceeding_budget_is_timeout_not_no_verdict

    -- _spawn_designated_test''s except subprocess.TimeoutExpired: branch

    became dead code, so a real timeout now falls into the generic is_err

    branch and returns NO_VERDICT instead of TIMEOUT. Fixing the caller to

    check guarded.danger_err is ProcessGuardError.Timeout is required to

    satisfy T-3015''s own acceptance criterion ("every existing caller

    continues to work"), discovered via T-2992''s full-suite run.

    '
  actor: logan
  at: '2026-08-26'
triage_changes:
- field: priority
  old_value: medium
  new_value: high
  reason: guarded_subprocess_run is the central subprocess seam every caller now routes
    through after T-2953; a seam that raises TimeoutExpired where callers expect a
    Result surfaces as random uncaught crashes anywhere under load, and it already
    crashed the move-module transaction mid-run
  actor: logan
  at: '2026-08-26'
evidence:
- tests/unit/test_process_guard.py::TestGuardedSubprocessRun::test_timeout_returns_err_never_raises
- tests/unit/test_process_guard.py::TestGuardedSubprocessRun::test_healthy_path_unchanged_when_timeout_kwarg_given
- tests/unit/test_process_guard.py::TestGuardedSubprocessRun::test_disabled_returns_err_without_spawning
- tests/unit/test_process_guard.py::TestGuardedSubprocessRun::test_enabled_spawns_and_returns_ok
- tests/test_gates_mutation_evidence.py::TestBugReproTimeout::test_slow_test_exceeding_budget_is_timeout_not_no_verdict
- tests/test_gates_mutation_evidence.py::TestBugReproTimeout::test_fast_genuinely_failing_test_still_refused
- tests/test_gates_mutation_evidence.py::TestBugReproTimeout::test_fast_genuinely_reproducing_test_completes_normally
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 746e77f2a047e713599b8be17708c9951584cad6
---
`frob.process._guard.guarded_subprocess_run` wraps `subprocess.run(args, **kwargs)`
with no try/except around the call (src/frob/process/_guard.py, line ~116). Any
caller passing a `timeout=` kwarg that actually expires gets an UNCAUGHT
`subprocess.TimeoutExpired` propagating straight out of `guarded_subprocess_run`
as a raised exception, not the `Result[CompletedProcess, ProcessGuardError]` its
own signature promises.

DISCOVERED: `frob refactor move-module frob.yaml_io frob.yamlio` (T-2989, using
the T-2990 verb). The transaction's own Verify phase calls
`frob.refactor._verify.verify_check_delta`, which calls `guarded_subprocess_run`
with `timeout=100` to run `frob check --delta`. In a repo this size, that
subprocess exceeded 100s, raised `subprocess.TimeoutExpired`, and the exception
propagated all the way through `run_move_module` and the CLI dispatcher,
crashing the whole process with an unhandled-exception traceback instead of
returning a failed `VerifyOutcome` -- exactly the outcome the design's
"the transaction always prints a disclosed report, commit or rollback" contract
exists to prevent. The transaction's own WIP commit (already made before Verify
runs) was left in place with no rollback attempt, because the crash happened
before `run_move_module`'s rollback logic could ever execute.

Every other `guarded_subprocess_run` caller that passes `timeout=` (both
`verify_pytest_collect` in the same module, and every `frob.check` tool runner
under `src/frob/gates/`/`src/frob/vet/`, per the module's own docstring) is
exposed to the identical crash-instead-of-Err failure mode whenever the
subprocess genuinely runs long -- this is not unique to the refactor package.

FIX: wrap the `subprocess.run` call in `guarded_subprocess_run` in a
try/except `subprocess.TimeoutExpired` (and probably `OSError` for symmetry
with every other subprocess call site in this repo already doing so) and
return a typed `Err` value instead of letting the exception escape. This needs
a new `ProcessGuardError` member (e.g. `Timeout`) so a caller can distinguish
"the exec kill switch is engaged" from "the process ran too long" -- both are
recoverable conditions a caller should get to handle via `Result`, not a raised
exception.

ACCEPTANCE
- `guarded_subprocess_run(..., timeout=N)` against a command that outlives `N`
  seconds returns `Err(ProcessGuardError.Timeout)` (or similarly named member),
  never raises.
- A regression test constructs a command that outlives a short timeout and
  asserts `Err`, not a raised exception.
- Every existing caller (`verify_check_delta`, `verify_pytest_collect`, and the
  `frob.check` tool runners) continues to work with the new `Err` branch --
  most already have an `if result.is_err: ...` path for `ExecDisabled`, which
  should also cover `Timeout`.