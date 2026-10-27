+++
id = "01M5XCW9WCHSZBR5F29VKYBM25"
title = "crunk outline, search and guidelines read verbs (token-economy design-system access for agents, served over MCP)"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CXQTERP5YASZGVEAH6KG4H"
reporter = "lognd"
created = "2026-10-27T00:41:33Z"
updated = "2026-10-27T00:41:33Z"
labels = ["area:crunk"]
scope = ["crates/crunk/src/outline.rs, crates/crunk/src/guidelines.rs, crates/crunk/tests/outline.rs"]

[[acceptance]]
text = "Given a project, when crunk outline runs, then a sparse tree of tokens, components, screens and flows (ids and one-line summaries only) is returned; given an id, then outline --node drills into only that node; given crunk guidelines, then the agent-guidelines file is returned; given crunk serve, then all three appear as read-only MCP tools"
bound = false
+++

Design crunk.md section 5 interop row (serve: outline first, drill into nodes, search over the design system, the code map, an agent-guidelines file). Reuse crunk query find and crunk map for search and code map; do not duplicate them. Read-only: the patch tool is in the phase 3 epic.
