## Done report

Changed:
- tests/test_gates.py::TestKnownGateRuleIds.test_every_emitted_rule_literal_is_known -- extended to resolve `rule=CONST_NAME` references against module-level `CONST_NAME = "RULE123"` constant assignments (the REL_*/SYS_* convention), in addition to the pre-existing inline `rule="..."` literal scan.
- tests/test_gates.py::TestKnownGateRuleIds._KNOWN_ISSUE_ALLOWLIST -- populated with SYS100/SYS101/SYS102/SYS200/SYS201/SYS202/SYS203, real ids the new constant-resolution scan found genuinely missing from `_KNOWN_GATE_RULES`; parked here citing T-0966, mirroring the existing T-0901/T-0924 allowlist precedent in this same file.

Evidence:
- Before-fails proof: with the OLD (unfixed) test body, temporarily removing "REL250" (a constant-referenced id, `REL_SPOF = "REL250"` in src/frob/strata/_spof.py) from `_KNOWN_GATE_RULES` in src/frob/gates/__init__.py left `test_every_emitted_rule_literal_is_known` PASSING (confirmed blind).
- With the NEW (fixed) test body, the same removal makes the test FAIL: `AssertionError: ... {'REL250': 'src/frob/strata/_spof.py:182'}`. File restored immediately after each proof run (verified via md5sum against the pre-edit backup).
- `pytest tests/test_gates.py::TestKnownGateRuleIds -q` -> 3 passed (test_returns_known_rule_id, test_is_frozenset, test_every_emitted_rule_literal_is_known).
- `pytest tests/test_gates.py -q` -> full file green (no regressions).
- Collected node ids (`pytest --collect-only -q -v`): tests/test_gates.py::TestKnownGateRuleIds::test_returns_known_rule_id, ::test_is_frozenset, ::test_every_emitted_rule_literal_is_known.

Filed: T-0966 ("gates: SYS100-102/SYS200-203 rule ids missing from _KNOWN_GATE_RULES (T-0964 constant-scan fallout)") -- the constant-resolution scan surfaced 7 real ids missing from `_KNOWN_GATE_RULES` in src/frob/gates/__init__.py, out of T-0964's tests/test_gates.py-only scope; carried in `_KNOWN_ISSUE_ALLOWLIST` until that ticket lands.

Gates: `frob check --ticket T-0964` clean across all `--only` stage groups (gates-fast, gates-native, gates-security, static: 0 errors each). `lint` stage shows ruff-format would reformat 3 pre-existing files (src/frob/arch/_lock_ordering.py, tests/test_ticket_land.py, tests/unit/test_arch.py) -- all outside T-0964's scope and pre-existing on main, not introduced by this change; tests/test_gates.py itself is ruff-format clean.
