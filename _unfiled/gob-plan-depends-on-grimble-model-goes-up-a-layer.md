+++
id = "01M5FRCMBS9DHQ223JWGN6RNW7"
title = "gob-plan depends on grimble-model (goes up a layer)"
type = "bug"
category = "todo"
priority = "low"
reporter = "lognd"
created = "2026-10-21T17:33:20Z"
updated = "2026-10-21T17:33:20Z"
+++

Found while working ~KCX28FW: gob-plan (layer 6) uses grimble_model in crates/gob-plan/src/examples/side.rs; move that code or invert the dependency, then drop the ALLOWED row in crates/gob-dev/tests/layering.rs.
