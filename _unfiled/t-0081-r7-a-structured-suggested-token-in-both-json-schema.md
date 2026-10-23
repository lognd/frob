+++
id = "01M1QDTV2H7VP2FZVKE415Q9QH"
title = "R7-A: structured suggested_token in both JSON schemas (A-027 item 7, CT-30)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:02Z"
aliases = ["crunk:T-0081"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/crunk/rules/models.py", "src/crunk/rules/_color.py", "src/crunk/rules/_scales.py", "src/crunk/rules/_tailwind.py", "src/crunk/report/json_out.py", "src/crunk/report/report_out.py", "tests/unit/test_rules_color.py", "tests/unit/test_rules_scales.py", "tests/unit/test_rules_tailwind.py", "tests/unit/test_report.py", "tests/system/test_e2e_30_suggested.py"]

[[acceptance]]
text = "given a mixed violating tree, when check --json and check --report --json run, then every COLOR001/SPACE001/TYPE001/RADIUS001/TW001 violation carries the documented suggested_token and other rules carry null (E2E-30)"
bound = false
+++

Per r7 rules.md (Violation.suggested_token bullet, UT-RUL-SUGGEST) and 02 (v1 schema additive field + report v2). Names via spec.naming; advice is not tolerance-gated; waived sites still carry it.
