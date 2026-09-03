---
id: T-3707
title: 'win32 round 23: explicit executor shutdown for check pipeline post-submit
  120s gap'
state: in-progress
kind: bug
origin: human
created: '2026-09-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/**
- src/frob/process/**
- tests/conftest.py
- .github/workflows/ci.yml
- src/frob/gates/__init__.py
- tests/gates_suite/test_run.py
- tests/unit/test_check_admission.py
- tests/unit/test_conftest_midrun_watchdog.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: narrow to the process-pool shutdown site and its existing test module
  actor: logan
  at: '2026-09-02'
- op: add
  glob: src/frob/gates/__init__.py
  reason: narrow to the process-pool shutdown site and its existing test module
  actor: logan
  at: '2026-09-02'
- op: add
  glob: tests/gates_suite/test_run.py
  reason: narrow to the process-pool shutdown site and its existing test module
  actor: logan
  at: '2026-09-02'
- op: add
  glob: tests/unit/test_check_admission.py
  reason: reformatted by frob format (pre-existing drift) / new watchdog regression
    tests
  actor: logan
  at: '2026-09-02'
- op: add
  glob: tests/unit/test_conftest_midrun_watchdog.py
  reason: reformatted by frob format (pre-existing drift) / new watchdog regression
    tests
  actor: logan
  at: '2026-09-02'
- op: add
  glob: tests/unit/test_check_admission.py
  reason: reformatted by frob format (pre-existing drift) / new watchdog regression
    tests
  actor: logan
  at: '2026-09-02'
- op: add
  glob: tests/unit/test_conftest_midrun_watchdog.py
  reason: reformatted by frob format (pre-existing drift) / new watchdog regression
    tests
  actor: logan
  at: '2026-09-02'
- op: add
  glob: tests/unit/test_check_admission.py
  reason: reformatted by frob format (pre-existing drift) / new watchdog regression
    tests
  actor: logan
  at: '2026-09-02'
- op: add
  glob: tests/unit/test_conftest_midrun_watchdog.py
  reason: reformatted by frob format (pre-existing drift) / new watchdog regression
    tests
  actor: logan
  at: '2026-09-02'
- op: add
  glob: tests/unit/test_check_admission.py
  reason: reformatted by frob format (pre-existing drift) / new watchdog regression
    tests
  actor: logan
  at: '2026-09-02'
- op: add
  glob: tests/unit/test_conftest_midrun_watchdog.py
  reason: reformatted by frob format (pre-existing drift) / new watchdog regression
    tests
  actor: logan
  at: '2026-09-02'
- op: add
  glob: tests/unit/test_check_admission.py
  reason: reformatted by frob format (pre-existing drift) / new watchdog regression
    tests
  actor: logan
  at: '2026-09-02'
- op: add
  glob: tests/unit/test_conftest_midrun_watchdog.py
  reason: reformatted by frob format (pre-existing drift) / new watchdog regression
    tests
  actor: logan
  at: '2026-09-02'
- op: add
  glob: tests/unit/test_check_admission.py
  reason: reformatted by frob format (pre-existing drift) / new watchdog regression
    tests
  actor: logan
  at: '2026-09-02'
- op: add
  glob: tests/unit/test_conftest_midrun_watchdog.py
  reason: reformatted by frob format (pre-existing drift) / new watchdog regression
    tests
  actor: logan
  at: '2026-09-02'
body_changes:
- mode: append
  reason: record BUG002 waiver for confirmatory-only-by-construction evidence
  actor: logan
  at: '2026-09-02'
  old_length: 833
  new_length: 1823
evidence:
- tests/gates_suite/test_run.py::TestProcessPoolGates::test_run_gates_leaves_no_live_pool_threads_or_children_behind
- tests/unit/test_conftest_midrun_watchdog.py::TestTotalBudgetExceeded::test_true_at_exactly_the_budget
- tests/unit/test_conftest_midrun_watchdog.py::TestRunMidrunWatchdogTotalBudget::test_fires_total_budget_exit_with_no_stall_threshold_armed
- tests/unit/test_conftest_midrun_watchdog.py::TestAnnounceTotalBudgetExceededAndHardExit::test_hard_exits_with_status_1_and_prints_the_inventory_line
designated_repro_test: tests/gates_suite/test_run.py::TestProcessPoolGates::test_run_gates_leaves_no_live_pool_threads_or_children_behind
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Follow-up to T-3692. CI run 33680767948 FROB_CHECK_TIMING breadcrumbs: every pipeline mark fires at ~1.0s, then a ~120s gap before atexit fires. Investigated frob.gates._open_process_pool: already properly torn down (shutdown(wait=True) in finally; teardown-exit marks land at ~1s) -- NOT the blocker. Real suspect found while narrowing, out of this scope, filed separately: src/frob/lang and src/frob/vet abandon ThreadPoolExecutor(max_workers=1) workers via shutdown(wait=False) on timeout; concurrent.futures.thread joins ALL such threads at interpreter atexit regardless of abandonment. In-scope work: (1) harden _open_process_pool/run_gates shutdown to context-manager + cancel_futures=True with a regression test proving no live pool threads/children survive run_check; (2) Part B watchdog total-budget + ci.yml budget var fix.



frob:waive BUG002 reason="confirmatory-only by construction, same posture T-3692/T-3705 already established for this ticket family: the designated repro test (TestProcessPoolGates::test_run_gates_leaves_no_live_pool_threads_or_children_behind) proves a PROPERTY that was already true before this ticket (frob.gates's ProcessPoolExecutor already shuts down cleanly, per T-3692's own timing-breadcrumb evidence) -- there was no pool-teardown bug in this ticket's own scope to reproduce with a fail-then-pass test. The win32-only symptom this ticket investigates (the ~120s interpreter-shutdown gap) is unreproducible on this WSL/Linux host by construction; this land ships the narrowing evidence (gates pool ruled out), a belt-and-suspenders hardening (cancel_futures=True), a real regression test guarding that property going forward, and the T-3707 Part B watchdog total-budget addition for the NEXT windows CI run to confirm or refute -- matching T-3692/T-3705's own round precedent"

