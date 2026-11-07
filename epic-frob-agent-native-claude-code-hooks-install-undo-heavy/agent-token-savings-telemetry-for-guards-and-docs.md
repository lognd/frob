+++
id = "01M4P2N20QFNBWY0GMKG0YE19W"
title = "agent: token-savings telemetry for guards and docs"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M4P2MQ9EDGX3NCSBRS0H1AYB"
reporter = "lognd"
created = "2026-10-11T18:12:27Z"
updated = "2026-11-07T06:07:28Z"
scope = ["docs/**", "crates/frob/**"]

[[acceptance]]
text = "each guard logs bytes avoided to .frob/telemetry.jsonl"
bound = true

[[acceptance]]
text = "docs describe install, uninstall, ownership markers, hooks and the heavy profile"
bound = true
+++
