+++
id = "01M5XCWA755KFHEMG04HPZ4WYW"
title = "crunk new flow and crunk new token plus --from templating"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M4CXR6ER06SRMEJGSZ20JD5Q"
reporter = "lognd"
created = "2026-10-27T00:41:33Z"
updated = "2026-10-27T00:41:33Z"
labels = ["area:crunk"]
scope = ["crates/crunk/src/new.rs, crates/crunk/tests/new_flow_token.rs"]

[[acceptance]]
text = "Given crunk new flow checkout, when run, then a valid flow file with a stable id is created and passes schema; given crunk new token color.brand --from color.base, then the new token aliases the source; given an existing name, then exit 2 and nothing is overwritten"
bound = false
+++

Design crunk.md section 5 author row. First verify which of component|screen|flow|token new.rs already supports and only add the missing ones; if all are present, close with evidence instead of adding code.
