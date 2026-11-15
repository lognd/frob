+++
id = "01M7EXW5BB4V5Q8CRGKC3M3SW5"
title = "grimble-model: for-arm verified_by parses and yields stub Unresolved; fix ticket ~NTVM2T5 record"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:21:21Z"
updated = "2026-11-15T06:21:21Z"
labels = ["no-story"]

[[acceptance]]
text = "A for-arm yields an Unresolved finding naming the rule"
bound = false

[[acceptance]]
text = "~NTVM2T5 gets a note correcting its claim"
bound = false
+++

Audit: ~/projects/frob-audit-grimble-crunk.md L5. verified_by ... for arms parse (crates/grimble-model/src/plan.rs:74-99) but are not judged; UNMODELED_FAILURE_RULE PLAN011 in crates/grimble-bind/src/outcome.rs:19-20 is test-only; ticket NTVM2T5 wrongly claims PLAN011 done. Other unimplemented rules already ticketed: ~ZGWF0B3, ~7HABQ01, ~ZAP2ZD4, ~TZ11GQA, ~4TP3HYX; PM046-049 not yet.
