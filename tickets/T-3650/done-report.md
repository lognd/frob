## Done report

Fixed needed_import_ops_for_symbols so carry-forward imports never re-import a name already resident as a module-level def/class/import at the destination file (the T-3628/T-3595 self-import repro shape). Added _dest_file_bound_names to read the destination's current bound names and exclude them from both the import-statement and synthetic-reimport carry-forward paths, alongside the existing moving_names (this chunk's own in-flight batch) exclusion. Two regression tests reproduce the T-3628 shape (move helper out, then split a class in the same source referencing it as a bare name into the same destination) and the T-3595 shape (_seed_repo referencing _git after _git was moved to conftest.py). T-3645 (import consolidation) and T-3646 (citation rewriter) are separate code paths (dest-file top-of-file import merging, archived-ticket citation attribution) that do not fit this fix cleanly -- landing them as separate sequential tickets per the series brief.

### Changed
```
 src/frob/refactor/_scan.py |  61 ++++++++++++++++----
 tests/test_refactor.py     | 141 ++++++++++++++++++++++++++++++++++++++++++++-
 tickets/T-3650/ticket.md   |   3 +
 3 files changed, 191 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/test_refactor.py::TestGapRegressions::test_gap5_split_after_move_no_self_import_when_dest_already_defines_helper` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestGapRegressions::test_gap5_split_seed_repo_referencing_git_helper_no_self_import` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 13 error(s), 4233 warning(s), 897 waived
- error-findings: ARCH102@src/frob/process/_lock.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, LARGE001@src/frob/refactor/_scan.py, LARGE001@src/frob/refactor/_verify.py, OPAQUE001@src/frob/app/_config_external.py, PRE001@tickets/T-3650, REL001@src/frob/__init__.py, SEC110@tests/ticket_land_suite/test_wip.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
