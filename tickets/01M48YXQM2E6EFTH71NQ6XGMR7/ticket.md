+++
id = "01M48YXQM2E6EFTH71NQ6XGMR7"
title = "Renew leases from check --ticket, test and ticket update, not only evidence add"
type = "bug"
category = "todo"
priority = "medium"
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-06T15:57:04Z"
updated = "2026-10-16T16:30:34Z"
scope = ["crates/frob-check/**"]
+++

found while working ~G2Y8E0R: frob_lease::heartbeat(cwd, clock) exists and ticket evidence add calls it; call it from frob check --ticket, frob test and ticket update run in a leased worktree (outside G2Y8E0R scope).
