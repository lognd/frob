## Done report

Changed: src/frob/gates/__init__.py::_KNOWN_GATE_RULES (added PARSE001,
TICK005, REG011, PII011, PII012, SYSWAIVE002, THREAT006)
Evidence: uv run pytest tests/test_gates.py -q (all pass); uv run frob
check --ticket T-0903 --only scope --only coverage --only drift --only
gates (0 errors, 884 warnings, 94 waived)
Filed: none
Gates: frob check --ticket T-0903 clean (0 errors)
