+++
id = "01M7BBZ1HGMWFJ3ZGEWXF2C1DD"
title = "frob-land test a_base_move_in_an_unrelated_crate_reuses_the_cargo_stage_pass_at_land fails on base"
type = "bug"
category = "todo"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-11-13T21:10:38Z"
updated = "2026-11-13T21:10:38Z"
scope = ["crates/frob-land/**"]

[[acceptance]]
text = "The test passes on experimental."
bound = false
+++

Stage runs twice where once is asserted; fails on bcd4801b77 independent of ~MM9Z56N.
