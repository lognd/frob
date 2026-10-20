+++
id = "01M35RZY7Z3RJKVSGQE4WKYE8F"
title = "Checked-in _KNOWN_RULE_FIXABILITY literal missing DOCARCH002/DSTACK001/FMT002 (landed rules never updated it)"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-10-04T21:07:59Z"
aliases = ["T-5375"]
labels = ["v1-cluster:F1"]
scope = ["src/frob/gates/_fixability_scan.py"]
+++

found while working T-4758: tests/gates_suite/test_sys.py::TestRuleFixability::test_checked_in_literal_matches_a_fresh_scan fails on dev -- generated_fixability() reports DOCARCH002/DSTACK001/FMT002 as auto-fixable but the checked-in _KNOWN_RULE_FIXABILITY literal (src/frob/gates/_fixability_scan.py) was never updated when those rules landed (T-4713/T-4714 and an earlier DOCARCH002 land). Pre-existing on dev, unrelated to T-4758's directive-comment-only sweep; confirmed by diff inspection (T-4758 never touches this file).
