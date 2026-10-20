+++
id = "01M4052TQSK1WXBD9280DDRNM5"
title = "Closing by commit keyword is a tracker edit: revert and propose"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:38Z"
updated = "2026-10-03T05:51:38Z"
idempotency_key = "m2-mirror2-closing-keyword"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/closing.rs"]

[[links]]
kind = "blocked-by"
target = "01M4052TC4BVA3JFFCHZX82EWS"

[[acceptance]]
text = "Given an issue closed by a commit's closing keyword while the ledger says open, when reconciled, then it is reopened and the closure is recorded as a proposal"
bound = false

[[acceptance]]
text = "Given the ledger says done, when the issue is closed by a commit keyword, then nothing is reverted"
bound = false
+++

Implements mirror.md section 3.6 (closing keywords in code-branch commits).

An issue closed by a closing keyword in a code-branch commit while the ledger says open is a tracker edit of the state field: reverted and proposed, never fought silently.
