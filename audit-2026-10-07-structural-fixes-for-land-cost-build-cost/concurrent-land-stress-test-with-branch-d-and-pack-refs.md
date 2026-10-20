+++
id = "01M4CXTQ7DM4XEG3F1EAVNARNQ"
title = "Concurrent land stress test with branch -D and pack-refs churn"
type = "task"
category = "done"
outcome = "done"
priority = "low"
points = 2
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T04:55:00Z"
updated = "2026-10-11T21:16:19Z"
scope = ["changelog.d/**", "crates/frob-land/**"]

[[acceptance]]
text = "Given two lands and concurrent ref churn, when run 20 times, then every land exits 0 or refuses cleanly"
bound = true
+++

Follow-up from ~BWMVSPZ: the back-to-back test cannot reproduce multi-process ref churn.
