---
id: T-1515
title: 'orphan-writer guard: land refuses/warns when another land process from a different
  session is live'
state: done
kind: feature
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout::test_holder_metadata_written_on_acquire
- tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout::test_lock_released_after_context_exits
- tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout::test_timeout_raises_when_a_foreign_holder_never_releases
- tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess::test_no_lock_file_reports_nothing
- tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess::test_live_holder_pid_is_reported_alive_and_healthy
- tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess::test_dead_holder_pid_is_reported_dead_but_self_healing_and_healthy
- tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess::test_malformed_lock_content_reports_nothing
designated_repro_test: null
threat: null
component: null
---
2026-08-04 incident (see T-1495): an orphaned background script from a dead conversation was serially landing the roster while a new coordinator session also wrote to main; the two writers' unwinds destroyed each other's commits. The advisory fcntl land.lock serializes lock-holders but cannot tell the second session that a foreign driver is mid-roster. Add: (1) land records pid+session-id+start-time in the lock file; (2) a fresh land invocation logs WHO holds it and refuses after timeout instead of queueing silently; (3) frob doctor reports live land processes for the repo so a session-start check is one command.