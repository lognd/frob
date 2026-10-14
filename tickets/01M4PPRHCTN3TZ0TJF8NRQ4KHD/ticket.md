+++
id = "01M4PPRHCTN3TZ0TJF8NRQ4KHD"
title = "G17b: gob-pattern grammar-level patterns, metavariables, fix templates and GPOL id generation"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 8
reporter = "lognd"
created = "2026-10-12T00:03:52Z"
updated = "2026-10-14T14:53:18Z"
scope = ["crates/gob-pattern/**", "crates/grimble-lints/**"]

[[links]]
kind = "blocked-by"
target = "01M3Z714QT3QXEAJAK9JDDEB70"

[[acceptance]]
text = 'Given pattern = "print($$$ARGS)" and a fix template, when run over a Python fixture, then it fires and the fix rewrites the call'
bound = true
+++

Remainder of ~JDDEB70 split off: metavariable patterns ($X, $$$ARGS) in the target language syntax, follows/precedes/regex combinators, metavariable constraints, fix templates, GPOL id generation, rule-embedded test cases.
