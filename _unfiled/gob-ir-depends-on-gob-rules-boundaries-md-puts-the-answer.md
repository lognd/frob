+++
id = "01M4PN6PKHXPXK9G4EA3CCNEW9"
title = "gob-ir depends on gob-rules: boundaries.md puts the answer lattice in gob-ir under gob-rules (audit M9)"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-11T23:36:39Z"
updated = "2026-10-27T02:58:17Z"
scope = ["crates/gob-ir/**", "crates/gob-rules/**"]
+++

Found by the layering test (~CJXZJ2V). Design: gob-rules uses the answer lattice from gob-ir; today gob-ir -> gob-rules goes up the layer table. Move the shared types so the edge points down, then delete the allow-list row in crates/gob-dev/tests/layering.rs.
