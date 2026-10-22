+++
id = "01M5JCT8CXN20B2GJHAE5JDHHC"
title = "gob-git: read_blob per blob dominates ticket reindex on large ledgers"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-22T18:08:47Z"
updated = "2026-10-22T18:08:47Z"
scope = ["crates/gob-git/src/read.rs"]
+++

found while working ~GQ3NZVK: reading 20k blobs one by one in Ledger::reindex_plan costs ~370ms of the remaining ~750ms warm reindex. Consider a batched or parallel blob read, or skipping unchanged blobs.
