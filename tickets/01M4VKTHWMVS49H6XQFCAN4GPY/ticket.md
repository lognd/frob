+++
id = "01M4VKTHWMVS49H6XQFCAN4GPY"
title = "boundaries.md still lists frob-gh after the crate was removed: gob-dev layering test fails on experimental"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "high"
points = 1
reporter = "lognd"
created = "2026-10-13T21:48:45Z"
updated = "2026-10-15T05:21:17Z"
scope = ["docs/design/boundaries.md"]
+++

found while working ~TXC59AG: gob-dev::layering workspace_layering_holds_and_every_crate_has_a_layer reports unknown frob-gh (rows at lines 98, 200, 339, 366 of docs/design/boundaries.md). Any workspace-wide frob test run fails.
