+++
id = "01M4MH61ZJD4VYYXPANZ8132AR"
title = "frob land: skip the re-check when the merged tree's per-stage input hashes equal a recorded passing check (content-addressed check results)"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-11T03:47:55Z"
updated = "2026-10-11T16:57:35Z"
scope = ["crates/frob-land/**"]

[[acceptance]]
text = "landing a branch whose merge with the current base changes no input of a stage reuses that stage's recorded pass and runs no cargo process for it, measured by a land test that counts spawned tool processes"
bound = true
+++

measured: a frob check takes 142 s median (17 runs) and every ticket pays it in check --ticket and again inside land, in a cold clean checkout. Land is the serialized step, so its cost caps throughput at about 12 to 25 lands per hour whatever the worker count. Tool stages already declare inputs globs; key the result by the hash of those inputs plus tool version.
