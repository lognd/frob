+++
id = "01M4X779QGF0CRSE952A3BARD0"
title = 'GRL lowering: kind with a string argument (directive "todo")'
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "logan"
created = "2026-10-14T12:47:00Z"
updated = "2026-10-14T14:32:10Z"
scope = ["crates/gob-plan/**"]
+++

Found while working ~C6W2KWJ. TODO001 (acceptance corpus ~0HC06TD) has `no d: directive "todo" where d adjoins c`; lowering reports "cannot lower a kind with a string argument yet" (convert.rs binding_parts and with_object). Covered by none of ~C6W2KWJ ~26X4K6K ~8Q9444T ~NVMH9MV ~HZ73YP7. Needs a decision on which field of the node the argument tests, and executor/model support for directive nodes.
