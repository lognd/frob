+++
id = "01M5HMPQB3WG50FBPZ3TQNJ1XC"
title = "TypeScript interface and inherited method dispatch from annotated receivers"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T11:07:25Z"
updated = "2026-10-23T00:15:19Z"
scope = ["crates/gob-symbols/src/graph/typescript.rs"]

[[acceptance]]
text = "Given a TypeScript receiver annotated with an interface, when a method is called on it, then the call graph links the call to the interface method declaration"
bound = false

[[acceptance]]
text = "Given a class extending a base class that defines the method, when called on an annotated receiver of the derived type, then the call links to the inherited method"
bound = false
+++

found while working ~69D9E89
