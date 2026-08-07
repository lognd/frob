## Done report

## Done report

Changed:
- src/frob/tickets/__init__.py::display_state (new, public)
- src/frob/app/ticket_runner.py::_list
- src/frob/app/ticket_runner.py::_show

`display_state(ticket, root)` is the single reusable overlay function:
ledger `state.value`, decorated `in-progress@<worktree-basename>` when the
ledger still shows QUEUED/PLANNED but a live, non-stale cross-worktree
lease exists for that ticket id. It reuses
`frob.tickets._leases.read_all_leases` verbatim (already drops leases
whose worktree path no longer exists, T-0473/T-0476) -- no second lease
reader was written. A ledger-recorded IN_PROGRESS ticket renders plain
"in-progress", undecorated, since that state is already visible without a
lease. `frob ticket list` and `frob ticket show` both call it; this is
display-only, never written back to the ledger (the T-0633/T-0682
write-through corruption class this ticket explicitly avoids).

`display_state` is exported from `frob.tickets.__all__` for T-0752
(dispatch-visibility) to reuse directly.

Evidence: 4 ids bound via --accepts 0 (the ticket's sole acceptance
criterion):
- tests/test_tickets_lease_overlay.py::TestDisplayState::test_queued_with_live_lease_decorated
- tests/test_tickets_lease_overlay.py::TestDisplayState::test_queued_with_stale_lease_undecorated
- tests/test_tickets_lease_overlay.py::TestDisplayState::test_ledger_in_progress_undecorated
- tests/test_tickets_lease_overlay.py::TestDisplayState::test_no_root_never_decorates

All 4 collected and passed (`uv run pytest tests/test_tickets_lease_overlay.py -p no:cacheprovider -q` -> 4 passed).

Filed: none (no out-of-scope work discovered).

Gates: `uv run frob check --ticket T-0716` clean except:
- gate:REL REL001 (public API minor bump needed) -- NOT fixed here; per
  this repo's agent playbook and the pre-commit guard (T-0731), the
  version line/CHANGELOG.md are never touched by an implementer, only at
  land by the coordinator (`frob release stamp`).
- ruff-format/ty diagnostics reported by the full (non---ticket-scoped)
  check are pre-existing, in src/frob/gates/__init__.py, outside this
  ticket's scope and untouched by this change (confirmed clean for both
  changed files: `uv run ruff check`, `uv run ruff format --check`,
  `uv run ty check` all pass on src/frob/tickets/__init__.py,
  src/frob/app/ticket_runner.py, tests/test_tickets_lease_overlay.py).
- gate:SCOPE SCOPE001 waived x2 (ticket_runner.py -- pre-existing waiver;
  the new test file -- new waiver added, same out-of-scope-test-file
  shape).
- gate:COV all COV002 edges added (frob:ticket directives on _list, _show,
  and every new test symbol); remaining COV warnings are pre-existing,
  unrelated files.

### Changed
```
 src/frob/app/ticket_runner.py       |  10 +-
 src/frob/tickets/__init__.py        |  32 +++++
 tests/test_tickets_lease_overlay.py | 116 ++++++++++++++++
 tickets.md                          | 268 +++++++++++++++++++++++++++++++++++-
 4 files changed, 418 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/test_tickets_lease_overlay.py::TestDisplayState::test_queued_with_live_lease_decorated` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease_overlay.py::TestDisplayState::test_queued_with_stale_lease_undecorated` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease_overlay.py::TestDisplayState::test_ledger_in_progress_undecorated` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease_overlay.py::TestDisplayState::test_no_root_never_decorates` (pytest node id, verified passing when recorded)
