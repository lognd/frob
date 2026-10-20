+++
id = "01M4MH62H1AE14Z472QDSD1QBK"
title = "Merge train: land several ready tickets as one speculative batch, verify the batch tip once, and fall back to bisecting on failure"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 8
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-11T03:47:56Z"
updated = "2026-10-13T07:12:01Z"
scope = ["crates/frob-land/**"]

[[acceptance]]
text = "landing N ready tickets whose scopes are disjoint runs one verification of the combined tree instead of N, and a failure lands the passing prefix, covered by a test with an injected failing ticket"
bound = true
+++

design: GitHub merge queue, Bors and Zuul speculative execution are the public precedents. Disjoint leases already tell frob which tickets cannot conflict. Depends on the content-addressed result cache ticket.
