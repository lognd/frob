+++
id = "01M5XCXVJBTE8064EAX8E4PP6F"
title = "T2 rendered contrast over images and gradients"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4CXRV40WWJQKHWJJBKJT1HZ"
reporter = "lognd"
created = "2026-10-27T00:42:24Z"
updated = "2026-10-27T00:42:24Z"
labels = ["area:crunk"]
scope = ["crates/crunk-gallery/src/rendered_contrast.rs, crates/crunk-gallery/tests/rendered_contrast.rs"]

[[links]]
kind = "blocked-by"
target = "01M5XCXV74XZTCK4N56B46PAY4"

[[acceptance]]
text = "Given a rendered PNG with text over a gradient, when checked, then CONTRAST finds the worst-case text/background pair by sampling and reports it with the pixel region. Edge cases: text over a fully transparent area falls back to the page background; text bounding box smaller than 1 px is skipped with a note; an image with alpha is composited over the declared surface; a uniform background reports exactly the declared ratio; large text uses the 3:1 threshold; missing PNG is Unresolved not run"
bound = false
+++

Design crunk.md section 4 T2 row. Pure function over Image from visual.rs plus boxes from the boxes capture, so it is unit testable without a browser.
