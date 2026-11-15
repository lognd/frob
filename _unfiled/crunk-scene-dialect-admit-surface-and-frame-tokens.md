+++
id = "01M7EXWNXE1W01DJEEABRWXEPY"
title = "crunk scene dialect: admit surface and frame tokens"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M7ETB6DKRHKAHRBA2NCGNQTB"
reporter = "lognd"
created = "2026-11-15T06:21:38Z"
updated = "2026-11-15T06:21:39Z"
idempotency_key = "crunkplan-ea4582d3e6f7"
labels = ["no-story"]

[[links]]
kind = "blocked-by"
target = "01M7EXWNDAT5YXREKS0AADJ4WY"

[[links]]
kind = "blocked-by"
target = "01M7EXWNMZVTG99EX1ZQHXNDXR"

[[acceptance]]
text = "a scene using a surface token solves with no PORT finding"
bound = false
+++

Source: ~/projects/frob-research-ui.md, section T3.
Remedy: let scenes bind material tokens; remove PORT findings for them
Crates/files: crates/crunk-ingest scene, crates/crunk-rules
Keep any new heuristic advisory and dated; a clean run means no known defect, not quality.
