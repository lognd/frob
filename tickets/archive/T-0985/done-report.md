## Done report

frob fmt idempotence, half delivered honestly: trailing noqa pragmas are now a line-level escape hatch the canonicalizer leaves byte-identical (folded into T-0976's refactored _rewrite_lines_via_runs at the equivalent decision point), proven by a run-twice-over-real-files idempotence test. The repo-wide recompaction was investigated and deliberately deferred: rewrapping can push frob:-shaped prose tokens to continuation-line starts that frob.graph.dsl misparses as bogus directives (verified on two files, cascades to 90 DSL errors repo-wide) -- that parser bug and the recompaction are filed as a blocked pair rather than forced.

### Changed
```
 docs/modules/gates.md              |  24 ++-
 src/frob/gates/_fmt_directives.py  |  42 ++++-
 tests/test_gates_fmt_directives.py | 203 ++++++++++++++++++++----
 tickets.md                         | 310 ++++++++++++++++++++++++++++++++++++-
 4 files changed, 543 insertions(+), 36 deletions(-)
```

### Evidence
- `tests/test_gates_fmt_directives.py::TestNoqaSuffixPragmaT0985::test_over_long_single_line_with_noqa_e501_is_byte_identical` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestNoqaSuffixPragmaT0985::test_over_long_single_line_with_bare_noqa_is_byte_identical` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestNoqaSuffixPragmaT0985::test_over_long_line_without_noqa_still_wraps` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestRepoWideIdempotenceT0985::test_canonicalizing_twice_over_real_repo_files_is_a_no_op` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
