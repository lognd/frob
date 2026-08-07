## Done report

SILENT LEDGER DATA LOSS, root-caused and fixed. `frob ticket land`'s
squash-apply (`_splice_only_ticket`, T-0479) unconditionally took every
SIBLING ticket's ledger section from main, discarding any edit a worktree
made to a DIFFERENT ticket's own section while landing one ticket -- no
error, no warning, three consecutive silent drops of the same legitimate
edit (T-1637's evidence rebind, dropped by T-1679's land, T-1714's land,
and T-1706's land in turn) before the pattern was diagnosed as structural.

ROOT CAUSE, precisely: T-0479's own scoping (`merged = dict(main_tickets)`,
overlay ONLY the landing ticket's block) is correct as a defense against a
worktree's STALE sibling state resurrecting on main (T-0475) -- but it
cannot tell "stale" from "a real, deliberate edit" because it never looks
at what either side actually changed, only at what the CURRENT state is.
T-0577 added ONE narrow exception (`_preserve_sibling_done_reports`, keep
the worktree's copy when it has a Done report main lacks) after a Done
report went missing; that exception did not generalize to arbitrary
content because it was built to close the one incident shape it had
evidence for, not the general class. T-1154 threaded a true-merge-base
3-way comparison into the ARCHIVE splice for this same class of problem --
but that fix's own docstring explicitly reasoned tickets.md's splice "does
not need this" because T-0479-scoping "already makes every sibling id
come from main_text untouched". That reasoning is a correct description
of the mechanism and a wrong justification: the untouched-by-default IS
the defect, not evidence base-awareness is unnecessary.

FIX. `_carry_forward_or_refuse_sibling_edits` (`_land_ledger_merge.py`)
replaces the narrow Done-report-only exception with a full base-aware
3-way comparison, threaded into BOTH `_splice_and_stage` call sites (the
pre-squash `_merge_main_into_worktree` merge AND the squash-apply
`_squash_and_splice_ledger` -- the actual final-landing site): for each
sibling id, compare main's current copy, the worktree's copy, and the
common merge-base's copy (`_true_merge_base` + `_read_text_at_ref`, the
SAME primitives T-1154 already established for the archive file).
Worktree-only edits carry forward; main-only edits are left alone
(unchanged, already-correct T-0479 behavior); both-sides-converged is a
silent no-op; BOTH SIDES CHANGED TO DIFFERENT CONTENT REFUSES
(`Err(TicketError.SiblingLedgerEditConflict)` /
`LandError.SiblingLedgerEditConflict`) rather than silently picking a
side, naming the conflicting id -- per the explicit design constraint:
silently choosing was the bug, not which side got chosen. `base_text=None`
(git could not resolve the merge-base) degrades to the pre-fix
Done-report-only heuristic unchanged, never a hard failure.

Deliberately did NOT add "raw content diff" as a fourth tiebreak
heuristic alongside `_newer`'s existing state-rank/richness comparison --
that would only move the arbitrariness, not remove it. The fix instead
answers a DIFFERENT, decidable question (did each side change since a
common base?) that `_newer`'s two-way, base-unaware comparison structurally
cannot ask.

VERIFIED END TO END, not just at the primitive level: `TestLand::
test_sibling_evidence_rebind_carried_forward_end_to_end` reproduces the
real T-1637 field incident through the actual `land()` entry point --
ticket B already DONE on main, rebind B's evidence in the SAME worktree
that lands ticket A, assert B's rebind survives on main after `land()`
returns. Passed on first attempt. Five more unit-level tests
(`TestCarryForwardOrRefuseSiblingEdits`) cover each branch of the 3-way
decision table directly against `_splice_only_ticket`, including the
refusal case and the no-base-available degrade path.

Also fixed, live, while verifying this ticket: my OWN worktree's local
`tickets.md` had accumulated a duplicate/stale T-1637 evidence entry from
an earlier abandoned repair attempt, resurrected by the registered ledger
merge-driver's `_union_evidence` logic during a `git rebase main` -- caught
by re-diffing against main post-rebase, fixed by writing main's exact
clean ticket record locally before continuing. Documents that the
registered merge-driver's own union-on-divergence behavior (a DIFFERENT
code path from this ticket's land-time fix) can also produce this shape
under the right conditions -- worth knowing, not itself part of this
ticket's fix.

Full unscoped `frob check --land-parity`: clean, 0 unscoped errors (the
`docs/audits/docs-completeness-2026-08-06.md`/`_evidence.py`/
`test_ticket_work_and_land_finish.py` T-1685 baseline, excluded as
checkpoint-artifact exempt per the same land-parity run, is the only
thing outside this ticket's own diff).

### Changed
```
 docs/modules/tickets.md                |  85 ++++++-
 src/frob/tickets/_land_git_ops.py      |  91 +++++--
 src/frob/tickets/_land_ledger_merge.py | 215 +++++++++++++++--
 src/frob/tickets/_land_squash.py       |  35 ++-
 src/frob/tickets/_models.py            |  30 +++
 tests/test_ticket_land.py              | 254 +++++++++++++++++++-
 tickets.md                             | 427 ++++++++++++++++++++++++++++++++-
 7 files changed, 1082 insertions(+), 55 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestCarryForwardOrRefuseSiblingEdits::test_worktree_only_edit_is_carried_forward` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestCarryForwardOrRefuseSiblingEdits::test_main_only_edit_is_left_alone` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestCarryForwardOrRefuseSiblingEdits::test_both_sides_edit_the_same_way_converges_silently` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestCarryForwardOrRefuseSiblingEdits::test_both_sides_edit_differently_refuses` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestCarryForwardOrRefuseSiblingEdits::test_no_base_available_falls_back_to_done_report_heuristic` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLand::test_sibling_evidence_rebind_carried_forward_end_to_end` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 496 warning(s), 721 waived
- error-findings: none (measured, zero errors)
