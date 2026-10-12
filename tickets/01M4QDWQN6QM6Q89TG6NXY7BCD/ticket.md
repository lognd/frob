+++
id = "01M4QDWQN6QM6Q89TG6NXY7BCD"
title = "Windows: land tool-pass reuse test spawns no tool (sh probe writes nothing on the runner)"
type = "bug"
category = "todo"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-10-12T06:48:07Z"
updated = "2026-10-12T06:48:07Z"
scope = ["crates/frob-land/tests/land.rs"]
+++

land_reuses_a_recorded_tool_pass... sees 0 spawns on windows-latest; the sh-based tool probably cannot spawn there. Test is ignored on Windows until a Windows-capable probe exists.
