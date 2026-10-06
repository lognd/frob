+++
id = "01M44YQTCDPH87ASRMSJEN2C8Q"
title = "gob-symbols: C# usings, imports and calls"
type = "story"
category = "in-progress"
priority = "high"
points = 5
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-05T02:36:58Z"
updated = "2026-10-06T05:44:51Z"
idempotency_key = "d94-calls"
scope = ["crates/gob-symbols/src/csharp.rs", "crates/gob-symbols/src/qualifier.rs", "crates/gob-symbols/src/stdtypes.rs", "crates/gob-symbols/src/graph/**", "crates/gob-symbols/src/graph.rs", "crates/gob-symbols/src/view.rs", "crates/gob-symbols/tests/csharp.rs", "crates/gob-symbols/tests/snapshots/corpus__csharp_group.snap", "crates/gob-symbols/src/graph/csharp.rs"]

[[links]]
kind = "blocked-by"
target = "01M44YQSZ3YEXRDW9RKER9HRA2"

[[acceptance]]
text = "Given a C# project whose methods call each other across namespaces through using and using static, when the graph is built, then the call edges resolve to the callee units"
bound = true

[[acceptance]]
text = "Given a call on a receiver whose type is not known, when the graph is built, then the edge is Unresolved and COV001 does not count it as reached"
bound = true

[[acceptance]]
text = "Given global using and alias using directives, when imports are listed, then each is present with its kind and target"
bound = true
+++

In crates/gob-symbols/src/csharp.rs and qualifier.rs: imports from `using` (namespace), `using static`, alias usings and `global using`, plus implicit usings declared in .csproj (resolved later by the project model story, recorded here as an Unresolved import until then). Calls: invocations with qualifiers (this, base, type, instance), object creation as a call to the constructor, extension methods resolved only where the receiver type is known (stdtypes.rs gains the .NET core types needed), otherwise Unresolved and never clean. Name resolution follows namespaces, nested types and `using` scope; unknown BCL symbols are external, not missing. Graph edges feed reach and COV rules unchanged (graph.rs, view.rs).
