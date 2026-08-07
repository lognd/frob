## Done report

Root cause: `frob.gates._symref_to_nodeid` (`path::a.b` -> `path::a::b`)
did a blanket `qualname.replace('.', '::')` over the ENTIRE qualname,
including any `[...]` parametrize case suffix. A collected node id whose
case text itself contains a literal dot (a version string like
`3.11.4`, a float parametrize value, or a dotted module path used as a
case id -- exactly the T-0222 auto-generated fixture pattern) got its
in-bracket dots corrupted into `::` (`3.11.4` -> `3::11::4`) before the
comparison, so the bracket-less base symref resolved (via
`_evidence_collected`'s prefix-match branch) while the specific
bracketed case id never could. `matches_collected`/`_evidence_collected`
themselves were already correct (exact membership check first) -- the
corruption happened one layer up, in the symref-to-node-id conversion
that feeds `_node_id_collected` (used by TESTS-edge/`frob:tests`
resolution) and is the same helper COV003's directive-side callers rely
on.

Fix: `_symref_to_nodeid` now splits the qualname at the first `[` before
converting dots, so only the dotted Class.method portion before any
bracket is touched; the `[...]` case suffix (if present) passes through
byte-for-byte unchanged.

Changed:
- src/frob/gates/__init__.py::_symref_to_nodeid

Evidence:
- tests/test_gates.py::TestCoverageGate::test_cov003_passes_for_parametrized_evidence_with_dot_in_case_id
- tests/test_gates.py::TestTestGate::test_test003_satisfied_by_parametrized_case_with_dot_in_case_id

Filed: none -- fix stayed inside declared scope (src/frob/gates/__init__.py,
tests/test_gates.py).

Gates: `uv run pytest tests/test_gates.py -q` 133 passed. `uv run frob
check --ticket T-0324` shows only pre-existing, out-of-scope items: PRE001
(stale sweep, refreshed via `frob ticket sweep T-0324` below), TEST006 (no
coverage stamp -- full-suite `make coverage` is a coordinator
responsibility per the playbook, not run here), and ARCH001 on
`src/frob/dup/_template.py` (pre-existing, unrelated file). No new
violations attributable to this change.
