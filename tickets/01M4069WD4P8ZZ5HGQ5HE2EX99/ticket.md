+++
id = "01M4069WD4P8ZZ5HGQ5HE2EX99"
title = "REL003 changelog fragment required: rule and [pm.done] changelog_fragment close guard"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:57Z"
updated = "2026-10-03T06:12:57Z"
idempotency_key = "m2-rel-rel003"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob-release/src/rel003.rs", "crates/frob-ledger/src/guards.rs", "docs/reference/rules/rel/**"]

[[links]]
kind = "blocked-by"
target = "01M4069W8ECWEPBH6YPAR7X0X0"

[[acceptance]]
text = "Given a diff touching crates/frob with no fragment, when close runs, then it exits 3 with REL003"
bound = false

[[acceptance]]
text = "Given a docs-only diff, when close runs, then it passes"
bound = false
+++

A land touching a product crate or public gob-* item without a fragment is refused (E-LAND-FRAGMENT, REL003); `[pm.done] changelog_fragment` evaluates it at close; tickets of type docs, chore and tests-only diffs are exempt via the ticket's `changelog = none` reason.
