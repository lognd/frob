+++
id = "01M4MH624WYQHRVHT9B3K1MDJD"
title = "Speculative check: run clippy and fmt for the touched packages in the background on each commit in a ticket worktree, so check --ticket and land find the result ready"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-11T03:47:55Z"
updated = "2026-10-11T03:53:16Z"
scope = ["crates/frob-check/**", "crates/gob-check/src/tools.rs", "crates/gob-check/src/tool_parse.rs", "crates/gob-check/src/options.rs", "crates/gob-check/src/pipeline.rs", "crates/gob-check/src/lib.rs", "crates/gob-check/Cargo.toml", "docs/**"]

[[acceptance]]
text = "a commit in a ticket worktree starts a background check for the touched packages; a later check --ticket on the same tree reads the finished result instead of re-running it, measured by a test that asserts zero tool spawns on the second call"
bound = false
+++

measured: tool stages are 61 percent of a 142 s check. The agent or developer spends minutes editing and testing between commits, so most of that time can be hidden. Results must be keyed by input hashes so a changed tree never reuses a stale pass.
