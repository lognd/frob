---
id: T-1634
title: An orphaned land.lock from a killed land blocks unrelated commands until deleted
  by hand
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/process/**
- src/frob/doctor.py
- tests/**
- src/frob/app/doctor_runner.py
- docs/guides/install.md
- tickets-archive.md
- docs/modules/app.md
- docs/modules/render.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/doctor_runner.py
  reason: doctor CLI runner needs the T-1634 self-heal disclosure line
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/app/doctor_runner.py
  reason: doctor CLI runner needs the T-1634 self-heal disclosure line
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/guides/install.md
  reason: doctor's live-land-process report doc anchor documents the T-1634 self-heal
    behavior
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tickets-archive.md
  reason: T-1515's evidence needed --replace after renaming a test this ticket touched
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/modules/app.md
  reason: AFFECT001 closure docs for doctor_runner.run
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/modules/render.md
  reason: AFFECT001 closure docs for doctor_runner.run
  actor: logan
  at: '2026-08-06'
evidence:
- tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout::test_orphaned_lock_from_a_confirmed_dead_pid_is_reclaimed_and_logged
- tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout::test_orphaned_lock_naming_a_genuinely_live_pid_still_refuses
- tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess::test_dead_holder_pid_is_reported_dead_but_self_healing_and_healthy
- tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess::test_ambiguous_holder_liveness_is_reported_unhealthy
- tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess::test_live_holder_pid_is_reported_alive_and_healthy
- tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerOrphanedLandLockDisclosure::test_healthy_report_with_confirmed_dead_holder_prints_self_healing_line
- tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerOrphanedLandLockDisclosure::test_healthy_report_with_no_land_lock_prints_nothing_extra
designated_repro_test: null
threat: null
component: null
---
A land that is killed (SIGKILL, an OOM kill, a terminated agent, a crashed session) leaves `.frob/land.lock` behind. Every later command that takes that lock then fails until a human deletes the file.

Observed 2026-08-06: a killed land left a lock naming pid 4098526. Hours later `make -n coverage-fast` still failed, and with it tests/test_coverage.py::TestCoverageTargetNativesGuard -- a test that has nothing to do with landing. From the suite's point of view this looked like a real regression; it was environment residue.

frob already does the hard part. The error message names the pid, the session id, the start time, and states plainly that the process is NOT running:

    land.lock is held by pid <N> (session pid-<N>, started <ts>) which is NOT
    running -- an orphaned lock file from a crashed/killed land; remove
    `.frob/land.lock` by hand after confirming no other process is actually
    mid-land

So the code has already PROVEN the holder is dead and has already decided the lock is orphaned. It then asks a human to act on its own conclusion. That gap is the bug: a diagnosis this certain should be self-healing.

Fix: when the recorded holder is confirmed absent (the same liveness probe that produces this message), reclaim the lock automatically and log loudly at WARNING with the full identity of the dead holder. Keep refusing, exactly as today, whenever liveness is AMBIGUOUS rather than confirmed-dead -- the distinction `frob.tickets._leases._probe_worktree_liveness` already draws for worktree leases (confirmed_absent vs ambiguous, T-0782/T-0584), which exists precisely so a transient stat failure never deletes a live peer's claim. Reuse that probe rather than writing a second liveness notion.

Also worth doing in the same pass:
- `frob doctor` should report an orphaned land.lock as a finding it can fix, so the state is discoverable without hitting it accidentally through an unrelated make target.
- Whatever cleanup path exists must run on the abort paths a land already has: this drive saw a land refuse to unwind and leave staged REL001 files behind (see the land-lease ticket), so "the land aborted, clean up after yourself" is a recurring gap rather than a one-off.

Regression test: write a land.lock naming a pid that does not exist, run a command that takes the lock, assert it proceeds and logs the reclaim; then write one naming a LIVE pid and assert it still refuses.