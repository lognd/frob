## Done report

Confirmed T-1958 (the blocker named in this ticket's own title) is
[done] before starting -- not left in a state that would repeat the
original ScopeLeaseConflict.

Added the WAIVE004 Tier-A fix-handler writeup near the existing
T-1579/T-1592/T-1904 incident section (docs/modules/gates.md), covering
the three points the ticket asked for: attach_examined_sites enriching
the self-manufactured run_gates() report before candidates are derived,
_drop_unexamined_archgate_candidates as a third additive guard gated on
archgate-family rule ids only, and the regression test
tests/test_gates.py::TestWaive004ExaminedSitesGuard (in particular
test_original_55_waiver_incident_shape_partial_examination_still_refuses,
the original incident's shape narrowed to per-site).

Also refreshed two now-stale cross-references discovered while placing
the new paragraph: the "T-1904, not yet built" line in the mass-
invalidation section, and the GateStats `examined_sites` docstring's
"NOT wired into WAIVE004 ... by this substrate" claim -- both predate
T-1942 and would otherwise mislead the next reader into re-deriving
what T-1942 already built.

check-repro note (per coordinator instruction to run it before landing):
the bound evidence test
(TestWaive004ExaminedSitesGuard.test_original_55_waiver_incident_shape_partial_examination_still_refuses)
reports PASSED_AT_PARENT / confirmatory-only. Expected and correct for
this docs-kind ticket -- no behavior changed, the test already covers
T-1942's existing code; BUG002/--check-repro's refusal targets bug-kind
repro designation, not a docs citation of an already-passing regression
lock.

Separately disclosed, NOT this ticket's scope: while running a scoped
`frob check --ticket T-1964`, found and restored 5 uncommitted ticket
files in this worktree (T-1988, T-1998 x2, T-2000, T-2008, T-2022) whose
on-disk content had diverged from my own last commit -- a detached
background sweep process (T-1983-shaped) appears to write directly into
a concurrent agent's worktree. Restored via `git checkout HEAD --
<files>` (verified content-identical to main afterward) and filed as a
critical bug (T-2030) with full reproduction detail rather
than fixed here, since the writer is out of this ticket's declared
scope.

### Changed
```
 docs/modules/gates.md              | 55 +++++++++++++++++++++++++---
 tickets/T-1964/ticket.md           |  6 ++-
 tickets/T-1988/ticket.md           |  7 +++-
 tickets/T-2022/ticket.md           |  7 +++-
 tickets/T-2030/ticket.md | 75 ++++++++++++++++++++++++++++++++++++++
 5 files changed, 139 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestWaive004ExaminedSitesGuard::test_original_55_waiver_incident_shape_partial_examination_still_refuses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH103@src/frob/app/ticket_runner/_query.py, F401@/home/logan/projects/frob/.claude/worktrees/t1969-series/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t1969-series/tests/unit/test_tickets_evidence_only_scope.py
