+++
id = "01M1T07J49J1VVTBJ4AJJ8G029"
title = "Map note gates on org buckets only (A-090 partial)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-09-06T00:00:02Z"
aliases = ["crunk:T-0137"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/crunk/report/terminal.py", "tests/unit/test_report.py", "docs/design/subsystems/report.md"]

[[acceptance]]
text = "given a project with a populated tokens bucket and empty org buckets, when map renders, then the note leads the output"
bound = false
+++

The r18 all-empty note tested every non-jsx bucket including entry and tokens, so a utility-first project whose only CSS is the tokens file and an entry sheet never printed it while its org bucket rows all read (empty). The note now gates on the declared organization buckets alone, which are exactly the rows that read like a parse failure.
