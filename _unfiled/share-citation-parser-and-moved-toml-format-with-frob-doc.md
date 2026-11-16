+++
id = "01M5NCNPRJE2AFXWKSNFKPR5G3"
title = "Share citation parser and MOVED.toml format with frob doc remap"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-23T22:04:01Z"
updated = "2026-11-16T10:45:20Z"
labels = ["no-story", "good-first"]
scope = ["crates/gob-text/**"]

[[acceptance]]
text = "Given frob doc remap and a MOVED.toml consumer, when each parses a citation, then both call one shared parser in gob-text with no duplicate"
bound = false
+++

Share the citation parser and the MOVED.toml format with frob doc remap; coordinate with 01M4H0WXVXJ18DX9SVX6EHT0AD; ~Q1ZG43K defines the [moved] format.

## Start here
Find the citation parser used by frob doc remap, move it into crates/gob-text, and have both callers use the shared copy.
