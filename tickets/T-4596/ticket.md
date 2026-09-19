---
id: T-4596
title: 'SELFAUDIT001 SYS111 auto-accept never fires: sys111_findings_touching runs
  in-process, never sees FROB_LAND_LOCK_ROOT'
state: done
kind: bug
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_squash.py
- src/frob/strata/_effects.py
- tests/unit/strata/test_selfconform.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_ticket_work_and_land_finish.py::TestSelfauditFindingsInTouchedFiles::test_land_lock_root_sets_env_for_the_in_process_gate_call
- tests/test_ticket_work_and_land_finish.py::TestSelfauditFindingsInTouchedFiles::test_no_land_lock_root_leaves_env_untouched
designated_repro_test: null
acceptance:
- text: GIVEN a land with a land_lock_root and a real SYS111 testsuite-glob-growth
    finding in touched files, WHEN _refuse_if_selfaudit_findings_in_touched_files
    runs its in-process gate calls, THEN FROB_LAND_LOCK_ROOT is set in os.environ
    for the duration of that call and restored afterward
  evidence:
  - tests/test_ticket_work_and_land_finish.py::TestSelfauditFindingsInTouchedFiles::test_land_lock_root_sets_env_for_the_in_process_gate_call
  - tests/test_ticket_work_and_land_finish.py::TestSelfauditFindingsInTouchedFiles::test_no_land_lock_root_leaves_env_untouched
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4583 fixed FROB_LAND_LOCK_ROOT forwarding for the SPAWNED subprocess check in _pre_commit_unscoped_error_sweep (_land_cmd.py), but _refuse_if_selfaudit_findings_in_touched_files (_land_squash.py, T-3324) calls frob.gates._sys.sys111_findings_touching/selfaudit_findings_touching/docptr_findings_touching IN-PROCESS (no subprocess spawn), so _land_commit_in_progress's os.environ.get(FROB_LAND_LOCK_ROOT_ENV) probe reads the parent land process's own environ, which was never set (T-4583 only sets it in the child env dict for the spawned check), and its fallback root/LAND_LOCK_REL probe checks 'stage' (the squash worktree), not the primary checkout _land_lock actually locks. Every real land with new testsuite-glob growth refuses forever with SELFAUDIT001 SYS111 pending-auto-accept, reproduced live on T-4508 at 05:37 even with T-4583 merged. Fix: thread the primary checkout root through _run_pre_commit_checks -> _refuse_if_selfaudit_findings_in_touched_files and temporarily set FROB_LAND_LOCK_ROOT in os.environ for the duration of the in-process gate calls (try/finally restore), plus add _log.info at each decision point (env-var seen, fallback probe path, file exists) so a real land's log names the reason.