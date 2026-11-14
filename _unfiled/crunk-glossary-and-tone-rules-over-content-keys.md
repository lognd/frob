+++
id = "01M5H5P5E98XTANP62H5TVTSC4"
title = "crunk: glossary and tone rules over content keys"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T06:44:58Z"
updated = "2026-11-14T13:39:36Z"
scope = ["crates/crunk-rules/**", "crates/crunk-spec/**", "docs/**"]

[[acceptance]]
text = "A content key whose text uses a glossary variant to avoid (CONTENT005) or a banned word (CONTENT006) from design/content/voice.toml is flagged, whole words only; keys using the preferred term or no banned word pass."
bound = true
+++

found while working ~VAAWD0R: glossary term enforcement and tone checks were cut.
