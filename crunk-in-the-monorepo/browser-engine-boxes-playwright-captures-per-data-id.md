+++
id = "01M5XCXV74XZTCK4N56B46PAY4"
title = "Browser engine boxes: Playwright captures per-data-id bounding boxes in layout-solve JSON shape for a scene"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4CXRV40WWJQKHWJJBKJT1HZ"
reporter = "lognd"
created = "2026-10-27T00:42:23Z"
updated = "2026-10-27T00:42:23Z"
labels = ["area:crunk"]
scope = ["crates/crunk-gallery/node/boxes.mjs, crates/crunk-gallery/src/boxes.rs, crates/crunk-gallery/tests/boxes.rs"]

[[acceptance]]
text = "Given a scene and a viewport, when the browser engine runs, then JSON of per-data-id boxes in the solver output shape is produced. Edge cases: fonts not ready or animations on are refused by settling (fonts ready, animations off, fixed clock, network idle); a node missing from the DOM is listed as missing, not dropped; display:none nodes are emitted as hidden; playwright missing is the typed error with the install remedy and exit 2; a page that never settles is killed at the timeout and the cell marked failed; output is stable across 3 runs"
bound = false
+++

Design crunk.md section 3 (T2/T3 render). Reuse the existing render.mjs orchestration and gob-exec timeouts from crunk-gallery render; do not fork them. Needs a playwright-enabled CI job (optional).
