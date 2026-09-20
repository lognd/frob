---
id: T-0794
title: 'arch: discharge self-join-deadlock advisory on vet/_scan.py::_run_with_timeout
  (same shape as T-0767)'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_scan.py
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _scan.py'
  actor: logan
  at: '2026-09-19'
  old_length: 258
  new_length: 1907
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _scan.py'
  actor: logan
  at: '2026-09-19'
  old_length: 1906
  new_length: 3555
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _scan.py'
  actor: logan
  at: '2026-09-19'
  old_length: 3554
  new_length: 5203
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _scan.py'
  actor: logan
  at: '2026-09-19'
  old_length: 5202
  new_length: 6851
evidence:
- tests/unit/arch_suite/test_concurrency.py::TestForkPoolHazards::test_self_join_deadlock_discharges_on_real_repo_vet_scan
designated_repro_test: null
acceptance:
- text: GIVEN main WHEN frob check runs THEN zero self-join-deadlock warnings on src/frob/vet
    while the timeout behavior is preserved and a regression test locks the discharge
  evidence:
  - tests/unit/arch_suite/test_concurrency.py::TestForkPoolHazards::test_self_join_deadlock_discharges_on_real_repo_vet_scan
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Promotion of T-0767's worktree draft 1910bd1a: the T-0695 self-join-deadlock advisory fires on vet/_scan.py::_run_with_timeout (unwaivable channel). Restructure the join ownership the same way T-0767 discharged _run_combined_jobs. Required for zero-warnings.

T-4718 sweep (condensed from src/frob/vet/_scan.py:477-499, trimmed for
DOCARCH002's 12-line cap): the trimmed block's full original text, kept
verbatim below.

# CORRECTNESS NOTE (review round 1 of T-0794 caught the predecessor issue,
# preserved and updated here): the original shape used a `with
# ThreadPoolExecutor(...)` block, whose `__exit__` calls `shutdown(wait=
# True)` unconditionally, including when the body returns early on a
# timeout -- so a naive `with pool: ... except FutureTimeoutError: return
# ...` blocks the caller for the FULL underlying task duration, not
# `timeout`, defeating the entire point of this function. T-0794 fixed
# that by constructing the pool WITHOUT a `with` and explicitly calling
# `shutdown(wait=False)` on the timeout path. T-3708 found that fix
# incomplete: `shutdown(wait=False)` does not actually free the abandoned
# worker from the interpreter -- `concurrent.futures.thread` keeps a
# process-global registry of every worker thread any `ThreadPoolExecutor`
# has created and its own atexit handler unconditionally joins all of them
# at interpreter shutdown, so a genuinely-still-blocked abandoned worker
# hangs process exit (this was the win32 CI ~120s teardown gap). This
# function now runs `_process_dependency` via
# `frob._daemon_timeout.run_bounded`, a plain `daemon=True` thread that
# `concurrent.futures.thread` never registers -- an abandoned worker keeps
# running in the background for as long as `_process_dependency` takes
# (Python cannot preempt a running thread; same disclosed trade-off as
# `_scan_dependencies`' docstring) but can no longer block interpreter
# shutdown.

T-4718 sweep (condensed from src/frob/vet/_scan.py:477-499, trimmed for
DOCARCH002's 12-line cap): the trimmed block's full original text, kept
verbatim below.

# CORRECTNESS NOTE (review round 1 of T-0794 caught the predecessor issue,
# preserved and updated here): the original shape used a `with
# ThreadPoolExecutor(...)` block, whose `__exit__` calls `shutdown(wait=
# True)` unconditionally, including when the body returns early on a
# timeout -- so a naive `with pool: ... except FutureTimeoutError: return
# ...` blocks the caller for the FULL underlying task duration, not
# `timeout`, defeating the entire point of this function. T-0794 fixed
# that by constructing the pool WITHOUT a `with` and explicitly calling
# `shutdown(wait=False)` on the timeout path. T-3708 found that fix
# incomplete: `shutdown(wait=False)` does not actually free the abandoned
# worker from the interpreter -- `concurrent.futures.thread` keeps a
# process-global registry of every worker thread any `ThreadPoolExecutor`
# has created and its own atexit handler unconditionally joins all of them
# at interpreter shutdown, so a genuinely-still-blocked abandoned worker
# hangs process exit (this was the win32 CI ~120s teardown gap). This
# function now runs `_process_dependency` via
# `frob._daemon_timeout.run_bounded`, a plain `daemon=True` thread that
# `concurrent.futures.thread` never registers -- an abandoned worker keeps
# running in the background for as long as `_process_dependency` takes
# (Python cannot preempt a running thread; same disclosed trade-off as
# `_scan_dependencies`' docstring) but can no longer block interpreter
# shutdown.

T-4718 sweep (condensed from src/frob/vet/_scan.py:477-499, trimmed for
DOCARCH002's 12-line cap): the trimmed block's full original text, kept
verbatim below.

# CORRECTNESS NOTE (review round 1 of T-0794 caught the predecessor issue,
# preserved and updated here): the original shape used a `with
# ThreadPoolExecutor(...)` block, whose `__exit__` calls `shutdown(wait=
# True)` unconditionally, including when the body returns early on a
# timeout -- so a naive `with pool: ... except FutureTimeoutError: return
# ...` blocks the caller for the FULL underlying task duration, not
# `timeout`, defeating the entire point of this function. T-0794 fixed
# that by constructing the pool WITHOUT a `with` and explicitly calling
# `shutdown(wait=False)` on the timeout path. T-3708 found that fix
# incomplete: `shutdown(wait=False)` does not actually free the abandoned
# worker from the interpreter -- `concurrent.futures.thread` keeps a
# process-global registry of every worker thread any `ThreadPoolExecutor`
# has created and its own atexit handler unconditionally joins all of them
# at interpreter shutdown, so a genuinely-still-blocked abandoned worker
# hangs process exit (this was the win32 CI ~120s teardown gap). This
# function now runs `_process_dependency` via
# `frob._daemon_timeout.run_bounded`, a plain `daemon=True` thread that
# `concurrent.futures.thread` never registers -- an abandoned worker keeps
# running in the background for as long as `_process_dependency` takes
# (Python cannot preempt a running thread; same disclosed trade-off as
# `_scan_dependencies`' docstring) but can no longer block interpreter
# shutdown.

T-4718 sweep (condensed from src/frob/vet/_scan.py:477-499, trimmed for
DOCARCH002's 12-line cap): the trimmed block's full original text, kept
verbatim below.

# CORRECTNESS NOTE (review round 1 of T-0794 caught the predecessor issue,
# preserved and updated here): the original shape used a `with
# ThreadPoolExecutor(...)` block, whose `__exit__` calls `shutdown(wait=
# True)` unconditionally, including when the body returns early on a
# timeout -- so a naive `with pool: ... except FutureTimeoutError: return
# ...` blocks the caller for the FULL underlying task duration, not
# `timeout`, defeating the entire point of this function. T-0794 fixed
# that by constructing the pool WITHOUT a `with` and explicitly calling
# `shutdown(wait=False)` on the timeout path. T-3708 found that fix
# incomplete: `shutdown(wait=False)` does not actually free the abandoned
# worker from the interpreter -- `concurrent.futures.thread` keeps a
# process-global registry of every worker thread any `ThreadPoolExecutor`
# has created and its own atexit handler unconditionally joins all of them
# at interpreter shutdown, so a genuinely-still-blocked abandoned worker
# hangs process exit (this was the win32 CI ~120s teardown gap). This
# function now runs `_process_dependency` via
# `frob._daemon_timeout.run_bounded`, a plain `daemon=True` thread that
# `concurrent.futures.thread` never registers -- an abandoned worker keeps
# running in the background for as long as `_process_dependency` takes
# (Python cannot preempt a running thread; same disclosed trade-off as
# `_scan_dependencies`' docstring) but can no longer block interpreter
# shutdown.