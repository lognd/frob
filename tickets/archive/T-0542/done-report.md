## Done report

Investigation found this ticket's fix ALREADY LANDED on main, unattached to
a ticket-workflow closure: commit 5c739693 ("fix(gates): require
unambiguous scope match for COV002", 2026-07-21, already an ancestor of
this worktree's base before any work started this session) rewrote
`_scope_covers` in src/frob/gates/__init__.py exactly per this ticket's
fix direction -- `coverage_gate`/`_cov002`/`_cov002_check_symref` now take
an `active_ticket` parameter that `_scope_covers` checks FIRST; when the
active ticket's own scope covers the file, no ambiguity question is even
asked. Absent an active-ticket match, a NEW `_scope_glob_specificity`
helper scores every open ticket's scope glob by literal-prefix length
against the file, and `_scope_covers` requires a UNIQUE, most-specific
winner among the open tickets whose scope covers the file -- a genuine tie
(two open tickets equally specific over the same path) now returns
`False` (uncovered), requiring an explicit `frob:ticket` edge instead of
silently picking the first/broadest match. This is exactly B10's fix
direction: "prefer the ACTIVE ticket's own scope first, and require a
narrower/more-specific glob match ... when multiple open tickets' scopes
could cover the same file, rather than accepting the first match found."

No code change was needed or made for T-0542 itself -- the implementation,
its doc-anchor comments (`# frob:ticket T-0542` above both new/changed
functions), and three dedicated tests already exist on main:
`TestCov002ScopeCoverage::test_open_ticket_scope_covers_changed_symbol`
(single-scope coverage still works), `test_ambiguous_overlapping_open_scopes_do_not_cover`
(the actual regression-fixing adversarial case: two equally-specific open
tickets both claiming `src/**` no longer silently cover a changed symbol
-- this fails against the pre-fix `_scope_covers`, which accepted ANY
match via `any(...)`), and `test_active_ticket_own_scope_wins_over_a_broader_open_ticket`
(the active-ticket-first half). All three re-run clean this session
(`uv run pytest tests/test_gates.py -k TestCov002ScopeCoverage -q`, 3
passed) and are now bound to T-0542 as evidence.

Ticket state was left `queued` despite the code being on main -- the
commit that implemented it was made directly, outside the ticket
open/evidence/close workflow (no `frob ticket start`/`evidence`/
`done-report`/`close` around it), so the ledger never recorded the
closure. This Done report closes that gap: evidence is bound to the
existing tests, no new code needed.

Gate check caveat: `uv run frob check --ticket T-0542` currently reports
SCOPE001/COV002 findings on `src/frob/tickets/_land.py` and
`tests/test_ticket_land.py` -- these are T-0846's already-committed work
earlier in this same serial-chain worktree (this session works T-0846,
T-0542, T-0590 in order on one branch), which the diff-against-main scan
picks up regardless of which ticket is passed as `--ticket`. They are
T-0846's own scope's responsibility (verified clean under
`frob check --ticket T-0846`), not a T-0542 regression -- T-0542 itself
made no source change. Confirmed via the targeted pytest run above,
since a whole-branch `--ticket T-0542` check cannot cleanly isolate one
ticket's slice of a multi-ticket worktree's cumulative diff.

### Changed
```
 src/frob/tickets/_land.py |  49 ++++++++++++++++++++-
 tests/test_ticket_land.py |  38 ++++++++++++++--
 tickets.md                | 110 +++++++++++++++++++++++++++++++++++++++++++++-
 3 files changed, 191 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestCov002ScopeCoverage::test_open_ticket_scope_covers_changed_symbol` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCov002ScopeCoverage::test_ambiguous_overlapping_open_scopes_do_not_cover` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCov002ScopeCoverage::test_active_ticket_own_scope_wins_over_a_broader_open_ticket` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 6 error(s), 1209 warning(s), 210 waived
