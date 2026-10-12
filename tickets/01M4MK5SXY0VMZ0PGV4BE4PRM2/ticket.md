+++
id = "01M4MK5SXY0VMZ0PGV4BE4PRM2"
title = "REF001 per-file cache key uses the ledger tip, so every ticket event misses all 14k files"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-11T04:22:44Z"
updated = "2026-10-12T07:58:38Z"
scope = ["crates/frob-check/src/filecheck.rs", "crates/frob-check/src/snapshot.rs", "crates/frob-obligations/src/**", "crates/frob-check/tests/**"]

[[acceptance]]
text = "a second frob check after an unrelated ledger event has file_hits equal to file_misses of the first run (no per-file recompute), covered by a test"
bound = true

[[acceptance]]
text = "creating or deleting a ticket that a file references changes that file's REF001 key (miss), covered by a test"
bound = true
+++

Found by ~1NN2YCK. The 23 percent hit rate has two causes: (1) engine keyed on exe bytes (fixed in ~1NN2YCK), (2) ObligationFileCheck::side_input for REF001 returns FrobShared.ledger_tip, which moves on every ticket event in any worktree. decode_all needs every rule key of a file to hit, so one stale REF001 key recomputes all four rules for every file (cache holds 12k REF001 rows vs 4k for DOC001 = 3 tips). Fix: key REF001 by the sorted set of ticket ids referenced in the file text whose standing is not Open/Terminal (empty when none), computed from a per-run set built in collect(). Mutating a referenced ticket must miss; an unrelated ticket event must hit. Measure cached_hits/files on a second run with a ticket event in between.
