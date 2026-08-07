## Done report

Changed:
- src/frob/vet/_lockfile.py::find_lockfile -- now resolves `root` directly
  when it is itself a supported lockfile path (uv.lock, package-lock.json,
  pnpm-lock.yaml, Cargo.lock), instead of only ever treating `root` as a
  directory to search under (the "uv.lock -> look for uv.lock/uv.lock" bug).
- src/frob/vet/_scan.py::scan_tree -- derives `project_root` as
  `lockfile.parent` when `root` was itself a file, so config (`frob.toml`)
  and cache lookups still resolve against the project directory rather than
  against the lockfile path itself, after find_lockfile's fix above.
- src/frob/app/vet_runner.py::run -- unchanged in this ticket; verified by
  direct test that its existing `sys.exit(1)` on `scan_tree`'s Err already
  produces a nonzero exit for LockfileUnsupported (bug (b) in the ticket's
  description does not reproduce on this tip -- see Disclosure below).

Bug (a) reproduced and fixed: `frob vet uv.lock` (or any direct lockfile
path) previously logged "no supported lockfile ... under /repo/uv.lock" and
returned Err even though the file existed. Fixed by having `find_lockfile`
check whether `root` itself is a supported lockfile file before falling
back to directory search.

Bug (b) disclosure: on this tip (1210bdb), `frob vet` on an unresolvable
lockfile already exits 1, not 0 -- `src/frob/app/vet_runner.py::_run_scan`
already calls `sys.exit(1)` on `scan_tree`'s Err path. Manually verified
before any code change:
`uv run frob vet /tmp/does/not/exist.lock` -> EXIT=1. This suggests bug (b)
was already fixed in a prior, unrelated change, or the ticket's original
repro predates that fix. Added
`TestVetRunnerLockArg::test_run_unsupp_nonzero` as a permanent regression
lock on this exit-code contract regardless, per the ticket's explicit ask
for a regression test covering it (same vacuous-pass doctrine as T-0184).

Evidence (frob:tests-bound, pytest node ids, collected via
`frob ticket evidence`, cache hit against 2520 node ids):
- tests/test_vet.py::TestLockfileParsers::test_find_lockfile_direct
- tests/test_vet.py::TestLockfileParsers::test_find_lockfile_bad_name
- tests/test_vet.py::TestScanTreeLockArg::test_scan_tree_lockfile_arg
- tests/test_vet.py::TestScanTreeLockArg::test_scan_tree_unsupp_err
- tests/test_vet.py::TestVetRunnerLockArg::test_run_lockfile_arg
- tests/test_vet.py::TestVetRunnerLockArg::test_run_unsupp_nonzero

Full suite: `uv run pytest tests/test_vet.py -p no:testmon` -> 109 passed.

Filed: none.

Gates: `uv run frob check --ticket T-0221` clean -- 0 errors, 10 warnings
(all pre-existing malformed-directive/coverage-source warnings unrelated to
this change), 223 waived (pre-existing repo waivers). `frob check` (full,
unscoped) also 0 errors. `ruff check`/`ruff format --check` both clean
under `uv run` and PATH `ruff`. `ty` clean. Deletion-filter
(`git diff main --diff-filter=D --stat`) empty. `frob-core/Cargo.lock` and
`strata-core/Cargo.lock` touched transiently by `make core`/coverage runs
and reverted before every check/commit -- not part of the final diff.
