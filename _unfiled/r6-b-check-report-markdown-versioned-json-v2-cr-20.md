+++
id = "01M1QDTV1X39GRJS23113J5FPH"
title = "R6-B: check --report, Markdown + versioned JSON v2 (CR-20)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:34Z"
aliases = ["crunk:T-0061"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/report/**", "src/crunk/app/**", "src/crunk/__main__.py", "tests/unit/test_report.py", "tests/unit/test_app.py", "tests/unit/test_main.py", "tests/integration/test_int_12_report.py", "tests/system/test_e2e_28_report.py", "docs/commands/check.md"]

[[acceptance]]
text = "given a mixed fixture tree, when check --report and check --report --json run, then the documented v2 schema and matching Markdown sections render byte-identically across runs and the exit matches plain check (E2E-28, INT-12)"
bound = false
+++

Per r6 report.md (render_report/render_report_json, UT-REP-07) and shell.md r6 wiring: report renderers over (spec, styles, violations, tokens_status); --report flag on check, composing with --json, mutually exclusive with --contrast (argparse error exit 2); document in docs/commands/check.md. Schema pinned in 02 (Check report section).
