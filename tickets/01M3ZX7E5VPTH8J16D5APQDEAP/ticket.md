+++
id = "01M3ZX7E5VPTH8J16D5APQDEAP"
title = "GRL snippet checks that need no parser: GRL006 and GRL008"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:20Z"
updated = "2026-10-12T00:17:44Z"
idempotency_key = "m2-grl-snippets"
labels = ["milestone:2", "area:grl"]
scope = ["crates/gob-plan/src/check/snippets.rs", "crates/gob-plan/src/grl/snippet.rs", "crates/gob-plan/src/check/mod.rs", "crates/gob-plan/tests/grl_errors/main.rs", "crates/gob-plan/src/check/render.rs", "docs/design/grl-spec.md", "crates/gob-plan/tests/grl_errors/cases/GRL006.grl", "crates/gob-plan/tests/snippets.rs"]

[[links]]
kind = "blocked-by"
target = "01M3Z714QT3QXEAJAK9JDDEB70"

[[links]]
kind = "blocked-by"
target = "01M3ZX7DYR7PR1PBCZ7E8Q56WW"

[[acceptance]]
text = "Given a plain snippet in a lang * rule, when compiled, then GRL006 is emitted byte-equal to its golden, and a snippet with as roles is accepted"
bound = true

[[acceptance]]
text = "Given a fix snippet whose metavariable no find snippet binds, when compiled, then GRL008 is emitted byte-equal to its golden with a did-you-mean"
bound = true
+++

Implements grl-spec.md sections 3, 7.3 and 10.

Parse snippets in their tagged language through gob-pattern (G17), select a context-only construct with `as KIND`, lift `as roles` snippets to U, and enforce universality.
