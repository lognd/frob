## Done report

Changed: src/frob/refactor/_scan.py::stale_dest_import_ops (new),
src/frob/refactor/_scan.py::scan_references (skips repointing an
ImportFrom node that lives in the symbol's own destination file --
`stale_dest_import_ops` owns that node instead),
src/frob/refactor/_transaction.py::build_plan (calls `stale_dest_
import_ops` and folds its result into `move_ops`, alongside the
existing `carry_forward_ops`)

Root cause confirmed exactly as the ticket described:
`needed_import_ops_for_symbols`'s T-3650 fix only ever guards a NEW
carry-forward import against self-importing a name already resident
at the destination -- it never revisits an EXISTING import statement
a PRIOR split/move already wrote into the destination file, when the
name that OLD import references later moves into that SAME
destination in a LATER call. Left alone, the destination file ends up
both importing the name from its old source module AND defining it
locally: a genuine `ImportError` (partially initialized module) at
real import time, caught only by Verify's `module_import` check
(correctly rolling back, never reaching main) -- `verify_no_self_
import`'s literal same-module AST check misses it, since the stale
import's target module is not the destination file's own module.

Fix: `stale_dest_import_ops(dest_file, moving_names)` parses
`dest_file`'s own top-level `ImportFrom` nodes and strips/deletes any
alias naming something in `moving_names` (the symbols this call is
about to newly define there), building on the same AST-level approach
`_dest_file_bound_names`/T-3650 already established. Wired into
`build_plan` alongside `needed_import_ops_for_symbols`, landing in
`move_ops` (not `reference_ops`) so it applies atomically with the
rest of the move. Also fixed a second-order conflict this surfaced:
`scan_references`'s own repo-wide loop independently found the SAME
stale import (as an ordinary "who imports this symbol" reference site)
and tried to repoint it too, producing a false `OverlappingRewrites`
refusal against the identical line -- `scan_references` now skips a
node that lives in the destination file itself, since `stale_dest_
import_ops` already owns cleaning it up.

Regression test added (`TestGapRegressions::test_gap5_stale_dest_
import_becomes_circular_when_its_own_symbol_later_moves_in`): `move`s
`_worker` (references `_key`, still in `mod.py`) into `helpers.py`
first (using `move`, not `split`, to isolate this ticket's own stale-
import gap from T-3660's separate reexport-shim circular-import gap,
which a `split`'s own shim would additionally trigger in this exact
shape); a later `split` of `_key` itself into that SAME `helpers.py`
must strip the resulting stale import and land cleanly. Confirmed
genuine via `frob ticket evidence --check-repro --base-ref d0152b664`
(the repro test's own standalone commit, before the fix commit).

Evidence: tests/test_refactor.py::TestGapRegressions::
test_gap5_stale_dest_import_becomes_circular_when_its_own_symbol_
later_moves_in (repro verified genuine); full tests/test_refactor.py
suite green (145 passed).

Filed: none. T-3660 (reexport-shim + free-var carry circular import)
is a related but genuinely distinct bug in the same family -- verified
via `frob ticket show` that it is not a duplicate of this ticket (both
still queued, no `duplicate_of` link, different failure shapes: T-3653
is a stale OLD import never revisited, T-3660 is a NEW mutual cycle
between the shim and the free-var carry) -- left queued for this
series' own step 2 slot, per the brief.

Gates: `frob check --ticket T-3653 --only scope` clean (0 errors; 2
pre-existing SCOPE002 warnings remain -- `design/frob.strata` and
`tests/unit/test_arch_srp.py`, the identical pre-existing coverage-
graph cascade T-3656 already left as-is in this same series, unrelated
to this diff's own symbols). `uv run ruff check src tests` clean.
`frob test`/`frob test . --base main` timed out at the 540s foreground
cap on this host (repeated, fleet contention) -- substituted the full
`tests/test_refactor.py` suite run plus the check-repro pass above,
per this series' own verification-budget instruction.

### Changed
```
 src/frob/refactor/_scan.py        | 86 +++++++++++++++++++++++++++++++++++++++
 src/frob/refactor/_transaction.py | 13 +++++-
 tests/test_refactor.py            | 74 +++++++++++++++++++++++++++++++++
 tickets/T-3653/ticket.md          | 21 +++++++++-
 4 files changed, 192 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_refactor.py::TestGapRegressions::test_gap5_stale_dest_import_becomes_circular_when_its_own_symbol_later_moves_in` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 19 error(s), 4233 warning(s), 899 waived
- error-findings: AFFECT001@src/frob/refactor/_transaction.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, DOC007@tests/test_tickets_leases.py, DRIFT001@src/frob/process/_derived_lock.py, DRIFT002@docs/modules/process.md, DRIFT002@tests/test_tickets_leases.py, LARGE001@src/frob/refactor/_scan.py, LARGE001@src/frob/refactor/_verify.py, OPAQUE001@src/frob/app/_config_external.py, PERF003@src/frob/refactor/_scan.py, PRE001@tickets/T-3653, REF002@src/frob/process/_lock_msvcrt.py, REL001@src/frob/__init__.py, SEC110@tests/ticket_land_suite/test_wip.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
