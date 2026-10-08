+++
id = "01M4D6NSXSZXY4G6282RSHJV4M"
title = "CLI test for work --unplanned --reason parsing"
type = "task"
category = "todo"
priority = "low"
points = 1
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T07:29:36Z"
updated = "2026-10-08T07:29:36Z"
scope = ["changelog.d/**", "crates/frob/**"]

[[acceptance]]
text = "Given work --unplanned without --reason, when parsed, then it is a usage error"
bound = false
+++

Follow-up from ~57FX1J2 (verified by hand only).
