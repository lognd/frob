## Done report

Implemented the worktree warm pool (part 2 of T-0732): src/frob/scaffold/
_pool.py adds warm_worktree/warm_pool/lease_worktree/refill_pool_async/
pool_status/read_manifest/default_pool_dir, a small JSON manifest under
<git-common-dir>/frob-pool tracking pre-warmed git worktrees (natives
built via an injectable build_fn, defaulting to `make core`). Leasing
merges the base ref into the slot (so it starts current with main) and
kicks off a background daemon thread that re-warms the same slot index
so the pool refills without blocking the caller -- the two halves of the
acceptance criterion.

Re-exported through src/frob/scaffold/__init__.py. Wired into the
Makefile as pool-warm/pool-lease/pool-status targets (N?=4), calling
straight into the Python API since a real `frob scaffold pool` CLI
subcommand would need to touch src/frob/app/scaffold_runner.py and
src/frob/app/config.py -- both outside this ticket's src/frob/scaffold/**
-only scope. Filed T-0877 (refiled from a land-lost worktree draft) for that CLI wiring follow-up.

docs/guides/worktree-pool.md documents the pool directory layout, public
API, Makefile targets, and the testing-safety note (never point tests at
the real clone's own worktrees).

A real bug caught and fixed while writing this: `lease_worktree`'s
default background refill originally reused the exact same path/branch
per slot index, which collided with the just-leased (still on-disk,
still in use) worktree the moment a refill ran -- fixed by giving every
`warm_worktree` call a unique random-token path/branch while keeping
`index` as a stable, human-readable slot number for status display. This
is exactly what tests/system/test_scaffold_pool.py::TestRefillAsync::
test_refill_thread_rewarms_slot exercises.

Scope was mutated once (frob ticket scope --add
"tests/system/test_scaffold_pool*.py") because the original ticket scope
(src/frob/scaffold/**, Makefile, docs/guides/**) had no test-file glob
and pyproject.toml's testpaths is restricted to tests/, so TEST001/
COV001 coverage could not otherwise be satisfied.

### Changed
```
 Makefile                           |  19 +-
 docs/guides/worktree-pool.md       |  76 ++++++
 src/frob/scaffold/__init__.py      |  29 ++-
 src/frob/scaffold/_pool.py         | 512 +++++++++++++++++++++++++++++++++++++
 tests/system/test_scaffold_pool.py | 278 ++++++++++++++++++++
 tickets.md                         | 158 +++++++++++-
 6 files changed, 1067 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/system/test_scaffold_pool.py::TestDefaultPoolDir::test_resolves_under_git_common_dir` (pytest node id, verified passing when recorded)
- `tests/system/test_scaffold_pool.py::TestManifestRoundTrip::test_write_then_read_round_trips` (pytest node id, verified passing when recorded)
- `tests/system/test_scaffold_pool.py::TestWarmWorktree::test_creates_worktree_and_marks_ready` (pytest node id, verified passing when recorded)
- `tests/system/test_scaffold_pool.py::TestWarmWorktree::test_build_failure_marks_not_ready` (pytest node id, verified passing when recorded)
- `tests/system/test_scaffold_pool.py::TestWarmPool::test_fills_pool_to_n_slots` (pytest node id, verified passing when recorded)
- `tests/system/test_scaffold_pool.py::TestWarmPool::test_leaves_existing_ready_slots_alone` (pytest node id, verified passing when recorded)
- `tests/system/test_scaffold_pool.py::TestLeaseWorktree::test_leases_ready_slot_and_removes_it` (pytest node id, verified passing when recorded)
- `tests/system/test_scaffold_pool.py::TestLeaseWorktree::test_empty_pool_returns_err` (pytest node id, verified passing when recorded)
- `tests/system/test_scaffold_pool.py::TestLeaseWorktree::test_lease_merges_base_ref_current` (pytest node id, verified passing when recorded)
- `tests/system/test_scaffold_pool.py::TestRefillAsync::test_refill_thread_rewarms_slot` (pytest node id, verified passing when recorded)
- `tests/system/test_scaffold_pool.py::TestPoolStatus::test_status_reflects_manifest` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
