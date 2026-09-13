---
id: T-4452
title: 'pytest DeprecationWarning: SIGKILL-victim test helpers fork a multi-threaded
  process (py3.14 macOS)'
state: queued
kind: bug
origin: agent
created: '2026-09-12'
priority: medium
parent: null
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_land_finish_guard.py
- tests/unit/test_land_lock_liveness.py
- tests/ticket_land_suite/test_verify_reset.py
- tests/unit/test_fix_engine_journal.py
- tests/helpers/*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
pytest warnings summary on the macOS leg (CI run 34734529382, Python 3.14.7): DeprecationWarning "This process (pid=N) is multi-threaded, use of fork() may lead to deadlocks in the child" from multiprocessing/popen_fork.py:76 (os.fork), raised by these tests: tests/unit/test_land_finish_guard.py::TestLandFinishPendingMarkerSigterm::test_sigterm_between_marker_write_and_mutation_leaves_marker_for_reconcile, tests/unit/test_land_lock_liveness.py::TestLandLockSurvivesSigkilledHolder::test_land_lock_reclaims_promptly_after_sigkill, tests/unit/test_land_lock_liveness.py::TestRefuseIfLandInProgressSurvivesSigkilledHolder::test_refuse_if_land_in_progress_clears_promptly_after_sigkill, tests/ticket_land_suite/test_verify_reset.py::TestSigkillMidStaging::test_sigkill_during_post_squash_reverification_leaves_ticket_recoverable, tests/ticket_land_suite/test_verify_reset.py::TestSigkillMidStaging::test_unrelated_land_does_not_absorb_a_killed_lands_staged_content, tests/unit/test_fix_engine_journal.py::TestAbandonedAutofixJournalSigkillSubprocess::test_sigkilled_journal_writer_is_detected_and_refused. Each uses multiprocessing with the default (fork) start method from a process that already has threads (the xdist worker, the stackdump thread, the daemon proxy thread). Python 3.14 warns because fork in a multi-threaded process can deadlock the child; on 3.14 the default start method on POSIX is already forkserver except where code explicitly asks for fork. ACCEPTANCE: (1) enumerate every `multiprocessing.Process(...)`/`get_context("fork")` in src/ and tests/ (`git grep -n "get_context(\"fork\"\|set_start_method\|multiprocessing.Process"`), and for each SIGKILL/SIGTERM-victim helper in these tests switch to an explicit `multiprocessing.get_context("spawn")` (or a subprocess.Popen of a `-c` script, matching the pattern tests/unit/test_graph_cache.py already uses for its sibling reader) so no test forks a threaded process; (2) the six node ids above emit no DeprecationWarning under `-W error::DeprecationWarning:multiprocessing` on Linux (and the same on the macOS leg on the next push); (3) if any PRODUCTION code path forks (not just tests), fix it the same way and say so in the Done report. Sprint v0.531.0.
