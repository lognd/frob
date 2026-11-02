+++
id = "01M4PN6PPRKZC9J8G6XNRMXHHR"
title = "frob-lease depends on frob-release: lease sits below release in the layer table (audit M9)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-11T23:36:39Z"
updated = "2026-11-02T08:21:08Z"
scope = ["crates/frob-lease/**", "crates/frob-release/**", "crates/gob-dev/tests/layering.rs"]

[[acceptance]]
text = "Given the workspace, when cargo metadata is read, then frob-lease has no dependency on frob-release and the layering allow-list has no frob-lease row"
bound = true
+++

Found by the layering test (~CJXZJ2V). frob-lease -> frob-release goes up a layer. Move what lease needs from release down (or invert the edge), then delete the allow-list row in crates/gob-dev/tests/layering.rs.
