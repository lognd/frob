+++
id = "01M5F1GJ2FJC4CPAM2SDKZXTCN"
title = "C#: partial types are per-file units, not merged across files"
type = "bug"
category = "todo"
priority = "medium"
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-21T10:53:32Z"
updated = "2026-10-21T10:53:32Z"
scope = ["crates/gob-symbols/src/csharp.rs"]

[[acceptance]]
text = "Given a partial class spread over two files, when the graph is built, then members of both parts resolve as members of one type"
bound = false
+++

Found while working ~01ENJEW: Widget declared partial in Widget.Part1.cs and Widget.Part2.cs yields two unrelated units path::Acme.App.Widget; callers of Decorate in Part1 resolve only through the same-file path.
