+++
id = "01M626H3HBFQZ86PPTDYQ8ZG91"
title = "crunk new component skeleton lacks CRAFT002 interaction states"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-28T21:26:47Z"
updated = "2026-11-15T21:42:12Z"
scope = ["crates/crunk/src/new/**", "crates/crunk/src/new.rs", "crates/crunk/tests/it/new.rs"]

[[acceptance]]
text = "The crunk new component skeleton passes crunk check with no CRAFT002 finding"
bound = true
+++

found while working WJH9CR5: new.rs test filters CRAFT002 out of the skeleton validation
