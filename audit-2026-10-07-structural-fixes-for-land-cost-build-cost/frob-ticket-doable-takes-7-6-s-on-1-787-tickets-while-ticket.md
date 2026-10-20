+++
id = "01M4MGNX6AWFK18T5YJ566VMKA"
title = "frob ticket doable takes 7.6 s on 1,787 tickets while ticket list takes 0.09 s; compute from the SQLite index and cache the result per ledger tip"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-11T03:39:06Z"
updated = "2026-10-11T17:06:02Z"
scope = ["crates/frob-ticket/**", "crates/frob-lease/**", "crates/frob-ledger/**", "crates/frob/**", "docs/**"]

[[acceptance]]
text = "frob ticket doable on this ledger completes in under 1 s, measured in a benchmark test with a generated 2,000-ticket ledger"
bound = true
+++

measured by timing the verbs: list 0.09 s, show 0.04 s, doable 7.57 s, doctor 1.52 s, frob test --dry-run selection 5.7 to 8.2 s (package graph rebuilt on each call).
