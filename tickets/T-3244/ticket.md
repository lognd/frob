---
id: T-3244
title: Burn down remaining platform-unsafe test-fixture code surfaced by multi-platform
  ty (T-3211 split)
state: done
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_leases.py
- tests/test_ticket_land.py
- tests/unit/test_rapid_sweep.py
- tests/unit/test_process_lock.py
- tests/unit/test_coordinator_scripts.py
- tests/test_serve_socket.py
- tests/unit/test_stackdump.py
- tests/unit/test_conftest_stackdump.py
- tests/unit/test_ticket_store.py
- tests/unit/test_app_runners_process.py
- tests/test_tickets_priority.py
- tests/test_tickets_parent.py
- tests/test_ticket_reconcile.py
- tests/test_coverage_wait_shared.py
- tests/test_app_daemon_proxy.py
- tests/unit/test_pytest_spawn_env_wiring.py
- tests/unit/test_land_lock_liveness.py
- tests/unit/test_land_finish_guard.py
- tests/test_serve_leases.py
- src/frob/app/_config_external.py
- src/frob/app/ticket_runner/_new.py
- src/frob/verify/_worker.py
evidence_scope:
- tests/unit/verify/test_worker.py
- tests/unit/test_app_config_flag_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_ticket_leases.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_ticket_land.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_process_lock.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_serve_socket.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_stackdump.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_conftest_stackdump.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_app_runners_process.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_tickets_priority.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_tickets_parent.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_ticket_reconcile.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_coverage_wait_shared.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_app_daemon_proxy.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_pytest_spawn_env_wiring.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_land_lock_liveness.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_land_finish_guard.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_serve_leases.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/app/_config_external.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/verify/_worker.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
evidence:
- tests/test_app_daemon_proxy.py::TestProbeDaemon::test_dead_socket_file_is_orphaned
- tests/test_app_daemon_proxy.py::TestProbeDaemon::test_probe_of_a_silent_listener_stays_within_budget
- tests/test_app_daemon_proxy.py::TestProbeDaemon::test_silent_listener_is_wedged
- tests/test_app_daemon_proxy.py::TestProbeDaemonVersion::test_matching_version_is_live
- tests/test_coverage_wait_shared.py::TestCoverageLockPlatformBackends::test_windows_backend_round_trips
- tests/test_serve_socket.py::TestAcquireSingletonLockPlatformBackends::test_windows_backend_round_trips
- tests/test_serve_socket.py::TestSocketPath::test_normal_depth_root_still_works
- tests/test_serve_socket.py::TestSocketPath::test_short_regardless_of_root_depth
- tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout::test_holder_metadata_written_on_acquire
- tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout::test_lock_released_after_context_exits
- tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout::test_orphaned_lock_from_a_confirmed_dead_pid_is_reclaimed_and_logged
- tests/test_ticket_land.py::TestLandLockPlatformBackends::test_windows_backend_round_trips
- tests/test_ticket_land.py::TestSigkillMidStaging::test_normal_land_reaches_done_exactly_once_no_extra_transition
- tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry
- tests/test_ticket_land.py::TestSigkillMidStaging::test_unrelated_land_does_not_absorb_a_killed_lands_staged_content
- tests/test_ticket_leases.py::TestConcurrentNewTicketAllocationDuringLand::test_n_concurrent_new_ticket_calls_produce_distinct_ids
- tests/test_ticket_leases.py::TestDispatchLandGuard::test_refused_verb_never_writes_the_ticket_file_at_all
- tests/test_ticket_leases.py::TestDispatchLandGuard::test_refuses_mutating_verb_while_land_in_progress
- tests/test_ticket_leases.py::TestLeaseStalenessReason::test_holder_dead
- tests/test_ticket_leases.py::TestLeaseStalenessReason::test_land_shields_lease
- tests/test_ticket_leases.py::TestNewTicketProgrammaticAutoCommit::test_new_verb_still_produces_one_commit_including_evidence
- tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_allows_after_a_killed_lands_lock_is_os_released
- tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_concurrent_land_and_ticket_new_cannot_corrupt_the_ledger
- tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_refuses_while_land_lock_held
- tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_wait_budget_counts_from_the_lands_own_start_not_this_calls_start
- tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_wait_times_out_and_still_refuses_loudly
- tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_waits_then_succeeds_once_the_lock_frees
- tests/test_ticket_reconcile.py::TestReconcileApplyLandInProgressGuard::test_apply_refuses_and_writes_nothing_while_land_lock_held
- tests/test_tickets_parent.py::TestSetParentLandInProgressGuard::test_refuses_and_writes_nothing_while_land_lock_held
- tests/test_tickets_priority.py::TestSetPriorityLandInProgressGuard::test_refuses_and_writes_nothing_while_land_lock_held
- tests/unit/test_conftest_stackdump.py::TestStackdumpHandler::test_sigusr1_writes_all_thread_stacks_when_enabled
- tests/unit/test_coordinator_scripts.py::TestFlockHoldersMatchingWin32Guard::test_win32_platform_returns_empty_without_calling_os_major_minor
- tests/unit/test_coordinator_scripts.py::TestOrphanedForkserverCount::test_counts_forkserver_reparented_to_init
- tests/unit/test_coordinator_scripts.py::TestOrphanedForkserverCountAgreesWithReap::test_young_xdist_parented_forkserver_agrees
- tests/unit/test_coordinator_scripts.py::TestStaleForkserverCount::test_counts_old_forkserver_when_no_checks_running
- tests/unit/test_coordinator_scripts.py::TestTrueFlockHolderPid::test_finds_the_true_holder
- tests/unit/test_land_finish_guard.py::TestLandFinishPendingMarkerSigterm::test_sigterm_between_marker_write_and_mutation_leaves_marker_for_reconcile
- tests/unit/test_land_lock_liveness.py::TestLandLockSurvivesSigkilledHolder::test_land_lock_reclaims_promptly_after_sigkill
- tests/unit/test_process_lock.py::TestDerivedStateLockPlatformBackends::test_windows_backend_round_trips
- tests/unit/test_process_lock.py::TestSharedIdCounterPlatformBackends::test_windows_backend_round_trips
- tests/unit/test_rapid_sweep.py::TestBaselineLock::test_windows_backend_serializes_two_concurrent_holders
- tests/unit/test_stackdump.py::TestStackdumpHandler::test_sigusr1_writes_all_thread_stacks_when_enabled
- tests/unit/test_ticket_store.py::TestLedgerLockPlatformBackends::test_windows_backend_round_trips
- tests/unit/verify/test_worker.py::TestEnsureReducedPriority::test_applies_nice_and_ionice_exactly_once
- tests/unit/verify/test_worker.py::TestEnsureReducedPriority::test_failed_nice_call_never_raises
- tests/test_serve_leases.py::TestLeaseRpc::test_second_client_blocks_until_first_releases
- tests/unit/test_app_config_flag_coverage.py::TestFindDroppedCliFlags::test_reconstructed_t1995_state_is_caught
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: fefa399845a750636dec5a2068a1d82c8c23ce3d
---
Split from T-3211, which fixed the 2 genuine product-code sites (scripts/fleet_status.py's os.major/os.minor/os.sysconf). The remaining ~197 ty findings (measured fresh via frob check --only ty on main at T-3211 time, 21 files: tests/test_ticket_leases.py, tests/test_ticket_land.py, tests/unit/test_rapid_sweep.py, tests/unit/test_process_lock.py, tests/unit/test_coordinator_scripts.py, tests/test_serve_socket.py, tests/unit/test_stackdump.py, tests/unit/test_conftest_stackdump.py, tests/unit/test_ticket_store.py, tests/unit/test_app_runners_process.py, tests/test_tickets_priority.py, tests/test_tickets_parent.py, tests/test_ticket_reconcile.py, tests/test_coverage_wait_shared.py, tests/test_app_daemon_proxy.py, tests/unit/test_pytest_spawn_env_wiring.py, tests/unit/test_land_lock_liveness.py, tests/unit/test_land_finish_guard.py, tests/test_serve_leases.py, src/frob/app/_config_external.py, src/frob/app/ticket_runner/_new.py, src/frob/verify/_worker.py) are unresolved-attribute/unknown-argument findings inside TEST bodies (mostly bare fcntl.flock/os.fork usage inside POSIX-only test fixtures, repeated many times across a small number of files -- tests/test_ticket_leases.py alone is 55 of the 197) plus 3 unused-ignore-comment findings on src files (a DIFFERENT bug shape -- a stale ty: ignore left over from before some earlier fix, not a missing platform guard; needs its own look, not the T-3191 pattern). WHAT TO BUILD: same triage T-3211 did -- re-measure fresh via frob check --only ty on current main (this list will have drifted further), then for each site either (a) apply the sys.platform-guard fix T-3191/T-3211 established, or (b) waive with a reason if it is a genuine false positive (e.g. a test class already coarsely POSIX-only). Given the volume, consider whether a shared pytest fixture/helper that wraps the fcntl.flock pattern once (rather than 8+ independent local imports in test_ticket_leases.py alone) is worth doing as part of this, to avoid 8 near-identical guards in one file.