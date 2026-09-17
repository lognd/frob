## Done report

T-4523 -- scaffold pool warm/lease/status: confirm dead or document

Measurement (before any change):

  git grep -n -E 'pool (warm|lease|status)|pool_warm|pool_lease|pool_status' \
      -- src tests docs .claude .github

Result: all three leaves have real callers, not zero references. The
ticket's "Measured 2026-09-16: ... 0 references" premise did not hold
by the time I worked the ticket (T-4523 promoted from a draft filed
earlier; something landed in between that wired/documented this):

- src/frob/_cli_parsers/_core.py:_populate_scaffold_actions registers
  `frob scaffold pool warm/lease/status` as real argparse subcommands
  (lines 59-70), already carrying a T-0877 comment.
- src/frob/app/scaffold_runner.py:_run_pool dispatches all three by
  name onto frob.scaffold._pool's warm_pool/lease_worktree/pool_status,
  and is itself dispatched from the CLI wiring (imported+called, not
  orphaned).
- tests/system/test_scaffold_pool_cli.py (2 tests) and
  tests/system/test_scaffold_pool.py exercise all three end to end via
  real `python -m frob scaffold pool warm/lease/status` subprocess
  calls and the underlying _pool.py functions directly.
- docs/guides/worktree-pool.md already documents the full manifest-file
  API and gives the exact `frob scaffold pool warm/lease/status` CLI
  usage.

The one real gap: docs/commands/scaffold.md (the command reference the
ticket's acceptance criterion names) never mentioned `pool` in its
Usage section -- it only showed list/new. That is the actual defect
here, not dead code.

Decision: document, do not delete. Added a "pool" usage block to
docs/commands/scaffold.md's Usage section, anchored
<!-- frob:describes src/frob/app/scaffold_runner.py::_run_pool --> next
to the existing _add_scaffold_parser anchor, giving the exact
warm/lease/status invocations with the one-line meaning of each
(mirroring docs/guides/worktree-pool.md's existing wording so the two
docs don't drift apart).

No code changes to src/frob/_cli_parsers/_core.py or
src/frob/scaffold/_pool.py: both are in-scope but already correct --
nothing to delete, nothing broken to fix. Only docs/commands/scaffold.md
changed (14 insertions).

Dead-code check (as instructed by the ticket body):

  frob check --only gates --files src/frob/scaffold/_pool.py <WT>

Ran clean of any DEAD001 finding naming _pool.py, warm_pool,
lease_worktree, or pool_status (grepped the full log -- zero hits).
The run's gate-summary line shows 152 errors repo-wide, all pre-existing
and unrelated to this ticket's scope (DUP001/DUP002 in unrelated test
files, MILE001 milestone-scheduling deadlock, PERF004 in doctor.py,
REF002 in vet/_capability_registry, SEC110 in app/config.py, WIRE002 in
dup/_legacy_cs.py) -- none touch _pool.py, _core.py, or
docs/commands/scaffold.md. Not filing new tickets for these: they
pre-exist and are outside this ticket's declared scope to fix.

Evidence: bound acceptance criterion [1] to the existing
tests/system/test_scaffold_pool_cli.py::TestScaffoldPoolCli::test_warm_lease_status_roundtrip
node via `frob ticket evidence T-4523 <node> --accepts 1 --base-ref dev`
(already covers parse+dispatch for warm/lease/status end to end: warm 2
-> status lists 2 -> lease removes one from status and prints a real
worktree path). No new test was needed since nothing was deleted and
the surviving leaves' parse+dispatch coverage already existed.

Verification run:
- ruff check src/frob/_cli_parsers/_core.py src/frob/scaffold/_pool.py
  docs/commands/scaffold.md -- All checks passed!
- ruff format --check src/frob/_cli_parsers/_core.py
  src/frob/scaffold/_pool.py -- 2 files already formatted (both unedited,
  checked only as a scope sanity confirmation)
- ty check: skipped -- no .py file was touched by this change, only
  docs/commands/scaffold.md.
- pytest (serial, -p no:xdist):
  PYTHONPATH=<WT>/src python -m pytest -q -p no:cacheprovider -p no:xdist \
      tests/system/test_scaffold_pool_cli.py
  -> "SUITE-RESULT: exitstatus=0 collected=2 failed=0"

git -C <WT> status --short is empty; HEAD is ac0af4c71
("docs(scaffold): document frob scaffold pool warm/lease/status").

Nothing found out of scope worth filing as a new ticket -- the pre-
existing repo-wide gate errors listed above are already tracked (or are
plainly pre-existing and unrelated to scaffold/pool).

READY.

### Changed
```
 docs/commands/scaffold.md | 14 ++++++++++++++
 tickets/T-4523/ticket.md  |  7 +++++--
 2 files changed, 19 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/system/test_scaffold_pool_cli.py::TestScaffoldPoolCli::test_warm_lease_status_roundtrip` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
