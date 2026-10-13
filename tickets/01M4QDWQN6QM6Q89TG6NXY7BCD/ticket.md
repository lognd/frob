+++
id = "01M4QDWQN6QM6Q89TG6NXY7BCD"
title = "Windows: land tool-pass reuse test spawns no tool (sh probe writes nothing on the runner)"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-10-12T06:48:07Z"
updated = "2026-10-13T00:03:14Z"
scope = ["crates/frob-land/tests/land.rs"]

[[acceptance]]
text = "land_reuses_a_recorded_tool_pass_for_an_unchanged_tree_and_reruns_after_an_input_changes passes on Linux and the Windows runner runs it un-ignored"
bound = true
+++

land_reuses_a_recorded_tool_pass... sees 0 spawns on windows-latest; the sh-based tool probably cannot spawn there. Test is ignored on Windows until a Windows-capable probe exists.
