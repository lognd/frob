---
id: T-2691
title: frob ticket land has no externally-pollable progress/lock-contention status
state: done
kind: feature
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/tickets/_land.py
- scripts/fleet_status.py
- tests/test_ticket_land.py
- tests/unit/test_coordinator_scripts.py
- docs/guides/coordinator-scripts.md
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: 'T-2691: land-status marker tests live alongside the existing land.lock
    test suite'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: 'T-2691: land-status marker reader/renderer tests live alongside the existing
    land-lock-holder test suite'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: 'T-2691: new public read_land_status_marker needs its own frob:doc anchor
    in this guide, same convention every sibling fleet_status.py function already
    follows'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: 'T-2691: land() changed (AFFECT001) requires touching its affects()-closure
    doc'
  actor: logan
  at: '2026-08-30'
evidence:
- tests/ticket_land_suite/test_land_lock.py::TestLandStatus::test_phase_transitions_are_pollable
- tests/ticket_land_suite/test_land_lock.py::TestLandStatus::test_waiting_phase_records_lock_holder
- tests/ticket_land_suite/test_land_lock.py::TestLandStatus::test_write_failure_is_best_effort_and_never_raises
- tests/unit/coordinator_suite/test_fleet_land.py::TestReadLandStatusMarker::test_reads_a_written_marker
- tests/unit/coordinator_suite/test_fleet_land.py::TestReadLandStatusMarker::test_missing_marker_returns_none
- tests/unit/coordinator_suite/test_fleet_land.py::TestReadLandStatusMarker::test_unparseable_marker_returns_none
- tests/unit/coordinator_suite/test_fleet_land.py::TestLandStatusMarkerLine::test_no_marker_renders_nothing
- tests/unit/coordinator_suite/test_fleet_land.py::TestLandStatusMarkerLine::test_marker_renders_phase_ticket_and_pid
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 3ee857bfca0f62082e44e49071c9cf8ee4f9c58b
---
An operator watching `frob ticket land` while the fleet is contended has
no visibility into whether it is progressing, waiting on land.lock, or
was preempted/killed mid-flight -- the only way to tell is inspecting the
process tree and `.frob/land.lock` by hand (observed directly during a
2026-08-20 fleet-serialization incident: a land killed by its own
foreground timeout under lock contention left a MERGE_HEAD-in-progress
worktree, an orphaned land.lock entry, and no visible signal beyond a
truncated log that the attempt had failed rather than succeeded -- 270s
of wall clock, mostly spent waiting on another ticket's held lock, then
nothing landed and no land commit produced).

`frob ticket land` already logs a WARNING when it starts waiting on a
held land.lock ("waiting up to 500s before refusing") and again when it
reclaims an orphaned one -- but that line only reaches whoever is reading
stdout live; it is not surfaced anywhere an operator or coordinator can
poll (no `.frob/land-status.json`, no `frob ticket show`/`fleet_status`
field distinguishing "queued behind lock" from "actively running gates"
from "dead, needs a retry"). Fold this into the T-2141 disclosure
direction: a small land-status marker file (holder pid, phase,
started_at, last-heartbeat) that `fleet_status.py` and a future,
not-yet-implemented "frob land status" verb can read, so "is my land
alive, and did it accomplish
anything" stops requiring manual `ps`/`git log --grep`/`git status`
archaeology after the fact.

Filed from the T-2141/T-1549/T-2303 series per an explicit coordinator
instruction during a live fleet-serialization hold (2026-08-20): the
starved-batch incident that motivated the hold is itself the missing-
disclosure case this ticket should fix.
