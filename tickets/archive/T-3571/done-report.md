## Done report

Changed:
src/frob/arch/_concurrency.py::_check_self_join
src/frob/arch/_concurrency.py::_dispatch_records
src/frob/arch/_concurrency.py::_DispatchRecord
src/frob/arch/_concurrency.py::_receiver_text
src/frob/arch/_concurrency.py::_assigned_name
src/frob/arch/_concurrency.py::_call_arg_texts
src/frob/arch/_concurrency.py::_param_names
src/frob/arch/_concurrency.py::_check_fork_pool_hazards
docs/modules/arch.md self-join-deadlock section

Evidence:
tests/unit/arch_suite/test_concurrency.py::TestForkPoolHazards::test_self_join_deadlock_fires_when_dispatched_task_joins_its_pool
tests/unit/arch_suite/test_concurrency.py::TestForkPoolHazards::test_self_join_deadlock_does_not_fire_on_undispatched_join
tests/unit/arch_suite/test_concurrency.py::TestForkPoolHazards::test_self_join_deadlock_does_not_fire_on_foreign_object_shutdown
tests/unit/arch_suite/test_concurrency.py::TestForkPoolHazards::test_self_join_deadlock_fires_on_genuine_thread_self_join
tests/unit/arch_suite/test_concurrency.py::TestForkPoolHazards::test_self_join_deadlock_discharges_on_real_repo_socketd_idle_monitor

The detector now requires the dispatch site to also pass the dispatched
function its own dispatcher object (self-pass correlation) before a
join/shutdown/close call inside that function fires self-join-deadlock.
_socketd.py::_idle_monitor is confirmed quiet (discharge test above);
a genuine Thread-based self-join and the existing pool-based positive
control both still fire.

Filed: none

Gates: frob check --ticket T-3571 clean on gate:SCOPE/gate:PRE/gate:AFFECT
after scope was widened to tests/unit/test_arch.py and docs/modules/arch.md;
repo-wide gate:DOC/DRIFT/DUP/etc. failures shown by an unscoped run are
pre-existing findings unrelated to this diff (covered by T-3590, the
error burn-down ticket) -- none touch _concurrency.py, test_arch.py, or
arch.md.
