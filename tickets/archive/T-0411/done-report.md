## Done report

Added a Priority model (LOW/MEDIUM/HIGH/CRITICAL, default MEDIUM) to
Ticket/TicketSpec (frob.tickets._models); `doable`/`doable_blocked` now
sort by priority first (PRIORITY_RANK, highest first) then oldest-created
within a tier, replacing the pure age-only order. New `frob.tickets.
set_priority` (+ `frob ticket priority <id> <level>` CLI, `--priority`
flag on `frob ticket new`) reprioritizes a ticket through the same
single-writer ledger-lock discipline as `mutate_scope`. New TICK004 gate
(frob.gates.tickets_gate) warns (escalating to error at 2x) when a
queued/planned ticket sits past its priority-specific rot-day threshold
(default 3/7/30/90 days for critical/high/medium/low), configurable via
frob.toml's [tickets] table (rot_days_critical/high/medium/low) --
answers "what is rotting" per the ticket's acceptance criteria.

CLI wiring (`--priority`, `frob ticket priority`) required touching
src/frob/__main__.py, src/frob/app/config.py, src/frob/app/ticket_runner.py
-- outside T-0411's declared scope (tickets/, gates/, frob.toml). Followed
the existing T-0453/T-0455 bootstrap precedent (SCOPE001 waived per-file
with a reason citing this and T-0446, which tracks the general
scope-declaration gap for command-adding tickets). Also formally expanded
scope (frob ticket scope --add, not a waive) for the new test file,
docs/modules/tickets.md, and the REL001 version-bump chain (pyproject.toml,
CHANGELOG.md, uv.lock, .frob-release.json, frob.lock) -- version bumped
0.47.0 -> 0.48.0 (additive/minor: new public Priority/PRIORITY_RANK/
set_priority symbols), stamped via `frob release stamp`.

Only remaining `frob check --ticket T-0411` finding is a pre-existing,
unrelated DOC003 in docs/commands/sys.md (OWASP CWE-78 claim gap) --
confirmed untouched by this ticket's diff and present before this work
started; not part of T-0411's scope.

### Changed
```
 .frob-release.json             |   5 +-
 CHANGELOG.md                   |  11 +
 docs/modules/tickets.md        |  16 +-
 frob.lock                      |   5 +
 pyproject.toml                 |   2 +-
 src/frob/__main__.py           |  31 +-
 src/frob/app/config.py         |   6 +
 src/frob/app/ticket_runner.py  |  31 +-
 src/frob/gates/__init__.py     |  84 +++++-
 src/frob/tickets/__init__.py   |  52 +++-
 src/frob/tickets/_models.py    |  30 ++
 tests/test_tickets_priority.py | 142 +++++++++
 tickets.md                     | 671 +++++++++++++++++++++++++++++++++++++++--
 uv.lock                        |   2 +-
 14 files changed, 1057 insertions(+), 31 deletions(-)
```

### Evidence
- `tests/test_tickets_priority.py::TestPriorityRank::test_critical_outranks_low` (pytest node id, verified passing when recorded)
- `tests/test_tickets_priority.py::TestDoablePriorityOrdering::test_high_priority_surfaces_before_older_low_priority` (pytest node id, verified passing when recorded)
- `tests/test_tickets_priority.py::TestDoablePriorityOrdering::test_same_priority_falls_back_to_age` (pytest node id, verified passing when recorded)
- `tests/test_tickets_priority.py::TestSetPriority::test_updates_priority_field` (pytest node id, verified passing when recorded)
- `tests/test_tickets_priority.py::TestTick004QueueRot::test_stale_critical_ticket_flags` (pytest node id, verified passing when recorded)
- `tests/test_tickets_priority.py::TestTick004QueueRot::test_fresh_ticket_does_not_flag` (pytest node id, verified passing when recorded)
