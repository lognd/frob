+++
id = "01M5GRYE3TSB9Q1MWWZA2BMME2"
title = "Wire gob-mdtest check_garbage against real adapters"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T03:02:18Z"
updated = "2026-10-22T03:44:07Z"
scope = ["crates/frob-check/**"]

[[acceptance]]
text = "rule_matrix.rs calls check_garbage per rule against the real adapters and passes"
bound = true
+++

found while working ~SASXGW5: call gob_mdtest::garbage::check_garbage from crates/frob-check/tests/rule_matrix.rs per rule so real adapters are probed.
