+++
id = "01M3ZZXAZ39410AVYQSRSYVF9C"
title = "gob-directives: an HTML comment inside a markdown code span is scanned as a directive"
type = "bug"
category = "todo"
priority = "low"
points = 1
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T04:21:15Z"
updated = "2026-10-03T04:21:15Z"
idempotency_key = "m2-directive-in-code-span"
labels = ["milestone:2"]
scope = ["crates/gob-directives/**"]

[[acceptance]]
text = "Given a markdown line with an HTML comment holding a frob directive inside backticks, when directives are scanned, then no directive is reported"
bound = false
+++

Found while landing ~2NAP90Y: the inline code span with an HTML comment containing frob:end, in docs/design/doc-consistency.md, raised DSL001 although it is code, not a comment. Markdown code spans and fenced blocks are text; directives inside them must be ignored (fenced blocks already are). Add a fixture with a directive-shaped HTML comment inside an inline code span.
