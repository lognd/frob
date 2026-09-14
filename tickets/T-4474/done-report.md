## Done report

T-4474: passenger detector now compares normalized directive identity instead of exact diff-line text, exempting move/rewrap and refusing new/reworded directives; refusal log distinguishes NEW vs MOVED ids.

### Changed
```
 src/frob/tickets/_land.py                    | 450 +++++++++++----------------
 src/frob/tickets/_land_passenger_identity.py | 119 +++++++
 tests/unit/test_land_cross_ticket_leakage.py | 131 +++++++-
 tickets/T-4474/ticket.md                     |  41 +++
 4 files changed, 465 insertions(+), 276 deletions(-)
```

### Evidence
- `tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_moved_and_rewrapped_directive_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_refusal_message_distinguishes_new_from_moved_ids` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_brand_new_directive_still_refuses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 11 error(s), 4915 warning(s), 1079 waived
- error-findings: AFFECT001@src/frob/tickets/_land.py, AFFECT001@src/frob/tickets/_land_passenger_identity.py, DRIFT001@src/frob/doctor.py, E501@/home/logan/projects/frob/.claude/worktrees/t-4474/src/frob/tickets/_land.py, E501@/home/logan/projects/frob/.claude/worktrees/t-4474/src/frob/tickets/_land_passenger_identity.py, FMT001@src/frob/tickets/_land_passenger_identity.py, FMT001@tests/unit/test_land_cross_ticket_leakage.py, I001@/home/logan/projects/frob/.claude/worktrees/t-4474/src/frob/tickets/_land.py, LANDFMT001@Would reformat: [1mtests/unit/test_land_cross_ticket_leakage.py[0m, PERF004@src/frob/tickets/_land.py, REF002@docs/design/macos-portability.md
