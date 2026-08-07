---
id: T-1655
title: 'TEST005 remainder (68 findings): successor to T-1650, do not close on partial
  progress'
state: done
kind: feature
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/**
- src/frob/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gitio.py::TestExcerpt::test_short_text_returned_unchanged
- tests/test_gitio.py::TestExcerpt::test_text_at_exact_boundary_returned_unchanged
- tests/test_gitio.py::TestExcerpt::test_long_text_truncated_to_last_n_lines
- tests/system/test_cli_doctor.py::TestDoctorVenvShims::test_non_python_shebang_is_skipped
- tests/system/test_cli_doctor.py::TestDoctorVenvShims::test_file_without_shebang_is_skipped
- tests/system/test_cli_doctor.py::TestDoctorVenvShims::test_directory_entry_is_skipped
- tests/system/test_cli_doctor.py::TestDoctorVenvShims::test_symlink_entry_is_skipped
- tests/system/test_cli_doctor.py::TestDoctorVenvShims::test_unreadable_entry_is_skipped_not_raised
- tests/test_mutate_journal.py::test_record_journal_progress_is_a_noop_with_no_journal
- tests/test_mutate_journal.py::test_record_journal_progress_swallows_write_failure
- tests/test_mutate_journal.py::test_remove_journal_swallows_oserror
- tests/test_vet_capability.py::TestDocstringProseNotObservedLineLevel::test_non_executable_line_numbers_surprising_span_shape_is_empty
- tests/test_refactor.py::TestGitOps::test_working_tree_clean_not_a_git_repo
- tests/test_refactor.py::TestGitOps::test_working_tree_clean_spawn_failure_is_git_error
- tests/test_refactor.py::TestGitOps::test_current_sha_not_a_git_repo
designated_repro_test: null
threat: null
component: null
---
Successor to T-1650, which was itself the successor to T-1273.

T-1650 was filed as the TRACKING ticket for 73 measured TEST005 findings. Its agent closed 5 (the `tickets` package, with 10 genuinely behavioural tests) and its Done report named the other 68 by package. The coordinator then landed and CLOSED T-1650 -- which dropped those 68 from the queue entirely. Same failure mode as T-1420 and T-1204 before it (T-1648), committed this time by the coordinator rather than an agent, and on a ticket whose whole purpose was to carry a remainder forward.

The lesson worth writing down: a ticket that exists to TRACK a remainder must not be closed when a slice of that remainder is done. It should stay open until its count reaches zero, or hand off explicitly to a named successor before closing. T-1648's proposed structured-remainder field would have caught this; until it exists, treat any ticket whose title says "remainder" as non-closeable on partial progress.

Remaining work, last measured on a fresh non-deflated coverage.xml (527 classes joined, no TEST017 finding): 68 findings, none at 0.0% -- gates=14, app=10, serve=9, arch=8, scaffold=5, refactor=5, testing=3, vet=2, strata=2, mutate=1, dup=1, doctor.py=1, gitio.py=1.

Method (carried forward, it worked):
- Measure UNSCOPED. A --ticket-scoped zero is not a package zero.
- Verify coverage.xml freshness and non-deflation before trusting any count; if TEST017 fires, stop and report rather than burning down against fiction. If the promote-to-committed step is blocked by an unrelated test failure, recover the real data from .frob/coverage.partial.xml per the playbook rather than guessing.
- Write tests that would FAIL if the behaviour broke -- induce the real failure (OSError, malformed input, missing ref) and assert the documented contract. A test that only executes lines to move a percentage is worse than the missing coverage, because it makes the gap permanently invisible.
- Bind each test to the symbol it covers with a frob:tests directive at the covered symbol, node-level.

Do NOT close this ticket on partial progress. Either drive it to zero or file a named successor first and say so in the Done report.