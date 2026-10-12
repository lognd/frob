+++
id = "01M3Z714QT3QXEAJAK9JDDEB70"
title = "G17a: gob-pattern U-level rules (kind, role, callee, all/any/not/inside/has) and the Doc spike decision"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:25Z"
updated = "2026-10-12T00:07:24Z"
idempotency_key = "m2-pattern"
labels = ["milestone:2"]
scope = ["crates/gob-pattern/**", "crates/grimble-lints/**", "docs/design/rules.md"]

[[links]]
kind = "blocked-by"
target = "01M3Z712DPZN71ZQDS6PXY6QQV"

[[links]]
kind = "blocked-by"
target = "01M3Z713YNM5666B7YFEHPFVKD"

[[links]]
kind = "blocked-by"
target = "01M3ZX7DCQGFR0761QHY8NPAQE"

[[links]]
kind = "blocked-by"
target = "01M3ZX7DMYNTWB3AP04CDMAECH"

[[acceptance]]
text = 'Given a language="*" rule file using kind, callee, not and inside, when run over a Rust and a Python U fixture, then it fires in both from the one file'
bound = true

[[acceptance]]
text = "Given a rule file with a bad id, an unknown key, a grammar-level pattern or an empty rule table, when parsed, then a typed PatternError names the cause"
bound = true
+++

rules.md section 3: the spike that implements ast-grep-core's Doc trait over U terms or decides on the in-house matcher; then declarative rules/*.grl.toml with pattern, metavariables, all/any/not/inside/has, fix; language-specific and IR-level with language=*; GPOL id generation.
