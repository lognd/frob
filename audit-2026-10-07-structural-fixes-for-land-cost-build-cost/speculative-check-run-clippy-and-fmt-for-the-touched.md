+++
id = "01M4MH624WYQHRVHT9B3K1MDJD"
title = "Speculative check: run clippy and fmt for the touched packages in the background on each commit in a ticket worktree, so check --ticket and land find the result ready"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-11T03:47:55Z"
updated = "2026-10-11T16:38:12Z"
scope = ["crates/frob-check/**", "crates/gob-check/src/tools.rs", "crates/gob-check/src/tool_parse.rs", "crates/gob-check/src/options.rs", "crates/gob-check/src/pipeline.rs", "crates/gob-check/src/lib.rs", "crates/gob-check/Cargo.toml"]

[[acceptance]]
text = "a second check on an unchanged tree reuses every recorded Done tool-stage result and spawns no tool process, and changing one input file misses, measured by a unit test counting spawns"
bound = true
+++

measured: tool stages are 61 percent of a 142 s check. The agent or developer spends minutes editing and testing between commits, so most of that time can be hidden. Results must be keyed by input hashes so a changed tree never reuses a stale pass.
Contract: gob-check RunOptions gains a ToolMemo trait (load/store opaque payload per expanded stage); frob-check implements it under <git common dir>/frob/check-results/<key>.json, shared by all worktrees.
Key = blake3(content of every file matching the stage inputs globs + command + expanded args + version_args + min/max version). No process is spawned to compute it.
Only StageResult::Done (pass or parsed findings) is stored; Missing, Failed, Lag and Problem are never cached. A hit is reported as cached in stage timing.
