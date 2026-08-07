## Done report

Measured a fresh, non-deflated coverage.xml via `make coverage` (exit 0,
COVERAGE-DONE:0; coverage.xml copied from .frob/coverage.partial.xml,
2933357 bytes, timestamped this run -- no stale-artifact substitution).
`frob check --only test` on that data reported 68 TEST005 findings before
this round, exactly matching T-1655's own carried-forward count, and 0
TEST017 (deflation) findings -- the measurement was trustworthy going in.

Closed 8 of the 68 findings in this slice with 15 new tests, each
inducing the real documented failure (OSError from a blocked read/write/
unlink, a non-git directory, a spawn-refusal stand-in for the kill
switch, a malformed span shape) and asserting the typani Result/None
contract, not merely executing lines:

- src/frob/gitio.py::excerpt (3 tests: unchanged-short, exact-boundary,
  truncated-long -- this symbol had ZERO direct tests before, only
  incidental exercise through git-failure logging paths)
- src/frob/doctor.py::scan_venv_shims (5 tests: non-python shebang
  skipped, no-shebang file skipped, directory entry skipped, symlink
  entry skipped, OSError-on-open skipped)
- src/frob/mutate/_journal.py::record_journal_progress (2 tests: no-op
  with no journal on disk, OSError on write swallowed)
- src/frob/mutate/_journal.py::remove_journal (1 test: OSError on unlink
  swallowed, journal survives untouched)
- src/frob/vet/_capability.py::non_executable_line_numbers (1 test:
  malformed span shape from `_non_executable_byte_spans` raises TypeError
  internally, caught and returns frozenset() per the "never raises"
  contract)
- src/frob/refactor/_gitops.py::working_tree_clean (2 tests: not-a-repo
  -> NotAGitRepo, guarded_subprocess_run spawn failure -> GitError)
- src/frob/refactor/_gitops.py::current_sha (1 test: not-a-repo ->
  GitError)

All 15 bound to their covered symbol via frob:tests directives
(node-level), and recorded as evidence via `frob ticket evidence T-1655`.
Ran the 5 touched test files together: 168 collected, 0 failed
(SUITE-RESULT: exitstatus=0 collected=168 failed=0).

Did NOT reach zero. The remaining ~53-60 findings (gates=14, app=10,
serve=9, arch=8, tickets=5, scaffold=5, refactor=4 remaining, testing=3,
vet=1 remaining, strata=2, dup=1) are carried forward to a named
successor per this ticket's own standing instruction (do not close on
partial progress): T-1657 (renumbers at land -- coordinator:
please confirm and cite the real T-#### id). gates/app/serve are the
largest remaining clusters and were not touched this round; dup's one
remaining finding (src/frob/dup/_pipeline/_smt.py) is z3-SMT-solver code
that may need a dedicated investigation rather than a quick Err-path
test -- flagged in the successor body rather than skipped silently.

Not closing T-1655 -- per its own body, a "remainder" ticket must not be
closed on partial progress; the successor above carries the rest.
</content>

### Changed
```
 src/frob/mutate/_journal.py     |  8 ++++
 src/frob/refactor/_gitops.py    |  4 ++
 src/frob/vet/_capability.py     |  3 ++
 tests/system/test_cli_doctor.py | 80 +++++++++++++++++++++++++++++++++++++
 tests/test_gitio.py             | 19 +++++++++
 tests/test_mutate_journal.py    | 66 +++++++++++++++++++++++++++++++
 tests/test_refactor.py          | 46 ++++++++++++++++++++++
 tests/test_vet_capability.py    | 20 ++++++++++
 tickets.md                      | 87 ++++++++++++++++++++++++++++++++++++++++-
 9 files changed, 332 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gitio.py::TestExcerpt::test_short_text_returned_unchanged` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestExcerpt::test_text_at_exact_boundary_returned_unchanged` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestExcerpt::test_long_text_truncated_to_last_n_lines` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorVenvShims::test_non_python_shebang_is_skipped` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorVenvShims::test_file_without_shebang_is_skipped` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorVenvShims::test_directory_entry_is_skipped` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorVenvShims::test_symlink_entry_is_skipped` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorVenvShims::test_unreadable_entry_is_skipped_not_raised` (pytest node id, verified passing when recorded)
- `tests/test_mutate_journal.py::test_record_journal_progress_is_a_noop_with_no_journal` (pytest node id, verified passing when recorded)
- `tests/test_mutate_journal.py::test_record_journal_progress_swallows_write_failure` (pytest node id, verified passing when recorded)
- `tests/test_mutate_journal.py::test_remove_journal_swallows_oserror` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestDocstringProseNotObservedLineLevel::test_non_executable_line_numbers_surprising_span_shape_is_empty` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestGitOps::test_working_tree_clean_not_a_git_repo` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestGitOps::test_working_tree_clean_spawn_failure_is_git_error` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestGitOps::test_current_sha_not_a_git_repo` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 15 passed (from 15 evidence id(s))
- gates: 0 error(s), 2869 warning(s), 845 waived
- error-findings: none (measured, zero errors)
