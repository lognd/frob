+++
id = "01M5XCWY267M72G3GPYE2ZAPQ5"
title = "layout-solve JSON model: boxes, text runs, overflow, focus order, token bindings; deterministic serialization and schema"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CXRC0Z94MGD87PY9NH8B7X"
reporter = "lognd"
created = "2026-10-27T00:41:53Z"
updated = "2026-10-27T00:41:53Z"
labels = ["area:crunk"]
scope = ["crates/crunk-layout/src/output/**, crates/crunk-layout/tests/output*.rs, docs/schemas/crunk-layout-solve-v1.json"]

[[acceptance]]
text = "Given a solved tree, when serialized twice, then bytes are identical (stable key order, nodes in document order, no HashMap iteration). Edge cases: coordinates round to a fixed 1/64 px grid before serialization and -0.0 prints as 0; NaN or infinite values are a typed error; a node with zero width or height is emitted with a zero_size flag; overflow records which axis and by how much; an empty scene yields an empty node list not null; the output validates against the shipped schema and stays readable by the existing crunk_ingest::scene::LayoutSolve consumers (superset only)"
bound = false
+++

Design crunk.md section 3 (boxes, text runs and overflow, tab and focus order, computed token bindings). crunk-ingest already has a LayoutSolve for the JSON scene mini-solver; extend or share its types rather than duplicating them. Focus order comes from the existing FocusGraph in focus.rs.
