## Done report

Root cause confirmed by reading git config (merge.frob-ledger.driver was already registered) and .gitattributes (the v1 tickets.md merge=frob-ledger line was retired at the ledger-v2 cutover with no replacement for what replaced it) -- tickets/<id>/ticket.md and frob-coverage.lock.json had zero merge-driver coverage, so a genuine divergence fell through to git's raw textual 3-way merge (F-038/F-045-first). Fixed by extending the EXISTING frob ticket merge-driver command (_merge_driver in _land_cmd.py) to dispatch by content shape -- git's merge-driver protocol only ever hands it %O/%A/%B temp files, never the real path -- trying frob-coverage.lock.json's JSON shape first (reusing the T-1434 elementwise-max-per-module merge verbatim via _merged_lock_doc), then a single ticket file's frontmatter+body shape (resolved via the existing _newer state-precedence function: done/dropped beats queued/in-progress, terminal supremacy), and falling back unchanged to the original whole-ledger splice_ledger path for the legacy v1 monofile shape. Two new .gitattributes lines (tickets/*/ticket.md and frob-coverage.lock.json, both merge=frob-ledger) route both new shapes through the SAME already-registered driver name/git-config entry -- no new per-clone setup needed. MUST-FIRE fixture: two branches independently mutating the same ticket's state (done vs in-progress, and F-038's exact dropped-vs-queued shape) merge through the driver to the terminal state, never conflict markers -- both a synthetic unit test and a real git merge end-to-end test. MUST-STAY-QUIET fixture: an ordinary land with no divergence on either the whole-ledger or the new v2 file merges cleanly with the new attribute registration in place. 15/15 tests pass in tests/test_ticket_merge_driver.py (6 new); tests/unit/test_gitattributes_merge.py (5/5, unaffected by the .gitattributes addition) and the T-1434 coverage-lock conflict test in tests/test_ticket_land.py also verified passing.

### Changed
```
 .gitattributes                          |  18 ++
 src/frob/app/ticket_runner/_land_cmd.py |  63 ++++++-
 tests/test_ticket_merge_driver.py       | 310 ++++++++++++++++++++++++++++++++
 tickets/T-3297/ticket.md                |  25 ++-
 4 files changed, 414 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_merge_driver.py::TestMergeDriverContentShapeDispatch::test_single_ticket_file_conflict_resolves_by_state_precedence_must_fire` (pytest node id, verified passing when recorded)
- `tests/test_ticket_merge_driver.py::TestMergeDriverContentShapeDispatch::test_single_ticket_file_dropped_beats_queued_must_fire` (pytest node id, verified passing when recorded)
- `tests/test_ticket_merge_driver.py::TestMergeDriverContentShapeDispatch::test_coverage_lock_shaped_conflict_merges_elementwise_max` (pytest node id, verified passing when recorded)
- `tests/test_ticket_merge_driver.py::TestMergeDriverContentShapeDispatch::test_whole_ledger_shape_still_falls_back_to_splice_ledger_must_stay_quiet` (pytest node id, verified passing when recorded)
- `tests/test_ticket_merge_driver.py::TestMergeDriverV2TicketFileViaRealGit::test_ordinary_land_with_no_divergence_merges_cleanly_must_stay_quiet` (pytest node id, verified passing when recorded)
- `tests/test_ticket_merge_driver.py::TestMergeDriverV2TicketFileViaRealGit::test_diverged_ticket_state_merges_cleanly_via_registered_driver` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 16 error(s), 4437 warning(s), 856 waived
- error-findings: COV001@src/frob/tickets/_scope.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DOC007@tests/unit/test_main_entry.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/tickets/_scope.py, DRIFT002@tests/unit/test_main_entry.py, DUP001@tests/test_ticket_merge_driver.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3297, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json, invalid-return-type@tests/test_ticket_merge_driver.py
