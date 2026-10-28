+++
id = "01M61MM4B45XV6D9W5R0N355KY"
title = "org R2: delete duplicate CI rule declarations from gob-check"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M61MHM8ER57BA9VVKXDTE2G7"
reporter = "lognd"
created = "2026-10-28T16:13:51Z"
updated = "2026-10-28T18:29:45Z"
scope = ["crates/gob-check/**"]

[[acceptance]]
text = "each CI id declared once; ratchet test fails on duplicates"
bound = false
+++

Org audit step; see section 4.7 of the Opus org audit report (scratchpad org-audit.md).
