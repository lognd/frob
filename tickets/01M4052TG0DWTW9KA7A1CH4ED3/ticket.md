+++
id = "01M4052TG0DWTW9KA7A1CH4ED3"
title = "Revert backoff and contested fields (MIR002 Advisory)"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:37Z"
updated = "2026-10-03T05:51:37Z"
idempotency_key = "m2-mirror2-contest"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/contest.rs"]

[[links]]
kind = "blocked-by"
target = "01M4052TC4BVA3JFFCHZX82EWS"

[[acceptance]]
text = "Given the same actor re-applying a field within the window, when reconciled over runs, then reverts occur after 1, 2 and 4 runs and at most once a day"
bound = false

[[acceptance]]
text = "Given three re-applications by the same actor, when reconciled, then the field is contested, no further revert is made and one pending proposal holds the latest value"
bound = false

[[acceptance]]
text = "Given a contested field, when a ledger event on the field or an accept or decline occurs, then the contested state is cleared"
bound = false
+++

Implements mirror.md section 3.4 (Revert wars end; MIR-AUD-06).

A field changed again by a non-mirror actor within the backoff window is reverted after 1, 2, 4 runs, at most once a day. After three re-applications by the same actor or automation the field becomes contested for that issue: no more reverts, one pending proposal with the latest value, listed in mirror status as MIR002 (Advisory). A new ledger event on the field, an accept or a decline clears it.
