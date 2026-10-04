+++
id = "01M1WJMD4257DX3WHV8QGMN5WS"
title = "cross-artifact producer/consumer check: a value one script writes and another parses must be verified as one contract, not per-half unit tests"
type = "task"
category = "triage"
priority = "low"
parent = "01M1WJMD2FWKPS1J7MPF18KDVY"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-04T21:06:06Z"
aliases = ["T-4226"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/gates"]
+++

Consumer F-373/P1 (T-4175): a shell script POSTs a header, a backend route's unit tests construct that header themselves, and a separate ops test asserts only on the payload -- both halves pass in isolation and no gate compares producer against consumer. Not fixture-testable in frob's own tree: no shell-to-backend script pairing exists here.
