+++
id = "01M4DVRGX0KNTCDA8Q2YT46TP7"
title = "Tool definitions as data in the std pack: pinned version, version probe, version-ranged command variants, exit classes, parser id, config files, suppression pattern, id map, fix command"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M4D8X558Q07HCMEBP224NQP4"
reporter = "lognd"
created = "2026-10-08T13:38:05Z"
updated = "2026-10-16T13:08:13Z"
scope = ["changelog.d/**", "crates/gob-check/**", "crates/gob-packs/**", "docs/design/rules.md", "crates/frob-obligations/src/native.rs", "docs/reference/tool-stages.md", "docs/reference/config.md", "docs/schemas/config.json", "frob.toml", "docs/design/boundaries.md"]

[[acceptance]]
text = "Given a tool definition for zizmor and one for ruff, when frob check runs, then both stages run from data with no tool-specific Rust code beyond their parsers"
bound = true

[[acceptance]]
text = "Given a tool whose version falls in a renamed-flag range, when the stage runs, then the matching command variant is used"
bound = false
+++

docs/design/tool-binding.md section 2 (D122), after qlty plugin.toml and Trunk plugin.yaml. Existing zizmor and actionlint stages move to definitions. Results cached by (file digest, tool version, config digest); tools found on the project's own path first.
