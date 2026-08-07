## Done report

Added `frob.arch._concurrency_model` (T-0698, child 5 of the T-0693
concurrency-hazard umbrella): classifies each python function as IO-BOUND
(a curated IO call in its own scope, no loop), CPU-BOUND (a loop, no
curated IO call), or MIXED/UNKNOWN (both or neither -- never advisory-
eligible, matching T-0332's noise-discipline precedent), then flags a
mismatch between that classification and the function's dispatched
executor: `gil-bound-in-threadpool` (a CPU-bound function submitted to a
`ThreadPoolExecutor`) and `ipc-overhead-in-processpool` (a trivially small
IO-bound function submitted to a `ProcessPoolExecutor`).

Reuse: the curated IO-call table is built on top of
`frob.arch._async_hazards`'s existing `_BLOCKING_CALL_TABLE`/
`_OPEN_BUILTIN_RE` (imported directly, not re-curated) plus a small
socket/db addition this ticket's own "sockets/... db" wording needs and
that table did not cover. Dispatch-target name extraction reuses
`frob.arch._concurrency._first_arg_names`. `async-zero-awaits` (one of
the four advisory shapes this ticket's own text names) already exists as
its own category from T-0696 -- not re-implemented here (T-0696's module
docstring already cross-references it as feeding this ticket).

Changed:
- src/frob/arch/_concurrency_model.py (new): `_classify_function`,
  `_executor_bindings`, `_bound_ctor_name`, `_dispatch_kinds_for_name`,
  `_is_io_call`, `_check_concurrency_model_mismatch`.
- src/frob/arch/_models.py::ArchCategory: added `gil-bound-in-threadpool`,
  `ipc-overhead-in-processpool`.
- src/frob/arch/__init__.py::_run_python_checks: wired
  `_concurrency_model._check_concurrency_model_mismatch` alongside the
  sibling concurrency-hazard families (skips test files, same reason as
  T-0694/T-0695/T-0696/T-0697).
- tests/unit/test_arch.py: new `TestConcurrencyModelMismatch` (4 tests).

Evidence: `pytest tests/unit/test_arch.py -k TestConcurrencyModelMismatch`
-> 4 passed individually, and the full `tests/unit/test_arch.py` suite
(258 tests) passes unchanged. `frob test --base main` (touched-set) ->
`[PASS] python exit=0`, 6 outcomes recorded.

Real-world validation over frob's own `src/frob/` (non-test files): 0
`gil-bound-in-threadpool`/`ipc-overhead-in-processpool` findings (no
ThreadPoolExecutor/ProcessPoolExecutor model mismatch in this repo's own
code today) -- 0 false positives on a real, large codebase.

Disclosed cut: this ticket's own text names a fourth advisory shape
("sequential awaits over independent IO -> suggest gather") not built
here -- proving two `await` expressions are data-independent needs a
def-use analysis `frob.arch`'s current normalized model does not provide,
and an unsound textual-adjacency approximation would risk false positives
against this repo's own noise-discipline convention (T-0332). Filed as
T-1027 (a duplicate accidental filing, T-1026, was
dropped/absorbed into it).

Gates: `frob check --ticket T-0698` clean across lint, gates-native,
gates-fast, gates-security, and static (0 errors in every stage; the one
ruff-format warning seen is pre-existing unrelated debt in
`src/frob/gates/_docptr.py`). `ruff check`/`ruff format`/`ty check` on the
new file are clean.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_cpu_bound_loop_in_threadpool_fires_gil_bound` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_io_bound_socket_read_in_threadpool_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_trivial_io_task_in_processpool_fires_ipc_overhead` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_mixed_loop_and_io_function_never_fires_either_advisory` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 4413 warning(s), 334 waived
- error-findings: none (measured, zero errors)
