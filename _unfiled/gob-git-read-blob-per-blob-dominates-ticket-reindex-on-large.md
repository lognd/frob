+++
id = "01M5JCT8CXN20B2GJHAE5JDHHC"
title = "gob-git: read_blob per blob dominates ticket reindex on large ledgers"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T18:08:47Z"
updated = "2026-10-22T19:49:55Z"
scope = ["crates/gob-git/src/read.rs", "crates/gob-git/tests/read_blobs.rs"]

[[acceptance]]
text = "Given a large ledger, when reindex_plan reads blobs, then it uses a batched read (cat-file --batch or equivalent) and results are identical to per-blob reads"
bound = false

[[acceptance]]
text = "Given a measured benchmark or timing test, when run, then blob-read time is lower than the per-blob baseline, with numbers reported"
bound = false
+++

found while working ~GQ3NZVK: reading 20k blobs one by one in Ledger::reindex_plan costs ~370ms of the remaining ~750ms warm reindex. Consider a batched or parallel blob read, or skipping unchanged blobs.
