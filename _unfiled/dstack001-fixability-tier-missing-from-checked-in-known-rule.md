+++
id = "01M336K776W6BEYCPZRSS33SAK"
title = "DSTACK001 fixability tier missing from checked-in _KNOWN_RULE_FIXABILITY literal"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5350"]
scope = ["src/frob/gates/__init__.py", "tests/gates_suite/test_sys.py"]
+++

Found while working T-5190 on dev tip after T-5274 landed: tests/gates_suite/test_sys.py::TestRuleFixability::test_checked_in_literal_matches_a_fresh_scan fails -- a fresh generated_fixability() scan reports DSTACK001: 'auto' but the checked-in _KNOWN_RULE_FIXABILITY literal (added by T-5274, wiring DSTACK001 into gates dispatch) doesn't have it. T-5274's own land should have updated this literal in lockstep; out of T-5190's scope (rule-id registration, not fixability tiers).
