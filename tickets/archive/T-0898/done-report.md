## Done report

Fully absorbed by T-0897's already-landed fix, present on main before this
ticket was started: RENDER001 (src/frob/gates/_render_lint.py's
render_lint_gate) and PII010/SEC110 (src/frob/gates/_pii_structural.py's
pii_structural_gate) both already emit a loud PARSE001 Violation on a
file their own read/ast.parse cannot get through, replacing the old
private silent-skip the paired fix ticket (T-0897) addressed. Both gates
already carry a regression test binding exactly this behavior --
TestRenderLintGate.test_unparseable_file_fires_parse001 and
TestPiiStructuralCrossLanguage.test_unparseable_python_file_fires_parse001,
both frob:tests-bound to their gates already and both re-verified passing
here. No new code or test needed under this ticket -- closing citing the
pre-existing T-0897 evidence.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestRenderLintGate::test_unparseable_file_fires_parse001` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_unparseable_python_file_fires_parse001` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 19767 warning(s), 339 waived
- error-findings: none (measured, zero errors)
