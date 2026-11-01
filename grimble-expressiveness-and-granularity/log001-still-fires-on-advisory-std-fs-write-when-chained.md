+++
id = "01M6B57E6YDZN09GH4QP8QM8BH"
title = "LOG001 still fires on advisory std::fs::write when chained (.unwrap/.expect/.map_err)"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T08:57:11Z"
updated = "2026-11-01T10:35:06Z"
scope = ["crates/grimble-check/src/log/**,crates/grimble-check/tests/log_rules.rs,changelog.d/**", "crates/grimble-check/src/product.rs", "crates/grimble-check/tests/log_rules.rs", "crates/grimble-check/src/log/**"]

[[acceptance]]
text = "grimble check --only LOG001 reports no std.fs.write* findings (235 today) on this repo"
bound = true

[[acceptance]]
text = "regression test in log_rules.rs covers std::fs::write(..).unwrap()/expect/map_err staying silent"
bound = true
+++

After ~FMRFH43 made rust.fs-write advisory, a fresh grimble release build still reports 235 file findings, all of the chained form std.fs.write.unwrap/expect/map_err (e.g. crates/crunk-spec/src/tells.rs:220). Plain std::fs::write may already be silent. See hit_call/first_match/shadowed_by_advisory in crates/grimble-check/src/log/engine.rs and catalogue.rs; find which path records the chained hit despite the advisory atom.
