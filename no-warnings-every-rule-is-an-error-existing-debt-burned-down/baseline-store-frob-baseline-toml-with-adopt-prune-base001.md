+++
id = "01M5XMJH35MV9Z2PFF27FDF275"
title = "Baseline store: frob-baseline.toml with adopt, prune, BASE001, BASE002"
type = "task"
category = "todo"
priority = "high"
points = 8
parent = "01M5XETK612GJ5QZZZXBA6CSGY"
reporter = "lognd"
created = "2026-10-27T02:56:01Z"
updated = "2026-10-27T02:56:01Z"
scope = ["crates/gob-rules/**"]

[[acceptance]]
text = "frob baseline adopt/prune exist; file is sorted TOML keyed by Finding::fingerprint; land prunes on the merge tree"
bound = false

[[acceptance]]
text = "BASE001 fails any key growth versus the base tip; BASE002 fails a table without a live ticket; ratchet lock migrates once"
bound = false
+++

Implements docs/design/rules.md section 6.1 (rules.md 6.1.2). Filed from ~ZHW5Y2M.
