---
id: T-4494
title: 'frob ticket land never installs the SIGUSR1 stack-dump handler: a 21-minute
  silent CPU-bound phase is undiagnosable and USR1 kills the land'
state: done
kind: bug
origin: agent
created: '2026-09-15'
priority: high
parent: T-4410
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/testing/_stackdump.py
- tests/unit/test_land_stackdump.py
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets-landing.md
  reason: T-4494's watchdog + unconditional handler-install need a doc anchor; docs/modules/tickets-landing.md
    is where every other _land_cmd.py T-#### feature (T-4417 phase-elapsed-logging,
    T-3613 queue, etc) already documents
  actor: logan
  at: '2026-09-16'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: T-4494's watchdog + unconditional handler-install need a doc anchor; docs/modules/tickets-landing.md
    is where every other _land_cmd.py T-#### feature already documents
  actor: logan
  at: '2026-09-16'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: T-4494's watchdog + unconditional handler-install need a doc anchor; docs/modules/tickets-landing.md
    is where every other _land_cmd.py T-#### feature already documents
  actor: logan
  at: '2026-09-16'
evidence:
- tests/unit/test_land_stackdump.py::TestLandLikeSubprocessSigusr1::test_survives_with_a_dump_after_the_fix
- tests/unit/test_land_stackdump.py::TestLandLikeSubprocessSigusr1::test_dies_without_the_handler
- tests/unit/test_land_stackdump.py::TestInstallStackdumpHandlerForce::test_force_installs_regardless_of_env
- tests/unit/test_land_stackdump.py::TestSilentPhaseWatchdog::test_fires_once_after_threshold_then_waits_for_next_episode
- tests/unit/test_land_stackdump.py::TestSilentPhaseWatchdog::test_never_fires_while_phase_lines_keep_arriving
- tests/unit/test_land_stackdump.py::TestSilentPhaseDumpThreshold::test_reads_configured_value
designated_repro_test: tests/unit/test_land_stackdump.py::TestLandLikeSubprocessSigusr1::test_survives_with_a_dump_after_the_fix
acceptance:
- text: GIVEN a running frob ticket land WHEN SIGUSR1 is sent THEN every thread's
    stack is written to .frob/stackdumps/pid-<pid>.txt and the land continues
  evidence:
  - tests/unit/test_land_stackdump.py::TestLandLikeSubprocessSigusr1::test_survives_with_a_dump_after_the_fix
  - tests/unit/test_land_stackdump.py::TestLandLikeSubprocessSigusr1::test_dies_without_the_handler
  - tests/unit/test_land_stackdump.py::TestInstallStackdumpHandlerForce::test_force_installs_regardless_of_env
- text: GIVEN a land phase runs longer than a configurable threshold with no log line
    WHEN the threshold passes THEN the land logs a self-dump of its own stack at WARNING
  evidence:
  - tests/unit/test_land_stackdump.py::TestSilentPhaseWatchdog::test_fires_once_after_threshold_then_waits_for_next_episode
  - tests/unit/test_land_stackdump.py::TestSilentPhaseWatchdog::test_never_fires_while_phase_lines_keep_arriving
  - tests/unit/test_land_stackdump.py::TestSilentPhaseDumpThreshold::test_reads_configured_value
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-15 landing T-4496 onto dev: after '[+0.3s] profile=rapid -- skipping the T-1463 pre-land baseline snapshot check' the process ran 21 minutes at 109 percent CPU in the land python process itself (no child), with no further log line. py-spy needs root on this WSL box; install_stackdump_handler (T-1466) is installed only by frob serve, so kill -USR1 terminated the land with exit 138 and nothing landed. The land must install the handler unconditionally (near-zero cost until triggered) and emit a periodic self-dump when a phase is silent past a threshold, so the next silent phase names its own function.