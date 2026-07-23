# Worktree warm pool (T-0738)

Part 2 of T-0732: pre-create N git worktrees with native extensions
already built and `main` already merged in, so leasing one costs no
`cargo`/`maturin` build and no fresh `git worktree add` on the dispatch
critical path. Part 1 (the shared `CARGO_TARGET_DIR` keyed on the git
common dir, see the Makefile's `core` target) already cut a from-scratch
build from ~34s to ~11s by sharing cargo's own dependency-crate cache
across worktrees of the same clone; this closes the remaining
per-worktree cost (the re-link + `git worktree add` + merge step still
paid by every fresh worktree even with a warm cargo cache) by paying it
ahead of time, in the background, instead of on an agent's own
critical path.

## Pool directory

The pool's manifest and its worktrees live under `<pool_dir>`, which
defaults to `<git-common-dir>/frob-pool` (`default_pool_dir` in
`src/frob/scaffold/_pool.py`) -- the same "shared across every worktree
of the clone" location `frob.tickets._leases` uses for its own lease
side-channel, and outside any single worktree's own tree so it survives
that worktree being removed. `manifest.json` records one entry per
warmed slot: its absolute `path`, its stable `index` (0..N-1, reused
across refills), whether it is `ready`, and when it was created.

## Public API (`frob.scaffold`)

- `warm_pool(repo_root, n, *, pool_dir=None, base_ref="main", build_fn=None)`
  -- ensure the pool holds exactly `n` ready slots; slots already `ready`
  are left untouched, so re-running after a partial fill only warms what
  is missing.
- `lease_worktree(repo_root, *, pool_dir=None, base_ref="main", refill=True, build_fn=None)`
  -- hand out the lowest-index ready slot, merge `base_ref` into it so it
  starts current with `main` (not just current as of its own warm time),
  remove it from the pool's own bookkeeping, and (unless `refill=False`)
  start a background daemon thread that re-warms the same slot index so
  the pool refills without blocking the caller.
- `pool_status(repo_root, *, pool_dir=None)` -- read the manifest as-is,
  for inspection.
- `refill_pool_async(repo_root, index, *, pool_dir=None, base_ref="main", build_fn=None)`
  -- the background-refill mechanism `lease_worktree` uses internally,
  exposed directly so a caller (or a test) can start and `.join()` a
  refill deterministically.

`build_fn`, when given, is called as `build_fn(path) -> Result[None, PoolError]`
in place of the default (`make core` in the new worktree) -- this is how
tests substitute a fast fake build step instead of paying a real cargo
compile per test run; a real caller only needs it to point at a
different build command.

## CLI (`frob scaffold pool`, T-0877)

```
frob scaffold pool warm [N]   # fill the pool to N ready slots (default N=4)
frob scaffold pool lease      # lease one ready slot, print its path, refill in background
frob scaffold pool status     # print the current manifest
```

Thin wrappers (`src/frob/app/scaffold_runner.py`'s `_run_pool`) over the
same `warm_pool`/`lease_worktree`/`pool_status` API above, using the
default `pool_dir`/`base_ref` in every case -- a caller needing a
non-default pool directory or base ref still goes through the Python API
directly.

## Makefile targets

```
make pool-warm N=4      # fill the pool to N ready slots (default N=4)
make pool-lease         # lease one ready slot, print its path, refill in background
make pool-status        # print the current manifest
```

These now delegate straight to the CLI above (`uv run frob scaffold pool
...`) -- no inline python left in the Makefile. Not currently wired into
`frob worktree sweep` (`src/frob/tickets/_leases.py`) either -- sweeping a
leased-then-abandoned pool worktree still goes through that existing
mechanism unchanged, since a leased pool slot is, from that point on, an
ordinary dispatched-agent worktree.

## Safety notes for testing this module

Never point a test at the real clone's own `.claude/worktrees` tree or
its real git common dir -- `warm_pool`/`lease_worktree` really do run
`git worktree add`/`git merge`, and a test asserting against a throwaway
`tmp_path` fixture repository (a small git-inited repo with one commit)
is the only safe way to exercise this without ever touching an existing,
possibly-live worktree of the actual `frob` clone.
