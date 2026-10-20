+++
id = "01M4X91TW6Y91R51R9BETGCVS0"
title = "GRL lowering: function-call terms (resolve, slug) in rule bodies"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-14T13:18:58Z"
updated = "2026-10-14T15:52:10Z"
scope = ["crates/gob-plan/**"]
+++

Found while working ~C6W2KWJ. DOC002 (acceptance corpus ~0HC06TD) uses resolve(l.target.path, l.file) and slug(h.text); convert.rs reports 'this term' unsupported. Covered by none of ~26X4K6K ~8Q9444T ~NVMH9MV ~HZ73YP7. Needs builtin function ops in the IR, codec, validate, executor and tests.
