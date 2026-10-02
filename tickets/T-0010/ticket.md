---
id: T-0010
title: 'gob-git: gix reads, ledger commit from a ref tree, CAS ref update'
state: done
kind: feature
origin: agent
created: '2026-10-02'
priority: high
blocked_by:
- T-0007
- T-0009
parent: T-0002
tier: ticket
sprint: null
runs_last: false
milestone: 2.0.0
flavour: null
due: null
rank: null
points: 8
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob-v2-wt/t-0010
branch: t-0010
scope:
- crates/gob-git/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- cmd:cargo nextest run --profile ci -p gob-git exit=0 sha256=e3b0c44298fc
designated_repro_test: null
acceptance:
- text: Given two writers committing different ticket files to the same ref concurrently,
    when both finish, then the ref contains both changes and no commit swept in unrelated
    staged files
  evidence:
  - cmd:cargo nextest run --profile ci -p gob-git exit=0 sha256=e3b0c44298fc
- text: Given a checkout with trunk checked out and a staged unrelated file, when
    commit_paths writes tickets/x, then the staged file is untouched and tickets/x
    is updated in index and worktree
  evidence:
  - cmd:cargo nextest run --profile ci -p gob-git exit=0 sha256=e3b0c44298fc
threat: null
component: gob-git
anchor: false
anchor_reason: null
land_commit: null
---
Implement crates/gob-git per git-io.md sections 1 to 3 and D23. Over gix: discover(repo from cwd, including worktrees and the common dir), head/branch info, status (changed and untracked paths honoring ignores), diff of paths between two trees or tree and worktree, merge_base, rev_parse, blob read at a ref, list worktrees. Ledger write primitive: commit_paths(ref_name, changes: Vec<(path, Option<bytes>)>, message, author from git config) that builds a new tree from the ref's current tree plus the given changes (never from any index), writes the commit, and updates the ref with compare-and-swap, retrying up to [git] cas_retries times by re-reading the ref and re-applying the changes; when the ref is checked out in the current worktree, update the index and worktree files for exactly those paths. Spawn fallbacks via gob-exec only for: worktree add, merge with conflicts, push. Record the git-io.md spawn list as an enum. Tests use temporary repositories created with gix (no git binary) and cover concurrent CAS writers (two threads) proving no lost update.