+++
id = "01M68WXG3TC3A8Q3J1PF7KJVS9"
title = "HTTP layer: constant and symbolic evaluation of client and server path strings"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-31T11:53:28Z"
updated = "2026-10-31T11:53:28Z"
scope = ["crates/gob-frameworks/**"]

[[acceptance]]
text = "A path passed as a const, Python module constant or Rust const resolves through const_value so it is Must instead of Unknown."
bound = false
+++

Found while working ~0ETTMMF. A Ref-only path is currently opaque.
