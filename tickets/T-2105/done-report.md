## Done report

Fix: land() (both v1 _merge_main_into_worktree and v2-mode
_merge_main_into_worktree_v2) now calls
detect_duplicate_ticket_id_collisions before merging main into the
worktree, comparing every tickets/<id>/ticket.md blob directly between
the two sides. An id absent at the true merge-base but present with
genuinely different content on both sides afterward is a duplicate-id
allocation collision (the T-2083/T-2090 field incident shape) and
refuses the land loudly (LandError.MergeConflict) instead of letting
the merge machinery silently keep one side. An id that already existed
at the merge-base (an ordinary sibling-ticket edit conflict, T-1914's
own case) is explicitly excluded so this does not misfire on ordinary
conflicts.

Repro test watched FAILED_AT_PARENT with the guard disabled, then
re-enabled and verified passing (frob ticket evidence --check-repro
confirmed FAILED_AT_PARENT).

Coordinator-observed contention: T-2105's scope narrowing of
docs/modules/tickets.md correctly published to the live lease
side-channel per T-2095 immediately, but the land-time
CrossTicketLeakage check still consults main's stale declared scope --
filed by the coordinator as T-2113 (critical), a second instance of
"one rule, two homes" (T-1966's class), and live evidence for T-1780
(docs/modules/tickets.md contention: six tickets serialized on this
one file in a single wave).

### Changed
```
 src/frob/tickets/_land.py                   |  40 +++-
 src/frob/tickets/_land_git_ops.py           | 133 ++++++++++++++
 tests/unit/test_land_duplicate_ticket_id.py | 272 ++++++++++++++++++++++++++++
 tickets/T-2105/ticket.md                    |  26 ++-
 4 files changed, 465 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_flags_id_with_genuinely_different_content_on_both_sides` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_ignores_the_landing_tickets_own_id` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_ignores_identical_content_on_both_sides` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_ignores_an_id_that_already_existed_at_the_merge_base` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_duplicate_ticket_id.py::TestLandRefusesOnDuplicateTicketIdCollision::test_land_refuses_instead_of_silently_discarding_a_colliding_record` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: COV001@src/frob/tickets/_land_git_ops.py, DUP001@src/frob/tickets/_land_git_ops.py, DUP001@tests/unit/test_land_duplicate_ticket_id.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2105/src/frob/tickets/_land.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2105/src/frob/tickets/_land_git_ops.py, SELFAUDIT001@design
