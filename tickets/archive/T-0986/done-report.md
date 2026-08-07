## Done report

Changed:
src/frob/gates/_docptr.py::_doc007_violation
src/frob/gates/_docptr.py::_tests_target_shape_violations
src/frob/gates/__init__.py::_KNOWN_GATE_RULES (added DOC007 literal)
tests/test_docptr_gate.py::TestDoc006TestsTargetShape.test_double_separator_target_flagged
tests/test_docptr_gate.py::TestDoc006TestsTargetShape.test_single_separator_target_not_flagged

Evidence:
tests/test_docptr_gate.py (18 passed)
tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known (passed)
tests/test_gates.py::test_gates_run_gates_integration (passed)
frob test --base main: touched=10, python exit=0, 3 outcomes recorded

Filed: none

Gates: frob check --ticket T-0986 clean across prework/scope/sys/drift/doc/
invariant/registry/tickets/dup stage groups (chunked --only runs, natives
rebuilt via make core first -- fresh worktree lacked strata_core/frob_core,
the documented T-0144 artifact, not a regression). gate:DOC 0 errors
confirms the new DOC007 rule has zero live findings on this tree (repo-wide
grep for `frob:tests` targets with a second `::` also confirms 0 real
occurrences outside test fixtures in tmp_path-isolated gate tests).

Mechanics: split DOC006's frob:tests target-form sub-check into its own
rule id, DOC007, shipped at ERROR from birth (not the WARN-first-turn-on
precedent DOC006 itself used) -- the mistake has zero adoption baseline
worth protecting and every historical occurrence only surfaced post-land
as DRIFT002. This deliberately leaves the other ~700 live DOC006 findings
untouched at WARN. Scope was extended (frob ticket scope --add
src/frob/gates/__init__.py) after discovering DOC007 needed registering
in the file-scoped _KNOWN_GATE_RULES catalog for WAIVE002 and the
TestKnownGateRuleIds test to recognize it; reason recorded in the ticket's
scope_changes audit trail.

### Changed
(no changed files detected)

### Evidence
- `tests/test_docptr_gate.py::TestDoc006TestsTargetShape::test_double_separator_target_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006TestsTargetShape::test_single_separator_target_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 4882 warning(s), 306 waived
- error-findings: none (measured, zero errors)
