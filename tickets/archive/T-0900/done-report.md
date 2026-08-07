## Done report

Fully absorbed by T-0894's own evidence, already landed (main commit
597904bfc98cd02f346c803c15608a29e5861538): T-0894's fix for
compliance_gate added exactly the regression test this ticket asks for --
test_compliance006_fires_on_deleted_registry_after_adoption commits
compliance.yaml, deletes it, and asserts the resulting COMPLIANCE006
violation fires through compliance_gate's real production invocation
(not a pure-function unit test in isolation); its sibling
test_compliance006_silent_on_never_adopted_registry covers the negative
case (never-committed compliance.yaml stays silent). No new code or test
added under this ticket -- it closes citing T-0894's already-landed
evidence, per this ticket's own "starting with COMPLIANCE005" framing.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestComplianceGate::test_compliance006_fires_on_deleted_registry_after_adoption` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestComplianceGate::test_compliance006_silent_on_never_adopted_registry` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 19579 warning(s), 339 waived
- error-findings: none (measured, zero errors)
