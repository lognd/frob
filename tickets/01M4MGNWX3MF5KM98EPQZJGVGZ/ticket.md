+++
id = "01M4MGNWX3MF5KM98EPQZJGVGZ"
title = "frob check runs the grimble sibling as a second full pass: 54 s median (38% of a check) re-walking and re-parsing the same 13.5k files; share the walk and cache"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-11T03:39:06Z"
updated = "2026-10-11T18:25:51Z"
scope = ["crates/frob-check/**"]

[[acceptance]]
text = "the grimble sibling stage reuses the host's file walk and content digests, measured by frob check telemetry: sibling:grimble median under 15 s on this repository"
bound = true
+++

measured from .frob/telemetry.jsonl over 17 runs: median frob check 142 s, of which external tool stages 87 s, sibling:grimble 54 s, file-rules 30 s, obligations 11 s.
