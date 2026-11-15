+++
id = "01M7EY9JR9AA7HEEYP80TK0VE7"
title = "crunk render --frames: filmstrip per flow edge and state change"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M7ETB6R3R5EEZ7XCX8GDRZXJ"
reporter = "lognd"
created = "2026-11-15T06:28:41Z"
updated = "2026-11-15T06:28:41Z"
idempotency_key = "crunkplan-997bf492fef4"
labels = ["no-story"]

[[acceptance]]
text = "frames 4 writes four frames per state change deterministically"
bound = false
+++

Source: ~/projects/frob-research-ui.md, section T9.
Remedy: render --frames N --at MS under the fixed clock; depends on browser engine ~X7ETR1R
Crates/files: crates/crunk render, crates/crunk-gallery
Keep any new heuristic advisory and dated; a clean run means no known defect, not quality.
