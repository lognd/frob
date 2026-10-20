+++
id = "01M42QE3588W2E0GZSZZATPJ15"
title = "Warm graph stage still 0.36 s (target 0.25 s): reduce allocation in call resolution or cache the assembled graph"
type = "task"
category = "todo"
priority = "low"
points = 3
reporter = "lognd"
created = "2026-10-04T05:50:50Z"
updated = "2026-10-04T05:50:50Z"
scope = ["crates/gob-symbols/**"]

[[acceptance]]
text = "Given this repository warm in release, when frob check --timing runs, then the graph stage is under 0.25 s with identical findings"
bound = false
+++

~36ZXTMR parallelized call resolution deterministically (warm graph stage 0.61 s to 0.36 s release). The rest is allocation-heavy resolution (owned by_name keys, cloned candidate lists, a text clone per status edge) and a 70 ms sequential merge. Options measured as promising by that agent: borrow instead of clone in resolution, a global allocator such as mimalloc in frob-cli (scope change), or caching the assembled graph keyed by the per-file digests. Measure before choosing.
