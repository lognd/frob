+++
id = "01M40H2JYVEHBZD62WV8Z6EXFW"
title = "gob-directives: stacked directives above one item bind only the last one"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T09:21:13Z"
updated = "2026-10-03T14:25:02Z"
idempotency_key = "m2-stacked-directives-bind"
labels = ["milestone:2", "release:0.532.0"]
scope = ["crates/gob-directives/**", "crates/frob-ack/src/inputs.rs", "docs/design/code-model.md"]

[[acceptance]]
text = "Given three frob:tests directives stacked above one test, when directives are bound, then all three bind to that test and TEST001 reports none unbound"
bound = true
+++

Found on ~KHXV2X7: several frob:tests lines stacked above one test function bind only the last to the item, so TEST001 reports the others as unbound and authors must split them. A directive block (consecutive directive lines, optionally interleaved with ordinary comments or attributes) above an item must bind every directive in it to that item. Add tests with two and three stacked frob:tests lines, mixed with #[test] and doc comments, in Rust and in markdown (HTML comments above a heading).
