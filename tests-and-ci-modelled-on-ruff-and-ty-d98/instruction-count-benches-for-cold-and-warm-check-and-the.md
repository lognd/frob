+++
id = "01M5FA5EHT4NSJZP7JVFCZTVFB"
title = "Instruction-count benches for cold and warm check and the other parsers"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-21T13:24:45Z"
updated = "2026-11-12T17:02:23Z"
labels = ["no-story"]
scope = ["crates/gob-plan/benches/**", "crates/frob-parse*/benches/**", "crates/*/Cargo.toml", "changelog.d/**", "crates/frob-check/benches/ic_check.rs", "crates/gob-languages/benches/ic_parse.rs"]

[[acceptance]]
text = "Given cargo dev bench-ic, when run, then a cold and a warm frob-check summary and at least one more parser summary are produced from new crates/*/benches/ic_*.rs benches"
bound = false
+++

follow-up to ~N9G1JSM: add gungraun benches (crates/*/benches/ic_*.rs) for cold and warm frob-check and the remaining parsers; the PR job and cargo dev bench-ic already pick up new summaries
