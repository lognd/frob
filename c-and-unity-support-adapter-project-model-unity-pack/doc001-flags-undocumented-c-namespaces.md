+++
id = "01M5F1GJ558PJREF77B1769XWM"
title = "DOC001 flags undocumented C# namespaces"
type = "bug"
category = "todo"
priority = "medium"
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-21T10:53:32Z"
updated = "2026-10-21T10:53:32Z"
scope = ["crates/frob-obligations/src/doc.rs"]

[[acceptance]]
text = "Given a C# file with documented types in an undocumented namespace, when DOC001 runs, then no namespace finding is raised"
bound = false
+++

Found while working ~01ENJEW: DOC001 warns 'public namespace ... has no doc comment' for every C# namespace, which C# cannot document with XML doc comments. Decide: NotApplicable for namespace symbols.
