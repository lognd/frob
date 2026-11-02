+++
id = "01M4PN6PKHXPXK9G4EA3CCNEW9"
title = "gob-ir depends on gob-rules: boundaries.md puts the answer lattice in gob-ir under gob-rules (audit M9)"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-11T23:36:39Z"
updated = "2026-11-02T08:36:10Z"
scope = ["crates/gob-ir/**", "crates/gob-rules/**"]

[[acceptance]]
text = "gob-ir has no gob-rules dependency; the finding vocabulary lives in gob-ir::vocab and gob-rules re-exports it"
bound = false
+++

Found by the layering test (~CJXZJ2V). Design: gob-rules uses the answer lattice from gob-ir; today gob-ir -> gob-rules goes up the layer table. Move the shared types so the edge points down, then delete the allow-list row in crates/gob-dev/tests/layering.rs.
