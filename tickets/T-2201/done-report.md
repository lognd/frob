## Done report

Changed:
- src/frob/app/ticket_runner/_land_cmd.py::_frob_directive_block -- now takes
  an optional genuine_comment_lines set (frob.tickets._land._genuine_comment_lines,
  T-2183's machinery) and stops the walk the instant a "#"-looking line above
  the def is NOT a real grammar comment, instead of trusting the text prefix
  alone.
- src/frob/app/ticket_runner/_land_cmd.py::_new_public_symbols_missing_doc_or_test_edge
  -- resolves the current worktree file's genuine comment lines and passes
  them through to _frob_directive_block; the hardcoded has_doc/has_tests
  boolean pair is replaced by a loop over a new data table,
  _DOC_TEST_EDGE_FAMILIES (label, directive, waive_rule) triples, returning
  a list of missing family labels instead of two booleans -- a future family
  is now a one-line table append, not a third copy of the pattern T-1907 and
  T-2114 each wrote independently.
- src/frob/app/ticket_runner/_land_cmd.py::_assert_new_public_symbols_have_doc_and_test_edge_pre_land
  -- updated to consume the new list[str] shape (missing_families) instead
  of the old (missing_doc, missing_tests) booleans; refusal message
  unchanged in spirit (still names every missing family).

Evidence:
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_directive_looking_line_inside_a_docstring_does_not_satisfy_the_gate
  (DESIGNATED REPRO, BUG002) -- new test proving a frob:doc/frob:tests-shaped
  line that is actually string-literal content (a multi-line string, not a
  grammar comment) directly above a new public def no longer satisfies the
  gate. Checked FAILED_AT_PARENT against 9471779e1 (the repro committed
  alone, before the fix): `uv run frob ticket evidence T-2201 --check-repro
  ... --base-ref 9471779e1` -> "FAILED_AT_PARENT: ... genuinely fails ...
  this is what BUG002 wants". Watched fail directly too:
  `pytest ... -o addopts=""` -> "Failed: DID NOT RAISE <class 'SystemExit'>"
  against the pre-fix code.
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::{test_a_new_public_symbol_with_no_edges_refuses_the_land,test_a_new_public_symbol_with_both_edges_does_not_refuse,test_an_unrelated_land_touching_no_new_public_symbols_is_unaffected,test_empty_touched_set_is_a_no_op,test_cli_land_end_to_end_refuses_a_worktree_with_a_new_undocumented_symbol}
  -- pre-existing T-2114 coverage, re-run and passing against the
  refactored/parameterized code path (acceptance [1]'s parameterization is
  exercised by every one of these, since they all go through
  _DOC_TEST_EDGE_FAMILIES now instead of the old hand-written pair).

Measured: `pytest tests/test_ticket_work_and_land_finish.py -o addopts="" -q`
-> "SUITE-RESULT: exitstatus=0 collected=60 failed=0" (60 passed, no
regression across the whole file). `uv run ruff check
src/frob/app/ticket_runner/_land_cmd.py tests/test_ticket_work_and_land_finish.py`
clean of anything I introduced (both PATH ruff and `uv run ruff`; the one
remaining finding is a pre-existing I001 at _land_cmd.py:3800, an unrelated
existing import block, untouched by this diff).

Filed: none. The one genuinely out-of-scope observation (ARCH001/ARCH103/
E501/PERF004 findings are not checked by ANY land-time gate at all, unlike
the ty/doc-test families this ticket's parameterization only prepares for)
is exactly what acceptance [1] asks NOT to solve yet ("parameterise ... 
rather than adding a third hardcoded pair" -- it asks for the table, not
new lint-family checking logic). _DOC_TEST_EDGE_FAMILIES now makes adding
that a one-line append plus a checker if/when someone takes it on; I did
not file a new ticket for "wire ARCH/lint families into this gate" since
the acceptance criterion's own text frames that as future work this ticket
enables, not work this ticket owes.

Gates: `frob check --only gates-fast --ticket T-2201 --json` -- SCOPE001,
COV002, PRE001 all clear after `frob ticket scope --add
tests/test_ticket_work_and_land_finish.py` and adding a `frob:ticket T-2201`
edge to the touched test class. Every remaining error in that run (gate:COV
COV004 attachment-sha mismatches on T-2195/T-2197, gate:DOC DOC011 stale
draft-ticket citations, gate:DRIFT DRIFT001 on two unrelated symbols,
gate:TEST TEST010 on tests/test_lang.py kind="control" [T-2203's own scope]
and one pre-existing malformed-directive line at
tests/test_ticket_work_and_land_finish.py:740 that predates this ticket
[confirmed via `git show 26ff8cdec:tests/test_ticket_work_and_land_finish.py`],
gate:TICK TICK004 rot warnings) is repo-wide pre-existing floor debt, not
introduced by this diff -- confirmed by diffing this ticket's own touched
lines against each finding's file/line.
`frob check --land-parity` -- 1 pre-existing unscoped error
(E501 src/frob/lang/_nodes.py, outside this ticket's scope entirely, not
touched by this diff).

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py   | 100 +++++++++++++++++++++++-------
 tests/test_ticket_work_and_land_finish.py |  36 +++++++++++
 tickets/T-2201/ticket.md                  |  38 ++++++++++--
 3 files changed, 146 insertions(+), 28 deletions(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_new_public_symbol_with_no_edges_refuses_the_land` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_new_public_symbol_with_both_edges_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_an_unrelated_land_touching_no_new_public_symbols_is_unaffected` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_empty_touched_set_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_cli_land_end_to_end_refuses_a_worktree_with_a_new_undocumented_symbol` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_directive_looking_line_inside_a_docstring_does_not_satisfy_the_gate` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t2201-series/src/frob/lang/_nodes.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, SELFAUDIT001@design, TEST010@tests/test_lang.py, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
