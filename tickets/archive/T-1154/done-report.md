## Done report

Fixed the wrong-side-merge corruption class (3rd occurrence) at its root
cause: `_merge_ledger_tickets`'s per-id tiebreak.

`_newer`'s tier-3 fallback (used when two same-id ledger/archive entries
tie on state-rank and richness) used to arbitrarily prefer `theirs`. A
same-id content edit that changes neither state nor evidence/acceptance
count (e.g. T-1143's evidence-path text migration inside an already-done
archived block) ties on both, so a worktree whose own copy was merely
stale (never touched since the branch point) could still beat main's
real edit purely because it happened to land on the `theirs` side of
that tie -- exactly what happened in T-1145's land (bc834b95), which
reverted T-1143's migration.

Added `_resolve_divergence(ours, theirs, base)`: when the true 3-way
merge-base ticket is available, whichever side is BYTE-IDENTICAL to
`base` made no deliberate edit and has no claim on the id -- the side
that DID change wins outright, before ever falling back to `_newer`.
Only a genuine two-sided divergence (both sides changed from base)
still falls through to the existing state-rank/richness tiebreak,
unchanged.

Threaded a `base` param through `_merge_ledger_tickets`, a `base_text`
param through `splice_ledger` and `_splice_and_stage_archive`, and wired
`_merge_main_into_worktree` to resolve the true `git merge-base` (via
`_true_merge_base` + the new `_read_text_at_ref` helper) and pass its
`tickets-archive.md` content through -- the archive splice is the one
exposed to this class since, unlike `tickets.md`'s own splice, it is
NOT scoped to the single ticket id being landed (T-0479's `ticket_id`
scoping already structurally protects tickets.md's sibling ids from
this exact bug).

`splice_ledger`'s own `base_text` param is plumbed but not yet wired
into the `frob ticket merge-driver` CLI entry point
(`src/frob/app/ticket_runner/_land_cmd.py::_merge_driver`) -- that file
is outside this ticket's declared scope (`src/frob/tickets/**`). Git's
merge-driver protocol already hands the merge-driver its own %O
(merge-base) argument, currently read but unused, so wiring it through
is a small follow-up; filed as residue below. Note this file's own
live incident during this ticket's own warm-up `git merge main`: the
STALE globally-installed `frob ticket merge-driver` (bare `frob`, not
`uv run frob`, per `.git`'s configured merge driver command) resolved a
real tickets.md conflict and reverted T-1111 from `done` back to
`queued` in this worktree via exactly the unfixed tie-break this ticket
closes -- caught before finalizing by the standard `git diff main --
tickets.md` scope check, repaired via the section-10b ledger-restore
recipe (not by hand-editing). This is independent live confirmation the
bug class is real and still reachable via the merge-driver path, which
is exactly why the merge-driver wiring is filed as follow-up rather
than silently left undone.

Added `TestArchiveSpliceDiscipline::
test_land_takes_mains_content_edit_over_a_worktree_copy_unchanged_since_branch`,
an end-to-end `land()` regression test with the real two-sided shape:
an archived ticket, same state and richness on both sides, main makes a
genuine content edit while the worktree's copy sits untouched since
branch. Verified it actually catches the regression by temporarily
disabling the fix (`base = None` in `_resolve_divergence`) and
confirming the test fails, then restored the fix and reconfirmed green.

### Changed
```
 docs/modules/tickets.md   |  16 ++-
 frob.lock                 |  10 ++
 src/frob/tickets/_land.py | 121 +++++++++++++++++++++--
 tests/test_ticket_land.py |  75 +++++++++++++-
 tickets.md                | 242 +++++++++++++++++++++++++++++++++++++++++++++-
 5 files changed, 448 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_takes_mains_content_edit_over_a_worktree_copy_unchanged_since_branch` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_splice_and_stage_archive_merges_by_id_never_overwrites` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_splice_and_stage_archive_refuses_when_authoritative_id_would_vanish` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestArchiveResurrection::test_archived_id_never_resurrected` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceLedger::test_malformed_ours_propagates_as_err` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceLedger::test_malformed_theirs_propagates_as_err` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceLedger::test_same_id_newer_state_wins` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceOnlyTicket::test_whole_ledger_splice_never_regresses_a_sibling_from_done` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_preserves_mains_newly_archived_blocks_over_a_stale_worktree_archive` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 13 error(s), 1023 warning(s), 436 waived
- error-findings: ARCH001@src/frob/tickets/_land.py, E501@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/doctor.py:243, E501@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/vet/_supplychain.py:295, F401@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/tickets/__init__.py:111, F401@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/tickets/__init__.py:22, F401@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/tickets/__init__.py:23, F401@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/tickets/__init__.py:35, F401@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/tickets/__init__.py:46
