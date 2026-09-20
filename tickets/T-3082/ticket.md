---
id: T-3082
title: quarantine.json persists on disk after clear; a stale cleared record is byte-identical
  in shape to a live one
state: in-progress
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: v0.540.0
runs_last: false
milestone: 0.534.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/verify/_quarantine.py
- tests/unit/verify/test_quarantine.py
- src/frob/app/verify_runner.py
- tests/unit/verify/test_verify_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/verify/test_quarantine.py
  reason: 'T-3082: add regression tests for the new .frob/quarantine.status tombstone
    marker written by raise/clear_quarantine'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/app/verify_runner.py
  reason: 'T-3082: wire quarantine_status_marker into frob verify status output so
    a human reading the CLI (not just raw disk) also sees the tombstone distinction'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/unit/verify/test_verify_runner.py
  reason: 'T-3082: added TestBuildStatus coverage for the new quarantine_status_marker
    field wired into frob verify status'
  actor: logan
  at: '2026-09-19'
triage_changes:
- field: sprint
  old_value: v0.533.0
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-16'
- field: milestone
  old_value: v0.533.0
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-16'
- field: sprint
  old_value: v0.534.0
  new_value: v0.540.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
evidence:
- tests/unit/verify/test_quarantine.py::TestQuarantineStatusMarker::test_none_when_never_raised
- tests/unit/verify/test_quarantine.py::TestQuarantineStatusMarker::test_raised_after_raise
- tests/unit/verify/test_quarantine.py::TestQuarantineStatusMarker::test_cleared_after_clear
- tests/unit/verify/test_quarantine.py::TestQuarantineStatusMarker::test_cleared_after_retire_unidentifiable_findings
- tests/unit/verify/test_quarantine.py::TestQuarantineStatusMarker::test_stays_raised_when_retire_leaves_a_sibling_undisposed
designated_repro_test: null
acceptance:
- text: GIVEN a raised quarantine is cleared (via clear_quarantine or retire_unidentifiable_findings)
    WHEN a caller reads .frob/quarantine.status directly THEN it reads 'cleared',
    never the byte-identical-in-shape stale record misread as live; the marker reads
    'raised' only while genuinely raised
  evidence:
  - tests/unit/verify/test_quarantine.py::TestQuarantineStatusMarker::test_none_when_never_raised
  - tests/unit/verify/test_quarantine.py::TestQuarantineStatusMarker::test_raised_after_raise
  - tests/unit/verify/test_quarantine.py::TestQuarantineStatusMarker::test_cleared_after_clear
  - tests/unit/verify/test_quarantine.py::TestQuarantineStatusMarker::test_cleared_after_retire_unidentifiable_findings
  - tests/unit/verify/test_quarantine.py::TestQuarantineStatusMarker::test_stays_raised_when_retire_leaves_a_sibling_undisposed
- text: GIVEN frob verify status is run WHEN quarantine has been raised and then cleared
    THEN its output surfaces the same raised/cleared tombstone marker (quarantine_status_marker)
    that a direct disk read would show, never leaving the CLI's own report as the
    only place still ambiguous between stale and live
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-3065 (2026-08-26/27 field evidence, item c).

clear_quarantine's own contract keeps the cleared record on disk (never
deletes .frob/quarantine.json) as an audit trail -- see its docstring.
This means READING the raw file is not a read of quarantine STATE: a
stale cleared record (cleared_at set) is byte-identical in shape to a
live raised one (cleared_at is None), and only is_quarantined/frob
verify status (which check cleared_at) distinguish them. Hit live: read
the file, believed quarantine was raised, spent four failed disposal
commands before discovering it had already been cleared.

Investigated as part of T-3065 and explicitly NOT fixed there: dozens of
existing tests (tests/unit/test_rapid_sweep.py, tests/unit/verify/
test_verify_runner.py) assert load_quarantine returns the cleared record
(with cleared_at/cleared_reason/cleared_by populated) immediately after
clear_quarantine -- i.e. the file keeps existing and stays readable
after clear is itself a tested contract multiple call sites depend on,
not a small change riding on a bugfix.

Decide and implement one of:
  (a) delete .frob/quarantine.json on clear and move the record to a
      separate append-only history file (e.g.
      .frob/quarantine-history.json), so the LIVE file's bare existence
      is truthful on its face, and update every test/caller currently
      asserting load_quarantine's post-clear behavior against the
      single-file shape; or
  (b) leave the single-file persistence as-is but make cleared-vs-raised
      obvious without reading is_quarantined -- e.g. a companion
      .frob/quarantine.status file, or renaming the raised file to
      quarantine-cleared.json on clear (atomic rename, single source of
      truth stays load_quarantine's caller-visible contract).

Either way, say why in the Done report -- this ticket exists because the
file surviving on disk after clear is presented as an intentional
audit-trail design choice, and the fix must not silently regress that
intent while fixing the human-facing footgun.
