+++
id = "01M5XCXVAR2WSR1H6X5X7ETR1R"
title = "crunk render --engine browser: PNG and boxes through the gallery renderer"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CXRV40WWJQKHWJJBKJT1HZ"
reporter = "lognd"
created = "2026-10-27T00:42:23Z"
updated = "2026-10-27T00:42:24Z"
labels = ["area:crunk"]
scope = ["crates/crunk/src/render_browser.rs, crates/crunk/tests/render_browser.rs"]

[[links]]
kind = "blocked-by"
target = "01M5XCXV74XZTCK4N56B46PAY4"

[[acceptance]]
text = "Given a screen, when crunk render --engine browser runs, then a hashed PNG and a boxes JSON are written beside the solve output; given a build without the gallery feature, then it reports not built in with the remedy and exits 2; given --engine solve and --engine browser on one screen, then both outputs share the same node ids"
bound = false
+++

Design crunk.md section 5 render row. Depends on the solve render verb for the shared flags. Thin wrapper over crunk-gallery render and the boxes capture.
