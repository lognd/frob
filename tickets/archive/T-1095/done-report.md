## Done report

Added a cross-worktree single-flight/result-cache layer on top of
T-0322's original per-worktree `run_coverage_wait`, keyed by SOURCE TREE
DIGEST rather than worktree path.

src/frob/testing/_coverage_wait.py:
- `tree_digest(snapshot)`: sha256 hex over the snapshot's tracked
  *.py/*.rs/*.ts/*.tsx file hashes, sorted by path. Two worktrees with
  byte-for-byte identical tracked source produce the identical digest
  regardless of path; any differing file changes it.
- `shared_state_dir(root)`: `<git-common-dir>/frob-coverage-shared/`,
  resolved via the existing `frob.gitio.git_common_dir` primitive -- ONE
  location per clone, shared by every linked worktree, not per worktree.
  Falls back to `<root>/.frob/frob-coverage-shared` outside a git repo.
- `SharedCoverageResult`: the content-addressed cached outcome
  (`ok`/`ran`/`duration_s`/`file_hashes`) one worktree records for a
  digest; `_read_shared_result`/`_write_shared_result` are the cache
  accessors, `_shared_coverage_lock` the per-digest flock serializing
  concurrent worktrees sharing that digest.
- `run_coverage_wait` now checks a digest cache hit before AND after
  acquiring the shared per-digest lock (the second check catches a
  worktree that raced this one and finished while it was blocked),
  adopting a hit via `_adopt_shared_result` (copies the cached
  `file_hashes` into this worktree's OWN local `.frob/coverage-stamp` so
  local staleness checks/gates see it as fresh too) with zero subprocess
  spawned. A miss runs `command` exactly as before
  (`_run_and_settle_shared`, extracted to keep `run_coverage_wait` under
  ARCH001's 60-line threshold) and records the result (success or
  failure -- acceptance [0] promises a shared fresh-OR-FAILED result, not
  success-only) for every other worktree sharing the digest.
- The ORIGINAL per-worktree `.frob/coverage.lock` (`_coverage_lock`,
  `coverage_lock_path`) is unchanged and still wraps the whole call --
  the shared layer composes with it, does not replace it.

Real two-worktree concurrency test (tests/test_coverage_wait_shared.py):
`_two_real_worktrees` creates an actual `git worktree add` pair off one
origin clone. `TestCrossWorktreeSingleFlight.
test_identical_digest_worktrees_share_one_run` runs `run_coverage_wait`
on both worktrees concurrently (two threads, a barrier, a faked but
slow-ish coverage command) and asserts exactly ONE real spawn happened
across both -- acceptance [0]. `test_differing_digest_worktrees_each_
run_independently` mutates one worktree's tracked file first and asserts
BOTH spawn independently -- acceptance [1]. `TestTreeDigest`/
`TestSharedStateDir` cover the two primitives directly.

Extended scope: had to add tests/test_app.py (T-1093/T-0803's own
pre-existing coverage-wait tests) -- run_coverage_wait now also spawns a
`git rev-parse --git-common-dir` subprocess via git_common_dir on every
call, and two of that file's tests monkeypatch subprocess.run with a
strict (cmd, cwd, check) signature that only anticipated the coverage
command itself; widened both fakes to pass unrelated commands through to
the real subprocess.run rather than TypeError-ing on the new spawn.

Pre-existing, unrelated: `frob check` reported two TICK006 phantom-draft
errors (T-1077/T-1084 done reports citing draft ids that died at land)
and INV006 hits on the freshly split gates modules, all predating this
ticket and outside its scope -- repaired inline by the coordinator
(prose repointed at the refiled real ids T-1115/T-1112, split-carried
INV006 waivers added) rather than fixed here. ruff-format also flags
src/frob/gates/__init__.py and tests/test_app_daemon_proxy.py as
needing reformatting; confirmed pre-existing on main (verified against
the root checkout directly), not introduced by this change.

Cut: none against acceptance [0]/[1] -- both are proven by a real
two-worktree test, not a simulated stand-in.

### Changed
```
 docs/modules/testing.md            |  47 +++++-
 src/frob/testing/__init__.py       |   6 +
 src/frob/testing/_coverage_wait.py | 327 ++++++++++++++++++++++++++++++++++---
 tests/test_app.py                  |  22 ++-
 tests/test_coverage_wait_shared.py | 231 ++++++++++++++++++++++++++
 tickets.md                         |   3 +-
 6 files changed, 605 insertions(+), 31 deletions(-)
```

### Evidence
- `tests/test_coverage_wait_shared.py::TestTreeDigest::test_identical_hashes_produce_identical_digest` (pytest node id, verified passing when recorded)
- `tests/test_coverage_wait_shared.py::TestTreeDigest::test_differing_hashes_produce_differing_digest` (pytest node id, verified passing when recorded)
- `tests/test_coverage_wait_shared.py::TestSharedStateDir::test_two_worktrees_of_same_clone_share_one_dir` (pytest node id, verified passing when recorded)
- `tests/test_coverage_wait_shared.py::TestSharedStateDir::test_no_git_falls_back_to_worktree_local` (pytest node id, verified passing when recorded)
- `tests/test_coverage_wait_shared.py::TestCrossWorktreeSingleFlight::test_identical_digest_worktrees_share_one_run` (pytest node id, verified passing when recorded)
- `tests/test_coverage_wait_shared.py::TestCrossWorktreeSingleFlight::test_differing_digest_worktrees_each_run_independently` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
