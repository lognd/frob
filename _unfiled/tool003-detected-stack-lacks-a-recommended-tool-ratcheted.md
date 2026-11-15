+++
id = "01M7EXT64M1YDK6Y9DN9MCPYZK"
title = "TOOL003: detected stack lacks a recommended tool (ratcheted, info)"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:16Z"
updated = "2026-11-15T06:21:16Z"
idempotency_key = "static-research-k6"
labels = ["no-story"]

[[links]]
kind = "blocked-by"
target = "01M7EXT3X9DSSHYJWNQ4ZQPV00"

[[acceptance]]
text = "TOOL003 fires on a fixture repo with a python stack and no ruff stage and is silent once the stage is added"
bound = false

[[acceptance]]
text = "Rule page documents TOOL003 and its default severity/off-in-baseline behavior"
bound = false
+++

Source: ~/projects/frob-research-static-analysis.md section 6 item 6, section 4.3 step 5. Rationale: a repo can have a detected stack with no linter bound and nobody is told. Remedy: new check rule TOOL003 that fires when a stack matched by a definition's [meta] detect has no configured stage for a recommended tool; ratcheted, default off in baselines of strict repos. Verify first that TOOL003 is unused: grep the rule registry for TOOL0 ids before allocating. Blocked by the frob tool verb ticket ([meta] detect).
