+++
id = "01M4Y3NMYTG2ZWEDGMWEM9910X"
title = "Wire Profile::teach_for to [ui] teach and .frob/seen.toml"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-14T21:04:10Z"
updated = "2026-10-20T13:51:39Z"
scope = ["crates/frob/src/profile.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7ZNF2PJ2E8WJH3CSCDFK"

[[acceptance]]
text = "Given teaching state from ~3CSCDFK, when a newcomer runs check, then the profile teach count comes from seen.toml and [ui] teach"
bound = false
+++

Follow-up of ~77EBEJP: Profile::teach_for exists as a pure function; connect it to the teaching state built by ~3CSCDFK once that lands.
