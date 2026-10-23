+++
id = "01M5K9QNQFYJNXZSSG2X91FJBQ"
title = "Add TS/JS/C# nondeterminism and control-flow vocabulary to testq"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-23T02:34:11Z"
updated = "2026-10-23T05:03:31Z"
scope = ["crates/grimble-lints/src/testq/**", "crates/grimble-lints/**"]

[[acceptance]]
text = "TESTQ002 reports nondeterminism in TS, JS and C# tests instead of unresolved"
bound = true

[[acceptance]]
text = "TESTQ003 reports control flow in TS, JS and C# tests instead of unresolved"
bound = true

[[acceptance]]
text = "deterministic straight-line tests in those languages stay quiet"
bound = true
+++

Found while working ~5ZSH4H5. TESTQ001 now reads TS/JS/C# tests; TESTQ002 and TESTQ003 still report unresolved for them.
