---
id: T-1966
title: 'One rule, two homes: ''files this branch''s own commits changed'' implemented
  twice and got wrong three times (T-1922, T-1955, T-1950)'
state: in-progress
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
