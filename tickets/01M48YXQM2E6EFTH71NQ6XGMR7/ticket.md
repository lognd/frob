+++
id = "01M48YXQM2E6EFTH71NQ6XGMR7"
title = "Renew leases from check --ticket, test and ticket update, not only evidence add"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-06T15:57:04Z"
updated = "2026-10-17T14:34:13Z"
scope = ["crates/frob-check/**", "crates/frob-tests/src/verb.rs", "crates/frob-tests/Cargo.toml", "crates/frob/src/ticket/write.rs", "crates/frob/tests/it/lease_heartbeat.rs", "crates/frob/tests/it/main.rs"]

[[acceptance]]
text = "Given a leased worktree, when frob check --ticket, frob test or frob ticket update runs there, then the lease renewed_at advances"
bound = true
+++

found while working ~G2Y8E0R: frob_lease::heartbeat(cwd, clock) exists and ticket evidence add calls it; call it from frob check --ticket, frob test and ticket update run in a leased worktree (outside G2Y8E0R scope).
