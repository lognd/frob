---
id: T-4266
title: the land status marker holds one land in a repository that runs several, so
  the fleet tool can name a finished land while a different one is running
state: done
kind: bug
origin: human
created: '2026-09-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- scripts/fleet_status.py
- tests/ticket_land_suite/test_land_lock.py
- tests/unit/coordinator_suite/test_fleet_land.py
- docs/guides/coordinator-scripts.md
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/ticket_land_suite/test_land_lock.py
  reason: 'T-4266: the multi-entry marker fix changes _write_land_status''s on-disk
    shape and fleet_status.py''s reader, so their existing unit tests must be updated
    and new multi-land tests added in the same change'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/unit/coordinator_suite/test_fleet_land.py
  reason: 'T-4266: the multi-entry marker fix changes _write_land_status''s on-disk
    shape and fleet_status.py''s reader, so their existing unit tests must be updated
    and new multi-land tests added in the same change'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: 'T-4266: both docs document _write_land_status/read_land_status_marker/_land_status_marker_line,
    which this ticket''s multi-entry fix changes'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: 'T-4266: both docs document _write_land_status/read_land_status_marker/_land_status_marker_line,
    which this ticket''s multi-entry fix changes'
  actor: logan
  at: '2026-09-07'
evidence:
- tests/ticket_land_suite/test_land_lock.py::TestLandStatus::test_concurrent_lands_each_get_their_own_entry
- tests/ticket_land_suite/test_land_lock.py::TestLandStatus::test_dead_lands_own_entry_survives_a_live_lands_write
- tests/ticket_land_suite/test_land_lock.py::TestLandStatus::test_phase_transitions_are_pollable
- tests/ticket_land_suite/test_land_lock.py::TestLandStatus::test_waiting_phase_records_lock_holder
- tests/ticket_land_suite/test_land_lock.py::TestLandStatus::test_write_failure_is_best_effort_and_never_raises
- tests/unit/coordinator_suite/test_fleet_land.py::TestReadLandStatusMarker::test_reads_a_written_marker
- tests/unit/coordinator_suite/test_fleet_land.py::TestReadLandStatusMarker::test_missing_marker_returns_none
- tests/unit/coordinator_suite/test_fleet_land.py::TestReadLandStatusMarker::test_unparseable_marker_returns_none
- tests/unit/coordinator_suite/test_fleet_land.py::TestReadLandStatusMarker::test_legacy_flat_marker_returns_none
- tests/unit/coordinator_suite/test_fleet_land.py::TestLandStatusMarkerLines::test_no_marker_renders_nothing
- tests/unit/coordinator_suite/test_fleet_land.py::TestLandStatusMarkerLines::test_marker_renders_phase_ticket_pid_and_liveness
- tests/unit/coordinator_suite/test_fleet_land.py::TestLandStatusMarkerLines::test_live_pid_is_tagged_live_not_dead
- tests/unit/coordinator_suite/test_fleet_land.py::TestLandStatusMarkerLines::test_concurrent_lands_each_render_their_own_line
designated_repro_test: null
acceptance:
- text: given several concurrent lands, when the fleet tool reports what is landing,
    then every live land is named and no finished land is presented as running
  evidence:
  - tests/unit/coordinator_suite/test_fleet_land.py::TestLandStatusMarkerLines::test_concurrent_lands_each_render_their_own_line
- text: given a land that died mid-phase, when its record is read afterwards, then
    its final phase is still readable and is distinguishable from a live land rather
    than occupying the same slot
  evidence:
  - tests/ticket_land_suite/test_land_lock.py::TestLandStatus::test_dead_lands_own_entry_survives_a_live_lands_write
- text: given the fix, when it lands, then the marker is not simply cleared on exit,
    since that would discard the crash-forensics purpose the file exists for
  evidence:
  - tests/ticket_land_suite/test_land_lock.py::TestLandStatus::test_phase_transitions_are_pollable
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE LAND STATUS MARKER IS A SINGLE-WRITER RECORD IN A MULTI-WRITER WORLD, AND
THE FLEET TOOL PRESENTS ITS ANSWER AS AUTHORITATIVE. Measured twice in one
session, both times while reading fleet state to decide whether it was safe to
act.

WHAT WAS OBSERVED. On the first occasion the marker named one ticket while the
land lock was held on behalf of a different one. On the second the marker named a
ticket in a running phase with a timestamp nineteen minutes old, while the land
actually executing at that moment was a third ticket entirely, freshly started.
In both cases the marker was not stale in the sense its own design anticipates;
it was accurate about a land that had happened and silent about the land that was
happening.

THE MECHANISM, READ FROM THE CODE. The marker is one JSON object at one fixed
path holding one pid, one ticket id, and one phase. Every land writes it at each
phase transition, and it is deliberately never cleared on exit so a crashed
land's last phase survives for post-mortem reading. That design is coherent for
one land at a time. This repository routinely runs several concurrently, and the
deferred and out-of-tree land paths make that the normal case rather than the
exception. With N lands and one slot, the file holds whichever wrote most
recently, and a reader cannot tell whether that is the newest land, a finished
one, or a dead one.

WHY IT MATTERS MORE THAN IT LOOKS. The fleet tool prints this marker near the top
of its output, directly under the count of lands in flight, as the answer to what
is currently landing. The count comes from a process scan and is right; the
marker sits beside it and can name something else entirely. A reader who trusts
the pair will conclude a land is stuck when it is not, or that a ticket is
progressing when its land ended long ago. The wrong conclusion here is expensive
in exactly the direction that matters: it invites clearing locks or intervening
in a shared checkout that is actually busy.

WHAT A FIX SHOULD DO. Make the record hold as many entries as there are lands,
keyed so that a reader can match an entry to a live process, and have the reader
present only entries it can still account for. Preserve the post-mortem property
the current design was built for: a dead land's final phase should remain
readable, but it must be distinguishable from a live one rather than occupying
the same slot.

DO NOT FIX THIS BY CLEARING THE MARKER ON EXIT. That trades a misleading record
for no record, and discards the crash-forensics use the file exists to serve.

A NOTE FOR WHOEVER TAKES THIS. The fleet tool's own line about the lock file
already models the right instinct: it tells the reader not to trust the recorded
pid or the lock's age, because the lock is advisory and freed on death. The
marker deserves the same honesty, either by being made trustworthy or by saying
plainly what it cannot answer.