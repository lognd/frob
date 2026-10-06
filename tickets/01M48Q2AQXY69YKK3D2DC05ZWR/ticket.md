+++
id = "01M48Q2AQXY69YKK3D2DC05ZWR"
title = "frob-metrics crate and frob stats: velocity, capacity, points remaining, cost per point"
type = "story"
category = "todo"
priority = "high"
parent = "01M48Q294B33TB7C0GSATZRGJB"
reporter = "lognd"
created = "2026-10-06T13:39:51Z"
updated = "2026-10-06T13:39:51Z"
scope = ["crates/frob-metrics/**", "crates/frob/**", "crates/frob-pm/**", "Cargo.lock"]

[[acceptance]]
text = "a fixture history reproduces known velocity, capacity and percentile values"
bound = false

[[acceptance]]
text = "the log-normal fit recovers parameters from synthetic samples within tolerance"
bound = false

[[acceptance]]
text = "below min_history the figures are Unresolved with the count"
bound = false

[[acceptance]]
text = "cycle velocity remains as a hidden alias printing the same numbers"
bound = false
+++

New crate crates/frob-metrics (pure functions over the fold and git): velocity and capacity (moved from cycle velocity, which becomes a hidden alias), points remaining by milestone and epic, throughput, cycle and lead time percentiles, and cost per point: fit log(cost) = a + b*log(points) on the log scale per cost unit (wall-clock, tokens when present), report median, P85, the geometric spread and b with an interval; below [pm] min_history samples every figure is Unresolved with the sample count, never a number. frob stats [--section ...] renders text and JSON from one value.
