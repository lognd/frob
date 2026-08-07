## Done report

All five fixes landed with regression tests (below), `frob check`
green (0 errors, 3 pre-existing unrelated warnings, 204 waived), `cargo
test` green in both frob-core (23 tests) and strata-core (111 tests),
full `pytest` suite green.

A: `_apply_evidence` (src/frob/app/ticket_runner.py) now loads
`[[test.runner]]` via `load_runners`, and if any entry declares
`language = "rust"`, calls `collect_rust_tests` and unions its node ids
into the validation set; a rust-collection failure logs a WARNING and
falls back to python-only validation rather than blocking the call.
Tests: `tests/test_tickets_evidence_cli.py::TestTicketEvidenceRustOracle`
(fake cargo-collect via a monkeypatched `collect_rust_tests`, a
no-rust-runner-declared guard proving cargo is never invoked
unnecessarily, and a rust-collection-failure degrade-to-python-only
case).

B: `_is_trailing_comment` (src/frob/lang/_extract.py) now compares
`_effective_end_row` (`span_of(node)[1] - 1`) instead of raw
`node.prev_sibling.end_point[0]`. Tests:
`tests/test_lang.py::TestParseTsRustCppC` (one-line/multi-line/zero-line
rustdoc-block matrix, all binding to the item below).

C: same test class,
`test_rust_directive_binds_regardless_of_indentation_mismatch` -- a
dedented directive above an indented multi-line rustdoc block and
indented item, confirming indentation never affects binding once B is
fixed. NO separate code change (see Description) -- flagging this
explicitly since the dispatching agent asked for a design decision and
the honest answer is "no new logic was warranted."

D: `_test005_symbols` (src/frob/gates/__init__.py) now skips
`_is_test_file(record.id.path)` symbols. Test:
`tests/test_gates.py::TestTestGate.test_test005_skips_test_file_symbols`.

E: `_cargo_list_result` (src/frob/testing/_collect.py) now matches
`_NO_LIB_TARGET_RE` against stderr and returns `Ok([])` with an INFO log
for that specific case; unmatched nonzero exits still `Err`. Tests:
`tests/test_testing.py::TestCollectRustTests::test_collect_rust_tests_skips_lib_less_crate`
and `::test_collect_rust_tests_still_errs_on_genuine_compile_error`.

DESIGN-CHANGE FLAG: none of these five fixes changed frob's public
contracts, CLI surface, or data shapes -- all are internal bug fixes
(a validation oracle gained a second source, a comment-binding
heuristic was corrected, a gate rule's skip-list gained one more
consistent entry, a collector gained one more recognized error shape).
No design change to flag.
