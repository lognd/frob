## Done report

Verified this ticket's exact fix is already implemented and landed under
T-0399 (commit 12874170, "AUDIT: green must claim quality -- promote
quality gates from WARN to blocking"), before this ticket was filed
(T-0896 was found during T-0786's later sweep, apparently without
cross-checking against T-0399's already-shipped fix).

dup_gate (src/frob/gates/__init__.py:9087) already fails closed exactly
as this ticket's plan proposes: when [dup].enforce=true and
core_available() is False, it emits a blocking DUP003 ERROR Violation
naming the missing native and the remediation (`make core`), not a
log-only no-op -- see the docstring at line 9088 and the emission block
at lines 9107-9127. The old silent log.warning()-then-return-() shape
this ticket describes no longer exists in the current tree.

Evidence: tests/test_gates.py::TestOptInGates::
test_dup_gate_fails_closed_when_enforced_but_core_missing (frob:ticket
T-0399, line 8588) already covers this exact scenario -- monkeypatches
core_available to False, sets [dup].enforce=true, and asserts a single
DUP003 ERROR violation is returned. Ran it foreground: 1 passed.

No code changes made under this ticket; closing as fixed-by-T-0399 with
the pre-existing test as evidence rather than re-implementing or
duplicating coverage.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestOptInGates::test_dup_gate_fails_closed_when_enforced_but_core_missing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 4655 warning(s), 333 waived
- error-findings: none (measured, zero errors)
