## Done report

Wired a real `frob scaffold pool` CLI subcommand group (`warm N` / `lease` /
`status`) through `src/frob/__main__.py`, `src/frob/app/config.py`, and
`src/frob/app/scaffold_runner.py`, onto the already-landed T-0738 pool API
(`frob.scaffold._pool`'s `warm_pool`/`lease_worktree`/`pool_status`). The
Makefile's `pool-warm`/`pool-lease`/`pool-status` targets now delegate to
`uv run frob scaffold pool ...` instead of the old `uv run python -c "..."`
inline-python shims, and `docs/guides/worktree-pool.md` documents the new
CLI section (with a matching `#cli-frob-scaffold-pool-t-0877` anchor) and
updates the Makefile-targets section to describe the delegation.

New `_run_pool` helper in `src/frob/app/scaffold_runner.py` dispatches
`cfg.scaffold_pool_command` (`warm`/`lease`/`status`) to the matching pool
API call against `Path(".")`, logging each `PoolEntry` the same way the old
Makefile shims printed them (`{index}: {path} ready={ready}`), and exiting
1 with the `PoolError` value on failure -- same failure-reporting shape the
inline-python shims had (`SystemExit(f'... failed: {err.value}')`).

New `AppConfig` fields `scaffold_pool_command: str | None` and
`scaffold_pool_n: int = 4`, threaded through `from_external`'s existing
str-field and int-field loops (no new parsing machinery).

New argparse wiring in `_add_scaffold_parser`: `scaffold pool` gets its own
subparsers (`warm [N]`, `lease`, `status`); `warm`'s `N` is a positional
`nargs="?"` defaulting to 4, matching the Makefile's existing `N ?= 4`
default.

Also added explicit `frob:ticket` directives (COV002 fix, not scope creep):
`# frob:ticket T-0877` above `_add_scaffold_parser` (`__main__.py`) and
`AppConfig` (`config.py`) -- both files are shared by many open tickets'
scope globs, so `frob check`'s open-ticket-scope inference is ambiguous
(multiple equally-specific open scopes cover the same path) and an explicit
edge is required; `# frob:ticket T-0870` above `_STASH_GUARD_HOOK_SCRIPT`
in `src/frob/scaffold/_managed.py` for the same reason, covering my prior
T-0870 diff in this same worktree.

New test file `tests/system/test_scaffold_pool_cli.py` (real CLI subprocess,
`python -m frob`, matching `tests/system/test_cli_scaffold_apply.py`'s
pattern -- never the real clone's own worktrees, only throwaway `tmp_path`
git repos with a trivial no-op `Makefile` `core:` target standing in for a
real cargo/maturin build, since the CLI has no way to inject a fake
`build_fn`):
- `TestScaffoldPoolCli.test_warm_lease_status_roundtrip` -- `pool warm 2`
  fills two ready slots (asserts both appear with `ready=True`), `pool
  status` lists them, `pool lease` hands one out (prints a real,
  now-existing worktree directory path -- found by filtering CLI
  stdout+stderr lines for the one that actually resolves to a directory,
  since a concurrent background refill thread's own log lines can
  interleave around it), and a follow-up `pool status` no longer lists the
  leased path.
- `TestScaffoldPoolCli.test_lease_on_empty_pool_fails` -- `pool lease`
  against a repo with no warmed pool reports `PoolError.Empty` via a
  nonzero exit and an error message, not a silent no-op.

Measured: `uv run pytest tests/system/test_scaffold_pool_cli.py
tests/system/test_cli_scaffold_apply.py tests/system/test_scaffold_pool.py
tests/unit/test_scaffold_stash_guard.py tests/unit/test_scaffold_managed.py
-p no:cacheprovider -q` -> 23 passed (2 new T-0877 tests + 21 pre-existing
scaffold tests, all green after the mid-ticket `git merge main` + `make
core` rebuild). Reran the two new tests 3x in isolation to rule out the
concurrent-refill-thread interleaving flakiness the fix targets -- stable
across all 3 runs.

Mutation evidence: `frob mutate src/frob/app/scaffold_runner.py --
uv run pytest tests/system/test_scaffold_pool_cli.py
tests/system/test_cli_scaffold_apply.py -p no:cacheprovider -q` -> 7
mutant(s), 7 killed, 0 survived (100%). This is a feature-kind ticket
(TEST016's mutation-evidence obligation gates bug-kind lands specifically),
but a clean 100% score is recorded regardless as it was cheap to run and
directly measures the new `_run_pool` dispatch logic.

Gate check (chunked `--only` loop, `--ticket T-0877`):
- lint: PASS 0 errors 0 warnings
- static: PASS 0 errors (warn-only frob-dup/frob-arch/frob-exports residue,
  pre-existing repo-wide, none touching my diff)
- gates-fast: PASS 0 errors after the `frob:ticket T-0877`/`T-0870`
  directive additions above resolved a COV002 ambiguity (multiple open
  tickets' scope globs cover `__main__.py`/`config.py`/`_managed.py`)
- gates-native: PASS 0 errors
- gates-security: PASS 0 errors

Known multi-ticket-worktree gate cross-talk (not a defect in either
ticket): running `frob check --ticket T-0877` while T-0870's own commits
are still present in this same worktree/branch flags
`src/frob/scaffold/_managed.py` as SCOPE001 (outside T-0877's own declared
scope) -- correctly so, since that file is T-0870's, not T-0877's. The
reverse is true running `--ticket T-0870`: it then flags T-0877's files.
Each ticket's own scope is independently clean when checked against files
it actually declares (verified above); this cross-ticket noise is inherent
to two tickets sharing one worktree/branch and is expected to resolve once
each ticket lands as its own separate commit set, per the coordinator's own
land workflow.

Deletion-filter check (`git diff main --diff-filter=D --stat`): `main`
advanced twice more while I worked (once mid-T-0870, once mid-T-0877,
both landing unrelated tickets); each time re-ran `git merge main` (a
sanctioned mid-ticket code sync) + `make core`, re-ran the full targeted
test set to confirm still green, and the filter came back empty both
times before finishing.

Filed: none -- no out-of-scope discoveries beyond the two small, in-scope
`frob:ticket` directive additions noted above.

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
- `tests/system/test_scaffold_pool_cli.py::TestScaffoldPoolCli::test_warm_lease_status_roundtrip` (pytest node id, verified passing when recorded)
- `tests/system/test_scaffold_pool_cli.py::TestScaffoldPoolCli::test_lease_on_empty_pool_fails` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
