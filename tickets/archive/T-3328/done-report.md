## Done report

Root cause (answers to the ticket's numbered questions):
1. Yes -- all five fail on the T-3230 refusal path. Captured log:
   'tickets: archive refused -- could not measure live git worktrees under
   <tmp> (git worktree list failed)' / result.err is
   TicketError.ArchiveWorktreeMeasurementFailed.
2. Not applicable to load/contention -- the coordinator's later
   deterministic re-measurement superseded that hypothesis. The five fail
   EVERY time, on an idle box, with no concurrent worktree mutation:
   git worktree list exits 128 under tmp_path because TestArchive's
   fixtures never git-init the directory -- it is not a git repository at
   all, so the read is genuinely unmeasurable, not transiently flaky.
3. git worktree list exits 128 on a non-repo directory deterministically
   (not a transient contention artifact); this ticket's part of the
   incident needed no measurement-side retry logic.

Chosen option: (a), fixture-side -- TestArchive now gets a real (uncommitted
is fine; git worktree list needs no commits) git repo under tmp_path via an
autouse fixture, calling _git_init. T-3230's fail-closed guard is untouched
and unweakened. Option (c) (distinguishing "read failed" from "not a repo"
in _archive.py) is out of this ticket's scope
(src/frob/tickets/_archive.py is currently under T-3442's live lease); if
still wanted, it is a separate follow-up ticket against _archive.py itself.

Sibling surface (T-3230's 28 low-stakes call sites): not re-examined in
this ticket -- doing so requires touching non-test call sites outside this
ticket's tests/test_tickets.py scope. Recommend a follow-up ticket if that
audit is still wanted; not filing one preemptively since it may duplicate
T-3442's in-progress work on the adjacent _archive.py surface.

Evidence:
- tests/test_tickets.py::TestArchive (11/11 pass, node-id run, -p no:xdist)
- tests/test_tickets.py (203/203 pass, full file, -p no:xdist)
- frob test --base main: touched=6 selected, run_selected python exit=0

Filed: none

Gates: frob check --ticket T-3328 --budget 300 -- DRIFT/WAIVE/OPAQUE/
SELFAUDIT/ruff-format failures present are REPO-WIDE per the tool's own
scope-note (not filtered to this ticket) and pre-exist this change;
tests/test_tickets.py itself is ruff-format clean and this ticket's own
gate:SCOPE/gate:PREWORK/gate:COV(diff-scoped)/gate:FMT/gate:AFFECT checks
show no ticket-attributable errors.

### Changed
```
 tests/test_tickets.py         | 67 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-3328/done-report.md | 55 +++++++++++++++++++++++++++++++++++
 tickets/T-3328/ticket.md      | 10 ++++++-
 3 files changed, 131 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets.py::TestArchive::test_idempotent_second_run_moves_nothing` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestArchive::test_moves_done_and_dropped_only` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestArchive::test_load_queue_merges_active_and_archive` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestArchive::test_new_ticket_id_continues_past_archived_max` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestArchive::test_blocked_by_archived_ticket_resolves_closed` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestArchive::test_archive_refuses_when_worktree_list_is_unmeasurable` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestArchive::test_archive_succeeds_in_a_normal_quiet_repo` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 11 error(s), 4104 warning(s), 856 waived
- error-findings: COV001@src/frob/tickets/_scope.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/tickets/_scope.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
