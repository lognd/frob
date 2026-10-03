+++
id = "01M3ZX7ZHBHNASXSNNCMHSZ4M6"
title = "Renderer: help, note, fix and explain lines; secondary spans; quiet drops help"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3ZX76ZV963F3AXRKJ8F744N"
reporter = "lognd"
created = "2026-10-03T03:34:38Z"
updated = "2026-10-03T03:34:38Z"
idempotency_key = "m2-diag-render-help"
labels = ["milestone:2", "area:diagnostics"]
scope = ["crates/gob-diagnostics/src/text.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7E968R74N08V8DW4RJVG"

[[acceptance]]
text = "Given a finding with a secondary span in another file and a maybe-incorrect fix, when rendered as text, then the snapshot matches the diagnostics.md section 2 example"
bound = false

[[acceptance]]
text = "Given --quiet, when rendered, then help lines are dropped and the message, span and code remain"
bound = false
+++

Implements diagnostics.md section 2.

Message shape of section 2: primary span with label, `:::` secondary spans in other files, note for facts, help for the next action, `= fix (needs review): ...` only when a machine fix exists, explain line, ASCII only, colour only on a terminal.
