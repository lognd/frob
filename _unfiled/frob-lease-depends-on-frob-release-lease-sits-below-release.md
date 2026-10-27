+++
id = "01M4PN6PPRKZC9J8G6XNRMXHHR"
title = "frob-lease depends on frob-release: lease sits below release in the layer table (audit M9)"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-11T23:36:39Z"
updated = "2026-10-27T02:58:17Z"
scope = ["crates/frob-lease/**", "crates/frob-release/**"]
+++

Found by the layering test (~CJXZJ2V). frob-lease -> frob-release goes up a layer. Move what lease needs from release down (or invert the edge), then delete the allow-list row in crates/gob-dev/tests/layering.rs.
