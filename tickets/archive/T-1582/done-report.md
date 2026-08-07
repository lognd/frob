## Done report

COV002's closing-diff grace is now mode-aware, not v1-only.

Added `_store_mode_at_base(root, base)` to src/frob/gates/__init__.py: a
git-object-based historical analog of `frob.tickets._store._store_mode`
(lists `tickets/T-####/ticket.md` blobs at `base` via `git ls-tree`, else
checks for a `tickets.md` blob there) -- needed because the grace must
resolve the ledger mode as it stood BEFORE this diff, which can differ
from the current working-tree mode across a v1 -> v2 migration commit.

`_ledger_states_at_base` now dispatches on it: v1 keeps the unchanged
`git show base:tickets.md` monofile read; v2 (`_ledger_states_at_base_v2`,
new) lists every `tickets/T-####/ticket.md` blob at `base` and reads each
one's `state:` field directly out of its git object via a new
`_ledger_state_from_frontmatter_text` frontmatter-only parser (reuses
`frob.tickets._store`'s `_FRONTMATTER_RE`/`_yaml_loader` rather than a
full `Ticket.model_validate`, so a ticket whose OTHER fields fail schema
validation still resolves its state instead of vanishing from the grace
map).

`_ticket_marker_in_diff_hunk` now checks the CURRENT working tree's store
mode (`frob.tickets._store._store_mode` directly -- this is "did THIS
diff touch this ticket's storage", not a historical question) and, in v2
mode, collapses straight to "does this ticket's own
`tickets/<id>/ticket.md` have a hunk in the diff" -- no block-span
scanning needed, since v2 gives each ticket its own whole file (no other
ticket's content to accidentally match against, unlike v1's shared
monofile).

Before this, a v2 repo's `_ledger_states_at_base` always hit the v1
branch, found no `tickets.md` blob at any base, and returned `{}` for
every diff; `_ticket_marker_in_diff_hunk` scanned a `tickets.md` that
never exists in v2 and always returned False. The T-0590/T-0214 grace
(a ticket created-and-closed, or opened-and-closed, entirely within the
current uncommitted diff) could never apply in a v2 repo, false-firing
COV002 on the exact worktree-agent create-and-close flow the grace exists
to permit -- on every new frob repo's very first close, since T-1553 made
v2 the fresh-repo default.

Added a v2 mirror test class section inside tests/test_gates.py's
TestCoverageGate (5 new tests: done_ticket_covers_own_closing_diff,
grace_covers_ticket_created_and_closed_in_same_diff,
marker_touch_without_state_transition_still_fires,
done_ticket_without_grace_still_fires,
stale_done_ticket_unrelated_touch_still_fires) plus two small test
helpers (`_write_ticket_v2`, `_v2_ticket_file_hunk`), per the ticket's own
instruction not to convert the v1-pinned cases. Kept only the
representative grace/anti-grace shapes (T-0214/T-0320/T-0590's core
cases), not every v1 variant (e.g. T-0564's marker-vs-state-line
distinction has no v2 analog at all, since v2 has no block to scan).

Documented the mode-aware dispatch in docs/modules/gates.md's COV002
decision-log entry (new bullet directly below the existing T-0214 grace
bullet).

Verification:
- pytest tests/test_gates.py::TestCoverageGate: 51 passed (46 pre-existing
  + 5 new v2), no regression
- pytest tests/test_gates.py (whole file): all passed
- frob check --only test --ticket T-1582: 0 errors
- frob check --only coverage --only doclink --only docanchor --only
  archgate --only scope --only prework --only fmt --ticket T-1582: 3
  COV002 + 1 PRE001 (stale sweep, refreshed) + 3 SCOPE001 seen on the
  scoped run -- all attributable to this being a multi-ticket worktree
  (T-1588 landed first in this same branch, still open/in-progress):
  --ticket T-1582 sets active_ticket=T-1582, and `_scope_covers` denies
  ambiguous ties among several OTHER open tickets (T-1588, T-1587, T-1583,
  T-1420) that also scope src/frob/tickets/_store.py/docs/design/
  ledger-v2.md -- confirmed via direct `_scope_covers` call that these
  same 3 files resolve clean once T-1588 (or no ticket) is the active
  ticket; not a defect introduced by this ticket's own changes.
- frob check --land-parity: clean, 0 unscoped errors (the authoritative
  check here, since it evaluates the real merged tree without an
  active-ticket tie-break skew)

### Changed
```
 docs/design/ledger-v2.md                  |  48 ++++++
 src/frob/tickets/_store.py                | 152 +++++++++++++++--
 tests/test_ticket_store_stale_snapshot.py | 268 ++++++++++++++++++++++++++++++
 tickets.md                                | 144 +++++++++++++++-
 4 files changed, 598 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestCoverageGate::test_cov002_v2_done_ticket_covers_own_closing_diff` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov002_v2_grace_covers_ticket_created_and_closed_in_same_diff` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov002_v2_marker_touch_without_state_transition_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov002_v2_done_ticket_without_grace_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov002_v2_stale_done_ticket_unrelated_touch_still_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 1077 warning(s), 797 waived
- error-findings: none (measured, zero errors)
