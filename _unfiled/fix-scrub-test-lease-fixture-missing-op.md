+++
id = "01M5GW08PF9XDMEQNN8KJE2ZQF"
title = "Fix scrub test lease fixture missing op"
type = "bug"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-22T03:55:44Z"
updated = "2026-10-22T03:55:47Z"
scope = ["crates/frob-ledger/tests/scrub.rs"]

[[acceptance]]
text = "frob-ledger scrub tests pass with a lease event carrying op"
bound = false
+++

The hand-written lease event in fixture() lacks the now-required op field, so 3 scrub tests fail with missing field 'op'.
