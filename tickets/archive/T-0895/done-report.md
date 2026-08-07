## Done report

This ticket asked for a regression test proving dup_gate emits a real
Violation (not just a log line) when [dup].enforce=true and
core_available() is mocked False. That exact test already exists and was
landed together with the T-0399 fix that gives dup_gate its fail-closed
behavior (see T-0896's Done report for the paired investigation):
tests/test_gates.py::TestOptInGates::
test_dup_gate_fails_closed_when_enforced_but_core_missing (frob:ticket
T-0399, tests/test_gates.py:8588-8608). It monkeypatches
frob.dup.core_available to return False, sets [dup].enforce=true with no
diff hunks, calls dup_gate directly, and asserts exactly one DUP003 ERROR
violation is returned -- precisely the "opted-in enforcement silently
no-ops when the native toolchain is missing" gap this ticket describes.

Ran it foreground: 1 passed.

No new test added under this ticket; closing citing the pre-existing
T-0399 test as evidence rather than duplicating coverage, per this
ticket's own note that it may be absorbed into the paired fix ticket's
evidence.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestOptInGates::test_dup_gate_fails_closed_when_enforced_but_core_missing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 19389 warning(s), 333 waived
- error-findings: none (measured, zero errors)
