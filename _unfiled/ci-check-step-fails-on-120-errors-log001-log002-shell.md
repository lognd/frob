+++
id = "01M6VYQZ5FEEP4TN8ZHVBCK63N"
title = "CI check step fails on 120 errors: LOG001/LOG002 shell scripts, TESTQ001/TESTQ002 tests"
type = "bug"
category = "todo"
priority = "critical"
reporter = "lognd"
created = "2026-11-07T21:30:58Z"
updated = "2026-11-12T12:30:35Z"
labels = ["ci"]
scope = [".github/scripts/**"]

[[acceptance]]
text = "given the CI rust ubuntu-latest job, when cargo dev ci --step check runs, then it exits 0"
bound = false
+++

Run 42412121808 rust (ubuntu-latest): cargo dev ci --step check exits 1 with 120 error findings: 42 LOG001 and 1 LOG002 in bash scripts, 30 TESTQ002 and 26 TESTQ001 in tests; plus 24 REF001/REL003 caused by the unpushed ledger. Fix the code (route shell output through the logging helper, give tests assertions, fake clocks) rather than baselining.
