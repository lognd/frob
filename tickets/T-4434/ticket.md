---
id: T-4434
title: 'Native staleness seeder still fails frob_core: untracked-file digest mismatch'
state: in-progress
kind: bug
origin: human
created: '2026-09-11'
priority: critical
parent: T-4410
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_native_staleness.py
- tests/unit/strata/test_native_staleness.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Follow-up to T-4431. T-4431's first post-fix land (T-4429) shows the fix
is partial:

  stale_natives: 1 native(s) stale vs their own source: ['frob_core']

strata_core is now quiet; frob_core still triggers T-1213's full
auto-rebuild.

Root cause (measured in a fresh detached worktree of main): the
byte-identical-content check `_seed_one_native_source_mtime` performs
before backdating a native's source dir mtimes calls
`_source_content_digest(directory)`, which walks via
`frob.excludes.walk_pruned(directory)` -- called with `directory` = the
CRATE SUBDIRECTORY (e.g. `frob-core`), not the repo root. `walk_pruned`
merges in `_load_repo_ignore_globs(root)` using ITS OWN `root` parameter,
so when called with a crate subdirectory it only ever looks for
`<crate>/.gitignore` (which does not exist for either crate) and never
sees the REPO ROOT's `.gitignore`, which is where `uv.lock` is declared
ignored (`.gitignore:14:uv.lock`). The primary checkout has a real,
locally-generated `strata-core/uv.lock` and `frob-core/uv.lock` (from
`uv sync`/`maturin develop`) that a freshly `git worktree add`-checked-out
worktree never has (gitignored, never checked out) -- so the digest
comparison sees an extra untracked file on the repo side for BOTH crates
and should, by this mechanism, refuse to seed BOTH. Reproduced directly
against a fresh detached worktree of main: `seed_worktree_native_source_
mtimes` seeded neither native (both digests diverged on `uv.lock` alone);
in the real T-4429 land only strata_core ended up quiet, which -- given
this mechanism affects both crates identically -- points at incidental
timing (e.g. whether `uv.lock` existed in the primary checkout at the
moment of that specific land) rather than a per-crate code branch, but
the underlying comparison is provably fragile against ANY locally
generated, gitignored file that differs between the primary checkout and
a fresh worktree (uv.lock today; equally exposed to future generated
crate-local files), so it is not really "fixed" for either native, only
sometimes accidentally not exercised.

Fix: compare only GIT-TRACKED content between `repo` and `worktree` for
each native's source dir (`git ls-files` scoped to the crate directory),
instead of a raw filesystem walk that includes locally-generated
untracked files the ignore-glob resolution never actually filters out at
crate-subdirectory granularity. A freshly cut disposable worktree's
checked-out tree for a path is by construction identical to `repo`'s own
TRACKED content for that path whenever `repo` has no uncommitted edit
there -- tracked-file comparison sidesteps the untracked-file noise
entirely rather than trying to extend gitignore resolution to also see
the repo root from a crate subdirectory.