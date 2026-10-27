+++
id = "01M1QDTV2YEAB07P7BZ980EGYC"
title = "unused tokens in report v2 (A-037)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:38Z"
aliases = ["crunk:T-0094"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/report/report_out.py", "src/crunk/app/app.py", "tests/unit/test_report.py", "tests/unit/test_app.py", "tests/system/test_e2e_39_report_unused.py", "docs/commands/check.md"]

[[links]]
kind = "blocked-by"
target = "01M1QDTV2RJ8GR3JVDGBDHXW4D"

[[acceptance]]
text = "given a declared-but-unreferenced token, when check --report runs, then unused_tokens carries it in the v2 JSON and the Markdown shows the Unused section, matching query unused exactly (E2E-39)"
bound = false
+++

Per r9 report.md (unused-token bullet) and 02 (v2 schema's unused_tokens field): the shell computes the list with the same utility-aware math query unused uses (share the code path -- no second implementation) and threads it into the report renderers.
