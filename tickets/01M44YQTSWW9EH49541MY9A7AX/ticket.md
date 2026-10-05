+++
id = "01M44YQTSWW9EH49541MY9A7AX"
title = "DOC rules read C# XML doc comments"
type = "story"
category = "todo"
priority = "medium"
points = 2
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-05T02:36:58Z"
updated = "2026-10-05T02:36:58Z"
idempotency_key = "d94-xmldoc"
scope = ["crates/frob-obligations/src/doc.rs", "crates/gob-symbols/src/csharp.rs", "docs/reference/rules/DOC001.md", "docs/reference/rules/DOC002.md", "crates/frob-check/tests/**"]

[[links]]
kind = "blocked-by"
target = "01M44YQSZ3YEXRDW9RKER9HRA2"

[[acceptance]]
text = "Given a public C# method with a /// <summary> block, when DOC001 runs, then it counts as documented"
bound = false

[[acceptance]]
text = "Given a public C# method with no XML doc comment, when DOC001 runs, then it is flagged with the member's location"
bound = false

[[acceptance]]
text = "Given a member with <inheritdoc/>, when DOC001 runs, then it is accepted"
bound = false
+++

`///` XML doc comments (summary, param, returns, inheritdoc) attach to the member below and feed the DOC rules the way Python docstrings do (see the done task for Python docstrings, ~TCKEFKF, and crates/frob-obligations/src/doc.rs). A member with `<inheritdoc/>` counts as documented. Docs: docs/reference/rules/DOC001.md and DOC002.md mention C# XML docs.
