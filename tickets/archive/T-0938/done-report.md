## Done report

T-0715's mandate asked for velocity/burndown derived from ledger
state-transition history, with an explicit "no new storage" constraint.
`tickets.md` retains no transition-history field of its own -- only each
ticket's CURRENT `state` (the same thing `sprint_view.closed` already
reads). The only place a past transition is genuinely recoverable
without adding storage is git's own commit history of `tickets.md`, so
`frob.tickets.sprint_velocity` mines it directly: walk every commit that
ever touched the ledger (oldest-first), read each commit's `tickets.md`
blob once, and for every ticket currently committed to the sprint check
whether its `state:` value flipped INTO `done` relative to the
previously observed commit -- each flip becomes one `SprintTransition`
(ticket id, commit sha, commit timestamp, from/to state).

A `git log -G<anchor>` pickaxe restriction (mine only commits whose diff
touches a ticket's `<!-- ticket:ID -->` anchor line, to avoid walking
the whole shared ledger's history once per ticket) was tried first and
is documented as rejected in the code: the anchor line itself never
changes across a state edit, only the `state:` line inside the block
does, so `-G` on the anchor structurally misses every transition after
a ticket's creation commit. The full walk (one `git log` + one blob read
per commit, shared across every ticket in the sprint rather than
repeated per ticket) is the correct approach, verified by a real test
(`test_transitions_mined_from_history`) that this bug would have
silently failed against.

`SprintVelocityReport` mirrors `SprintReport`'s shape (`sprint`,
`transitions`, `closed`, `remaining`, `total`) but `closed` here is
`len(transitions)` -- a real history-derived count, not a current-state
snapshot -- so a ticket closed and later reopened shows up as two
transitions (`test_reopen_and_reclose_both_counted` verifies this
explicitly, the case `sprint_view.closed` cannot distinguish).

Honest, disclosed limits of the derivation (documented in both the
docstring and docs/modules/tickets.md, not silently papered over): (1)
a ticket's CURRENT `sprint` label selects which tickets get mined --
sprint-reassignment history is not retained, so a ticket closed under a
different sprint label before being reassigned will not appear in
either sprint's velocity; (2) if `tickets.md` was ever squash-merged or
hand-edited such that a `done` transition never appears as its own
commit, that transition is invisible to this mining -- git history is a
lower bound on real transitions, not a completeness guarantee.

Scope note: T-0938's own scope (`src/frob/tickets/**`) covers only the
derivation function and its models. `frob check --only scope` (SCOPE002)
forced widening scope to also include `docs/modules/tickets.md` (every
pre-existing symbol in `src/frob/tickets/__init__.py` with a `frob:doc`
edge into that file trips SCOPE002 the moment the doc file itself is
out of scope) and `tests/test_tickets_velocity.py` (SCOPE001, new test
file) -- both added via `frob ticket scope T-0938 --add`, not a
hand-edit. The `frob ticket sprint velocity <label>` CLI subcommand
(argparse wiring in `src/frob/__main__.py`/`src/frob/app/
ticket_runner.py`) is intentionally NOT built here -- the acceptance
criterion names it as a separate "CLI-surface child ticket" -- and is
not filed as a new ticket by this session since it was not discovered
as unplanned work; it is exactly what the acceptance criterion already
names as out of this ticket's scope.

A real bug was found and fixed during implementation, not shipped: the
first `sprint_velocity` draft used a `git log -G<anchor>` pickaxe filter
per ticket, which a first test run proved silently misses every
transition after a ticket's creation commit (the anchor line never
changes on a state edit). Rewritten to walk the ledger's full commit
history once (shared across every ticket in the sprint) and verified
against `test_transitions_mined_from_history` before that test was
accepted as evidence.

DUP001 also fired against the pre-existing `sprint_view` (95% similar
filter+sort-by-sprint logic) -- fixed by extracting the shared
`_tickets_committed_to(queue, sprint)` helper both functions now call,
rather than waiving the duplication.

### Changed
```
 docs/modules/tickets.md        |  64 +++++++++-
 src/frob/tickets/__init__.py   | 206 +++++++++++++++++++++++++++++--
 src/frob/tickets/_models.py    |  42 ++++++-
 tests/test_tickets_velocity.py | 133 ++++++++++++++++++++
 tickets.md                     | 270 ++++++++++++++++++++++++++++++++++++++++-
 5 files changed, 699 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/test_tickets_velocity.py::TestSprintVelocity::test_transitions_mined_from_history` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestSprintVelocity::test_reopen_and_reclose_both_counted` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestSprintVelocity::test_no_tickets_in_sprint_is_empty_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestSprintVelocity::test_non_git_root_returns_empty_transitions` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestModelsAreFrozen::test_sprint_transition_rejects_field_assignment` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestModelsAreFrozen::test_sprint_velocity_report_rejects_field_assignment` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
