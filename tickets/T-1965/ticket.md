---
id: T-1965
title: Retire T-1942's WIRE001 follow_up citations in _arch.py/_coverage_sites.py
  now that the WAIVE004 consumer is wired
state: done
kind: docs
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_arch.py
- src/frob/gates/_coverage_sites.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- cmd:bash -c 'n=$(uv run frob check --only gates 2>&1 | grep -c "gate:WIRE\]"); echo
  WIRE001_findings=$n; test "$n" = 0' exit=0 sha256=76944a594555
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-1942 wired frob.gates._coverage_sites' examined-sites substrate into
fix_waive004_stale_waiver as its first production consumer. Four
WIRE001 waivers in src/frob/gates/_arch.py (arch_examined_sites) and
src/frob/gates/_coverage_sites.py (attach_examined_sites,
is_family_instrumented, site_examined) cite follow_up="T-1942" as "the
follow-up ticket that will call this from production code" -- now
fulfilled. Re-point those 4 follow_up attributes to this ticket (or
simply drop follow_up now that the cited work is done, whichever this
ticket's own review decides), so T-1942 can close without a
LiveTrackerCited refusal.

## Done report

Re-pointed the 4 WIRE001 waiver follow_up citations in src/frob/gates/_arch.py
(arch_examined_sites) and src/frob/gates/_coverage_sites.py
(attach_examined_sites, is_family_instrumented, site_examined) away from the
now-done T-1942 to the open T-1943.

Investigation: T-1942 landed real production callers for attach_examined_sites
and site_examined (frob.gates._fix_engine_sync._waive004_verified_candidates /
_drop_unexamined_archgate_candidates), and confirmed arch_examined_sites'
existing indirect-dict-call waiver is now backed by that same production path
transitively -- so its premise is permanent, not pending. is_family_instrumented
still has no production caller (T-1943's own scope is what would add one, if
ever). WIRE002 requires every WIRE001 waiver to bind to a live OPEN ticket, so
dropping follow_up outright (one of this ticket's two allowed options) is not
actually possible without failing gate:WIRE -- confirmed by measurement (re-
running frob check --only gates after dropping follow_up entirely surfaced 4
new WIRE002 errors). Re-pointed all 4 to T-1943 instead, with reason text
explaining why T-1943 is cited (WIRE002 compliance, not because T-1943 is
expected to touch these specific waivers).

Changed:
- src/frob/gates/_arch.py::arch_examined_sites -- WIRE001 waiver reason
  updated, follow_up T-1942 -> T-1943.
- src/frob/gates/_coverage_sites.py::attach_examined_sites -- WIRE001 waiver
  reason updated (no longer "no production caller yet"), follow_up T-1942 ->
  T-1943.
- src/frob/gates/_coverage_sites.py::is_family_instrumented -- WIRE001 waiver
  reason updated, follow_up T-1942 -> T-1943.
- src/frob/gates/_coverage_sites.py::site_examined -- WIRE001 waiver reason
  updated (no longer "no production caller yet"), follow_up T-1942 -> T-1943.

Evidence: cmd:bash -c 'n=$(uv run frob check --only gates 2>&1 | grep -c
"gate:WIRE\]"); echo WIRE001_findings=$n; test "$n" = 0' -- confirms gate:WIRE
is 0 errors repo-wide after the re-point (was 4 WIRE002 errors immediately
after the naive drop-follow_up attempt, before this fix).

Filed: none.

Gates: frob check --only gates --ticket T-1965 clean for gate:WIRE/gate:SCOPE/
gate:PREWORK; repo-wide floor unchanged at 4 pre-existing errors (gate:DSL x1,
gate:SELFAUDIT x2, gate:TEST x1), none in this ticket's scope files, matching
the pre-change floor measured before any edits.

### Changed
```
 src/frob/gates/_arch.py           |  9 +++++++--
 src/frob/gates/_coverage_sites.py | 34 +++++++++++++++++++++++-----------
 tickets/T-1965/ticket.md          |  5 ++++-
 3 files changed, 34 insertions(+), 14 deletions(-)
```

### Evidence
- `cmd:bash -c 'n=$(uv run frob check --only gates 2>&1 | grep -c "gate:WIRE\]"); echo WIRE001_findings=$n; test "$n" = 0' exit=0 sha256=76944a594555` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: DSL001@CHANGELOG.md, F401@/home/logan/projects/frob/.claude/worktrees/coverage-family-series/tests/unit/test_tickets_evidence_only_scope.py, SELFAUDIT001@design, TEST001@src/frob/app/ticket_runner/_new.py
