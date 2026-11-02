+++
id = "01M6DEF8W2KCZ331FB0XAY9FYQ"
title = "layering test reads docs/design/boundaries.md, which moved to docs/design/shared/charter.md"
type = "bug"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-11-02T06:17:13Z"
updated = "2026-11-02T09:09:09Z"
scope = ["crates/gob-dev/tests/layering.rs"]

[[acceptance]]
text = "workspace_layering_holds_and_every_crate_has_a_layer reads docs/design/shared/charter.md and passes"
bound = true
+++

found while working ~NRMXHHR: workspace_layering_holds_and_every_crate_has_a_layer unwraps a missing file (layering.rs:185); the layer table now lives in docs/design/shared/charter.md
