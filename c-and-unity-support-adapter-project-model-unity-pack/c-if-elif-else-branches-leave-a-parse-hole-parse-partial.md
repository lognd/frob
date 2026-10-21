+++
id = "01M5F1GHZYYC90BNTF9TGMC3A2"
title = "C#: #if/#elif/#else branches leave a parse hole (PARSE partial)"
type = "bug"
category = "todo"
priority = "medium"
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-21T10:53:31Z"
updated = "2026-10-21T10:53:31Z"
scope = ["crates/gob-symbols/src/csharp.rs"]

[[acceptance]]
text = "Given a C# method with #if/#elif/#else branches, when the file is folded, then it parses Complete or the hole is narrowed to the inactive branch only"
bound = false
+++

Found while working ~01ENJEW: the Platform.cs fixture (return statements in #if WINDOWS / #elif LINUX / #else) folds as Partial with 1 hole, so COV001, DOC001 and AFFECT001 go Unresolved for the whole file.
