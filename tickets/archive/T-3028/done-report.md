## Done report

Root cause: detect_project_type's fallback for a source-file-only repo (no marker file) checked ONLY root-level '*.py' via root.glob('*.py'), while the nested-marker walk (_detect_nested_native_project_type, originally native-language-only) never looked at Python at all. A src/-layout Python project with no pyproject.toml/setup.py and no root-level .py file (the T-3028 repro's own second git worktree: tickets.md + src/feature.py) therefore fell all the way through to 'unknown', so frob check --ticket <id> hit CHECK001 before ANY gate (including gate:PREWORK/the ticket-lease-pin refusal) ever got a chance to run -- not an ordering bug in the CLI's lease-pin call site (verified: _refuse_ticket_lease_mismatch already runs before project-type dispatch in check_runner.run(); with --stamp-baseline, mutating=True, the lease refusal already fires correctly regardless of project type) but a project-type MISDETECTION bug that made the unknown-type short-circuit fire when it should never have been reached at all. Fix: renamed _detect_nested_native_project_type to _detect_nested_project_type and folded pyproject.toml/setup.py (marker files) and .py (source suffix) into its existing bounded, pruned recursive walk (frob.excludes.iter_files) alongside the existing Cargo.toml/CMakeLists.txt/.cpp/.cc/.c entries -- one shared walk, not a second one. Once detect_project_type correctly resolves this repo shape to 'python', dispatch reaches the real Python check pipeline, which runs gate:PREWORK (no recorded sweep in the second worktree) and produces the expected 'frob ticket start T-0001' refusal text, exactly what the test asserts. Left T-3422's remediation-text wording untouched entirely (did not touch check_runner.py or gates/_waive_lease.py at all, only src/frob/check/__init__.py, within declared scope). Evidence: test_nested_py_file_no_root_marker_is_python (must-fire -- the exact T-3028 repro shape, src/feature.py with no root marker, now resolves to 'python' not 'unknown'), test_nested_cpp_source_still_wins_over_absent_python (must-stay-quiet -- folding Python into the shared marker/suffix tables does not regress the existing nested C/C++ detection), and the originally-failing tests/system/test_cli_check.py::TestCheckTicketLeasePinRefusal::test_ticket_lease_recorded_elsewhere_refuses, now passing end-to-end. Manually reproduced and confirmed both the failure on unmodified main (CHECK001) and the fix (test passes) via a standalone repro script outside pytest, not just the test's own assertions.

### Changed
```
 tickets/T-3028/ticket.md | 6 +++++-
 1 file changed, 5 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_check.py::TestDetectProjectType::test_nested_py_file_no_root_marker_is_python` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDetectProjectType::test_nested_cpp_source_still_wins_over_absent_python` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestCheckTicketLeasePinRefusal::test_ticket_lease_recorded_elsewhere_refuses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
