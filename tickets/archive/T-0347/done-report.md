## Done report

Added _sys004_native_hint(root) in src/frob/gates/__init__.py (calls
frob.strata.stale_natives) and threaded root into _sys004/sys_gate, so a
SYS004 caused by a grammar-ahead-of-native mismatch now names `make core`
as the likely remedy -- distinguishing it from a genuine .strata syntax
error (the T-0166 incident's fix (2)). docs/modules/gates.md SYS004 row
updated to document the new clause.

Evidence (3 TestSysGate tests, pass): test_sys004_names_stale_native_as_likely_remedy
(the ticket's required regression), plus the two existing SYS004 tests
(load_failure, suppresses_sys001) confirming no behavior change to the
non-stale paths. Scope widened to tests/test_gates.py (the test file for
this ticket's own work). Implemented by the easy-wins sweeper; coordinator
inline-reviewed and landed via 3-way.

Coordinator note: while landing this, caught a separate regression the
sweeper flagged -- my earlier T-0292 COV003-message change had left
test_cov003_honest_remedy_when_no_native_missing asserting the removed fake
`frob test --collect` flag. Fixed that test to assert the corrected message
(committed separately).
