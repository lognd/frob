## Done report

Incident: a `tickets.md` conflict resolved by hand (the merge driver not
invoked, or its own hunk shape declined) can keep stale non-terminal
states for tickets main had already closed -- the real T-0537 7-ticket
resurrection.

(a) Investigated `splice_ledger`/`_splice_only_ticket`'s existing
`_newer` state-rank tiebreak (terminal states rank highest) and confirmed
it already makes a terminal->non-terminal regression structurally
impossible for anything that goes THROUGH the splice, whether the
whole-ledger merge (`frob ticket merge-driver`) or the ticket-scoped
splice `frob ticket land` uses. Added a new regression-lock test
(`TestSpliceOnlyTicket::test_whole_ledger_splice_never_regresses_a_sibling_from_done`)
proving this holds today, rather than introducing a second, redundant
guard. Did NOT add a "landing ticket" exception to
`_splice_only_ticket` after prototyping one and finding it broke an
existing regression test (`TestCloseFailAfterMerge`) that depends on the
SAME landing-ticket id race being caught, not bypassed -- disclosed here
rather than silently dropped from the ticket's stated plan.

(b) New TICK005 gate (`src/frob/gates/__init__.py`): after a genuine
two-parent merge commit, diffs the current ledger against the merge's
FIRST parent's tickets.md and ERRORs on any ticket that was DONE/DROPPED
there but is neither DONE nor DROPPED (nor archived) now -- this is the
part that actually catches the incident, since it inspects git history
directly and does not depend on which mechanism (or lack of one)
resolved the conflict. Non-vacuous fixture
(tests/test_gates_tick005.py) reproduces the exact incident shape: a
real two-parent merge commit (built via `commit-tree` for a
deterministic "which side won" outcome) whose tree keeps the stale
queued state for a ticket done on the other parent.

Verified: `uv run pytest tests/test_gates_tick005.py tests/test_ticket_land.py`
(53 passed), `uv run ruff check`/`ruff format --check`/`uv run ty check`
on the touched files (all clean), `uv run frob check --ticket T-0537`
(0 errors, all gates pass).

### Changed
```
 Makefile                    |  29 ++++++
 docs/modules/testing.md     |  11 +++
 src/frob/gates/__init__.py  | 110 +++++++++++++++++++++-
 tests/test_coverage.py      |  65 ++++++++++++-
 tests/test_gates_tick005.py | 218 ++++++++++++++++++++++++++++++++++++++++++++
 tests/test_ticket_land.py   |  35 +++++++
 tickets.md                  |  58 +++++++++++-
 7 files changed, 518 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_hand_resolved_conflict_resurrecting_done_ticket_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_forward_progress_across_a_merge_is_clean` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_non_merge_commit_never_checked` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_archived_ticket_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceOnlyTicket::test_whole_ledger_splice_never_regresses_a_sibling_from_done` (pytest node id, verified passing when recorded)
