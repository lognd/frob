## Done report

Changed:
src/frob/gates/__init__.py::_KNOWN_GATE_RULES (added DEC000)
tests/test_gates.py::TestKnownGateRuleIds.test_every_emitted_rule_literal_is_known
tests/test_gates.py::TestKnownGateRuleIds._KNOWN_ISSUE_ALLOWLIST
Evidence: uv run pytest tests/test_gates.py -q (all pass); uv run frob
check --ticket T-0901 --only scope --only coverage --only drift --only
gates (0 errors, 884 warnings, 94 waived)
Filed: T-0924 (COMPLIANCE00x/HOST00x/HOST-BLAST/KRB00x/
LINT00x/PII00x/RELWAIVE002/THREAT001-005 batch, out of this ticket's
file scope, carried in the new test's explicit allowlist)
Gates: frob check --ticket T-0901 clean (0 errors)
