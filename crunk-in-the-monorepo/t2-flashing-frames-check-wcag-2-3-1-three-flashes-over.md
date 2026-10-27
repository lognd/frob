+++
id = "01M5XCXVQXDWR7J92VZDBK0E3V"
title = "T2 flashing-frames check (WCAG 2.3.1 three flashes) over captured frame sequences"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CXRV40WWJQKHWJJBKJT1HZ"
reporter = "lognd"
created = "2026-10-27T00:42:24Z"
updated = "2026-10-27T00:42:24Z"
labels = ["area:crunk"]
scope = ["crates/crunk-gallery/src/flashing.rs, crates/crunk-gallery/tests/flashing.rs"]

[[acceptance]]
text = "Given a frame sequence with 4 general flashes in one second, when checked, then a finding names the frame range; given 3 flashes it passes. Edge cases: a flash is a luminance change of at least 10 percent of max with the dark frame under 0.8; red flashes use the red threshold; a sequence under 2 frames is Unresolved; flashes covering under 25 percent of a 10-degree field are ignored; frame timestamps not monotonic are a typed error"
bound = false
+++

Design crunk.md section 4 T2 row (flashing frames). Pure frame-sequence logic over Image; capture hookup is out of scope.
