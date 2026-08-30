---
id: T-3457
title: strata_core Rust extensions never release the GIL, so pytest-timeout's thread
  watchdog cannot preempt a long native call
state: in-progress
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- strata-core/src/lib.rs
- tests/unit/strata/test_strata_core_gil.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_strata_core_gil.py
  reason: new Python must-fire/must-stay-quiet test proving strata_core releases the
    GIL during long calls
  actor: logan
  at: '2026-08-29'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-3449.

MEASURED (in T-3449's worktree, ac5c2ae67 code, natives built via 'frob natives build'):
  - tests/system/test_frob_self_model.py::TestFrobSelfModel::test_fragments_module_fs_read_is_declared_not_selfaudit001
    run with '--timeout=5 --timeout-method=thread' completed NORMALLY (PASS) in 67s,
    with pytest-timeout's watchdog NEVER firing at all -- not delayed, never.
  - A synthetic time.sleep(20)-based test with the SAME '--timeout=3 --timeout-method=thread'
    fires correctly at 3.7s, proving the general pytest-timeout mechanism (Timer thread +
    os._exit) works fine in this venv; the failure is specific to tests that call into
    strata_core.

ROOT CAUSE: pytest-timeout's thread method (src: .venv/lib/python3.11/site-packages/pytest_timeout.py)
schedules a threading.Timer callback that dumps stacks and calls os._exit(1). That callback is
itself Python code and needs the GIL to run. strata-core/src/lib.rs's #[pyfunction]s
(reachable, worst_age, propagated_demand, etc., see also strata-core/src/graph/query.rs)
contain no py.allow_threads(...) anywhere -- grepped 'allow_threads' in strata-core/src: zero
hits. So while the main thread is inside one of these Rust calls, it holds the GIL for the
ENTIRE call and the watchdog Timer thread cannot run, so pytest-timeout cannot preempt it no
matter how long the call takes. This defeats BOTH the per-test @pytest.mark.timeout AND the
pyproject --timeout for any test whose native call runs long (T-3449's CI stall: 19 minutes,
un-preempted).

FIX: wrap the body of each long-running #[pyfunction] in strata-core/src/lib.rs (worst_age,
reachable, propagated_demand at minimum) in Python::with_gil-compatible py.allow_threads(||
{ ... }) so the GIL is released for the duration of the pure-Rust computation, letting
pytest-timeout's watchdog thread (or any other Python thread) run concurrently. Needs a
signature change to accept Python<'_> in each #[pyfunction] (pyo3 auto-injects it as an
extra arg when declared). Add a regression test that artificially inflates edges so the call
takes >1s and asserts (via a background thread incrementing a counter, or threading.Event)
that OTHER PYTHON THREADS actually get scheduled DURING the native call -- proves the GIL is
released, not just that the function eventually returns.

Not fixed in T-3449 because strata-core/src/lib.rs is Rust, outside that ticket's declared
Python-file scope (_selfconform*.py, _claims.py, _facts.py).