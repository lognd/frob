+++
id = "01M4CTTYH76JQASEJJQC02YD0F"
title = "Failed test evidence: show the cause, keep the real test id, and do not commit a ledger event per failed attempt"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CTTPJ00PTDE0A1SE4MJFCF"
reporter = "lognd"
created = "2026-10-08T04:02:41Z"
updated = "2026-10-08T04:02:41Z"
scope = ["changelog.d/**", "crates/frob-evidence/**", "crates/frob-tests/**"]

[[acceptance]]
text = "Given a failing test, when frob test records evidence, then the output names the test id unmangled and the failure cause, and no ledger commit is made for an unrecorded failure"
bound = false
+++

notes/review/adoption-trial-2026-10-07.md MEDIUM.
