+++
id = "01M7EXT5474HCVF33F341E29JC"
title = "Generalize frob init stack detection to read tool-definition detect metadata"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:15Z"
updated = "2026-11-15T06:21:16Z"
idempotency_key = "static-research-k5"
labels = ["no-story"]

[[links]]
kind = "blocked-by"
target = "01M7EXT3X9DSSHYJWNQ4ZQPV00"

[[acceptance]]
text = "frob init output for an eslint, a dotnet and a ruff repo is byte-identical to today (golden test) while sourced from definitions"
bound = false

[[acceptance]]
text = "Adding a new definition with detect globs makes init suggest it with no Rust change"
bound = false
+++

Source: ~/projects/frob-research-static-analysis.md section 6 item 5. Rationale: frob init hard-codes eslint/dotnet/ruff stanzas (crates/frob/src, eslint stanza near line 52 of the init module). Remedy: drive detection from the [meta] detect field of std-pack tool definitions and emit stanzas from the definition, removing the hard-coded stanzas. Blocked by the frob tool verb ticket that introduces [meta] detect.
