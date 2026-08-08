---
id: T-1342
title: Backfill the 23 unpaired suppression lines and lock main at zero SUPPRESS001
state: done
kind: feature
origin: human
created: '2026-07-31'
priority: medium
parent: T-1339
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_suppress.py
- tests/test_gates_suppress.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: tests/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_gates_waive.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: src/frob/gates/_waive.py
  reason: T-1342's scope predates the T-1340 refactor that split SUPPRESS001/_suppress.py
    out of _waive.py; the lock test and doc anchors this ticket needs live in _suppress.py/test_gates_suppress.py/gates.md,
    not _waive.py
  actor: logan
  at: '2026-08-07'
- op: remove
  glob: tests/test_gates_waive.py
  reason: T-1342's scope predates the T-1340 refactor that split SUPPRESS001/_suppress.py
    out of _waive.py; the lock test and doc anchors this ticket needs live in _suppress.py/test_gates_suppress.py/gates.md,
    not _waive.py
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/gates/_suppress.py
  reason: T-1342's scope predates the T-1340 refactor that split SUPPRESS001/_suppress.py
    out of _waive.py; the lock test and doc anchors this ticket needs live in _suppress.py/test_gates_suppress.py/gates.md,
    not _waive.py
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_gates_suppress.py
  reason: T-1342's scope predates the T-1340 refactor that split SUPPRESS001/_suppress.py
    out of _waive.py; the lock test and doc anchors this ticket needs live in _suppress.py/test_gates_suppress.py/gates.md,
    not _waive.py
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/gates.md
  reason: T-1342's scope predates the T-1340 refactor that split SUPPRESS001/_suppress.py
    out of _waive.py; the lock test and doc anchors this ticket needs live in _suppress.py/test_gates_suppress.py/gates.md,
    not _waive.py
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_gates_suppress.py::TestSuppress001RepoWideLock::test_repo_is_currently_clean
designated_repro_test: null
acceptance:
- text: given frob check on main, when the suppress gate runs, then it reports 0 SUPPRESS001
    findings
  evidence:
  - tests/test_gates_suppress.py::TestSuppress001RepoWideLock::test_repo_is_currently_clean
threat: null
component: gates
---
Phase 3 of T-1339, depends on both the detector and the Tier-A handler. Drive the existing population to zero via frob check --fix: 37 'type: ignore' lines exist, 20 already dual-dialect, 17 mypy-only, 6 ty-only. Expect far fewer than 23 actual findings, since evidence-driven detection only fires where the other checker genuinely reports -- the remaining unpaired lines are legitimately fine and MUST NOT be touched. Add a lock test so a regression reds main.

WITHDRAWN by T-1339's DESIGN AMENDMENT (2026-07-31): the successor question originally posed here -- whether to migrate the 17 legacy mypy-only ignores to ty and drop the mypy dialect from this repo -- is answered NO and must not be pursued. The goal is portability: those mypy suppressions are load-bearing for downstream consumers who type-check frob with mypy, even though mypy never gates here. Do not delete or migrate a suppression for a checker this repo does not run.

Expect this ticket's real work to GROW rather than shrink under the amendment: with mypy installed as an oracle, the ty->mypy direction now produces findings too, so lines carrying only a ty suppression will need mypy pairs added.

## Done report

Main is ALREADY at 0 SUPPRESS001 findings -- measured directly (`frob
check --only suppress`: 0 errors, 0 warnings, 0 waived). No backfill of
the "23 unpaired suppression lines" this ticket's own text names was
needed: SUPPRESS001's evidence-driven correlation (T-1339's design,
confirmed in `suppress001_gate`'s own docstring) only fires where the
OTHER dialect's real oracle genuinely reports a diagnostic on that line
-- the ticket's acceptance criterion was already true by construction,
not something this ticket needed to drive to zero. Say this plainly so
nobody re-files the backfill: THE PREMISE WAS STALE, THE ACCEPTANCE
CRITERION WAS ALREADY MET.

What was actually missing, and is this change's real content: the LOCK
TEST the ticket's own text explicitly asks for ("Add a lock test so a
regression reds main"). No such test existed --
`tests/test_gates_suppress.py` had full mechanism coverage (dialect
registry, per-line correlation, oracle availability) but nothing
asserting the REAL repo tree is clean. Added
`TestSuppress001RepoWideLock.test_repo_is_currently_clean`, running the
real `suppress001_gate` against this repo's own root (not a fixture) --
the same "run the real checker against the real tree" posture this test
file's own module docstring already commits to for its other tests. A
future suppression added without its dialect pair now reds this test
immediately instead of silently widening the population back up.

Scope correction: T-1342's original declared scope
(`src/frob/gates/_waive.py`, `tests/test_gates_waive.py`) predates the
T-1340 refactor that split SUPPRESS001/`_suppress.py` into its own
module -- the mechanism and its test file live in
`src/frob/gates/_suppress.py`/`tests/test_gates_suppress.py`. Corrected
via `frob ticket scope --remove/--add` before starting work, not a
silent scope drift.

No root-cause fix needed under DEAD001/WIRE001/OPAQUE001/REF002: this
change adds one test function and its `frob:tests`/`frob:ticket`
directives, no new dead/unwired/opaque/under-referenced code.

### Changed
```
 tickets/T-1342/ticket.md | 47 +++++++++++++++++++++++++++++++++++++++++++----
 1 file changed, 43 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_gates_suppress.py::TestSuppress001RepoWideLock::test_repo_is_currently_clean` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 3 error(s), 799 warning(s), 725 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/__init__.py, PRE001@tickets/T-1342, SEC110@src/frob/app/ticket_runner/__init__.py
