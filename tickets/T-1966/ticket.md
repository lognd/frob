---
id: T-1966
title: 'One rule, two homes: ''files this branch''s own commits changed'' implemented
  twice and got wrong three times (T-1922, T-1955, T-1950)'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_unlanded.py
- tests/unit/test_unlanded_branch_work.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/
  reason: narrow whole-package scope to the two duplicated-function homes plus their
    test file, per T-1866 breadth guard
  actor: logan
  at: '2026-08-11'
- op: add
  glob: src/frob/tickets/_land.py
  reason: narrow whole-package scope to the two duplicated-function homes plus their
    test file, per T-1866 breadth guard
  actor: logan
  at: '2026-08-11'
- op: add
  glob: src/frob/tickets/_unlanded.py
  reason: narrow whole-package scope to the two duplicated-function homes plus their
    test file, per T-1866 breadth guard
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tests/unit/test_unlanded_branch_work.py
  reason: narrow whole-package scope to the two duplicated-function homes plus their
    test file, per T-1866 breadth guard
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_unlanded_branch_work.py::TestBranchOwnChangedFilesConsolidation::test_unlanded_has_no_second_implementation
- tests/unit/test_unlanded_branch_work.py::TestBranchOwnChangedFilesConsolidation::test_both_former_call_sites_agree_on_a_real_branch
- tests/unit/test_unlanded_branch_work.py::TestBranchOwnChangedFilesConsolidation::test_freshly_cut_branch_yields_empty_set
designated_repro_test: tests/unit/test_unlanded_branch_work.py::TestBranchOwnChangedFilesConsolidation::test_unlanded_has_no_second_implementation
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
REPEATED-MISTAKE AUDIT (2026-08-10). The concept "which files did THIS
BRANCH'S OWN COMMITS change" has been implemented independently at least
twice and got wrong twice, each time in a different consumer, each time
fixed locally without consolidating.

THE DUPLICATION, measured:
  src/frob/tickets/_land.py:2668      def _branch_changed_files(...)
  src/frob/tickets/_unlanded.py:144   def _branch_own_changed_files(...)
plus a consumer, src/frob/tickets/_land.py:2182
  def _restrict_to_branch_own_files(...)

`_unlanded.py`'s own docstring says it mirrors `frob.tickets._land`'s --
so the second was written with the first in view and still copied rather
than imported. Two homes for one rule is a desync waiting to happen; here
the desync already happened twice before the second home even existed.

THE THREE INSTANCES OF THE UNDERLYING CONFUSION:
1. T-1550 -> T-1922. `_committed_waive_deletions` diffs `base_ref..HEAD`
   two-dot from main's LIVE TIP (deliberately, to fix T-1225/T-1444's
   sibling re-attribution). That reintroduced false refusals when main
   reworded a waiver on a file the branch never touched; T-1922 fixed it
   by intersecting against `_branch_changed_files` (three-dot).
2. T-1955. `_finished_signals_on_branch` built its candidate list from
   `git ls-tree -r <branch>`, which lists everything REACHABLE from the
   tip. Since every branch is cut from main, every branch inherited
   main's entire finished-ticket history -> 216 false positives (4
   tickets x 77 branches), including branches cut minutes earlier. Fixed
   by adding `_branch_own_changed_files` -- a second copy of (1)'s fix.
3. T-1950. LAND-PROOF and scripts/verify_lands.py check commit ANCESTRY
   and ticket state, never whether the commit contains the ticket's own
   changes. Two confirmed instances now: T-1720 (its code rode in on
   T-1922's commit) and T-1951 (landed with `rapid-debt.jsonl` +1 as its
   entire commit; the fix rode in on T-1954's).

All three are the same mistake in different clothes: confusing "what is
reachable from / differs against a ref" with "what this branch's own
commits actually did".

DO NOT FIX IT THIS WAY:
- Do NOT add a lint banning two-dot diffs. `A...B` is exactly
  `merge-base(A,B)..B`, so the existing `{merge_base}..HEAD` call sites
  (e.g. _land_git_ops.py:1123, _land_squash.py:530) are CORRECT and a
  naive ban would flag them while missing the real bug shape, which is a
  two-dot whose LEFT OPERAND IS A BRANCH TIP.
- Do NOT mechanically rewrite T-1550's deliberate two-dot at
  _land_git_ops.py:1329 to three-dot. Its docstring explains why it uses
  main's live tip, and reverting that reintroduces T-1225/T-1444. Its
  correctness now depends on the intersection T-1922 added -- that
  coupling is exactly what belongs in one documented helper.

FIX DIRECTION: one shared, named helper for "files this branch's own
commits changed", imported by every consumer, whose docstring states the
three-dot semantics and the T-1550 interaction once. Delete the duplicate.
Then audit remaining consumers for the branch-tip-two-dot shape and report
the set, fixing only those that are genuinely wrong.

ACCEPTANCE: first test must FAIL before the fix -- assert only one
definition of the concept exists in src/ (the duplicate makes it fail).
Then assert both former call sites produce identical results on a branch
with commits on both sides of the merge-base, and that a freshly-cut
branch yields the empty set from the shared helper.

<!-- frob:waive BUG002 reason="the fix itself already landed on main as an acknowledged passenger of T-2132's land (commit 183f59675edb, same series worktree, --allow-cross-ticket used deliberately) -- this ticket's own close now has no un-landed diff, so its designated repro (tests/unit/test_unlanded_branch_work.py::TestBranchOwnChangedFilesConsolidation::test_unlanded_has_no_second_implementation) correctly PASSES at main's current tip: the defect it names is already fixed there, not still present. The repro genuinely FAILED at its own pre-fix commit (e411743d1) before that land, exactly as required by BUG002/T-1929's --check-repro gate at the time evidence was bound; the check now sees a main whose parent already contains the fix (T-1950's own documented limitation for a squash-landed passenger, referenced in this ticket's own body) and there is no way to re-derive a genuine pre-fix ref for a close-time check after the code has already shipped." -->

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
