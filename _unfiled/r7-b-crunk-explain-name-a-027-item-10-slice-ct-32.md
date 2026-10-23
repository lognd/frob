+++
id = "01M1QDTV2J8PDS3FE3BT246153"
title = "R7-B: crunk explain NAME (A-027 item 10 slice, CT-32)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:02Z"
aliases = ["crunk:T-0082"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/crunk/query/**", "src/crunk/report/query_out.py", "src/crunk/app/**", "src/crunk/__main__.py", "tests/unit/test_query.py", "tests/unit/test_report_query.py", "tests/unit/test_app.py", "tests/unit/test_main.py", "tests/system/test_e2e_32_explain.py", "docs/commands/query.md"]

[[acceptance]]
text = "given the jsx fixture, when crunk explain space-12 runs, then value, group, defining file, CSS and JSX use sites, and mapped utilities print; an unknown token exits 2 naming close matches (E2E-32)"
bound = false
+++

Per r7 query.md (Explain section, UT-QRY-08) and shell.md r7 wiring: query.explain + ExplainAnswer + QueryError.UnknownToken with close matches; query_out renders it; top-level crunk explain NAME wired through cached styles, tokens.entries, utility_token_map. Document beside the query verbs.
