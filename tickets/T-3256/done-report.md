## Done report

Changed:
src/frob/check/__init__.py
  - New cross-process, memory-aware admission budget (T-3256): a
    check-admission registry under .frob/check-admission/ (one marker
    per live frob check PID), _available_memory_mb (delegates to
    frob.testing._coverage_refresh's T-1672 function -- DUP001 caught
    the would-be byte-identical copy, deferred/local import avoids the
    frob.check<->frob.testing/frob.graph module cycle docs/rework.md's
    layering rule already warns about), _compute_admitted_workers (pure
    math: min(real cpu, available_mem_mb // per_worker_mb) divided by
    live concurrent check count, floored at 1, FROB_CHECK_MAX_WORKERS
    override), and _admission_budget (context manager: registers this
    PID, monkeypatches os.cpu_count() for the duration ONLY when the
    admitted budget is smaller than the real core count, restores in
    finally, logs once at WARNING naming the exact numbers).
  - Wired into _run_check_with_skips (the Python-mode entry point every
    frob check invocation reaching frob.gates._run_gates's own
    os.cpu_count()-sized pool passes through) as the outermost context
    manager, ahead of derived_state_lock.
tests/unit/test_check_admission.py (new)
  - 25 unit tests: pure-math cases (idle box gets full pool, six
    concurrent checks reduce it, memory beats cpu when memory is
    tighter, never admits zero, unmeasurable memory falls back to a
    concurrency-only split, FROB_CHECK_MAX_WORKERS opt-out/pin/malformed
    handling, FROB_CHECK_PER_WORKER_MEM_MB override/malformed handling),
    registry mechanics (marker write/count/reap-dead-pid/non-numeric-
    skip), the context manager (patches and restores os.cpu_count only
    when reduced, restores on exception, removes its marker on exit and
    on exception, logs the reduction naming the numbers, logs nothing
    when nothing was reduced -- the MUST-STAY-QUIET fixture), and
    _available_memory_mb's delegation to the shared implementation.

Evidence:
  - tests/unit/test_check_admission.py: 25/25 passed (uv run pytest).
  - tests/unit/test_check.py + tests/unit/test_check_budget.py (existing
    check-module tests, to confirm the new context manager wrapping
    _run_check_with_skips did not regress anything): 167/167 passed.
  - ruff check + ruff format: clean on both changed files.
  - ty check: clean on both changed files (0 diagnostics; the ty:
    ignore[invalid-assignment] on the os.cpu_count patch is documented
    inline -- ty correctly flags reassigning a stdlib function and this
    is a deliberate, narrowly-scoped, try/finally-restored technique).
  - frob check --ticket T-3256 --only scope: 0 errors (73 pre-existing
    warnings on symbols/anchors this ticket's edit did not touch).
  - frob check --ticket T-3256 (full): confirmed the gate:DUP finding
    DUP001 flagged (my first _available_memory_mb draft, a byte-
    identical copy of frob.testing._coverage_refresh's own T-1672
    function) is gone after switching to a delegating import; every
    other FAIL family's error count is IDENTICAL to this session's
    earlier, unrelated T-3254 full-check baseline (gate:COV 34, ty 21,
    gate:DRIFT 60, frob-cycle 1, etc.) -- confirmed pre-existing and not
    attributable to this diff, not merely assumed.
  - Live end-to-end sanity: `uv run frob check --only ruff` (whole-repo,
    not --ticket-scoped) ran successfully through the admission-budget
    context manager with no crash, no leaked os.cpu_count patch
    afterward (verified: a second invocation in the same session behaved
    identically, i.e. nothing left globally mutated).

Filed:
  - T-3269 -- fleet_status cannot distinguish live check
    contention from stalled agents (feature, scope=scripts/
    fleet_status.py). Report-only per this ticket's own instruction.
  - T-3270 -- frob ticket land's fixed wall-clock timeout
    races variable-cost contention, killing progressing lands (bug,
    scope=src/frob/tickets/_land.py, src/frob/app/ticket_runner/
    _land_cmd.py). Directly from the coordinator's T-3256 field evidence
    (a land killed by its own 540s wrapper while its child check was
    335s in at 82.8% CPU) plus this implementer's own independent,
    repeated reproduction of the identical shape landing T-3254 under
    the same box conditions.

Gates: frob check --ticket T-3256 --only scope clean (0 errors). DUP001
(the one NEW error this diff introduced) fixed by delegating to the
existing implementation rather than waived. No frob:waive used anywhere
in this change.

Design choices stated explicitly, per the ticket's own acceptance criteria:
  1. Cross-process admission budget: a token-file registry under
     .frob/check-admission/ (one of the ticket's own named candidates),
     combined with real-time /proc/meminfo reads (the ticket's other
     named candidate, "size against observed current load") -- both
     together, not either alone, because a memory-read-only approach
     alone is vulnerable to N checks starting near-simultaneously all
     reading the same idle-looking memory before any of them has spawned
     workers (a real TOCTOU the registry's live-PID count corrects for).
  2. Degrades, never refuses: _compute_admitted_workers always returns
     >= 1; os.cpu_count() is only patched (and only logged) when the
     admitted budget is smaller than the real core count.
  3. Memory, not just CPU: the budget is min(cpu, available_mem_mb //
     per_worker_mb) -- verified by test_memory_bound_beats_cpu_bound
     (64 cores, 300MB available -> admits 1, not 64).
  4. Idle-box full pool preserved: test_idle_box_admits_full_pool and
     test_full_budget_never_patches_cpu_count assert os.cpu_count is
     literally untouched when concurrent=1 and memory is ample.
  5. The mechanism (monkeypatching os.cpu_count() for this process's
     lifetime, restored in finally) was chosen over
     os.sched_setaffinity because affinity throttles CPU SCHEDULING but
     leaves worker COUNT (and therefore RSS) unchanged -- it would not
     address the ticket's own stated binding constraint (14.5GB of
     forkservers, not CPU contention). In this codebase os.cpu_count()
     directly gates worker PROCESS COUNT at frob.gates._run_gates's
     `proc_workers = max(1, min(len(process_jobs), os.cpu_count() or
     4))` (confirmed by reading the call site, not touched -- out of
     this ticket's src/frob/check/__init__.py-only scope), so shrinking
     it directly shrinks memory footprint, not just scheduling.
  6. fleet_status visibility and land-timeout budget-awareness: reported
     above, not fixed here, each filed as its own ticket (see Filed).
  7. T-3011 gates: not applicable to this ticket (no release/consent
     surface touched).

### Changed
```
 src/frob/check/__init__.py         | 321 ++++++++++++++++++++++++++++++++-
 tests/unit/test_check_admission.py | 360 +++++++++++++++++++++++++++++++++++++
 tickets/T-3256/ticket.md           | 108 +++++++++++
 tickets/T-3269/ticket.md |  47 +++++
 tickets/T-3270/ticket.md |  65 +++++++
 5 files changed, 892 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/unit/test_check_admission.py::TestComputeAdmittedWorkers::test_idle_box_admits_full_pool` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_admission.py::TestComputeAdmittedWorkers::test_six_concurrent_checks_reduce_the_pool` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_admission.py::TestComputeAdmittedWorkers::test_memory_bound_beats_cpu_bound` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_admission.py::TestComputeAdmittedWorkers::test_never_admits_zero` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_admission.py::TestAdmissionBudgetContextManager::test_reduced_budget_patches_cpu_count_for_the_duration` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_admission.py::TestAdmissionBudgetContextManager::test_full_budget_never_patches_cpu_count` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_admission.py::TestAdmissionBudgetContextManager::test_cpu_count_restored_even_on_exception` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_admission.py::TestAdmissionBudgetContextManager::test_marker_removed_even_on_exception` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 98 error(s), 3976 warning(s), 881 waived
- error-findings: ARCH102@src/frob/gates/_waive.py, ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV003@tickets/T-3223, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-3262/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/gates/_docstring_archaeology.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DOCENUM001@docs/modules/gates.md, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/clean/_core.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/gates/_docstring_archaeology.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@src/frob/app/ticket_runner/_land_cmd.py, OPAQUE001@tests/test_vet_capability.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3256, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@tests/test_ci_report.py, SUPPRESS001@tests/test_tickets.py, SUPPRESS001@tests/test_tickets_acceptance.py, SUPPRESS001@tests/test_tickets_brief.py, SUPPRESS001@tests/test_tickets_velocity.py, SUPPRESS001@tests/unit/verify/test_backpressure.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/unit/test_main_entry.py
