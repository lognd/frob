Fixed `frob test --base` leaving stale cargo fingerprints: after the run, files changed against the base get a fresh mtime so the next cargo build in the worktree recompiles them.
