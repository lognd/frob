## Done report

Added `frob.arch._shared_state_race` (T-0697, child 4 of the T-0693
concurrency-hazard umbrella): a structural, interprocedural scan flagging
`unguarded-shared-write` -- a write (rebind assignment, subscript
assignment, or a curated mutating-method call) to module-level or
class-level mutable state (list/dict/set constructions), on a call path
reachable from a thread-target/executor-submission/async-task dispatch
point, with no lock acquisition lexically enclosing the write.

Model: reuses `frob.arch._lock_ordering`'s exact module/class-level
identity convention (`_collect_module_locks`'s structure, re-keyed on
mutable-literal construction instead of lock construction) and its
`_resolve_lock_expr`/`_LOCK_NAME_HINT_RE` resolution machinery (imported
directly, not re-implemented) for both shared-state identity and for
deciding whether a write is lock-enclosed. Reuses
`frob.arch._concurrency`'s `_first_arg_names`/`_target_kwarg_names`
dispatch-corpus helpers (imported directly) for the thread/executor-submit
half of dispatch-entrypoint detection, and adds the async-task half
(`asyncio.create_task`/`ensure_future`/`<loop>.create_task`) this ticket's
own text calls for, which `_concurrency._dispatched_callee_names` did not
cover. Interprocedural reachability is a same-module call-graph BFS
closure from every directly-dispatched function (mirrors the bare-name
same-module resolution convention `_lock_ordering`/`_mayraise`/
`_fallibility` all share) -- a write inside any function transitively
CALLED by a dispatched function is reported too, not just the dispatched
function's own body. Lock enclosure is checked lexically within the
writing function's own ancestor chain only (a documented model limit: a
lock acquired by a caller before dispatching into the writing callee is
not modeled).

Changed:
- src/frob/arch/_shared_state_race.py (new): `_collect_shared_state`,
  `_dispatch_entrypoints`, `_async_task_arg_names`,
  `_reachable_from_dispatch`, `_writes_in_function`,
  `_enclosing_lock_with`, `_collect_function_scans`,
  `_check_shared_state_race_hazards`.
- src/frob/arch/_models.py::ArchCategory: added `unguarded-shared-write`.
- src/frob/arch/__init__.py::_run_python_checks: wired
  `_shared_state_race._check_shared_state_race_hazards` alongside the
  sibling concurrency-hazard families (skips test files, same reason as
  T-0694/T-0695/T-0696).
- tests/unit/test_arch.py: new `TestSharedStateRaceHazards` (5 tests).

Evidence: the 5 node ids recorded above; `pytest tests/unit/test_arch.py
-k TestSharedStateRaceHazards` -> 5 passed individually, and the full
`tests/unit/test_arch.py` suite (254 tests) passes unchanged. `frob test
--base main` (touched-set) -> `[PASS] python exit=0`, 7 outcomes recorded.

Real-world validation over frob's own `src/frob/` (non-test files):
1 `unguarded-shared-write` finding -- `serve/_daemon.py::_worktree_branches`
writing the module-level `_ttl_skip_logged` set with no enclosing lock, on
a path reachable from that module's own thread dispatch. This is a
plausible real finding (not an obviously-false positive), consistent with
this check's advisory/approximation posture -- not fixed here (out of this
ticket's own scope, which is the detector itself, not fixing everything it
finds).

Gates: `frob check --ticket T-0697` clean across lint, gates-native (one
PERF003 false positive waived with a reasoned justification -- an
ancestor-chain walk bounded by AST nesting depth over each with-statement's
own small item list, not a cross join), gates-fast (one INV006 false
positive on this module's design-rationale prose, waived per the same
first-turn-on-pool disposition `_lock_ordering`'s own module docstring
already carries; one stale PRE001 fixed via `frob ticket sweep T-0697`
re-run after the file was added), gates-security (0 errors -- no
SELFAUDIT001 false positive this time, since this module's curated tables
are for mutating-method names and dispatch-call names, not
net/exec-capability substrings), and static (0 errors, pre-existing
frob-exports/frob-dup/frob-arch warnings unrelated to this ticket's
files). `ruff check`/`ruff format`/`ty check` on the new file are clean.

Filed: none.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_arch.py::TestSharedStateRaceHazards::test_unguarded_write_from_thread_submitted_function_fires` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSharedStateRaceHazards::test_same_write_under_with_lock_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSharedStateRaceHazards::test_write_reachable_via_callee_of_dispatched_function_fires` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSharedStateRaceHazards::test_write_not_reachable_from_any_dispatch_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSharedStateRaceHazards::test_async_create_task_dispatch_fires_same_as_thread_submit` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 4543 warning(s), 334 waived
- error-findings: none (measured, zero errors)
