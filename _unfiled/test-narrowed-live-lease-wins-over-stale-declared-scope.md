+++
id = "01M30M6G3T0A0396VWDT4XMWDW"
title = "test_narrowed_live_lease_wins_over_stale_declared_scope fails on current dev (CI run 35510697497 burn-down)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-21T00:00:00Z"
updated = "2026-09-21T00:00:02Z"
aliases = ["T-5242"]
scope = ["src/frob/gates/_fix_engine.py", "tests/gates_suite/test_fix_engine.py", "src/frob/gates/_fix_engine_scope.py"]
+++

Found while burning down CI run 35510697497 (dev @ e99570be, now an ancestor of dev tip 4483b1da29). Re-verified failing on current dev tip (not stale): tests/gates_suite/test_fix_engine.py::TestFixEngineScopeLease::test_narrowed_live_lease_wins_over_stale_declared_scope fails both in the original CI run (ubuntu+windows) and locally on dev tip. Needs investigation of the fix-engine's scope/lease precedence logic: a narrowed live lease should win over a stale declared scope, and currently does not (or the test's fixture/expectation itself is stale -- confirm which before changing behavior).
