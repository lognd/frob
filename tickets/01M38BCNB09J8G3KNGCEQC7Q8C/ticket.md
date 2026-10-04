+++
id = "01M38BCNB09J8G3KNGCEQC7Q8C"
title = "app_runners JSON guard: runner produces empty stdout instead of JSON"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "agent"
created = "2026-09-24T00:00:00Z"
updated = "2026-09-24T00:00:02Z"
aliases = ["T-5472"]
labels = ["milestone:v0.534.0"]
scope = ["src/frob/app/fmt_runner.py", "tests/unit/test_app_runners_json_guard_t2492.py"]
+++

Found while draining CI run 35951365410 (dev 9e0c89bb19). Failing:
tests/unit/test_app_runners_json_guard_t2492.py::TestFmtRunnerJsonGuard::test_planted_leak_does_not_reach_stdout

The test captures a runner's stdout and expects valid JSON; it gets an
EMPTY string instead (json.decoder.JSONDecodeError: Expecting value: line
1 column 1 char 0) -- the runner produced no JSON output at all where the
test's own positive control (T-2492's planted-leak guard) expects some.

Needs: identify which runner under test stopped emitting JSON (or started
emitting nothing) and why. Not narrowed further in this drain pass; this
file is in touch-scope (not webapp/sql/strata-core).
