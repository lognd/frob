## Done report

Extended the T-0811 draft-id-renumber prose rewrite (`_rewrite_draft_references_in_bodies`, ledger bodies only) to cover WAIVE-site channels that were still exempt: `design/*.strata` `waive ... ticket "T-draft-..."` clauses and source `frob:waive ... ticket=T-draft-...` comments. Left as-is, WAIVE007's unconditional `T-draft-*` exemption would silently become load-bearing for these sites once their draft id is renumbered at land (the original T-draft-8cd37914 incident class), since a waiver would never be re-litigatable again.

Added `_rewrite_draft_references_in_waive_sites` in `src/frob/tickets/_land.py`, called from `_land_finalize_and_close` right after the existing ledger-body rewrite and before `_commit_finalize_writes` (which `git add -A`s and commits any working-tree changes it made, so the new rewrite lands atomically in the same finalize commit, before the squash-apply). It reuses the identical fixed-width-token regex approach from T-0811 (`(?:old-id|old-id|...)(?![0-9a-fA-F])`), but scopes the file set cheaply via `git grep -l --fixed-strings -e <old_id> ...` against the worktree -- only files that literally contain an old draft id are ever opened, and the ledger files (`tickets.md`/`tickets-archive.md`) are excluded from this raw-text pass since they are already handled by the ticket-model-driven `_rewrite_draft_references_in_bodies`.

Also added the T-0811 reviewer's missing negative test as a SEPARATE test (not folded into the existing blanket "zero T-draft- ids in the ledger" assertion, since planting an unrelated draft id in that same test would conflict with that assertion): an unrelated draft id mentioned in ledger prose survives a land untouched.

Deviations from the ticket body: none. Both waive-site channels (.strata clauses and frob:waive comments) are covered, plus the reviewer's negative test, as scoped.

### Changed
(no changed files detected)

### Evidence
- `tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_rewrites_strata_waive_clause_draft_id_reference` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_rewrites_frob_waive_comment_draft_id_reference` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_leaves_unrelated_draft_id_reference_untouched` (pytest node id, verified passing when recorded)
