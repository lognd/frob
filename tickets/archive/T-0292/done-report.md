## Done report

Corrected the COV003 remediation hint (src/frob/gates/__init__.py::
_cov003_evidence_violation) instead of adding the flag: verified that
collect_python_tests/collect_rust_tests already key their caches
(.frob/pytest-collect.json, .frob/cargo-collect.json) on a content-hash of
the test files, so the collection cache self-refreshes on the next
`frob test`/`frob check` run -- a `--collect` flag would be redundant. The
hint now describes that auto-refresh plus the manual fallback (delete the
cache file), and names NO nonexistent flag.

Evidence: tests/test_gates.py::TestCoverageGate::test_cov003_remediation_hint_names_no_nonexistent_flag
-- asserts every `--flag`-shaped token in the live COV003 message is a flag
`_add_test_parser` actually registers (a static regression guard against any
future hint reintroducing a fictional flag). Inline-reviewed by coordinator.

Note: the implementer found two MORE stale `frob test --collect` references
outside this ticket's scope (app/ticket_runner.py, tickets/__init__.py) --
filed as T-0445. Landed onto current main (the COV003 message had since been
refactored to a `remedy` variable; the fix was re-applied to that form).
