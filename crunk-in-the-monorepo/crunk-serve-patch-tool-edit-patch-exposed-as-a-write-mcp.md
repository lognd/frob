+++
id = "01M5XCW9ZZ5GX5VGERB6H96M2G"
title = "crunk serve patch tool: edit --patch exposed as a write MCP tool with touched-node findings"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CXR6ER06SRMEJGSZ20JD5Q"
reporter = "lognd"
created = "2026-10-27T00:41:33Z"
updated = "2026-10-27T00:41:33Z"
labels = ["area:crunk"]
scope = ["crates/crunk/src/serve_patch.rs, crates/crunk/tests/serve_patch.rs"]

[[acceptance]]
text = "Given an MCP client, when it calls the patch tool with an RFC 6902 patch addressed by stable id, then the diff and the findings of the touched nodes are returned; given a patch that fails schema validation, then nothing is written and a located error is returned; given a read-only serve session (no --allow-write), then the tool is absent"
bound = false
+++

Design crunk.md section 9 item 3 ("the serve patch tool"). Wrap the existing edit.rs Edit logic; no second patch engine. Write tools must be opt-in on the serve command.
