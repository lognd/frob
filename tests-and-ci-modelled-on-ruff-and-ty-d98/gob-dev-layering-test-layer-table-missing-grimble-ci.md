+++
id = "01M5FH32SRA9JWGMTJ9KCX28FW"
title = "gob-dev layering test: layer table missing grimble-ci"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-21T15:25:47Z"
updated = "2026-10-21T17:31:46Z"
scope = ["crates/gob-dev/tests/layering.rs"]

[[acceptance]]
text = "Given the workspace, when the layering test runs, then every crate including grimble-ci has a layer and the test passes"
bound = false
+++

found while working ~9HS3VP7: workspace_layering_holds_and_every_crate_has_a_layer fails on base too
