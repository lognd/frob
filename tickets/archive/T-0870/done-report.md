## Done report

The scaffolded `reference-transaction` stash-guard hook (`frob.scaffold._managed`,
T-0574) refused every ref-update touching `refs/stash` unconditionally in a
multi-worktree clone -- including a maintenance `pack-refs` rewrite triggered by
`git gc`, which writes the SAME resolved value, just relocating it from a loose
file to the packed-refs store. That broke `git gc` clone-wide any time it ran
with >1 worktree registered (reproduced live during this dispatch's own `git
merge main`, matching the ticket's observed incident).

Root cause (verified empirically against a throwaway git repo, not assumed):
`git pack-refs` does NOT present a single "old_oid == new_oid" line for
`refs/stash` the way the ticket's own text speculated -- it fires the
reference-transaction hook TWICE: once creating the packed-refs entry
(old=0000...0, new=<existing value>), then once pruning the now-redundant loose
file (old=<existing value>, new=0000...0). So `old_oid == new_oid` within one
line never actually happens and is not a usable signal.

Fix: refuse a `refs/stash` line only when it writes a non-zero value that does
NOT already match what `refs/stash` currently resolves to (checked live via
`git rev-parse -q --verify refs/stash` at "prepared" time, before the loose
ref is unlinked). A maintenance repack's "add to packed-refs" half writes a
value that already matches (the loose ref is still present at that point), so
it passes through; a genuine `git stash push`/update always writes a value
that does not match (no ref yet, or the OLD different entry), so it is still
refused. Pure deletions (new_oid all-zero -- the repack's loose-file prune, or
a real `stash pop`/`drop`) never collide across worktrees and are never
blocked either way.

Both hunks touched are entirely inside `_STASH_GUARD_HOOK_SCRIPT` (a shell
script embedded as a Python string constant) plus adjoining doc comments --
no executable Python logic was changed, so there is nothing for `frob mutate`
to mutate in the diff; confirmed via `frob mutate src/frob/scaffold/_managed.py`
that none of its 19 surviving mutants fall within my diff's hunk ranges (lines
81-91, 124-141, 144, 148-153 -- all comment or shell-script-string content).
The actual shell logic is exercised behaviorally by the two new fixture tests
against real throwaway git repos (never the real clone's own hooks, per the
ticket's own directive).

New test file `tests/unit/test_scaffold_stash_guard.py`:
- `TestStashGuardPackRefs.test_pack_refs_succeeds_with_existing_stash_and_multiple_worktrees`
  -- builds a real tmp_path repo, applies the managed stash-guard hook, creates
  a genuine stash while it's the only worktree, registers a second worktree,
  then asserts `git pack-refs --all` and `git gc` both succeed (returncode 0)
  even with the pre-existing `refs/stash` and 2 worktrees live -- this is the
  exact regression shape from the ticket's observed incident.
- `TestStashGuardPackRefs.test_stash_still_refused_with_multiple_worktrees`
  -- same setup, but with a genuine `git stash push` attempted with 2
  worktrees live; asserts it is still refused (nonzero exit,
  "refusing 'git stash'" + the playbook pointer in stderr) -- proves the
  pack-refs fix did not weaken the original T-0574 guard.

Measured: `uv run pytest tests/unit/test_scaffold_stash_guard.py
tests/unit/test_scaffold_managed.py -p no:cacheprovider -q` -> 9 passed (2 new
+ 7 existing stash-guard/managed-block tests, all still green after the merge
and native rebuild).

Gate check (chunked `--only` loop, `--ticket T-0870`):
- lint: PASS 0 errors 0 warnings
- static: WARN 0 errors, pre-existing repo-wide warnings only (frob-dup,
  frob-arch, frob-exports), none touching my diff
- gates-fast: PASS -- gate:DRIFT 0 errors (after fixing my own frob:tests
  directive to use the graph's dotted `Class.method` qualname form instead of
  pytest's `Class::method` node-id form, per playbook section 5's own wording),
  gate:PRE 0 errors after a `frob ticket sweep T-0870` refresh; the only
  remaining FAIL in this stage (gate:TICK TICK006, referencing T-0738's Done
  report) is pre-existing on `main` (verified via `git diff main -- tickets.md`
  before I touched it), unrelated to this ticket, and resolved on `main`
  itself by the time I merged (commit c2dde825)
- gates-native: PASS 0 errors
- gates-security: PASS 0 errors

Deletion-filter check (`git diff main --diff-filter=D --stat`): initially
showed 2 unrelated files deleted (`src/frob/process/_lock.py`,
`tests/unit/test_process_lock.py`) because `main` had advanced past my
worktree's warm-up merge point while I worked; ran `git merge main` again
(mid-ticket code sync, sanctioned by playbook 1b) and `make core` to rebuild
natives, re-ran the new/changed test files to confirm still green, then the
filter came back empty.

Filed: none -- no out-of-scope discoveries this ticket.

### Changed
```
 Makefile                                |  12 +--
 docs/guides/worktree-pool.md            |  29 +++++---
 src/frob/__main__.py                    |  24 ++++++
 src/frob/app/config.py                  |   9 +++
 src/frob/app/scaffold_runner.py         |  47 ++++++++++++
 src/frob/scaffold/_managed.py           |  38 +++++++++-
 tests/system/test_scaffold_pool_cli.py  | 125 ++++++++++++++++++++++++++++++++
 tests/unit/test_scaffold_stash_guard.py | 101 ++++++++++++++++++++++++++
 tickets.md                              |   6 +-
 9 files changed, 373 insertions(+), 18 deletions(-)
```

### Evidence
- `tests/unit/test_scaffold_stash_guard.py::TestStashGuardPackRefs::test_pack_refs_succeeds_with_existing_stash_and_multiple_worktrees` (pytest node id, verified passing when recorded)
- `tests/unit/test_scaffold_stash_guard.py::TestStashGuardPackRefs::test_stash_still_refused_with_multiple_worktrees` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
