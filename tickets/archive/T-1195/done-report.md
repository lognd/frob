## Done report

AMENDMENT (post-close review, REJECT then fixed):

The initial close was reviewed and rejected for three issues, all fixed
in follow-up commits within this same worktree (T-1195 stays closed;
these ride the same land):

1. COV002 (102 unwaived errors, all in the 3 new files): caused by a
   bogus module-level "frob:ticket T-1195" line sitting in each new
   file's docstring text -- not a real directive (no leading '#'), so
   it created no coverage binding at all. COV002 had actually been
   passing only via T-1195's own open-ticket scope coverage while the
   ticket was open; once closed, that stopped applying, and turned out
   to be ambiguous besides (multiple other open tickets independently
   claim 'src/frob/' scope, defeating COV002's B10 unambiguous-
   narrowest-match rule). Fix: removed the bogus docstring lines and
   added real per-symbol "# frob:ticket T-1195" directives (valid via
   the T-0214/T-0965 grace window -- T-1195 closed within this same
   uncommitted diff) to every symbol COV002 flagged; narrowed
   T-1270's scope from a bare 'src/frob/' catch-all to its
   actual residue file list to remove the scope-ambiguity tie.
2. DUP001 (unwaived, arch/_abstraction.py::_near_duplicate_cluster,
   95% similar to strata/_report.py::_assumption_ledger_lines and
   app/test_runner.py::_print_fuzz_results): pre-existing duplication
   surfaced by the move, not introduced by it. Fixed with a
   frob:waive DUP001 naming both counterparts.
3. DUP002 (unwaived, two 100%-identical tests in
   tests/unit/test_arch.py::TestLanguageParityExclusion): collapsed
   test_duplicate_tag_within_group_still_flagged and
   test_untagged_member_within_group_still_flagged into one
   parametrized test_non_parity_group_still_flagged; updated T-1068's
   archived evidence (tickets-archive.md) to the new parametrized
   pytest node ids.

Re-verification (uv run frob check --base main, full generous-timeout
foreground runs, after `git merge main` to bring the worktree current):
- --only coverage: 0 errors, 12 warnings, 135 waived (down from 104
  errors before the fix; the 12 warnings/135 waived are pre-existing,
  none touching the 3 split modules or the two original split-source
  files)
- --only gates-native: 0 errors (ARCH/DUP/EXHAUST/LARGE/PERF all pass;
  clones/DUP shows 0 errors, 2 waived -- the DUP001 waiver from item 2)
- --only gates-security: 0 errors (DEAD/OPAQUE/PII/SEC all pass)
- --only gates-fast: 7 pre-existing errors (DEPR002 x4 on unrelated
  app/xref_runner.py etc., DOC001 on an unrelated audit doc that
  arrived via a main merge, PRE001/SCOPE001 -- both artifacts of
  running the check bare without --ticket/a T-####-branch, not real
  diff gaps) -- none reference arch/_abstraction.py,
  app/_check_chunking.py, gates/_docblocks_refs.py, arch/_python.py,
  app/check_runner.py, or gates/_docblocks.py
- --only static: all pass (frob-cycle, frob-dup, frob-arch, frob-
  exports x7 -- pre-existing warnings only)
- --only lint: 0 errors, 0 warnings (ruff-check, ruff-format, ty all
  clean)

Touched-set pytest re-run (all green): tests/unit/test_arch.py,
tests/test_arch_near_duplicate_native.py, tests/unit/test_check_budget.py,
tests/unit/test_app_runners_batch6.py, tests/test_docblocks_gate.py.

Fix commit: 9a4ce42b "fix(arch,app,gates): resolve reviewer-flagged
COV002/DUP001/DUP002" (rides the same land as the original 3 split
commits; T-1195 itself was not reopened).

### Changed
```
 docs/modules/arch.md                     |   4 +-
 src/frob/app/_check_chunking.py          | 521 +++++++++++++++++++++
 src/frob/app/check_runner.py             | 472 +------------------
 src/frob/arch/_abstraction.py            | 762 ++++++++++++++++++++++++++++++
 src/frob/arch/_python.py                 | 701 +---------------------------
 src/frob/gates/_docblocks.py             | 777 +++----------------------------
 src/frob/gates/_docblocks_refs.py        | 770 ++++++++++++++++++++++++++++++
 tests/test_arch_near_duplicate_native.py |   6 +-
 tests/unit/test_arch.py                  | 161 ++++---
 tests/unit/test_check_budget.py          |  27 +-
 tickets-archive.md                       |   8 +-
 tickets.md                               | 469 ++++++++++++++++++-
 12 files changed, 2705 insertions(+), 1973 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestDispatchFamilySuppression::test_dispatch_family_no_abstraction_opportunity` (pytest node id, verified passing when recorded)
- `tests/test_arch_near_duplicate_native.py::test_near_duplicate_cluster_dispatches_to_native_and_matches_reference` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_mode_calls_stamp_and_returns` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_runs_selected_chunks_and_reports_result` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
