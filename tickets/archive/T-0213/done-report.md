## Done report

Changed:
src/frob/gates/__init__.py::_cov001 (the `_log.debug` short-form message
line 779, changed from `"COV001: %s undocumented"` to
`"COV001: %s public with no frob:doc edge"` to match the accurate
long-form Violation.message already emitted a few lines below). The
long-form message was already correct and untouched.
tests/test_gates.py::TestCoverageGate.test_cov001_message_wording_for_docstring_without_doc_edge
(new regression test)

Evidence:
tests/test_gates.py::TestCoverageGate::test_cov001_message_wording_for_docstring_without_doc_edge
-- asserts COV001 still fires for a symbol carrying a docstring but no
frob:doc edge, and that the violation message contains "no frob:doc edge"
and does not contain "undocumented".
`uv run pytest tests/test_gates.py -k cov001 -q` -- 3 passed (existing
test_cov001_undocumented_public_symbol, existing
test_cov001_passes_when_documented, new
test_cov001_message_wording_for_docstring_without_doc_edge).
`uv run frob test --base main` -- selection touched=5 ripple=0,
`uv run pytest -q tests/test_gates.py tests/test_gates.py::test_gates_run_gates_integration`
exit=0 duration=6.73s.

Filed: none

Gates: `uv run frob check --stamp-baseline` then
`uv run frob check --delta --ticket T-0213` -- gates 0/8 new, 0 errors,
0 warnings, 27 waived (pre-existing, all waived). SCOPE001 initially
fired on `frob-core/Cargo.lock` and `strata-core/Cargo.lock` (native
`make core` build noise, not source changes); reverted both files with
`git checkout -- frob-core/Cargo.lock strata-core/Cargo.lock` before the
final delta run, which came back clean.
