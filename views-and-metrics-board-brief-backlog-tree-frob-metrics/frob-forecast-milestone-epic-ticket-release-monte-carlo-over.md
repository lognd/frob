+++
id = "01M48Q2BACGAMNNMM6MWH8W3D7"
title = "frob forecast <milestone|epic|ticket|release>: Monte Carlo over the fitted costs and throughput"
type = "task"
category = "todo"
priority = "medium"
points = 8
parent = "01M48Q294B33TB7C0GSATZRGJB"
reporter = "lognd"
created = "2026-10-06T13:39:52Z"
updated = "2026-10-28T12:57:44Z"
labels = ["no-story"]
scope = ["crates/frob-metrics/**", "crates/frob/**", "crates/frob-release/**"]

[[links]]
kind = "blocked-by"
target = "01M48Q2AQXY69YKK3D2DC05ZWR"

[[acceptance]]
text = "a seeded fixture gives stable P50/P85/P95"
bound = false

[[acceptance]]
text = "release status and ticket show print the forecast line from the same function"
bound = false

[[acceptance]]
text = "Unresolved below min_history"
bound = false
+++

The one forecast (D104): 10k trials over the frob-metrics distributions (bootstrap while samples are few), P50/P85/P95 dates and the dominant risk (dependency chain, capacity, unsized work); release status and ticket show print one line from it; Unresolved with the sample count below min_history.

no-story: internal engineering task in frob-metrics; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
