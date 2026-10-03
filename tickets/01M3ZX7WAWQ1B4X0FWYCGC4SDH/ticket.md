+++
id = "01M3ZX7WAWQ1B4X0FWYCGC4SDH"
title = "Effect broker: reads beneath the root without symlinks, tracked files only"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:35Z"
updated = "2026-10-03T03:34:35Z"
idempotency_key = "m2-sec-broker-reads"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-wasm/src/broker/read.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7S5JYVCTRD0ZYC57GJ93"

[[links]]
kind = "blocked-by"
target = "01M3ZX7VYSYT45N8ZKZJQ2DY5D"

[[acceptance]]
text = "Given a symlink inside the work tree pointing outside, when the guest requests it, then the broker denies the read"
bound = false

[[acceptance]]
text = "Given an untracked or ignored file and a file with link count 2, when requested, then both are denied"
bound = false
+++

Implements security.md section 2.5 (reads).

The parent performs granted reads: openat2 RESOLVE_BENEATH|RESOLVE_NO_SYMLINKS on Linux, component-wise O_NOFOLLOW elsewhere, tracked files only (the git index), refusing link count above 1, case-insensitive matching on case-insensitive file systems.
