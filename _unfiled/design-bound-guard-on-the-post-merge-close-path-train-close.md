+++
id = "01M6PJRR6E92MAW2S15AYTWBET"
title = "design_bound guard on the post-merge close path (train_close)"
type = "bug"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-05T19:25:29Z"
updated = "2026-11-05T23:31:43Z"
scope = ["crates/frob-land/**", "crates/frob-ledger/**"]
+++

found while working ~2QTA3PK: DesignBoundGuard (PM038) runs on frob ticket close and frob land, but the post-merge close in train_close.rs does not run it, so a done close there bypasses PM038.
