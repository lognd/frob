+++
id = "01M7E61BQ80VGD5FXMAP0V42TV"
title = "crunk: add the export figma-variables CLI verb"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-14T23:24:46Z"
updated = "2026-11-15T01:02:45Z"
scope = ["crates/crunk/src/export.rs", "crates/crunk/tests/it/export.rs", "docs/guides/crunk.md", "crates/gob-dev/profile.toml", "crates/crunk/src/lib.rs", "crates/crunk/tests/it/export_verb.rs", "docs/reference/cli/crunk.md"]

[[acceptance]]
text = "crunk export figma-variables emits the Figma variables JSON for a spec, with a test and a profile scenario and guide row"
bound = true
+++

found while working YC5VP5X: Target::FigmaVariables and its exporter exist; crates/crunk/src/export.rs needs an ExportFigmaVariables export_command!, plus the generated CLI docs
