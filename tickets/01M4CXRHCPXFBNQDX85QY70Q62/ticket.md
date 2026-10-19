+++
id = "01M4CXRHCPXFBNQDX85QY70Q62"
title = "LAYOUT and RESP rules at T1: overflow, overlap, clipping, safe area, target size, breakpoint coverage"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M4CXRC0Z94MGD87PY9NH8B7X"
reporter = "lognd"
created = "2026-10-08T04:53:48Z"
updated = "2026-10-19T10:18:17Z"
scope = ["changelog.d/**", "crates/crunk-check/**", "crates/crunk-rules/**", "crates/crunk-ingest/**", "crates/crunk-spec/**"]

[[links]]
kind = "blocked-by"
target = "01M4S9HRETE0RW4H034W1H7QCD"

[[acceptance]]
text = "Given fire and clean scenes per rule, when checked at T1, then each fires only on its fire case"
bound = false
+++

docs/design/crunk.md section 6.
