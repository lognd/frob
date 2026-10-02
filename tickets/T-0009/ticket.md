---
id: T-0009
title: 'gob-exec: bounded process pool, spawn allowlist, PROC001'
state: done
kind: feature
origin: agent
created: '2026-10-02'
priority: high
blocked_by:
- T-0007
parent: T-0002
tier: ticket
sprint: null
runs_last: false
milestone: 2.0.0
flavour: null
due: null
rank: null
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob-v2-wt/t-0009
branch: t-0009
scope:
- crates/gob-exec/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- cmd:cargo nextest run --profile ci -p gob-exec exit=0 sha256=e3b0c44298fc
designated_repro_test: null
acceptance:
- text: Given a spec with a 100 ms timeout and a sleeping process, when run, then
    it returns a Timeout outcome within 1 s and the child is gone
  evidence:
  - cmd:cargo nextest run --profile ci -p gob-exec exit=0 sha256=e3b0c44298fc
- text: Given a Rust file outside gob-exec and gob-git that references std::process,
    when PROC001 runs, then it fires with the span
  evidence:
  - cmd:cargo nextest run --profile ci -p gob-exec exit=0 sha256=e3b0c44298fc
threat: null
component: gob-exec
anchor: false
anchor_reason: null
land_commit: null
---
Implement crates/gob-exec per git-io.md section 3 and architecture.md section 9. The only crate besides gob-git allowed to reference std::process. Provide Runner { pool: bounded by [perf] jobs knob (default = available cores) } with run(Spec { program (must be in an allowlist enum: Git, Cargo, Hook, Sibling, Tool), args, cwd, env additions only, timeout, capture }) returning Output { status, stdout, stderr (redacted via gob-log), duration }; a per-process spawn counter and a snapshot test helper that asserts the spawn count for a scenario; a PROC001 rule declared with #[derive(Rule)] that fires on std::process usage outside gob-exec and gob-git (implemented as a text scan over Rust sources for now; it moves to a tree-sitter rule when gob-languages lands). Use tokio-free std threads plus a semaphore. Kill the process group on timeout.