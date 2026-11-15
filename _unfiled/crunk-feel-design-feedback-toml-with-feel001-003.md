+++
id = "01M7EXXARE5R3DYSSY882AY7J8"
title = "crunk feel: design/feedback.toml with FEEL001-003"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M7ETB6R3R5EEZ7XCX8GDRZXJ"
reporter = "lognd"
created = "2026-11-15T06:21:59Z"
updated = "2026-11-15T06:21:59Z"
idempotency_key = "crunkplan-2e5164bcf5a4"
labels = ["no-story"]

[[acceptance]]
text = "FEEL001 and FEEL002 fire on fixtures"
bound = false

[[acceptance]]
text = "FEEL003 is not enabled until a sourced threshold is recorded"
bound = false
+++

Source: /home/logan/projects/frob-research-ui.md, section T10.
Remedy: parse feedback.toml (channels, latency budget, reduced variant); FEEL001 single channel, FEEL002 no reduced variant, FEEL003 latency over budget (needs a sourced number first)
Crates/files: crates/crunk-spec, crates/crunk-rules
Keep any new heuristic advisory and dated; a clean run means no known defect, not quality.
