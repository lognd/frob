+++
id = "01M4052WE1HV1XJVZR6MCADM51"
title = "Property tests: safety S1 to S9 against the fake GitHub"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:39Z"
updated = "2026-10-21T09:54:08Z"
idempotency_key = "m2-mirror2-prop-safety"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/tests/prop_safety.rs", "changelog.d/01M4052WE1HV1XJVZR6MCADM51.added.md"]

[[links]]
kind = "blocked-by"
target = "01M4052W6Q1FAQK362YF6RCGW1"

[[links]]
kind = "blocked-by"
target = "01M4052WAB3H52W92NYG3AS571"

[[acceptance]]
text = "Given random scenarios of human edits, crashes and failures, when runs execute, then S1, S2, S4 and S5 hold after every step"
bound = true

[[acceptance]]
text = "Given the D1 trace (a pasted marker), when replayed, then the map never points ticket B at ticket A's issue"
bound = true

[[acceptance]]
text = "Given a converged state, when a run starts from a fresh map, then it makes no mutation and no ledger commit (S9)"
bound = true

[[acceptance]]
text = "Given a human edit recorded as a proposal, when the proposal is declined and the history is re-read after a crash before the cursor commit (F9), then it is never pending again (S8)."
bound = true

[[acceptance]]
text = "Given a cursor set after a publish or a late create (F2, F3), when a human edit lands before it, then the edit is recorded as a proposal (S2) and proposals never change the tracker (S4)."
bound = false
+++

Implements mirror.md section 3.7 (safety rows) and the model README section 5 (S1 to S9).

proptest scenarios over the adversaries and faults check: no tracker-owned write (S1), cursor soundness (S2), proposals never change the tracker and writes come from the ledger (S4), map integrity (S5), comment bound (S6), run bound (S7), no reopen (S8), idempotence (S9). The model's counterexample traces D1, F2, F3, F4, F7 and F9 are fixed regression cases.
