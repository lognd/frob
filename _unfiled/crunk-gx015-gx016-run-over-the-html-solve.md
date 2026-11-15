+++
id = "01M7EXSH6H0HVPK55GXKXNXNZR"
title = "crunk GX015/GX016: run over the html solve"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M7ETKAPM2000N80NA0W5NAM5"
reporter = "lognd"
created = "2026-11-15T06:19:55Z"
updated = "2026-11-15T06:19:57Z"
idempotency_key = "crunkplan-7c5816816eb4"
labels = ["no-story"]

[[links]]
kind = "blocked-by"
target = "01M7EXSFWBE6NF7KTA3R2C2421"

[[acceptance]]
text = "GX015 flags an html scene element outside the safe area"
bound = false

[[acceptance]]
text = "GX016 flags undersized text in an html scene"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding H8.
Evidence: GX015 safe area and GX016 text size do not use the html solve
Remedy: feed them solve boxes
Crates/files: crates/crunk-rules gx rules
Verify against HEAD first; the audit ran on a stale binary.
