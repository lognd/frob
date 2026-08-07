## Done report

T-1257 built the v2 per-ticket history mining primitive (v2_state_
transitions, src/frob/tickets/_store.py) but never wired it into the
user-facing commands that actually cost time: sprint_velocity and
ticket_flow (both funnel through _mine_done_transitions) stayed
hardcoded to the v1 whole-ledger walk regardless of store mode.

Change: _mine_done_transitions_v1 is the original body, split out
unchanged. _mine_done_transitions_v2 is new: for each queried ticket
id, it calls v2_state_transitions (git log --follow -p over that
ticket's own small file) instead of re-reading the ENTIRE tickets.md
blob at every commit in the ledger's history via _blob_at. _mine_done_
transitions itself now dispatches on _store_mode(root): v2 mode uses
the new fast path, v1/dir mode keeps the original walk.

Measured before/after (synthetic benchmark, this repo is still v1-
mode per LEDGERV1001 so a live frob ticket flow timing on THIS repo
is not yet possible -- see below): 30 tickets each cycling queued ->
in-progress -> done (90 ticket-mutating commits total), querying 3
target ids' done transitions.
  v1 (_mine_done_transitions_v1, whole-ledger walk): 0.597s
  v2 (_mine_done_transitions_v2, per-ticket walk):   0.038s
  ~15.7x faster at this scale; the gap widens with total ledger
  history size since v1's cost is O(all ticket-mutating commits ever)
  regardless of how many ids are queried, while v2's cost is O(sum of
  the QUERIED tickets' own commit counts) -- the actual driver behind
  the ~6 minute frob ticket flow/list --stats cost this ticket exists
  to fix once a repo migrates to ledger v2.

Found while building the v1/v2 parity test (T-1330's own acceptance
criterion, mirroring T-1257's unclosed #3): v2_state_transitions
itself has a real, separate bug -- git's `--follow` copy detection can
misattribute a new ticket's creation commit as a "copy" of a sibling
ticket's file when the two are >=50% byte-similar (routine, since
every v2 ticket.md shares templated frontmatter), and combined with
--reverse this silently truncates the mined history to just that one
commit, dropping every real subsequent transition. This is a defect
in the T-1257 primitive itself, not in this ticket's dispatch wiring;
filed as T-1543 (renumbers at land), out of this ticket's
declared scope (src/frob/tickets/_store.py is not in scope) to fix
here. The parity test in this ticket's own evidence uses distinct
enough ticket content to avoid tripping it, so it is not itself
affected, but a real v2-mode repo could be until the follow-up lands.

### Changed
```
 design/frob.strata                       | 711 ++++++++++++++++---------------
 docs/audits/docs-staleness-2026-07-29.md |  32 +-
 docs/design/ledger-v2.md                 |  10 +
 docs/design/registry/check-coverage.yaml |   6 +-
 docs/modules/tickets.md                  |  18 +
 src/frob/gates/_doclink_docanchor.py     | 125 +++++-
 src/frob/gates/_waive.py                 |   4 +
 src/frob/tickets/_reporting.py           |  17 +-
 src/frob/tickets/_setters.py             |  91 +++-
 src/frob/tickets/_store.py               | 130 +++++-
 tests/test_tickets_velocity.py           | 129 +++++-
 tests/unit/gates/test_doc011.py          | 111 +++++
 tests/unit/test_ticket_store.py          | 123 ++++++
 tickets.md                               | 419 +++++++++++++++++-
 14 files changed, 1538 insertions(+), 388 deletions(-)
```

### Evidence
- `tests/test_tickets_velocity.py::TestSprintVelocityV2Mode::test_v2_mode_mines_via_v2_state_transitions` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestSprintVelocityV2Mode::test_v1_v2_parity_for_equivalent_history` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 609 warning(s), 791 waived
- error-findings: none (measured, zero errors)
