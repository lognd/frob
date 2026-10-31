+++
id = "01M67PBKDJP2WCYAAHMX41BW80"
title = "CAP: infer C# receiver type from var local initialised by a call"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-31T00:39:36Z"
updated = "2026-10-31T00:39:36Z"
scope = ["crates/gob-symbols/**"]

[[acceptance]]
text = "A var local initialised from a method call with a declared return type resolves its method calls through that type, or is reported Unresolved"
bound = false
+++

found while working VVKBEKG: var c = Make(); c.GetAsync(u) is silently clean today; needs return-type inference
