+++
id = "01M47RDFJX56SCTFTZJRQ1SC2B"
title = "Feed CrateDeps::implicit_usings_of into C# import resolution"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-06T04:44:11Z"
updated = "2026-10-21T23:21:28Z"
scope = ["crates/gob-symbols/src/csharp.rs", "crates/gob-symbols/src/graph/csharp.rs", "crates/gob-symbols/src/graph.rs", "crates/gob-symbols/tests/it/csharp.rs", "changelog.d/01M47RDFJX56SCTFTZJRQ1SC2B.added.md", "docs/design/code-model.md"]

[[acceptance]]
text = "Given a project with ImplicitUsings, when a C# file uses a type from an implicit namespace, then the import resolves"
bound = false

[[acceptance]]
text = "Given a project with Using Remove/Include items, when a C# file calls a type, then added namespaces resolve and removed ones do not"
bound = false

[[acceptance]]
text = "Given no ImplicitUsings, when a C# file uses a type from that namespace, then it stays unresolved"
bound = false
+++

found while working ~ECEBCQ1: dotnet.rs exposes project-wide implicit usings (ImplicitUsings plus Using items, per SDK) via CrateDeps::implicit_usings_of(path). csharp.rs/qualifier.rs import resolution (after ~JEN2C8Q) should consume it so calls on implicit-using namespaces are not left Unresolved.
