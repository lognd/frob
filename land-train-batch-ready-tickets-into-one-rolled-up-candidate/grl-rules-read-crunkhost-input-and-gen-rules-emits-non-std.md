+++
id = "01M5ETSEBZ7PV63NBN0474HWJV"
title = "GRL rules read CrunkHost input and gen rules emits non-std pack target"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-21T08:56:03Z"
updated = "2026-11-09T18:41:11Z"
scope = ["crates/gob-dev/src/render/std_rules.rs", "packs/crunk-core/**", "docs/design/shared/rules.md", "docs/design/shared/packs-and-plugins.md"]
+++

Split from ~CZSG7YJ. Rules must read CrunkHost (spec + stylesheet index) rather than a code-model tree, and cargo dev gen rules must emit a non-std pack against a non-gob host; then wire crunk.json into the pack and drop exceptions.toml entries.
