+++
id = "01M6B0TE2FBPF0HBFSHZQ8Q0K0"
title = "LOG001 precision: is_terminal advisory and exempt fake bins, benches, examples, scripts (phase 2)"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T07:40:11Z"
updated = "2026-11-01T07:40:15Z"
scope = ["docs/design/output-atoms.md,frob.toml,crates/grimble-check/src/log/**,crates/grimble-check/tests/log_rules.rs"]

[[acceptance]]
text = "std.io.stdout.is_terminal and .lock atoms no longer error (writes nothing); fake binaries, benches, examples and scripts are exempt via [log] exempt in frob.toml; grimble check --only LOG001,LOG002 drops by about 40 errors"
bound = false
+++

From the post-phase-1 measurement: ~12 is_terminal/lock sites are false positives; ~31 sites live in gob-testsupport fake bins, benches, examples.
