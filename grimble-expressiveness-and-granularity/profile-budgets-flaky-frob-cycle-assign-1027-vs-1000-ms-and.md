+++
id = "01M6BDWBHK4G453AXAW6F0D3DG"
title = "Profile budgets flaky: frob cycle assign (1027 vs 1000 ms) and frob doc remap (5413 vs 5000 ms) breach on CI"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T11:28:25Z"
updated = "2026-11-01T12:12:54Z"
scope = ["crates/gob-dev/profile.toml", "changelog.d/01M6BDWBHK4G453AXAW6F0D3DG.fixed.md"]

[[acceptance]]
text = "profile job passes on 3 consecutive CI runs, by speeding the scenarios up or recalibrating budgets with a recorded reason"
bound = true
+++

Run 41300750419 profile job failed with 2 breaches; the same job passed on run 41298273182. Warm medians are within 3-8 percent of budget. Investigate whether it is runner noise or growth in the repo fixture.
