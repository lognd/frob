## Done report

Continued the one-family-per-land split discipline (T-1186/T-1187/T-1188/
T-1189/T-1192) on `_land_merge.py`: extracted the ledger-merge/newest-wins
family named in the ticket body -- `splice_ledger`, `_merge_ledger_tickets`,
`_resolve_divergence`, `_newer`/`_newer_winner`/`_richness`,
`_union_evidence`/`_union_acceptance`, `_drop_resurrected_ids`,
`_preserve_sibling_done_reports`, `_carry_forward_new_worktree_tickets`,
`_overlay_landed_ticket`, `_splice_only_ticket` -- plus the `_STATE_RANK`/
`_TERMINAL_RANK` table and `_has_done_report` helper the family shares, into
a new `src/frob/tickets/_land_ledger_merge.py` (552 lines). Pure verbatim
move: every function keeps its original body, docstring, and
`frob:ticket`/`frob:tests`/`frob:invariant` directives unchanged.
`_land_merge.py` (1006 lines, was 1507) imports `splice_ledger`,
`_splice_only_ticket`, `_merge_ledger_tickets`, and `_has_done_report` back
for its own `_splice_and_stage`/`_splice_and_stage_archive`/
`_validate_closeable` use; `_land.py`'s re-export of `splice_ledger` is
unaffected (it still imports it from `_land_merge`, which now re-exports it
transitively).

Updated `frob:tests`/doc bindings that named the old location:
`docs/modules/tickets.md`'s `splice_ledger` `frob:describes` anchor now
points at `_land_ledger_merge.py`; `tests/test_ticket_land.py`,
`tests/test_tickets_collision.py`, and `tests/test_evidence_integrity.py`
import the moved private symbols from `_land_ledger_merge` instead of
`_land_merge`, and their `frob:tests` comment directives were repointed at
the new module path. Two hypothesis-property tests
(`TestNewerWinnerQualifiedPreferenceProperty`) and two guard tests
(`TestSpliceLedgerIdDropGuard`/`TestSpliceOnlyTicket`'s
`test_render_that_would_drop_an_id_is_refused`) that monkeypatch
`_render_ledger`/reference `_newer_winner` directly were repointed at the
`_land_ledger_merge` module object, since those symbols now live there.

Budget did not allow the git-plumbing/wip-commit family or the
`_land_finalize.py` split named in the ticket's residue list this land;
refiled the remaining residue (unchanged in substance) as
T-1251 per the T-1189/T-1192 precedent, since a fresh
implementer will need the same seam description.

Gates: `uv run frob check --ticket T-1194 --only gates-fast` -- 0 errors
after adding `frob:ticket T-1194` edges to the changed test classes/methods
COV002 flagged and expanding scope (`frob ticket scope T-1194 --add ...`)
to cover the new module, the three touched test files, and the doc anchor
edit. `uv run frob test --base main` -- `[PASS] python exit=0 10.28s`, 25
outcome(s) recorded, touched-set selection covering both moved-family
call sites and the archive/sibling/newer-winner property suites.
`uv run ruff check`/`ruff format --check` clean on both files.

### Changed
```
 tickets.md | 95 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 93 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestSpliceLedger::test_same_id_newer_state_wins` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceOnlyTicket::test_render_that_would_drop_an_id_is_refused` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard::test_render_that_would_drop_an_id_is_refused` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSiblingDoneReportPreserved::test_sibling_done_report_survives_landing_another_ticket` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestArchiveResurrection::test_archived_id_never_resurrected` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_takes_mains_content_edit_over_a_worktree_copy_unchanged_since_branch` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestNewerWinnerQualifiedPreferenceProperty::test_terminal_side_always_wins_over_non_terminal` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestNewerWinnerQualifiedPreferenceProperty::test_strictly_higher_rank_poorer_side_always_wins` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestNewerWinnerQualifiedPreferenceProperty::test_richer_side_wins_at_equal_or_lower_rank` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_id_title_mismatch_is_refused_not_silently_overwritten` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_same_id_same_title_still_resolves_via_newer` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: 0 error(s), 572 warning(s), 671 waived
- error-findings: none (measured, zero errors)
