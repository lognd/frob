---
id: T-2111
title: CrossTicketLeakage refuses on the stale DECLARED scope instead of the live
  lease, so a narrowing that already freed a file still blocks every other ticket
  until land
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- tests/unit/test_land_cross_ticket_leakage.py
- src/frob/tickets/_land_git_ops.py
- tickets/T-2116/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_land_cross_ticket_leakage.py
  reason: repro/coverage test for the T-2111 live-lease-scope fix
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: same COV001/E501 fixup as T-2105's post-land floor
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tickets/T-2116/ticket.md
  reason: same COV001/E501 fixup as T-2105's post-land floor
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_a_narrowing_published_to_the_live_lease_releases_the_file_before_that_tickets_own_land
designated_repro_test: tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_a_narrowing_published_to_the_live_lease_releases_the_file_before_that_tickets_own_land
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Done report

Fix: _find_leaked_tickets/_leaked_hits_for_candidate now resolve a
sibling ticket's SCOPE via _effective_leakage_scope, which prefers a
live cross-worktree lease's recorded scope over the declared ledger
scope whenever a lease exists for that id. This mirrors the T-2095
precedent (the live lease is already the authority _scope_add_conflicts
consults for its own conflict checks) applied to the SECOND place that
answered "which files does this ticket claim" from a different, stale
source. Never unioned with the declared scope -- a union could only
ever keep the stale, broader path alive, defeating the whole point of
narrowing.

Repro: a landing worktree forked from root BEFORE the sibling ticket
was even filed (so _ledger_ticket_at_merge_base returns None for it and
T-1390's "unchanged since fork" exemption cannot mask the bug), the
sibling started with a broad scope and narrowed via the real
mutate_scope entrypoint in a SEPARATE worktree (publishing to the live
lease immediately), then the landing ticket touched a path the OLD
broad scope covered but the NEW live-lease scope released. Watched
FAILED_AT_PARENT against the test-only commit (435842eb0), then fixed;
frob ticket evidence --check-repro confirmed FAILED_AT_PARENT.

Also cleared T-2105's post-land floor as flagged by the coordinator's
re-measurement (both attributable to that land, escaped because the
rapid profile defers the post-land sweep): wrapped the one E501 in
_land.py, and waived COV001 on detect_duplicate_ticket_id_collisions
with a follow-up filed (draft T-2116) to add the real
frob:doc anchor once docs/modules/tickets.md's contention clears --
same precedent as src/frob/tickets/_leases.py::is_effectively_in_progress
(T-2003/T-1999).

### Changed
```
 src/frob/tickets/_land.py                    | 50 +++++++++++++++++---
 src/frob/tickets/_land_git_ops.py            |  6 +++
 tests/unit/test_land_cross_ticket_leakage.py | 70 ++++++++++++++++++++++++++++
 tickets/T-2111/ticket.md                     | 25 +++++++++-
 tickets/T-2116/ticket.md           | 24 ++++++++++
 5 files changed, 167 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_a_narrowing_published_to_the_live_lease_releases_the_file_before_that_tickets_own_land` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: COV001@src/frob/__main__.py, TEST001@src/frob/__main__.py, TICK004@tickets.md
