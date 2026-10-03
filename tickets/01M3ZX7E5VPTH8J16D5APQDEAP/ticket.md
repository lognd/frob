+++
id = "01M3ZX7E5VPTH8J16D5APQDEAP"
title = "GRL snippets over gob-pattern: GRL002, as KIND, as roles, GRL006-GRL008"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:20Z"
updated = "2026-10-03T03:34:20Z"
idempotency_key = "m2-grl-snippets"
labels = ["milestone:2", "area:grl"]
scope = ["crates/gob-plan/src/check/snippets.rs", "crates/gob-plan/src/grl/snippet.rs"]

[[links]]
kind = "blocked-by"
target = "01M3Z714QT3QXEAJAK9JDDEB70"

[[links]]
kind = "blocked-by"
target = "01M3ZX7DYR7PR1PBCZ7E8Q56WW"

[[acceptance]]
text = "Given a snippet that does not parse in its language, when compiled, then GRL002 shows the parse tree it got and suggests `as KIND`"
bound = false

[[acceptance]]
text = "Given a plain snippet in a `lang *` rule, an `as roles` snippet holding a node with no universal operator, and a metavariable used in a message but bound by no snippet, when compiled, then GRL006, GRL007 (naming the node) and GRL008 are emitted"
bound = false
+++

Implements grl-spec.md sections 3, 7.3 and 10.

Parse snippets in their tagged language through gob-pattern (G17), select a context-only construct with `as KIND`, lift `as roles` snippets to U, and enforce universality.
