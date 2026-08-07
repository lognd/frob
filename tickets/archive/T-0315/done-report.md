## Done report
ALREADY RESOLVED on main by T-0301 (commit 51c62cf): `_test005_symbols` in
src/frob/gates/__init__.py now skips a record when `_is_test_file(record.id
.path)` -- the exact fix this ticket asks for, reusing the same _is_test_file
predicate TEST001/002 use. The lithos FROBLEM (2026-07-19) was written before
T-0301 landed. Verified on current main: the per-symbol TEST005 loop guards on
_is_test_file, and tests/test_gates.py::TestTestGate::test_test005_skips_test_
file_symbols locks it. No further change needed; closing as resolved-by-T-0301.
