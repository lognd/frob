## Done report

Repro: committed tests/unit/test_unlanded_branch_work.py alone (e411743d1),
confirmed test_unlanded_has_no_second_implementation FAILS at that commit
via --check-repro (FAILED_AT_PARENT). Fixed in a separate commit
(12a972949).

Consolidation: frob.tickets._land._branch_changed_files is now THE single
implementation of "files this branch's own commits changed". It gained an
optional ref= parameter (default "HEAD", so every pre-existing _land.py
call site is byte-for-byte unaffected) so a caller can diff an arbitrary
branch name without checking it out. frob.tickets._unlanded._branch_own_
changed_files is now a thin delegate to it (root, "main", ref=branch),
converting the Result into the module's existing best-effort frozenset
contract on error -- it no longer runs its own git diff spawn, so it
cannot desync from the canonical implementation the way the hand-copied
twin already did once (T-1955 was exactly that: T-1922's fix landing a
second time, independently, in this second home).

Consumer audit (within this ticket's narrowed scope, _land.py and
_unlanded.py only): grepped _land.py for any two-dot ("..", not "...")
diff literal -- none found outside the deliberate T-1550 two-dot at
_land_git_ops.py:1329 (out of this ticket's scope, and per the ticket's
own "DO NOT FIX IT THIS WAY" guidance, that one is correct as-is, its
correctness depending on the T-1922 intersection). No further
branch-tip-two-dot instances found in the two consolidated files.
A repo-wide audit of every git diff call site outside src/frob/tickets/
_land.py and _unlanded.py was not performed -- out of this ticket's
narrowed scope; if the coordinator wants that wider sweep, it should be
its own ticket.

Verified: tests/unit/test_unlanded_branch_work.py (17/17 pass, including
the 3 new T-1966 tests). tests/test_ticket_land.py + tests/unit/
test_land_step_ordering.py (the other two consumers of
_branch_changed_files): 278 passed, 1 pre-existing failure
(TestLedgerV2LandMergeStory::test_same_ticket_conflict_surfaces_loudly_no_splice,
a ticket-ownership-lease assertion wholly unrelated to this change) --
confirmed pre-existing by running the identical test against the
pre-fix commit (b3d090934, this worktree's merge-main point) in a scratch
worktree: it fails identically there, with no _branch_changed_files/
_branch_own_changed_files code in the failure path at all.

### Changed
```
 src/frob/tickets/_land.py               | 34 ++++++++++----
 src/frob/tickets/_unlanded.py           | 49 ++++++++++----------
 src/frob/verify/_quarantine.py          | 65 +++++++++++++++++++++++++--
 tests/unit/test_unlanded_branch_work.py | 80 +++++++++++++++++++++++++++++++++
 tests/unit/verify/test_quarantine.py    | 62 +++++++++++++++++++++++++
 tickets/T-1966/ticket.md                | 37 +++++++++++++--
 tickets/T-2132/done-report.md           | 43 ++++++++++++++++++
 tickets/T-2132/ticket.md                | 37 +++++++++++++--
 8 files changed, 366 insertions(+), 41 deletions(-)
```

### Evidence
- `tests/unit/test_unlanded_branch_work.py::TestBranchOwnChangedFilesConsolidation::test_unlanded_has_no_second_implementation` (pytest node id, verified passing when recorded)
- `tests/unit/test_unlanded_branch_work.py::TestBranchOwnChangedFilesConsolidation::test_both_former_call_sites_agree_on_a_real_branch` (pytest node id, verified passing when recorded)
- `tests/unit/test_unlanded_branch_work.py::TestBranchOwnChangedFilesConsolidation::test_freshly_cut_branch_yields_empty_set` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/verify/_quarantine.py, DUP001@src/frob/verify/_quarantine.py, E402@/home/logan/projects/frob/.claude/worktrees/t2132-t1966/tests/test_ticket_leases.py, E501@/home/logan/projects/frob/.claude/worktrees/t2132-t1966/src/frob/tickets/_unlanded.py, E501@/home/logan/projects/frob/.claude/worktrees/t2132-t1966/src/frob/verify/_quarantine.py, PRE001@tickets/T-1966, SELFAUDIT001@design, TICK004@tickets.md
