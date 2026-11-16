+++
id = "01M63G1NY275Y890ZD5W1EVN63"
title = "gob-symbols C# graph overflows the stack on using static System.Console"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-29T09:32:21Z"
updated = "2026-11-16T15:33:24Z"
scope = ["crates/gob-symbols/**", "crates/gob-symbols/src/graph/csharp.rs", "crates/gob-symbols/tests/it/csharp_name_only.rs"]

[[acceptance]]
text = "Given a C# call whose receiver type is unproven, when it is resolved by an extension method of the same name, then the edge is May with EdgeBasis::NameOnly"
bound = false

[[acceptance]]
text = "Given a file with using static System.Console, when the graph is built, then it terminates and resolves WriteLine"
bound = false
+++

found while working ~JKKJPTT: one-file C# repo with using static System.Console aborts with stack overflow (reproduced on the baseline release binary)
