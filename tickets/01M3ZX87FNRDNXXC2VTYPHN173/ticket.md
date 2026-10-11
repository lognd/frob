+++
id = "01M3ZX87FNRDNXXC2VTYPHN173"
title = "frob profile newcomer|experienced and .frob/profile.toml"
type = "task"
category = "done"
outcome = "done"
priority = "low"
points = 2
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:46Z"
updated = "2026-10-11T01:50:27Z"
idempotency_key = "m2-nav-profile-store"
labels = ["milestone:2", "area:navigation"]
scope = ["crates/frob/src/profile_cmd.rs", "crates/frob/src/lib.rs", "crates/frob/src/product.rs", "crates/frob/tests/profile.rs", "crates/gob-dev/profile.toml", "docs/reference/**", "docs/schemas/**"]

[[acceptance]]
text = "Given a fresh clone, when `frob profile` runs, then it reports newcomer; after `frob profile experienced` it reports experienced and profile.toml records it"
bound = true

[[acceptance]]
text = "Given the third closed ticket by this actor, when the verb finishes, then a one-time note suggests switching and is not repeated"
bound = true
+++

Implements navigation.md section 4.1.

Local, disposable store; default newcomer until the person has closed three tickets in this repository, then a one-time note suggests switching. Presentation only, never a gate.
