+++
id = "01M4052WHPPDKMCBA9Y1BM06W5"
title = "Property tests: convergence and no loss under finite edits and faults (L1, L2)"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:40Z"
updated = "2026-10-03T05:51:40Z"
idempotency_key = "m2-mirror2-prop-liveness"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/tests/prop_liveness.rs"]

[[links]]
kind = "blocked-by"
target = "01M4052W6Q1FAQK362YF6RCGW1"

[[links]]
kind = "blocked-by"
target = "01M4052WAB3H52W92NYG3AS571"

[[acceptance]]
text = "Given finite random edits and faults, when runs repeat, then every repository-owned field eventually equals the ledger and stays so"
bound = false

[[acceptance]]
text = "Given a human edit and no further ledger push, when only scheduled runs occur, then the edit is reverted and recorded (F1)"
bound = false

[[acceptance]]
text = "Given every human edit within retained history, when the runs finish, then each is in a proposal or superseded by a later one"
bound = false
+++

Implements mirror.md section 3.7 (convergence rows) and the model README section 5 (L1, L2).

Under finitely many human edits, ledger commits and faults and a budget covering one ticket's reads plus one write, repeated runs reach a state where every repository-owned field equals the ledger and every human edit within retained history is recorded as a proposal or superseded. Includes the F1 trace (no push, scheduled run only).
