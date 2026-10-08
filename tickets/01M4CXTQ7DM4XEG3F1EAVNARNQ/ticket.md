+++
id = "01M4CXTQ7DM4XEG3F1EAVNARNQ"
title = "Concurrent land stress test with branch -D and pack-refs churn"
type = "task"
category = "todo"
priority = "low"
points = 2
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T04:55:00Z"
updated = "2026-10-08T04:55:00Z"
scope = ["changelog.d/**", "crates/frob-land/**"]

[[acceptance]]
text = "Given two lands and concurrent ref churn, when run 20 times, then every land exits 0 or refuses cleanly"
bound = false
+++

Follow-up from ~BWMVSPZ: the back-to-back test cannot reproduce multi-process ref churn.
