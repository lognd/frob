+++
id = "01M4CXQZEYWB5WNCMFXYCNEE4J"
title = "crunk export uss and csharp: USS custom properties and an engine-free C# token class"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M4CXQTERP5YASZGVEAH6KG4H"
reporter = "lognd"
created = "2026-10-08T04:53:30Z"
updated = "2026-10-08T04:53:30Z"
scope = ["changelog.d/**", "crates/crunk-tokens/**"]

[[acceptance]]
text = "Given tokens with two modes, when exported to uss and csharp, then both files are generated, deterministic, and a golden test pins them"
bound = false
+++

docs/design/crunk.md sections 2 and 7. C# output uses plain floats so an assembly with no engine reference can use it (hullbreach D3 rule).
