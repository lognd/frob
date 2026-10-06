+++
id = "01M47SE72KECMSYSGSVZDT6Q6X"
title = "gob-symbols: add a kind field to UseBinding instead of encoding C# import kinds in strings"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-06T05:02:03Z"
updated = "2026-10-06T05:02:03Z"
scope = ["crates/gob-symbols/src/model.rs", "crates/gob-symbols/src/csharp.rs", "crates/gob-symbols/src/graph/csharp.rs"]

[[acceptance]]
text = "Given a C# using static directive, when imports are listed, then the binding carries a typed static kind"
bound = false
+++

found while working JEN2C8Q: C# using kinds (namespace, static, alias, global) are encoded in UseBinding.local and ImportEdge.target strings; a typed kind field on UseBinding (serde default) would replace the convention.
