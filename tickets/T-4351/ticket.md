---
id: T-4351
title: Windows completes with 4 platform-specific failures; drive them to zero
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_worktree_guard.py
- tests/unit/test_main_entry.py
- tests/test_gate_cache.py
- tickets/T-draft-65a1a73b/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_main_entry.py
  reason: T-4308 ambient-venv test is windows-affected per T-4351 ticket
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/test_gate_cache.py
  reason: 'T-4351: archgate recompute test hits Windows process_time clock-granularity
    collision with the cache-hit 0.0 sentinel'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tickets/T-draft-65a1a73b/**
  reason: 'T-4351: filing the followup ticket for the non-reproducible 4th Windows
    failure touches its own ticket file'
  actor: logan
  at: '2026-09-08'
body_changes:
- mode: append
  reason: BUG002 cannot classify a platform-specific Windows defect from a Linux repro
    check; real before/after evidence is the winrun transcripts in the fix commits
    and Done report
  actor: logan
  at: '2026-09-08'
  old_length: 2752
  new_length: 3468
evidence:
- tests/unit/test_main_entry.py::TestEnsureVenv::test_sets_when_unset
- tests/unit/test_main_entry.py::TestEnsureVenv::test_leaves_existing
- tests/unit/test_main_entry.py::TestEnsureVenv::test_skips_non_venv
- tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_bare_eval_succeeds_with_no_filtering
- tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_stdout_contains_only_export_lines
- tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_diagnostics_still_appear_on_stderr
- tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_no_fleet_context_still_produces_valid_eval_output
- tests/test_gate_cache.py::TestRunGatesUseCacheProcessGates::test_tracked_file_edit_forces_process_gate_recompute
- tests/test_gate_cache.py::TestRunGatesUseCacheProcessGates::test_second_warm_run_serves_process_gate_from_cache
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE WINDOWS SUITE NOW COMPLETES, AND ITS REAL FAILING SET IS FIVE TESTS -- NOT THE
NINETEEN THE BACKLOG CLAIMED, AND NOT THE UNKNOWN IT ACTUALLY WAS.

MEASURED, FIRST COMPLETED RUN OF THIS DRIVE:

  SUITE-RESULT: exitstatus=1 collected=13786 failed=5

Previously this leg aborted partway with an internal worker-controller error and
emitted only a partial, explicitly lower-bound set, so every Windows number in the
backlog was inherited rather than measured. That is now fixed and the denominator
exists. Note the only internal-error string in the new log is a workflow COMMENT
about an unrelated historical revert -- do not read that grep hit as an abort.

ONE OF THE FIVE IS NOT WINDOWS-SPECIFIC and is already owned elsewhere: the
scaffold test that fails identically on the linux leg. Leave it alone; it is filed
separately. That leaves FOUR genuinely platform-specific failures:

  - the gate cache's "a tracked file edit forces a process-gate recompute" test
  - the land-time lint attribution test asserting a pre-existing violation that
    merely shifted lines does not refuse a land
  - the worktree guard's agent-env stdout-purity test for a bare eval
  - the ambient-virtual-env test asserting the variable is set when unset

TAKE THEM ONE AT A TIME AND SAY WHAT EACH ONE IS. Four failures with four
different shapes is not a cascade; resist looking for a single root cause until
the evidence supports one. The last item is worth reading first -- it covers a
helper added the same day as this run, so it is the most likely to be a fresh
regression rather than long-standing platform drift.

WINDOWS IS VERIFIABLE LOCALLY -- MEASURE, DO NOT REASON. The `winrun` script
(/home/logan/bin/winrun) syncs this repo to a Windows mirror and runs commands
natively via PowerShell. Caveats that have cost time before: the mirror is a
single shared checkout so concurrent syncs clobber each other, the Windows venv
uses `Scripts/` not `bin/`, and a bare `python3` hits a Store app-execution-alias
stub exiting 9009 -- invoke the venv's python explicitly.

WHAT THIS UNLOCKS, and it is the reason this is worth doing now. The workflow
marks this platform advisory (`continue-on-error`) precisely because its failure
set was large and unmeasured, which means the run's overall conclusion can never
be green on all three legs and a release has to reach for an override. Four fixes
would let that flag be removed and give the workflow an honest conclusion. Do not
remove the flag in this ticket -- get the four to zero first, then propose it.

VERIFY on Windows, and quote the suite counts from a completed run rather than a
scoped one. If a fix cannot be verified there, say which conclusions are inferred
rather than presenting a linux run as evidence.

frob:waive BUG002 reason="the designated repro (TestEnsureVenv::test_sets_when_unset) and every other bound evidence test is a Windows-ONLY defect (path-separator normalization vs a hardcoded POSIX literal, and clock-granularity/nested-uv fragility for the other two tests) -- it PASSES at the parent commit on the platform frob check/BUG002 actually runs the repro check on (linux), so a same-platform PASSED-at-parent reading is expected and not informative; the genuine before/after evidence for all three fixes is the winrun (real Windows subprocess) transcripts quoted in each fix commit message and the ticket Done report, which show FAILED before and PASSED after on win32 for the exact node ids bound here"