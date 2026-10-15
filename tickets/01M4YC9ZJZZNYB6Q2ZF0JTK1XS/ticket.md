+++
id = "01M4YC9ZJZZNYB6Q2ZF0JTK1XS"
title = "Rule coverage: exempt alias rules (COV003 aliases TEST001, never emitted) instead of allowlisting"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M480C43A6BCH54NX8C5DQ4WJ"
reporter = "lognd"
created = "2026-10-14T23:35:05Z"
updated = "2026-10-15T03:47:27Z"
scope = ["crates/gob-mdtest/**"]

[[acceptance]]
text = "gob_mdtest::coverage treats a declared alias rule as covered by its target (or exempts it); the COV003 allowlist entry is deleted; rule_coverage passes"
bound = true
+++

Found by ~K4JKY97: COV003 can never fire, so no fire block exists. See crates/frob-obligations/src/lib.rs COV003_ALIAS_OF.
