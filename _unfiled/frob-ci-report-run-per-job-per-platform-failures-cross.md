+++
id = "01M38BCNND6VZHYJ11GK9D9A9C"
title = "frob ci report <run>: per-job, per-platform failures, cross-platform diff, clusters"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-09-24T00:00:02Z"
aliases = ["T-5805"]
labels = ["milestone:v0.535.0"]
scope = ["src/frob/_cli_parsers/_ci.py", "tests/unit/cli/test_ci_report.py", "src/frob/app/app.py", "src/frob/app/ci_runner.py", "src/frob/ghio.py", "tests/test_ghio.py", "docs/modules/ci_report.md", "tests/fixtures/ci_report", "docs/modules/ghio.md"]
+++

frob ci report <run-id>: the T-2982 command surface over frob.ghio and frob.ci_report (T-5477 made the parser recognise this repo's SUITE-RESULT output): per job, per platform, the failing test node ids and failing steps, the cross-platform diff (shared vs platform-only), and a cluster grouping by file. Parity control: the CLI output equals build_run_report's own return for a fixture log with a known cluster. Errors are typed GhError values, never tracebacks (the T-2982 body's recorded '--log-failed returned EMPTY' mode gets a named error).
