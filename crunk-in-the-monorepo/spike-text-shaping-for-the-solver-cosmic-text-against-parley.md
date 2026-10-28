+++
id = "01M4CXRCXEYE7GZSYRPHKN808M"
title = "Spike: text shaping for the solver, cosmic-text against parley over bundled fonts (width agreement with Chromium, speed, determinism)"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CXRC0Z94MGD87PY9NH8B7X"
reporter = "lognd"
created = "2026-10-08T04:53:43Z"
updated = "2026-10-28T12:55:54Z"
labels = ["no-story"]
scope = ["changelog.d/**", "crates/crunk-layout/**", "notes/research/**"]

[[acceptance]]
text = "Given 200 strings in 3 fonts, when measured by both libraries and Chromium, then the report gives width deltas, timing and a recorded choice"
bound = false
+++

docs/design/crunk.md section 3. Record the measurement; decide and update the design.

no-story: internal engineering task in crunk-layout; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
