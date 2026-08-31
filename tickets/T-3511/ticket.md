---
id: T-3511
title: Re-measure Windows suite to completion after the five primitive fixes
state: done
kind: docs
origin: human
created: '2026-08-30'
priority: medium
blocked_by:
- T-3506
- T-3507
- T-3508
- T-3509
- T-3510
parent: T-3505
tier: ticket
sprint: null
runs_last: false
milestone: 1.0.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/design/windows-portability.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: kind
  old_value: bug
  new_value: docs
  reason: measurement/triage ticket, docs-only scope per its own FILES IN SCOPE note
    (docs/design/windows-portability.md), no source diff -- allows --evidence-cmd
    close
  actor: logan
  at: '2026-08-31'
evidence:
- cmd:grep -n 'Re-measurement after the five primitive fixes' docs/design/windows-portability.md
  exit=0 sha256=a4d277d50889
kind_history:
- 2026-08-31 bug->docs evidence=0 done_report=yes
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 15cfc5e39421c30556c40f9ffe649db1bca2ea6f
---
Re-run the Windows test suite to completion after the five primitive
fixes (T-3506 fcntl, T-3507 os.sysconf, T-3508 AF_UNIX, T-3509 fork
context, T-3510 charmap) land, and re-cluster whatever remains.

WHY: T-3076's own measured run (33035660969) was INTERRUPTED
(exitstatus=2, not a clean pass/fail), so 365-failed / 278-windows-only
is a floor observed mid-interrupt, not a stable number. T-3076
explicitly says the large downstream buckets --
  33  assert False
  16  assert None is not None
  11  SystemExit: 1
  11  AssertionError: assert False
  10  AssertionError: assert None is not None
   8  AssertionError: PerfError.SpawnFailed
-- are "almost certainly downstream of the same five [primitives] and
should be re-measured AFTER they are addressed rather than triaged
independently". This leaf is that re-measurement -- do not guess at
what remains; run it and read the real numbers.

WORK
- Trigger (or wait for) a windows-latest CI run on a commit containing
  all five primitive fixes; if it still cannot COMPLETE (exitstatus=2
  INTERRUPTED again), that non-completion is itself the finding to
  characterize (per T-3076's own acceptance criterion) -- do not treat
  a second interrupt as "close enough".
- Record the new stable failed-count and re-cluster by root cause and
  by file, the same shape T-3076 used, so it is directly comparable.
- For anything still failing that is NOT one of the five primitives,
  file new leaf ticket(s) under T-3505 (this epic) -- do not silently
  fold new work into this ticket's own scope; this ticket's job is
  measurement, not further fixing.
- Update T-3076 itself with the re-measured, stable count as its
  closing acceptance evidence.

FILES IN SCOPE
  docs/design/windows-portability.md (record the re-measured baseline)
  (no source files -- this is a measurement/triage ticket; it must not
  hold write scope over fix targets it doesn't touch)

MUST-FIRE
- A COMPLETED (non-interrupted) windows-latest run's stable failure
  count is recorded, replacing the interrupted 278/365 numbers as the
  reference baseline.
- Any residual failures are triaged into new, filed tickets under
  T-3505, each with its own precise scope -- none left unticketed.

MUST-STAY-QUIET
- This ticket makes no source changes; a diff on this ticket touching
  anything under src/ is out of scope.

BLOCKED BY: T-3506, T-3507, T-3508, T-3509, T-3510 -- must run after
all five primitives land, since the whole point is measuring their
combined effect, not each one's effect in isolation.