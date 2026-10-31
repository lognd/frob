+++
id = "01M67PBKM5106NHVXDKS9WT4C2"
title = "CAP: TypeScript untyped-parameter and generic receivers report Unresolved"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-31T00:39:36Z"
updated = "2026-10-31T00:39:36Z"
scope = ["crates/gob-symbols/**"]

[[acceptance]]
text = "A method call on an untyped parameter or generic type-parameter receiver whose name is a capability method (e.g. listen) is reported Unresolved rather than silently clean, without flooding unrelated code"
bound = false
+++

found while working VVKBEKG: function go(app) { app.listen(8080) } is silently clean; also C# generic T receivers
