+++
id = "01M53Q07K4MZH7ZARNA59MPZGY"
title = "ticket scope/lease widen can loop, committing one tickets(update) per changelog fragment"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-17T01:18:12Z"
updated = "2026-10-17T05:42:09Z"
scope = ["crates/frob-pm/**", "crates/frob-ledger/src/ops.rs", "crates/frob-ledger/tests/ledger.rs"]

[[acceptance]]
text = "A scope edit exceeding 64 globs is refused and repeats dedupe"
bound = true
+++
