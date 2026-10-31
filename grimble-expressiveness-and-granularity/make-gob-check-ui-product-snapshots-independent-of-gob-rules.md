+++
id = "01M69Q5CE25ZFVS4MA44MHNMZ6"
title = "Make gob-check ui_product snapshots independent of gob-rules source lines"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T19:32:09Z"
updated = "2026-10-31T20:05:27Z"
idempotency_key = "uiproduct-snapshot-fragile"
scope = ["crates/gob-rules/**", "crates/gob-check/**"]

[[acceptance]]
text = "ui_product stderr snapshots no longer quote gob-rules source lines, so re-indenting index.rs cannot break them"
bound = true
+++

The dup_id, dup_slug and retired_reused trybuild snapshots quote the describe(msg, &b).fail(); line in gob-rules index.rs and broke when assert_unique was re-indented (fixed by re-bless in ZMD06WA). Move the call into a stable helper or normalize the output.
