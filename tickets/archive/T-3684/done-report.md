## Done report

Reproduced the CI ubuntu flake locally (not in isolation -- required real
background CPU/IO contention: a concurrent `pytest -n 12` full-suite run
plus 6 parallel loop processes hammering
tests/test_tickets_ledger_concurrency.py::TestArchiveRaceWithConcurrentNew,
2 failures in ~150 runs, exact CI traceback). Root cause: `archive_v2`
moves a ticket's whole directory under only that ticket's own
`ticket_lock` (T-1750), never a whole-tree lock, so a concurrent
`load_all`/`load_archive` glob can capture a path just before the move
and then hit a bare `FileNotFoundError` reading it -- `_parse_ticket_file`
had no exception handling at all, so this crashed the calling
`threading.Thread` uncaught (whose exception never reaches the joining
thread), matching the CI symptom exactly (`new_result` left `None`). This
is a genuine product TOCTOU, not the "gitio: git-common-dir lookup
failed" fixture/git-env red herring CI's captured log highlighted (that
path already degrades gracefully via `Result` and is unrelated to the
crash).

Fix: `_parse_ticket_file` now catches `FileNotFoundError` and returns the
new `TicketError.TicketVanishedDuringScan` instead of propagating the raw
exception; `load_all`'s and `load_archive`'s glob-then-parse loops skip
that specific outcome (the ticket was concurrently moved/deleted out of
this point-in-time snapshot -- legitimately absent, not a load failure)
rather than aborting the whole call the way every other parse error still
does. No whole-tree lock added -- that would reintroduce the contention
T-1750's `archive_v2` design deliberately avoided; the fix belongs at the
read-tolerance layer.

Re-verified with the identical 150-run loop-under-load recipe after the
fix: 0 failures. `--check-repro` was attempted and correctly refused
(PASSED_AT_PARENT) -- expected for a statistical flake, since the parent
commit also passes the test most of the time; the loop-under-load
before/after comparison is the real evidence here, not a single diff run.

Also investigated the macOS leg's flake
(tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_refuses_without_force_when_a_live_lease_exists)
under the same load recipe (120 iterations) -- did not reproduce on
Linux. Filed as T-3685, investigation-only, distinct root cause (a fully
sequential single-process test, so not the same load_all glob-then-read
race), no code touched, scope left narrow pending a real macOS
reproduction. T-3639 (renumber_one allocator race) was NOT folded into
this ticket -- its own scope is a different file (`_new_renumber.py`'s
allocator, not `_store.py`'s glob-then-parse loop this ticket fixed);
worth re-checking once T-3684 lands in case it shares the mechanism, but
that check belongs to T-3639 itself.

### Changed
```
 docs/modules/tickets-data-storage.md |  8 ++++++
 src/frob/tickets/_models.py          |  6 +++++
 src/frob/tickets/_store.py           | 48 ++++++++++++++++++++++++++++++++++--
 tickets/T-3684/ticket.md             | 10 ++++++++
 4 files changed, 70 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_tickets_ledger_concurrency.py::TestArchiveRaceWithConcurrentNew::test_concurrent_new_ticket_survives_a_racing_archive` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 11 error(s), 4299 warning(s), 909 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/check/__init__.py, COV003@tests/test_ci_workflow_matrix.py, DEPR006@frob-deprecated-baseline.lock.json, DRIFT001@src/frob/process/_derived_lock.py, DRIFT002@docs/modules/process.md, PERF003@src/frob/refactor/_scan.py, PERF004@src/frob/refactor/_scan_carry.py, PRE001@tickets/T-3684, REL001@src/frob/__init__.py, WAIVE011@frob-ratchet.lock.json
