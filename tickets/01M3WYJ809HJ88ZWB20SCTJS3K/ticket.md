+++
id = "01M3WYJ809HJ88ZWB20SCTJS3K"
title = "gob-exec: bounded process pool, spawn allowlist, PROC001"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M3WYJ802ZVWE6E3050EVRCSV"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-02T00:00:03Z"
aliases = ["T-0009"]
labels = ["milestone:2.0.0", "component:gob-exec"]
scope = ["crates/gob-exec/**"]

[[links]]
kind = "blocked-by"
target = "01M3WYJ8070P06AN3YYSFBR9ZG"

[[acceptance]]
text = "Given a spec with a 100 ms timeout and a sleeping process, when run, then it returns a Timeout outcome within 1 s and the child is gone"
bound = false

[[acceptance]]
text = "Given a Rust file outside gob-exec and gob-git that references std::process, when PROC001 runs, then it fires with the span"
bound = false
+++

Implement crates/gob-exec per git-io.md section 3 and architecture.md section 9. The only crate besides gob-git allowed to reference std::process. Provide Runner { pool: bounded by [perf] jobs knob (default = available cores) } with run(Spec { program (must be in an allowlist enum: Git, Cargo, Hook, Sibling, Tool), args, cwd, env additions only, timeout, capture }) returning Output { status, stdout, stderr (redacted via gob-log), duration }; a per-process spawn counter and a snapshot test helper that asserts the spawn count for a scenario; a PROC001 rule declared with #[derive(Rule)] that fires on std::process usage outside gob-exec and gob-git (implemented as a text scan over Rust sources for now; it moves to a tree-sitter rule when gob-languages lands). Use tokio-free std threads plus a semaphore. Kill the process group on timeout.
