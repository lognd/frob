+++
id = "01M3ZX7ZD77ZW385N5B992NX3A"
title = "explain RULE: the full rule page offline, with a pager on a TTY"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3ZX76ZV963F3AXRKJ8F744N"
reporter = "lognd"
created = "2026-10-03T03:34:38Z"
updated = "2026-10-03T03:34:38Z"
idempotency_key = "m2-diag-explain-verb"
labels = ["milestone:2", "area:diagnostics"]
scope = ["crates/gob-cli/src/explain.rs", "crates/frob/src/explain_cmd.rs", "crates/grimble/src/explain_cmd.rs"]

[[acceptance]]
text = "Given `frob explain TODO001` offline, when run, then the embedded rule page prints and matches docs/reference/rules/TODO001.md"
bound = false

[[acceptance]]
text = "Given an unknown id, when run, then a did-you-mean with the closest ids is returned and the exit code is 2"
bound = false
+++

Implements diagnostics.md sections 1.2, 5.1 and 6.

Pages are the generated docs/reference/rules/ID.md embedded in the binary: one source, three outputs. Long text goes through $PAGER then `less -R` on a TTY and prints plainly otherwise.
