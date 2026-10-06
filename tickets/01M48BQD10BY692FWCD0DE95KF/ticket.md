+++
id = "01M48BQD10BY692FWCD0DE95KF"
title = "Bump rustls past RUSTSEC-2026-0285 (frob-gh pins =0.23.43)"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-06T10:21:39Z"
updated = "2026-10-06T10:21:39Z"
scope = ["crates/frob-gh/Cargo.toml", "deny.toml"]

[[acceptance]]
text = "frob-gh no longer pins rustls =0.23.43 and the RUSTSEC-2026-0285 ignore in deny.toml is removed"
bound = false
+++

found while working ~19X37CZ: cargo deny reports RUSTSEC-2026-0285 on rustls 0.23.43; the fix is 0.23.45 but crates/frob-gh pins =0.23.43. Bump the pin, then delete the ignore entry in deny.toml.
