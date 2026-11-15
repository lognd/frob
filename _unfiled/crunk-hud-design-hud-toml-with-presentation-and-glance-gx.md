+++
id = "01M7EXXAY30XADWZ1GYNA31YR6"
title = "crunk HUD: design/hud/*.toml with presentation and glance GX checks"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M7ETB6R3R5EEZ7XCX8GDRZXJ"
reporter = "lognd"
created = "2026-11-15T06:22:00Z"
updated = "2026-11-15T06:22:00Z"
idempotency_key = "crunkplan-f5403cae5f31"
labels = ["no-story"]

[[acceptance]]
text = "a peripheral element signalling by hue alone raises a finding"
bound = false

[[acceptance]]
text = "a peripheral text longer than two glyphs raises a finding"
bound = false
+++

Source: ~/projects/frob-research-ui.md, section T10.
Remedy: parse hud files (presentation, glance, priority); GX rules for peripheral text length, hue-only state and luminance delta
Crates/files: crates/crunk-spec, crates/crunk-rules gx
Keep any new heuristic advisory and dated; a clean run means no known defect, not quality.
