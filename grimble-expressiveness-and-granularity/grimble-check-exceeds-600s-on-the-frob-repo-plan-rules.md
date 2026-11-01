+++
id = "01M6A73SAGJNKRZ6JHGYNRQJ09"
title = "grimble check exceeds 600s on the frob repo (PLAN rules regression)"
type = "bug"
category = "in-progress"
priority = "critical"
points = 5
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T00:10:54Z"
updated = "2026-11-01T00:10:58Z"
idempotency_key = "grimble-check-perf-plan-2026-10-31"
scope = ["crates/grimble-bind/**", "crates/grimble/**", "crates/gob-symbols/**"]

[[acceptance]]
text = "grimble check on this repo completes under 30s in a release build (profile budget 4s x 2)"
bound = false

[[acceptance]]
text = "a regression test bounds the PLAN pass work on a large fixture"
bound = false
+++

CI run 41251789959: sibling SIB001 timeout and profile job both fail because grimble check runs >600s. Old release grimble (pre-PLAN) takes 10s; current debug build exceeds 60s. Suspect PLAN001-PLAN010 / PLAN006 passes (commits 1b96d6c675 .. 47831f770f) scaling badly (quadratic over collected rows/subjects). Repro: cargo build -p grimble; time target/debug/grimble check --json. Profile with perf/sampling to find the hot loop.
