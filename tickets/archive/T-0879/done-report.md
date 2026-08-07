## Done report

Changed:
- `src/frob/mutate/__init__.py::run_mutations` -- holds
  `derived_state_lock(root, exclusive=True)` for its whole run.
- `src/frob/doctor.py::run_diagnosis` -- its fingerprint-read +
  manifest-write span (`verify_derived_state` through
  `_write_drift_manifest`) holds `derived_state_lock(resolved_root,
  exclusive=True)`.
- `tests/test_mutate.py::test_run_mutations_holds_exclusive_lock_blocking_a_shared_reader`
  (new)
- `tests/test_doctor.py::test_run_diagnosis_holds_exclusive_lock_blocking_a_shared_reader`
  (new)
- `docs/modules/mutate.md` -- new "Cross-process exclusive lock (T-0879)"
  section.
- `docs/guides/install.md` -- T-0879 note in the derived-state-manifest
  section.

NOT changed (deliberate scope cut, see below): `src/frob/dup/**`,
`src/frob/graph/**` -- `find_clones`/`build_graph` were NOT wired.

Rationale for the dup/graph cut: `frob.mutate.run_mutations` and
`frob.doctor.run_diagnosis` are safe to wrap unconditionally because
every production call site is genuinely standalone (`frob mutate`;
`frob.tickets._land`/`app/ticket_runner.py`'s mutation-evidence
obligation for `run_mutations`; `frob doctor` for `run_diagnosis`) --
confirmed by grepping every caller in `src/frob/`. `frob.dup.find_clones`
and `frob.graph.build_graph` are NOT: both are called from INSIDE `frob
check`'s own gate execution (`frob.check._python._run_dup`'s dup gate,
and `build_graph` from `check/_python.py`/`gates/_prework.py`) while the
main thread already holds check's own SHARED `derived_state_lock` for
the run's entire duration (`check/__init__.py::_run_check_with_skips`).
Those gate functions run inside a `ThreadPoolExecutor` worker thread --
a DIFFERENT thread than the one holding the shared lock.
`derived_state_lock`'s re-entrancy guard is per-thread
(`frob.process._lock._lock_local`, `threading.local`), and POSIX
`flock(2)` itself grants NO same-process re-entrancy across distinct
open file descriptions (two `os.open` calls on the same path, even in
one process, contend against each other exactly like two processes
would). Wrapping `find_clones`/`build_graph` in `exclusive=True`
unconditionally would therefore deadlock every real `frob check` run
that reaches the dup gate or a cache-miss graph rebuild: the worker
thread blocks waiting for EXCLUSIVE against the main thread's SHARED
hold, which cannot release until that same worker returns. Forcing this
into scope would trade the TOCTOU race T-0879 exists to close for a
guaranteed hang -- strictly worse. Filed T-0918 (see below) as
the prerequisite-bearing follow-up rather than forcing it.

Evidence:
- `tests/test_mutate.py::test_run_mutations_holds_exclusive_lock_blocking_a_shared_reader`
  (recorded via `frob ticket evidence`, verified passing)
- `tests/test_doctor.py::test_run_diagnosis_holds_exclusive_lock_blocking_a_shared_reader`
  (recorded via `frob ticket evidence`, verified passing)
- `pytest tests/test_mutate.py tests/test_doctor.py tests/test_mutate_journal.py
  tests/system/test_cli_doctor.py tests/unit/test_process_lock.py` -- all pass,
  no regressions in the mutate/doctor/lock suites.
- `frob test --base main` -- exit 0, full touched-set selection green.
- `frob check --only lint --ticket T-0879` -- pass.
- `frob check --only gates-fast --ticket T-0879` -- pass (0 errors; AFFECT001/
  SCOPE001 closed via the doc updates + scope extension above).
- `frob check --only gates-native --ticket T-0879` -- pass.
- `frob check --only gates-security --ticket T-0879` -- pass (0 errors).
- `frob check --only static` -- pass.

Filed: T-0918 (bug, "Wire derived_state_lock exclusive side
into dup/graph cache rebuilders (needs process-wide reentrancy signal)")
-- the dup/graph follow-up described above; scope
`src/frob/process/_lock.py`, `src/frob/dup/_pipeline.py`,
`src/frob/graph/__init__.py`.

Gates: `frob check --only {lint,gates-fast,gates-native,gates-security,
static} --ticket T-0879` all clean (chunked per agent-playbook section
3b's FROB_AGENT foreground-cap requirement; a bare full `frob check`
refuses under FROB_AGENT by design).
