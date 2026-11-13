+++
id = "01M78RWCD8SY69H44WENCV14W4"
title = "CAP: collapse empty-callee computed use into one unresolved finding instead of reaching every vocab atom"
type = "bug"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-11-12T20:58:39Z"
updated = "2026-11-13T06:52:22Z"
labels = ["good-first", "no-story"]
scope = ["crates/grimble-bind/**"]

[[acceptance]]
text = "Empty-callee computed use yields one unresolved finding, covered by a test."
bound = false
+++

Collapse empty-callee computed use into one Unresolved CAP finding instead of reaching every vocab atom.

## Start here

Find the CAP computed-use path in crates/grimble-bind caps and emit a single finding when the callee is empty.
