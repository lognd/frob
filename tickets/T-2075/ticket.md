---
id: T-2075
title: Split _commit_orphaned_new_ticket_dir_only_drift/_refuse_if_main_dirty under
  ARCH001's threshold
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
evidence_scope:
- tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDrift::test_well_formed_orphaned_dir_is_committed
- tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_two_well_formed_orphaned_dirs_are_both_committed
- tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestRefuseIfMainDirtyOrphanedTicketHeal::test_orphaned_ticket_dir_no_longer_refuses
- tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestRefuseIfMainDirtyOrphanedTicketHeal::test_genuinely_human_dirty_root_still_refuses
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2026's own land (and T-2046's widening) grew _commit_orphaned_new_ticket_dir_only_drift to 95 lines and _refuse_if_main_dirty to 74, both past ARCH001's 60-line threshold -- ERRORS on the unscoped floor, not warnings. Genuine seam: validate-candidates (_orphaned_new_ticket_dir_candidates) vs stage-and-commit for the first; apply-auto-heals (_apply_dirty_main_auto_heals) vs decide-refuse for the second -- same split shape the repo's own precedent (_orphaned_evidence_findings pure-data vs _refuse_orphaned_evidence action) already uses.

frob:no-behavior-change reason="pure function-extraction split of two ARCH001-flagged functions into a validate/apply half and an act/decide half; control flow verified unchanged line-by-line against the pre-split diff (every early return preserved via the same Result/bool shape), and the existing T-2026/T-2046 orphaned-ticket-dir test suite (13 tests) plus the DirtyMain-heal subset of test_ticket_land.py (5 tests) all pass unchanged -- no new behavior, only a line-count-driven seam"

## Done report

Reviewed the pre-existing commit (1b115834f, made by a prior agent that died
on context before landing) on its merits, not blindly: split
_commit_orphaned_new_ticket_dir_only_drift into a pure validate half
(_orphaned_new_ticket_dir_candidates) and a stage-and-commit half
(unchanged name, now thin), and split _refuse_if_main_dirty into an
apply-auto-heals half (_apply_dirty_main_auto_heals) and a decide-refuse
half (unchanged name). Control flow is preserved exactly -- confirmed by
reading the diff line by line: every early return in the original became
an early return via the same Result/bool shape in the split function, no
branch was added, removed, or reordered.

The cross-worktree lease this agent was blocked on (T-2055) has since
landed, so the split was free to land. Re-measured on the CURRENT merged
main (not the stale base the split was written against): `frob check
--only archgate --json` shows both _land.py findings for this file are
note/warning severity (the pre-existing waived _land_locked orchestrator,
and a LARGE001 file-size warning) -- zero error-severity ARCH001 findings
remain for src/frob/tickets/_land.py. The 4 error-severity ARCH001
findings the same run reports are in unrelated files
(_query.py, _rapid_sweep.py), not in scope here.

Ran the full existing test suite for both split functions --
tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py (13 tests) plus
the orphan-marked subset of tests/test_ticket_land.py (5 tests) -- all
pass, 0 failures.

Item 2 (PERF004 sorted() in the same file) was already fixed by a
concurrent agent under T-2046/T-draft-a3e1ea29 and merged in via `git
merge main`; confirmed absent from the merged tree (grep for the old
`sorted(...)` call returns nothing). Not touched here to avoid two agents
editing the same line.

### Changed
```
 src/frob/tickets/_land.py          | 195 +++++++++++++++++++++++--------------
 tickets/T-2075/ticket.md |  31 ++++++
 2 files changed, 153 insertions(+), 73 deletions(-)
```

### Evidence
- `tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDrift::test_well_formed_orphaned_dir_is_committed` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_two_well_formed_orphaned_dirs_are_both_committed` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestRefuseIfMainDirtyOrphanedTicketHeal::test_orphaned_ticket_dir_no_longer_refuses` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestRefuseIfMainDirtyOrphanedTicketHeal::test_genuinely_human_dirty_root_still_refuses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH103@src/frob/app/ticket_runner/_query.py, COV001@src/frob/strata/_claims.py, DOC002@src/frob/strata/_claims.py
