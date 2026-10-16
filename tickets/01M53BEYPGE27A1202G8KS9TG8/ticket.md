+++
id = "01M53BEYPGE27A1202G8KS9TG8"
title = "GRL examples: call edges for super:: calls and macro args, unresolved for param calls (COV001 examples 1 and 2)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-16T21:56:32Z"
updated = "2026-10-16T22:51:03Z"
scope = ["crates/gob-symbols/**", "crates/gob-plan/tests/ten_rules/**", "crates/gob-plan/src/examples/**", "crates/gob-ir/src/eval/ctx.rs"]
+++

Follow-up of ~QPX2EJM: test attr lands there. Remaining: rust super::double and assert_eq! args yield no call edges; python cb() on a parameter is not marked unresolved; COV001.grl needs 'not f is test'; then drop COV001 1/2 from KNOWN_ENGINE_GAPS.
