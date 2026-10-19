+++
id = "01M4052VK08NTRJS6HZZ9B82RZ"
title = "TICK rule: a .github tree on the ticket branch other than the generated nudge is an Error"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:39Z"
updated = "2026-10-19T21:16:24Z"
idempotency_key = "m2-mirror2-tick-github"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-obligations/src/tick_github.rs", "crates/frob-check/src/product.rs", "crates/frob-ledger/src/github_tree.rs", "crates/frob-ledger/src/legacy.rs", "crates/frob-ledger/src/lib.rs", "crates/frob-ledger/src/nudge.rs", "crates/frob/src/explain_cmd.rs", "docs/design/navigation.md", "docs/reference/rules/README.md", "docs/reference/rules/TICK010.md"]

[[links]]
kind = "blocked-by"
target = "01M4052VF61FCR6FQS2KSS1NJG"

[[acceptance]]
text = "Given a ticket branch with any extra file under .github/, when checked, then an Error names the path"
bound = true

[[acceptance]]
text = "Given a nudge workflow whose bytes differ from the generated ones, when checked, then an Error is reported"
bound = true

[[acceptance]]
text = "Given a ticket branch with only the generated nudge, when checked, then no finding is emitted"
bound = true
+++

Implements mirror.md section 3.1 (A TICK rule). The rule id is not assigned in the design (next free is TICK008 in navigation.md 6); assign it here and add it to the rule tables.

On the ticket branch any file under .github/ other than the generated nudge workflow, byte-compared, is an Error.
