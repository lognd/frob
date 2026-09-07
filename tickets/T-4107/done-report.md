## Done report

Changed:
- src/frob/dup/_legacy.py: _posix_rel (new shared helper), _effective_min_lines (docstring), _scan_py_file, _scan_cpp_file, _walk

Evidence:
- tests/unit/test_dup.py::TestTestsDirectoryFloor::test_short_fixture_style_duplicate_under_tests_is_no_longer_a_group
- tests/unit/test_dup.py::TestTestsDirectoryFloor::test_genuine_helper_duplicate_at_20_lines_still_fires
- tests/unit/test_dup.py::TestTestsDirectoryFloor::test_fragment_file_is_forward_slash_separated_in_nested_directory
- tests/unit/test_dup.py::TestTestsDirectoryFloor::test_walk_does_not_exclude_a_file_that_matches_no_configured_exclude_glob

Filed: none (searched for sibling bare-startswith-against-relative_to comparisons across src/;
no other site matches a directory-prefix table with a bare rel.startswith(prefix) pattern --
the only other prefix-startswith use found, tickets/_models.py:762, matches against a
collected-node-id string, not a filesystem rel path, so it is out of this bug's family)

Gates: uv run frob check --ticket T-4107 shows the same FAIL set (ruff-format 25 files,
ty 6 diagnostics, gates graph-build-failed) on bare main with no ticket scope too --
pre-existing repo-wide state, not introduced by this change. frob-dup, frob-arch,
frob-cycle, frob-exports all pass. Added a fourth test
(test_walk_does_not_exclude_a_file_that_matches_no_configured_exclude_glob) to kill
the surviving TEST016 mutant at _legacy.py:402 (boolop And swapped to Or in
`exclude_globs and is_excluded(rel, exclude_globs)`); the four bound tests now
kill 1/1 mutants in changed lines. `uv run frob test --base main` timed out at
540s (consistent with a known repo-wide graph-build issue); direct
`pytest tests/unit/test_dup.py -q` is 21/21 green including all four acceptance
tests above.

### Changed
```
 src/frob/dup/_legacy.py       |  34 ++++-
 tests/unit/test_dup.py        |  58 +++++++++
 tickets/T-4107/done-report.md |  40 ++++++
 tickets/T-4107/ticket.md      | 292 +++++++++++++++++++++++++++++++++++++++++-
 4 files changed, 414 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/unit/test_dup.py::TestTestsDirectoryFloor::test_short_fixture_style_duplicate_under_tests_is_no_longer_a_group` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup.py::TestTestsDirectoryFloor::test_genuine_helper_duplicate_at_20_lines_still_fires` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup.py::TestTestsDirectoryFloor::test_fragment_file_is_forward_slash_separated_in_nested_directory` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup.py::TestTestsDirectoryFloor::test_walk_does_not_exclude_a_file_that_matches_no_configured_exclude_glob` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 3 error(s), 4452 warning(s), 936 waived
- error-findings: PRE001@tickets/T-4107, SCOPE002@tickets.md, missing-argument@tests/unit/test_check_gates_summary.py
