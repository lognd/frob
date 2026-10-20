+++
id = "01M3ZX7WF3VNDYXFTWX2KGCRVN"
title = "Effect broker: writes beneath the root, never the control plane"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:35Z"
updated = "2026-10-03T03:34:35Z"
idempotency_key = "m2-sec-broker-writes"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-wasm/src/broker/write.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7WAWQ1B4X0FWYCGC4SDH"

[[acceptance]]
text = "Given a write to frob.toml or .git/hooks/pre-commit, when requested, then it is denied regardless of grants"
bound = false

[[acceptance]]
text = "Given a granted write to a new file under src/, when performed, then the byte count appears in the summary"
bound = false
+++

Implements security.md section 2.5 (writes) and 2.6.

Tracked or new files only; the control plane list (configs, locks, packs, CI definitions, CODEOWNERS, state, trust store) is refused; byte counts reported.
